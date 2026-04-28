#!/usr/bin/env python3
"""
PC Switchable Camera Launcher
Runs the original Jetson project on PC with dynamic camera source switching
Does NOT modify any original project files
"""

import sys
import os
from pathlib import Path
import logging
import asyncio

# Add parent directory to path to import original backend modules
PARENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PARENT_DIR / 'backend'))

# Start with webcam config by default
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


def check_model():
    """Check if YOLO model exists"""
    model_path = PARENT_DIR / 'models' / 'best.pt'
    if model_path.exists():
        logger.info(f"[OK] YOLO model found: {model_path}")
        return True
    else:
        logger.error(f"[FAIL] YOLO model not found: {model_path}")
        return False


def run_system():
    """Run the system with switchable camera support"""
    logger.info("=" * 60)
    logger.info("PC Switchable Camera Mode - Inventory Vision System")
    logger.info("=" * 60)
    logger.info(f"Using initial config: {PC_CONFIG_PATH}")
    logger.info(f"Project root: {PARENT_DIR}")
    logger.info("Camera: Switchable (Webcam <-> Phone)")
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
                logger.info(f"  → Camera {cam['index']} (Webcam): {cam['resolution']}")
            else:
                logger.info(f"  → Camera {cam['index']} (Phone?): {cam['resolution']}")
    
    logger.info("\n[OK] All pre-flight checks passed")
    logger.info("")
    
    # Import and run the original system with camera switching support
    try:
        logger.info("Importing original backend modules...")
        
        from camera import USBCamera
        
        # Patch camera opening for Mac/Windows compatibility
        import platform
        import cv2
        
        original_open = USBCamera.open
        
        def mac_compatible_open(self):
            """Mac/Windows-compatible camera open"""
            try:
                system = platform.system()
                # Use appropriate backend based on OS
                if system == 'Darwin':  # macOS
                    self.cap = cv2.VideoCapture(self.camera_index)
                elif system == 'Windows':  # Windows
                    try:
                        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                    except:
                        self.cap = cv2.VideoCapture(self.camera_index)
                else:
                    # Linux - use V4L2
                    self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
                
                if not self.cap.isOpened():
                    logger.error(f"Failed to open camera at index {self.camera_index}")
                    return False
                
                # Set camera properties
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                
                # Skip V4L2-specific settings on Mac/Windows
                if system not in ('Darwin', 'Windows'):
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
        
        import yaml
        
        logger.info("[OK] Modules imported successfully")
        logger.info("")
        
        # Load initial configuration (webcam)
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
        
        logger.info(f"[OK] Camera: {camera.get_info()}")
        
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
        
        # Initialize web server (original code) - AUTH DISABLED for PC testing
        # Use custom frontend HTML with camera switching UI
        frontend_dir = PARENT_DIR / 'apps' / 'web-frontend'
        server = VideoStreamServer(
            host=config['server']['host'],
            port=config['server']['port'],
            frontend_dir=frontend_dir,
            enable_auth=False
        )
        
        # Override index.html route to serve PC testing version
        from aiohttp import web
        pc_testing_dir = Path(__file__).parent
        pc_index_html = pc_testing_dir / 'index_switchable.html'
        
        async def serve_pc_index(request):
            """Serve PC testing index.html with camera switching UI"""
            return web.FileResponse(pc_index_html)
        
        # Add custom index route before server starts
        server.app.router.add_get('/', serve_pc_index)
        
        logger.info("[OK] Web server configured (PC testing mode)")
        
        # Initialize stream manager (original code)
        stream_manager = StreamManager(
            camera=camera,
            detector=detector,
            inventory_tracker=inventory_tracker,
            server=server,
            target_fps=config['stream']['target_fps']
        )
        
        logger.info("[OK] Stream manager initialized")
        
        # Initialize camera switch manager (PC testing only)
        from pc_camera_switch import CameraSwitchManager
        switch_manager = CameraSwitchManager(
            camera=camera,
            stream_manager=stream_manager,
            detector=detector,
            inventory_tracker=inventory_tracker,
            parent_dir=PARENT_DIR
        )
        
        logger.info("[OK] Camera switch manager initialized")
        
        # Enumerate and set available cameras at startup
        from camera import USBCamera
        available_cameras = USBCamera.enumerate_cameras()
        server.set_available_cameras(available_cameras)
        server.set_camera(camera)
        logger.info(f"[OK] Enumerated {len(available_cameras)} camera(s) at startup")
        
        # Add camera switch API endpoint to server
        
        async def handle_camera_switch(request):
            """Handle camera source switch requests"""
            try:
                data = await request.json()
                target_source = data.get('source')
                
                if not target_source:
                    return web.json_response({
                        "ok": False,
                        "error": "Missing 'source' parameter"
                    }, status=400)
                
                # Perform switch
                result = switch_manager.switch_source(target_source)
                
                status = 200 if result['ok'] else 400
                return web.json_response(result, status=status)
                
            except Exception as e:
                logger.error(f"Error in camera switch handler: {e}", exc_info=True)
                return web.json_response({
                    "ok": False,
                    "error": str(e),
                    "active_source": switch_manager.active_source
                }, status=500)
        
        async def handle_camera_status(request):
            """Handle camera status requests"""
            try:
                status = switch_manager.get_status()
                return web.json_response({
                    "ok": True,
                    **status
                })
            except Exception as e:
                logger.error(f"Error in camera status handler: {e}", exc_info=True)
                return web.json_response({
                    "ok": False,
                    "error": str(e)
                }, status=500)
        
        # Add routes to server
        server.app.router.add_post('/api/camera/source', handle_camera_switch)
        server.app.router.add_get('/api/camera/status', handle_camera_status)
        
        logger.info("[OK] Camera switch API endpoints registered")
        logger.info("")
        
        # Run the system (original async code)
        async def main():
            logger.info("=" * 60)
            logger.info("SYSTEM READY - PC Switchable Camera Mode")
            logger.info("=" * 60)
            logger.info(f"Initial camera: {switch_manager.active_source.capitalize()} (index {config['camera']['index']})")
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
                stream_manager.stop()
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
