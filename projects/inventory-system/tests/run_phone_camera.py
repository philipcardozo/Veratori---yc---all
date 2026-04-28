#!/usr/bin/env python3
"""
Phone Camera Launcher
Runs the original Jetson project on PC using a phone camera (iPhone via USB)
Does NOT modify any original project files
"""

import sys
import os
from pathlib import Path
import logging

# Add parent directory to path to import original backend modules
PARENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PARENT_DIR / 'backend'))

# Set environment variable to use phone camera config
PHONE_CONFIG_PATH = Path(__file__).parent / 'phone_config.yaml'
os.environ['POKEBOWL_CONFIG_PATH'] = str(PHONE_CONFIG_PATH)

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
                backend = cap.getBackendName()
                available.append({
                    'index': i,
                    'resolution': f"{width}x{height}",
                    'backend': backend
                })
                logger.info(f"  ✓ Camera {i}: {width}x{height} ({backend})")
            cap.release()
    
    return available


def detect_phone_camera(cameras):
    """Try to detect which camera index is the phone"""
    # On Mac with iPhone via USB, it's usually index 1
    # But we'll check all cameras and let user choose
    phone_indices = []
    
    # Check for common phone camera indices (1, 2, 3)
    for cam in cameras:
        if cam['index'] > 0:  # Skip index 0 (PC webcam)
            phone_indices.append(cam['index'])
    
    return phone_indices


def check_phone_camera(index=None):
    """Check if phone camera is accessible"""
    try:
        import cv2
        import time
        
        if index is None:
            # Load config to get default index
            import yaml
            with open(PHONE_CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
            index = config['camera']['index']
        
        # Try up to 3 times with small delays (camera may need time to initialize)
        for attempt in range(3):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                # Give camera a moment to initialize
                time.sleep(0.1)
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    logger.info(f"✓ Phone camera (index {index}) test successful")
                    return True
                elif attempt < 2:
                    # Retry if frame read failed
                    time.sleep(0.2)
                    continue
                else:
                    logger.warning(f"✗ Phone camera opened at index {index} but cannot read frames")
                    return False
            else:
                if attempt < 2:
                    time.sleep(0.2)
                    continue
                else:
                    logger.error(f"✗ Cannot open phone camera at index {index}")
                    return False
        
        return False
    except Exception as e:
        logger.error(f"✗ Phone camera test failed: {e}")
        return False


def check_model():
    """Check if YOLO model exists"""
    model_path = PARENT_DIR / 'models' / 'best.pt'
    if model_path.exists():
        logger.info(f"✓ YOLO model found: {model_path}")
        return True
    else:
        logger.error(f"✗ YOLO model not found: {model_path}")
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
            logger.info(f"✓ {package} installed")
        except ImportError:
            missing.append(package)
            logger.error(f"✗ {package} not installed")
    
    return len(missing) == 0


def run_system():
    """Run the original system with phone camera configuration"""
    logger.info("=" * 60)
    logger.info("Phone Camera Mode - Inventory Vision System")
    logger.info("=" * 60)
    logger.info(f"Using config: {PHONE_CONFIG_PATH}")
    logger.info(f"Project root: {PARENT_DIR}")
    logger.info("Camera: Phone Camera (iPhone via USB)")
    logger.info("")
    logger.info("IMPORTANT: Connect your iPhone via USB and trust this computer")
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
                logger.info(f"  - Camera {cam['index']} (PC Webcam): {cam['resolution']}")
            else:
                logger.info(f"  → Camera {cam['index']} (Possible Phone): {cam['resolution']}")
    
    # Load config to check default index
    import yaml
    with open(PHONE_CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    phone_index = config['camera']['index']
    
    # Check phone camera
    if not check_phone_camera(phone_index):
        logger.warning(f"\nPhone camera test failed at index {phone_index}.")
        logger.warning("\nTroubleshooting:")
        logger.warning("1. Make sure iPhone is connected via USB")
        logger.warning("2. Unlock your iPhone and tap 'Trust This Computer'")
        logger.warning("3. Check if phone appears in System Preferences → Camera")
        
        if available_cameras:
            logger.warning("\nAvailable cameras:")
            for cam in available_cameras:
                if cam['index'] > 0:
                    logger.warning(f"  - Camera {cam['index']}: {cam['resolution']}")
                    logger.warning(f"    Try editing phone_config.yaml and set camera.index to {cam['index']}")
        
        logger.warning("\nIf your phone camera is at a different index, edit phone_config.yaml")
        logger.warning("Or use: python3 run_pc_webcam.py for PC webcam")
        
        # Check if running in non-interactive mode (background)
        import sys
        if not sys.stdin.isatty():
            # Running in background, auto-continue if camera 1 exists
            logger.warning("\nRunning in background mode - auto-continuing...")
            # Try to use camera 1 anyway
            phone_index = 1
            if check_phone_camera(phone_index):
                logger.info(f"✓ Camera {phone_index} works! Using it.")
                config['camera']['index'] = phone_index
            else:
                logger.error("Cannot continue - phone camera not available")
                return False
        else:
            # Interactive mode - ask user
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                return False
    else:
        logger.info(f"✓ Phone camera detected at index {phone_index}")
    
    logger.info("\n✓ All pre-flight checks passed")
    logger.info("")
    
    # Import and run the original system
    try:
        logger.info("Importing original backend modules...")
        
        from camera import USBCamera
        from detector import YOLODetector
        from inventory import InventoryTracker
        from server import VideoStreamServer, StreamManager
        
        import asyncio
        import platform
        
        logger.info("✓ Modules imported successfully")
        logger.info("")
        
        # Patch camera opening for Mac/Windows compatibility (V4L2 is Linux-only)
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
        
        # Apply the patch
        USBCamera.open = mac_compatible_open
        
        logger.info("Initializing components...")
        
        # Initialize camera (original code) - Phone Camera
        camera = USBCamera(
            camera_index=config['camera']['index'],  # Phone camera index
            width=config['camera']['width'],
            height=config['camera']['height'],
            fps=config['camera']['fps']
        )
        
        if not camera.open():
            logger.error("Failed to open phone camera")
            logger.error("Make sure iPhone is connected via USB and trusted")
            return False
        
        logger.info(f"✓ Camera: {camera.get_info()}")
        
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
            camera.release()
            return False
        
        logger.info(f"✓ Detector: {detector.get_info()}")
        
        # Warmup
        detector.warmup(num_iterations=3)
        
        # Initialize inventory tracker (original code)
        inventory_tracker = InventoryTracker(
            smoothing_window=config['inventory']['smoothing_window'],
            smoothing_method=config['inventory']['smoothing_method'],
            class_names=detector.class_names
        )
        
        logger.info("✓ Inventory tracker initialized")
        
        # Initialize web server (original code) - AUTH DISABLED for phone camera
        frontend_dir = PARENT_DIR / 'apps' / 'web-frontend'
        server = VideoStreamServer(
            host=config['server']['host'],
            port=config['server']['port'],
            frontend_dir=frontend_dir,
            enable_auth=False  # Bypass authentication for phone camera testing
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
        
        logger.info("✓ Stream manager initialized")
        logger.info("")
        
        # Run the system (original async code)
        async def main():
            logger.info("=" * 60)
            logger.info("SYSTEM READY - Phone Camera Mode")
            logger.info("=" * 60)
            logger.info(f"Camera: Phone Camera (index {config['camera']['index']})")
            logger.info(f"Web interface: http://{config['server']['host']}:{config['server']['port']}")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            logger.info("")
            
            try:
                await server.start()
                stream_manager.start()
                
                # Keep running
                while True:
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("\nShutting down...")
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
