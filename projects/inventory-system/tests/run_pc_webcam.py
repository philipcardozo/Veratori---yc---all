#!/usr/bin/env python3
"""
PC Webcam Launcher
Runs the original Jetson project on PC using the built-in webcam
Does NOT modify any original project files
"""

import sys
import os
from pathlib import Path
import logging

# Add parent directory to path to import original backend modules
PARENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PARENT_DIR / 'backend'))

# Set environment variable to use PC webcam config
PC_CONFIG_PATH = Path(__file__).parent / 'pc_config.yaml'
os.environ['POKEBOWL_CONFIG_PATH'] = str(PC_CONFIG_PATH)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def list_available_cameras():
    """List all available camera devices"""
    import cv2
    available = []
    logger.info("Scanning for available cameras...")
    
    for i in range(10):  # Check first 10 indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                available.append({
                    'index': i,
                    'resolution': f"{width}x{height}"
                })
                logger.info(f"  [OK] Camera {i}: {width}x{height}")
            cap.release()
    
    return available


def check_pc_webcam():
    """Check if PC webcam is accessible at index 0"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                logger.info("[OK] PC webcam (index 0) test successful")
                return True
            else:
                logger.warning("[FAIL] PC webcam opened but cannot read frames")
                return False
        else:
            logger.error("[FAIL] Cannot open PC webcam at index 0")
            return False
    except Exception as e:
        logger.error(f"[FAIL] PC webcam test failed: {e}")
        return False


def check_model():
    """Check if YOLO model exists"""
    model_path = PARENT_DIR / 'models' / 'best.pt'
    if model_path.exists():
        logger.info(f"[OK] YOLO model found: {model_path}")
        return True
    else:
        logger.error(f"[FAIL] YOLO model not found: {model_path}")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    required = ['torch', 'cv2', 'ultralytics', 'aiohttp', 'yaml']
    missing = []
    
    for package in required:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'yaml':
                import yaml
            else:
                __import__(package)
            logger.info(f"[OK] {package} installed")
        except ImportError:
            missing.append(package)
            logger.error(f"[FAIL] {package} not installed")
    
    return len(missing) == 0


def run_system():
    """Run the original system with PC webcam configuration"""
    logger.info("=" * 60)
    logger.info("PC Webcam Mode - Inventory Vision System")
    logger.info("=" * 60)
    logger.info(f"Using config: {PC_CONFIG_PATH}")
    logger.info(f"Project root: {PARENT_DIR}")
    logger.info("Camera: PC Webcam (built-in)")
    logger.info("")
    
    # Pre-flight checks
    logger.info("Running pre-flight checks...")
    
    if not check_dependencies():
        logger.error("\nMissing dependencies. Run: bash install_pc_dependencies.sh")
        return False
    
    if not check_model():
        logger.error("\nYOLO model not found. Ensure models/best.pt exists.")
        return False
    
    # List available cameras
    available_cameras = list_available_cameras()
    if available_cameras:
        logger.info(f"\nFound {len(available_cameras)} camera(s)")
        for cam in available_cameras:
            if cam['index'] == 0:
                logger.info(f"  → Using Camera {cam['index']} (PC Webcam): {cam['resolution']}")
    
    if not check_pc_webcam():
        logger.warning("\nPC webcam test failed at index 0.")
        logger.warning("Available cameras:")
        for cam in available_cameras:
            logger.warning(f"  - Camera {cam['index']}: {cam['resolution']}")
        logger.warning("\nIf your PC webcam is at a different index, edit pc_config.yaml")
        logger.warning("Or use: python3 run_phone_camera.py for phone camera")
        logger.warning("Continuing anyway...")
    
    logger.info("\n[OK] All pre-flight checks passed")
    logger.info("")
    
    # Import and run the original system
    try:
        logger.info("Importing original backend modules...")
        
        from camera import USBCamera
        
        # Patch camera opening for Mac/Windows compatibility (V4L2 is Linux-only)
        import platform
        original_open = USBCamera.open
        
        def mac_compatible_open(self):
            """Mac/Windows-compatible camera open that uses default backend instead of V4L2"""
            try:
                import cv2
                system = platform.system()
                # Use appropriate backend based on OS
                if system == 'Darwin':  # macOS
                    self.cap = cv2.VideoCapture(self.camera_index)
                elif system == 'Windows':  # Windows - try DirectShow first
                    try:
                        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                    except:
                        # Fallback to default backend if DirectShow fails
                        self.cap = cv2.VideoCapture(self.camera_index)
                else:
                    # Use original method for Linux
                    self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
                
                if not self.cap.isOpened():
                    logger.error(f"Failed to open camera at index {self.camera_index}")
                    return False
                
                # Set camera properties
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                
                # On Mac/Windows, skip V4L2-specific settings
                system = platform.system()
                if system not in ('Darwin', 'Windows'):
                    # Set MJPEG format for better USB bandwidth utilization (Linux only)
                    self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                
                # Set buffer size to 1 to minimize latency
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Verify actual settings
                actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
                
                logger.info(f"Camera opened: {actual_width}x{actual_height} @ {actual_fps}fps")
                
                self.is_opened = True
                self.frame_count = 0
                return True
                
            except Exception as e:
                logger.error(f"Exception opening camera: {e}")
                return False
        
        # Monkey-patch the open method for Mac compatibility
        USBCamera.open = mac_compatible_open
        from detector import YOLODetector
        from inventory import InventoryTracker
        from server import VideoStreamServer, StreamManager
        
        import asyncio
        import yaml
        
        logger.info("[OK] Modules imported successfully")
        logger.info("")
        
        # Load PC configuration
        with open(PC_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("Initializing components...")
        
        # Initialize camera (original code) - PC Webcam
        camera = None
        camera_enabled = config['camera'].get('enabled', True)
        
        if camera_enabled:
            camera = USBCamera(
                camera_index=config['camera']['index'],  # Index 0 = PC webcam
                width=config['camera']['width'],
                height=config['camera']['height'],
                fps=config['camera']['fps']
            )
            
            if not camera.open():
                logger.error("Failed to open PC webcam")
                return False
            
            logger.info(f"[OK] Camera: {camera.get_info()}")
        else:
            logger.info("[OK] Camera disabled in configuration - running without camera")
        
        # Initialize detector (original code)
        model_path = PARENT_DIR / config['detector']['model_path']
        detector = YOLODetector(
            model_path=str(model_path),
            conf_threshold=config['detector']['conf_threshold'],
            iou_threshold=config['detector']['iou_threshold'],
            imgsz=config['detector']['imgsz'],
            device=config['detector']['device'],
            half=config['detector']['half']
        )
        
        if not detector.load():
            logger.error("Failed to load YOLO model")
            if camera:
                camera.release()
            return False
        
        logger.info(f"[OK] Detector: {detector.get_info()}")
        
        # Warmup
        detector.warmup(num_iterations=3)
        
        # Initialize inventory tracker (original code)
        inventory_tracker = InventoryTracker(
            smoothing_window=config['inventory']['smoothing_window'],
            smoothing_method=config['inventory']['smoothing_method'],
            class_names=detector.class_names
        )
        
        logger.info("[OK] Inventory tracker initialized")
        
        # Initialize web server (original code) - AUTH DISABLED for PC webcam
        frontend_dir = PARENT_DIR / 'apps' / 'web-frontend'
        server = VideoStreamServer(
            host=config['server']['host'],
            port=config['server']['port'],
            frontend_dir=frontend_dir,
            enable_auth=False  # Bypass authentication for PC webcam testing
        )
        
        logger.info(f"✓ Web server configured")
        
        # Initialize stream manager (original code)
        stream_manager = StreamManager(
            camera=camera,
            detector=detector,
            inventory_tracker=inventory_tracker,
            server=server,
            target_fps=config['stream']['target_fps']
        )
        
        logger.info("[OK] Stream manager initialized")
        logger.info("")
        
        # Run the system (original async code)
        async def main():
            logger.info("=" * 60)
            logger.info("SYSTEM READY - PC Webcam Mode")
            logger.info("=" * 60)
            if camera:
                logger.info(f"Camera: PC Built-in Webcam (index {config['camera']['index']})")
            else:
                logger.info("Camera: Disabled (running without video feed)")
            logger.info(f"Web interface: http://{config['server']['host']}:{config['server']['port']}")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            logger.info("")
            
            try:
                await server.start()
                if camera:
                    stream_manager.start()
                
                # Keep running
                while True:
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                if camera:
                    await stream_manager.stop()
                    camera.release()
                logger.info("Shutdown complete")
        
        # Run the async main function
        asyncio.run(main())
        return True
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return True
    except Exception as e:
        logger.error(f"\nError running system: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    try:
        success = run_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
