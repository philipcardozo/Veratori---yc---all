"""
Camera Source Switch Module for PC Testing
Handles safe switching between webcam and phone camera sources
"""

import logging
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

logger = logging.getLogger(__name__)


class CameraSwitchManager:
    """Manages camera source switching with atomic transitions and rollback"""
    
    def __init__(self, camera, stream_manager, detector, inventory_tracker, parent_dir):
        self.camera = camera
        self.stream_manager = stream_manager
        self.detector = detector
        self.inventory_tracker = inventory_tracker
        self.parent_dir = parent_dir
        self.active_source = "webcam"  # Default
        self.switch_lock = threading.Lock()
        self.state_file = Path(__file__).parent / ".camera_source_state"
        
        # Load persisted state if exists
        self._load_state()
        
    def _load_state(self):
        """Load persisted camera source state"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = yaml.safe_load(f)
                    if data and 'active_source' in data:
                        self.active_source = data['active_source']
                        logger.info(f"Restored camera source: {self.active_source}")
        except Exception as e:
            logger.warning(f"Could not load state file: {e}")
    
    def _save_state(self):
        """Persist camera source state"""
        try:
            with open(self.state_file, 'w') as f:
                yaml.dump({'active_source': self.active_source}, f)
        except Exception as e:
            logger.warning(f"Could not save state file: {e}")
    
    def get_config_path(self, source: str) -> Path:
        """Get config path for given source"""
        if source == "webcam":
            return Path(__file__).parent / 'pc_config.yaml'
        elif source == "phone":
            return Path(__file__).parent / 'phone_config.yaml'
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def load_config(self, source: str) -> Dict[str, Any]:
        """Load configuration for given source"""
        config_path = self.get_config_path(source)
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def switch_source(self, target_source: str) -> Dict[str, Any]:
        """
        Switch camera source atomically with rollback on failure
        
        Returns:
            dict: Result with 'ok', 'active_source', 'restart_ms', and optional 'error'
        """
        if target_source not in ["webcam", "phone"]:
            return {
                "ok": False,
                "error": f"Invalid source: {target_source}",
                "active_source": self.active_source
            }
        
        if target_source == self.active_source:
            return {
                "ok": True,
                "active_source": self.active_source,
                "restart_ms": 0,
                "message": "Already using requested source"
            }
        
        # Acquire lock for atomic switch
        with self.switch_lock:
            start_time = time.time()
            previous_source = self.active_source
            previous_index = self.camera.camera_index
            
            logger.info(f"Switching camera source: {previous_source} -> {target_source}")
            
            try:
                # Step 1: Stop streaming
                logger.info("Stopping stream manager...")
                self.stream_manager.stop()
                time.sleep(0.1)  # Brief pause
                
                # Step 2: Release current camera
                logger.info(f"Releasing camera at index {previous_index}...")
                self.camera.release()
                time.sleep(0.2)  # Wait for camera release
                
                # Step 3: Load new configuration
                logger.info(f"Loading configuration for {target_source}...")
                config = self.load_config(target_source)
                new_index = config['camera']['index']
                
                # Step 4: Update camera settings
                logger.info(f"Updating camera to index {new_index}...")
                self.camera.camera_index = new_index
                self.camera.width = config['camera']['width']
                self.camera.height = config['camera']['height']
                self.camera.fps = config['camera']['fps']
                
                # Step 5: Attempt to open new camera
                logger.info(f"Opening camera at index {new_index}...")
                if not self.camera.open():
                    raise Exception(f"Failed to open camera at index {new_index}")
                
                # Step 6: Verify camera works
                logger.info("Verifying camera...")
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    raise Exception("Camera opened but cannot read frames")
                
                # Step 7: Restart streaming
                logger.info("Restarting stream manager...")
                self.stream_manager.start()
                
                # Success! Update state
                self.active_source = target_source
                self._save_state()
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Camera switch successful: {previous_source} -> {target_source} ({elapsed_ms}ms)")
                
                return {
                    "ok": True,
                    "active_source": self.active_source,
                    "restart_ms": elapsed_ms,
                    "message": f"Switched to {target_source}"
                }
                
            except Exception as e:
                # Rollback to previous source
                logger.error(f"Camera switch failed: {e}. Rolling back to {previous_source}...")
                
                try:
                    # Release failed camera
                    self.camera.release()
                    time.sleep(0.2)
                    
                    # Restore previous settings
                    rollback_config = self.load_config(previous_source)
                    self.camera.camera_index = previous_index
                    self.camera.width = rollback_config['camera']['width']
                    self.camera.height = rollback_config['camera']['height']
                    self.camera.fps = rollback_config['camera']['fps']
                    
                    # Reopen previous camera
                    if not self.camera.open():
                        raise Exception("Rollback failed: cannot reopen previous camera")
                    
                    # Restart streaming with previous source
                    self.stream_manager.start()
                    
                    logger.info(f"Rollback successful: restored {previous_source}")
                    
                except Exception as rollback_error:
                    logger.error(f"CRITICAL: Rollback failed: {rollback_error}")
                    # System is in bad state, but we tried our best
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "ok": False,
                    "error": str(e),
                    "active_source": self.active_source,
                    "restart_ms": elapsed_ms
                }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current camera source status"""
        return {
            "active_source": self.active_source,
            "camera_index": self.camera.camera_index,
            "is_opened": self.camera.is_opened
        }
