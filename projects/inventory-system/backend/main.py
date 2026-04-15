#!/usr/bin/env python3
"""
Veratori Inventory System - Main Entry Point
Production-ready computer vision system for Jetson Orin Nano

Initialization Order:
1. Config Loader - Load system configuration
2. Logging System - Setup centralized logging
3. Database Connection - Initialize SQLite persistence
4. Detector - Initialize YOLO with mock fallback
5. Analytics Engine - Initialize analytics processor
6. Web Server - Start HTTP/WebSocket server
"""

import asyncio
import logging
import logging.handlers
import signal
import sys
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

# Add backend directory to path for imports
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RUN_DIR = PROJECT_ROOT / 'run'
DATA_DIR = PROJECT_ROOT / 'data'
EXPORTS_DIR = RUN_DIR / 'exports'
RESTOCK_PHOTOS_DIR = PROJECT_ROOT / 'restock_photos'
MODELS_DIR = PROJECT_ROOT / 'models'
CONFIG_PATH = PROJECT_ROOT / 'config' / 'config.yaml'
SYSTEM_LOG_PATH = RUN_DIR / 'system.log'
DB_PATH = DATA_DIR / 'inventory.db'


def setup_directories():
    """Create required directories for demo data path."""
    for directory in [RUN_DIR, DATA_DIR, EXPORTS_DIR, RESTOCK_PHOTOS_DIR, MODELS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    """
    Setup centralized logging system.
    Logs to both console and run/system.log with rotation.
    """
    setup_directories()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler for system.log
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            SYSTEM_LOG_PATH,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file handler: {e}")

    return logging.getLogger(__name__)


# Initialize logging first
logger = setup_logging()

# Try to load environment variables from .env
try:
    from dotenv import load_dotenv
    if load_dotenv():
        logger.info("Loaded environment variables from .env")
except ImportError:
    logger.debug("python-dotenv not installed, skipping .env loading")

# Import local modules after logging is setup
from camera import USBCamera
from detector import YOLODetector
from inventory import InventoryTracker
from inventory_persistent import PersistentInventoryTracker
from server import VideoStreamServer, StreamManager

# Try to import optional modules
try:
    from analytics import AnalyticsProcessor
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    logger.warning("Analytics module not available")


class InventorySystem:
    """
    Main application class
    Coordinates all components and manages lifecycle

    Demo-safe design:
    - All components initialize with graceful fallbacks
    - No uncaught exceptions
    - No dependency on external services
    - Suitable for edge deployment (Raspberry Pi 4, Jetson Orin Nano)
    """

    def __init__(self, config_path: Path):
        """
        Initialize inventory system

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = config_path
        self.start_time = datetime.now(timezone.utc)

        # Step 1: Load configuration
        logger.info("=" * 60)
        logger.info("INITIALIZATION PHASE 1: Configuration")
        logger.info("=" * 60)
        self.config = self.load_config()

        # Components (initialized in order)
        self.camera: Optional[USBCamera] = None
        self.detector: Optional[YOLODetector] = None
        self.inventory_tracker: Optional[InventoryTracker] = None
        self.analytics_processor = None
        self.server: Optional[VideoStreamServer] = None
        self.stream_manager: Optional[StreamManager] = None
        self.db_connection: Optional[sqlite3.Connection] = None

        # System state
        self.shutdown_event = asyncio.Event()
        self.initialization_status: Dict[str, Any] = {
            'config': False,
            'database': False,
            'detector': False,
            'analytics': False,
            'camera': False,
            'server': False,
            'stream': False
        }
        self.initialization_errors: Dict[str, str] = {}
        
    def load_config(self) -> dict:
        """
        Load configuration from YAML file
        
        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.info("Using default configuration")
            return self.get_default_config()
    
    def get_default_config(self) -> dict:
        """
        Get default configuration
        
        Returns:
            Default configuration dictionary
        """
        return {
            'camera': {
                'index': 0,
                'width': 1280,
                'height': 720,
                'fps': 30
            },
            'detector': {
                'model_path': 'models/best.pt',
                'conf_threshold': 0.25,
                'iou_threshold': 0.45,
                'imgsz': 640,
                'device': '0',
                'half': True
            },
            'inventory': {
                'smoothing_window': 10,
                'smoothing_method': 'median',
                'enable_persistence': True,
                'snapshot_interval': 5.0,
                'expiration_days': 5,
                'sales_confirm_intervals': 2,
                'sales_min_delta': 1,
                'sales_cooldown_seconds': 10.0
            },
            'alerts': {
                'enable_alerts': True,
                'alert_confirm_intervals': 2,
                'alert_cooldown_seconds': 3600.0,
                'low_stock_thresholds': {
                    'mango': 3,
                    'watermelon': 2,
                    'pineapple': 2,
                    'passion fruit': 2,
                    'maui custard': 2,
                    'lemon cake': 2
                }
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8080
            },
            'stream': {
                'target_fps': 30
            }
        }
    
    def initialize_components(self) -> bool:
        """
        Initialize all system components in proper order.
        Demo-safe: all components have graceful fallbacks.

        Initialization Order:
        1. Database Connection
        2. Detector (YOLO with mock fallback)
        3. Analytics Engine
        4. Camera (optional)
        5. Inventory Tracker
        6. Web Server
        7. Stream Manager

        Returns:
            True if core components initialized (server must work)
        """
        try:
            # ================================================================
            # PHASE 2: Database Connection
            # ================================================================
            logger.info("=" * 60)
            logger.info("INITIALIZATION PHASE 2: Database")
            logger.info("=" * 60)

            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                self.db_connection = sqlite3.connect(
                    str(DB_PATH),
                    check_same_thread=False,
                    timeout=30
                )
                self.db_connection.execute("PRAGMA journal_mode=WAL")
                self.db_connection.execute("PRAGMA synchronous=NORMAL")
                self.initialization_status['database'] = True
                logger.info(f"Database connected: {DB_PATH}")
            except Exception as e:
                logger.warning(f"Database connection failed: {e} - using in-memory fallback")
                self.db_connection = sqlite3.connect(':memory:')
                self.initialization_errors['database'] = str(e)

            # ================================================================
            # PHASE 3: Detector Initialization (with mock fallback)
            # ================================================================
            logger.info("=" * 60)
            logger.info("INITIALIZATION PHASE 3: Detector (YOLO/Mock)")
            logger.info("=" * 60)

            detector_config = self.config.get('detector', {})

            # Resolve model path - try multiple locations
            model_path = Path(detector_config.get('model_path', 'models/best.pt'))
            if not model_path.is_absolute():
                model_path = PROJECT_ROOT / model_path

            # Resolve secondary model path (for custom Coke model)
            secondary_model_path = detector_config.get('secondary_model_path')
            if secondary_model_path:
                secondary_model_path = Path(secondary_model_path)
                if not secondary_model_path.is_absolute():
                    secondary_model_path = PROJECT_ROOT / secondary_model_path
                secondary_model_path = str(secondary_model_path)

            self.detector = YOLODetector(
                model_path=str(model_path),
                secondary_model_path=secondary_model_path,
                conf_threshold=detector_config.get('conf_threshold', 0.25),
                iou_threshold=detector_config.get('iou_threshold', 0.45),
                imgsz=detector_config.get('imgsz', 640),
                device=detector_config.get('device', '0'),
                half=detector_config.get('half', True),
                enable_mock_fallback=True  # Always enable for demo safety
            )

            # Load detector - will auto-fallback to mock if needed
            if self.detector.load():
                self.initialization_status['detector'] = True
                mode = "MOCK" if self.detector.is_mock() else "YOLO"
                logger.info(f"Detector initialized in {mode} mode")
                if self.detector.is_mock():
                    logger.warning(f"Mock mode reason: {self.detector.mock_reason}")
                    self.initialization_errors['detector'] = self.detector.mock_reason
            else:
                # This should never happen with mock fallback enabled
                logger.error("Detector failed to initialize even with mock fallback")
                return False

            # Warmup detector
            self.detector.warmup(num_iterations=5)
            logger.info(f"Detector info: {self.detector.get_info()}")

            # ================================================================
            # PHASE 4: Analytics Engine
            # ================================================================
            logger.info("=" * 60)
            logger.info("INITIALIZATION PHASE 4: Analytics Engine")
            logger.info("=" * 60)

            try:
                if ANALYTICS_AVAILABLE:
                    self.analytics_processor = AnalyticsProcessor(
                        db_path=DB_PATH,
                        config=self.config
                    )
                    self.initialization_status['analytics'] = True
                    logger.info("Analytics engine initialized")
                else:
                    logger.warning("Analytics module not available")
            except Exception as e:
                logger.warning(f"Analytics initialization failed: {e}")
                self.initialization_errors['analytics'] = str(e)

            # ================================================================
            # PHASE 5: Camera (optional)
            # ================================================================
            logger.info("=" * 60)
            logger.info("INITIALIZATION PHASE 5: Camera")
            logger.info("=" * 60)

            camera_config = self.config.get('camera', {})

            if not camera_config.get('enabled', True):
                logger.info("Camera disabled in configuration")
                self.camera = None
            else:
                try:
                    self.camera = USBCamera(
                        camera_index=camera_config.get('index', 0),
                        width=camera_config.get('width', 1280),
                        height=camera_config.get('height', 720),
                        fps=camera_config.get('fps', 30)
                    )

                    if self.camera.open():
                        self.initialization_status['camera'] = True
                        logger.info(f"Camera initialized: {self.camera.get_info()}")
                    else:
                        logger.warning("Camera failed to open - running without camera")
                        self.camera = None
                except Exception as e:
                    logger.warning(f"Camera initialization failed: {e}")
                    self.camera = None
                    self.initialization_errors['camera'] = str(e)

            # ================================================================
            # PHASE 6: Inventory Tracker
            # ================================================================
            logger.info("=" * 60)
            logger.info("INITIALIZATION PHASE 6: Inventory Tracker")
            logger.info("=" * 60)

            inventory_config = self.config.get('inventory', {})
            alerts_config = self.config.get('alerts', {})
            enable_persistence = inventory_config.get('enable_persistence', True)

            try:
                if enable_persistence:
                    self.inventory_tracker = PersistentInventoryTracker(
                        smoothing_window=inventory_config.get('smoothing_window', 10),
                        smoothing_method=inventory_config.get('smoothing_method', 'median'),
                        class_names=self.detector.class_names,
                        snapshot_interval=inventory_config.get('snapshot_interval', 5.0),
                        expiration_days=inventory_config.get('expiration_days', 5),
                        enable_persistence=True,
                        sales_confirm_intervals=inventory_config.get('sales_confirm_intervals', 2),
                        sales_min_delta=inventory_config.get('sales_min_delta', 1),
                        sales_cooldown_seconds=inventory_config.get('sales_cooldown_seconds', 10.0),
                        enable_alerts=alerts_config.get('enable_alerts', True),
                        low_stock_thresholds=alerts_config.get('low_stock_thresholds'),
                        alert_confirm_intervals=alerts_config.get('alert_confirm_intervals', 2),
                        alert_cooldown_seconds=alerts_config.get('alert_cooldown_seconds', 3600.0)
                    )
                    logger.info("Inventory tracker initialized with persistence")
                else:
                    self.inventory_tracker = InventoryTracker(
                        smoothing_window=inventory_config.get('smoothing_window', 10),
                        smoothing_method=inventory_config.get('smoothing_method', 'median'),
                        class_names=self.detector.class_names
                    )
                    logger.info("Inventory tracker initialized (no persistence)")
            except Exception as e:
                logger.error(f"Inventory tracker failed: {e}")
                # Fallback to basic tracker
                self.inventory_tracker = InventoryTracker(
                    smoothing_window=10,
                    smoothing_method='median',
                    class_names=self.detector.class_names
                )
                self.initialization_errors['inventory'] = str(e)

            # ================================================================
            # PHASE 7: Web Server
            # ================================================================
            logger.info("=" * 60)
            logger.info("INITIALIZATION PHASE 7: Web Server")
            logger.info("=" * 60)

            server_config = self.config.get('server', {})
            frontend_dir = PROJECT_ROOT / 'apps' / 'web-frontend'

            self.server = VideoStreamServer(
                host=server_config.get('host', '0.0.0.0'),
                port=server_config.get('port', 8080),
                frontend_dir=frontend_dir
            )

            # Expose components to server
            self.server.set_camera(self.camera)
            self.server.set_detector(self.detector)
            self.server.set_inventory_tracker(self.inventory_tracker)

            # Set system info for API responses
            self.server.set_system_info({
                'start_time': self.start_time.isoformat(),
                'detector_mode': self.detector.get_mode(),
                'initialization_status': self.initialization_status,
                'initialization_errors': self.initialization_errors
            })

            # Enumerate cameras
            try:
                available_cameras = USBCamera.enumerate_cameras()
                self.server.set_available_cameras(available_cameras)
            except Exception as e:
                logger.warning(f"Camera enumeration failed: {e}")
                self.server.set_available_cameras([])

            self.initialization_status['server'] = True
            logger.info(f"Web server initialized at http://{server_config.get('host')}:{server_config.get('port')}")

            # ================================================================
            # PHASE 8: Stream Manager
            # ================================================================
            logger.info("=" * 60)
            logger.info("INITIALIZATION PHASE 8: Stream Manager")
            logger.info("=" * 60)

            stream_config = self.config.get('stream', {})
            self.stream_manager = StreamManager(
                camera=self.camera,
                detector=self.detector,
                inventory_tracker=self.inventory_tracker,
                server=self.server,
                target_fps=stream_config.get('target_fps', 30)
            )

            self.initialization_status['stream'] = True
            logger.info("Stream manager initialized")
            
            # Set stream manager reference in server
            self.server.set_stream_manager(self.stream_manager)

            # Log final initialization summary
            self._log_initialization_summary()

            return True

        except Exception as e:
            logger.error(f"Critical initialization failure: {e}", exc_info=True)
            return False

    def _log_initialization_summary(self):
        """Log a summary of initialization status."""
        logger.info("=" * 60)
        logger.info("INITIALIZATION COMPLETE")
        logger.info("=" * 60)

        for component, status in self.initialization_status.items():
            icon = "[OK]" if status else "[--]"
            error = self.initialization_errors.get(component, "")
            suffix = f" ({error})" if error and not status else ""
            logger.info(f"  {icon} {component.capitalize()}{suffix}")

        logger.info("")
        logger.info(f"Detector Mode: {self.detector.get_mode().upper()}")
        logger.info(f"Database: {DB_PATH}")
        logger.info(f"Logs: {SYSTEM_LOG_PATH}")
        logger.info(f"Exports: {EXPORTS_DIR}")
        logger.info("")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Graceful shutdown of all components"""
        logger.info("Shutting down inventory system...")
        
        # Stop streaming
        if self.stream_manager and self.camera is not None:
            await self.stream_manager.stop()
        
        # Release camera
        if self.camera:
            self.camera.release()
        
        # Close persistence layer and log final statistics
        if self.inventory_tracker:
            stats = self.inventory_tracker.get_statistics()
            logger.info(f"Final statistics: {stats}")
            
            # Close persistence if available
            if hasattr(self.inventory_tracker, 'close'):
                self.inventory_tracker.close()
        
        self.shutdown_event.set()
        logger.info("Shutdown complete")
    
    async def run(self):
        """
        Main application loop
        """
        logger.info("=" * 60)
        logger.info("Veratori Inventory System")
        logger.info("=" * 60)
        
        # Initialize components
        if not self.initialize_components():
            logger.error("Initialization failed, exiting")
            return
        
        try:
            # Start web server
            logger.info("Starting web server...")
            await self.server.start()
            
            # Start streaming only if camera is available
            if self.camera is not None:
                logger.info("Starting video stream...")
                self.stream_manager.start()
            else:
                logger.info("Skipping video stream (no camera available)")
            
            logger.info("=" * 60)
            logger.info("System ready!")
            logger.info(f"Web interface available at: {self.server.get_url()}")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Runtime error: {e}", exc_info=True)
        
        finally:
            await self.shutdown()


def create_pid_file():
    """
    Create PID file for single-instance protection
    """
    pid_file = '/tmp/pokebowl.pid'
    
    # Check if already running
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            
            # Check if process is still running
            try:
                os.kill(old_pid, 0)
                logger.error(f"Another instance is already running (PID: {old_pid})")
                sys.exit(1)
            except OSError:
                # Process not running, remove stale PID file
                logger.warning(f"Removing stale PID file (PID: {old_pid})")
                os.remove(pid_file)
        except Exception as e:
            logger.warning(f"Error checking PID file: {e}")
    
    # Write current PID
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID file created: {pid_file}")
    except Exception as e:
        logger.warning(f"Failed to create PID file: {e}")


def remove_pid_file():
    """
    Remove PID file on shutdown
    """
    pid_file = '/tmp/pokebowl.pid'
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
            logger.info("PID file removed")
    except Exception as e:
        logger.warning(f"Failed to remove PID file: {e}")


async def main():
    """
    Application entry point
    """
    # Create PID file for single-instance protection
    create_pid_file()
    
    try:
        # Determine config path
        config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
        
        # Create and run system
        system = InventorySystem(config_path)
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(system.shutdown()))
        
        # Run system
        await system.run()
    
    finally:
        # Always remove PID file
        remove_pid_file()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        remove_pid_file()

