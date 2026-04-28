#!/usr/bin/env python3
"""
PC Testing Launcher
Runs the original Jetson project on PC with webcam support
Does NOT modify any original project files
"""

import sys
import os
from pathlib import Path
import logging

# Add parent directory to path to import original backend modules
PARENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PARENT_DIR / 'backend'))

# Set environment variable to use PC config
PC_CONFIG_PATH = Path(__file__).parent / 'pc_config.yaml'
os.environ['POKEBOWL_CONFIG_PATH'] = str(PC_CONFIG_PATH)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def check_camera():
    """Check if camera is accessible"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                logger.info("✓ Camera test successful")
                return True
            else:
                logger.warning("✗ Camera opened but cannot read frames")
                return False
        else:
            logger.error("✗ Cannot open camera at index 0")
            return False
    except Exception as e:
        logger.error(f"✗ Camera test failed: {e}")
        return False


def check_model():
    """Check if YOLO model exists"""
    model_path = PARENT_DIR / 'best.pt'
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
    """Run the original system with PC configuration"""
    logger.info("=" * 60)
    logger.info("PC Testing Mode - Inventory Vision System")
    logger.info("=" * 60)
    logger.info(f"Using config: {PC_CONFIG_PATH}")
    logger.info(f"Project root: {PARENT_DIR}")
    logger.info("")
    
    # Pre-flight checks
    logger.info("Running pre-flight checks...")
    
    if not check_dependencies():
        logger.error("\nMissing dependencies. Run: bash install_pc_dependencies.sh")
        return False
    
    if not check_model():
        logger.error("\nYOLO model not found. Ensure best.pt exists in project root.")
        return False
    
    if not check_camera():
        logger.warning("\nCamera test failed. System may not work properly.")
        logger.warning("Check camera permissions and try again.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    logger.info("\n✓ All pre-flight checks passed")
    logger.info("")
    
    # Import and run the original system
    try:
        logger.info("Importing original backend modules...")
        
        # Import original modules (unmodified)
        from camera import USBCamera
        from detector import YOLODetector
        from inventory import InventoryTracker
        from server import VideoStreamServer, StreamManager
        
        import asyncio
        import yaml
        
        logger.info("✓ Modules imported successfully")
        logger.info("")
        
        # Load PC configuration
        with open(PC_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("Initializing components...")
        
        # Initialize camera (original code)
        camera = USBCamera(
            camera_index=config['camera']['index'],
            width=config['camera']['width'],
            height=config['camera']['height'],
            fps=config['camera']['fps']
        )
        
        if not camera.open():
            logger.error("Failed to open camera")
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
        
        # Initialize web server (original code)
        frontend_dir = PARENT_DIR / 'frontend'
        server = VideoStreamServer(
            host=config['server']['host'],
            port=config['server']['port'],
            frontend_dir=frontend_dir
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
            logger.info("SYSTEM READY - PC Testing Mode")
            logger.info("=" * 60)
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
