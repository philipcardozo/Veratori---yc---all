"""
YOLO Object Detector Wrapper for Jetson Orin Nano
GPU-accelerated inference with Ultralytics YOLO
Includes automatic mock mode fallback for demo safety
"""

import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

# Default class names for mock mode (based on typical poke bowl inventory)
DEFAULT_CLASS_NAMES = {
    0: 'mango',
    1: 'watermelon',
    2: 'pineapple',
    3: 'passion fruit',
    4: 'maui custard',
    5: 'lemon cake',
    6: 'cantaloupe'
}


class YOLODetector:
    """
    Wrapper for YOLO model inference
    Optimized for Jetson Orin Nano with CUDA acceleration

    Features automatic mock mode fallback when:
    - Model file not found
    - YOLO/PyTorch import fails
    - CUDA not available
    - Any initialization error occurs
    """

    def __init__(
        self,
        model_path: str,
        secondary_model_path: Optional[str] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        imgsz: int = 640,
        device: str = '0',  # CUDA device
        half: bool = True,  # FP16 precision for Jetson
        enable_mock_fallback: bool = True  # Auto-fallback to mock mode
    ):
        """
        Initialize YOLO detector

        Args:
            model_path: Path to trained YOLO model (.pt file)
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            imgsz: Input image size (will be resized to this)
            device: CUDA device ('0' for GPU, 'cpu' for CPU)
            half: Use FP16 precision (recommended for Jetson)
            enable_mock_fallback: If True, automatically switch to mock mode on failure
        """
        self.model_path = Path(model_path)
        self.secondary_model_path = Path(secondary_model_path) if secondary_model_path else None
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.device = device
        self.half = half
        self.enable_mock_fallback = enable_mock_fallback

        self.model = None
        self.secondary_model = None
        self.class_names = {}
        self.secondary_class_names = {}
        self.is_loaded = False
        self.inference_times = []

        # Mock mode state
        self.mock_mode = False
        self.mock_reason = None
        self.initialization_error = None
        self._random_seed = 42  # For deterministic mock results
        
    def load(self) -> bool:
        """
        Load YOLO model with CUDA acceleration.
        Automatically falls back to mock mode if loading fails.

        Returns:
            True if model loaded successfully OR mock mode activated
        """
        try:
            # Try alternative model paths if primary not found
            model_paths_to_try = [
                self.model_path,
                self.model_path.parent / 'yolov8n.pt',
                self.model_path.parent / 'best.pt',
                Path(__file__).parent.parent / 'models' / 'best.pt',
                Path(__file__).parent.parent / 'models' / 'yolov8n.pt',
            ]

            model_found = None
            for mp in model_paths_to_try:
                if mp.exists():
                    model_found = mp
                    break

            if model_found is None:
                raise FileNotFoundError(
                    f"No model found. Tried: {[str(p) for p in model_paths_to_try]}"
                )

            self.model_path = model_found
            logger.info(f"Loading YOLO model from {self.model_path}")

            from ultralytics import YOLO

            start_time = time.time()

            # Load model
            self.model = YOLO(str(self.model_path))

            # Move to device
            if self.device == '0' or self.device == 'cuda':
                try:
                    import torch
                    if torch.cuda.is_available():
                        self.model.to('cuda')
                        logger.info("Model moved to CUDA device")

                        # Enable half precision for Jetson (CUDA only)
                        if self.half:
                            self.model.model.half()
                            logger.info("FP16 (half precision) enabled")
                    else:
                        logger.warning("CUDA not available — falling back to CPU (FP16 disabled)")
                        self.device = 'cpu'
                        self.half = False  # half precision is not supported on CPU
                except ImportError:
                    logger.warning("PyTorch not available for CUDA check — using CPU (FP16 disabled)")
                    self.device = 'cpu'
                    self.half = False

            # Extract class names
            if hasattr(self.model, 'names'):
                self.class_names = self.model.names
                logger.info(f"Loaded {len(self.class_names)} classes for primary model")

            # Load secondary model (custom Coke model) if path provided
            if self.secondary_model_path and self.secondary_model_path.exists():
                logger.info(f"Loading secondary YOLO model from {self.secondary_model_path}")
                self.secondary_model = YOLO(str(self.secondary_model_path))
                
                if self.device == '0' or self.device == 'cuda':
                    if torch.cuda.is_available():
                        self.secondary_model.to('cuda')
                        if self.half:
                            self.secondary_model.model.half()
                
                if hasattr(self.secondary_model, 'names'):
                    self.secondary_class_names = self.secondary_model.names
                    logger.info(f"Loaded {len(self.secondary_class_names)} classes for secondary model")

            load_time = time.time() - start_time
            logger.info(f"Model(s) loaded in {load_time:.2f}s")

            self.is_loaded = True
            self.mock_mode = False
            return True

        except ImportError as e:
            error_msg = f"YOLO/ultralytics import failed: {e}"
            logger.warning(error_msg)
            return self._activate_mock_mode(error_msg)

        except FileNotFoundError as e:
            error_msg = f"Model file not found: {e}"
            logger.warning(error_msg)
            return self._activate_mock_mode(error_msg)

        except Exception as e:
            error_msg = f"Failed to load YOLO model: {e}"
            logger.error(error_msg, exc_info=True)
            return self._activate_mock_mode(error_msg)

    def _activate_mock_mode(self, reason: str) -> bool:
        """
        Activate mock mode as fallback when YOLO fails.

        Args:
            reason: Description of why mock mode was activated

        Returns:
            True if mock mode activated, False if fallback disabled
        """
        if not self.enable_mock_fallback:
            logger.error("YOLO failed and mock fallback is disabled")
            return False

        logger.warning(f"Activating MOCK MODE: {reason}")
        self.mock_mode = True
        self.mock_reason = reason
        self.initialization_error = reason
        self.is_loaded = True  # Mark as loaded so system continues
        self.class_names = DEFAULT_CLASS_NAMES
        logger.info(f"Mock mode active with {len(self.class_names)} simulated classes")
        return True
    
    def detect(self, frame: np.ndarray) -> List[dict]:
        """
        Run inference on a single frame.
        Returns mock detections only when explicitly in mock mode.
        Returns an empty list on any real-YOLO error (no silent mock fallback).

        Args:
            frame: Input image as numpy array (H, W, 3) in BGR format

        Returns:
            List of detection dictionaries with keys:
            - class_id: int
            - class_name: str
            - confidence: float
            - bbox: [x1, y1, x2, y2] in pixel coordinates
        """
        # Validate frame before anything else
        if frame is None:
            logger.warning("detect() called with None frame")
            return []
        if frame.ndim < 2 or frame.shape[0] == 0 or frame.shape[1] == 0:
            logger.warning(f"detect() called with invalid frame shape: {frame.shape}")
            return []

        if not self.is_loaded:
            logger.warning("Detector not initialized")
            return []

        # Use mock detection only when explicitly in mock mode
        if self.mock_mode:
            return self._generate_mock_detections(frame)

        if self.model is None:
            # Not in mock mode but model missing — return empty, do not fake results
            logger.error("YOLO model is None but mock mode is not active — returning empty detections")
            return []

        try:
            start_time = time.time()

            # Run inference
            results = self.model.predict(
                source=frame,
                imgsz=self.imgsz,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
                device=self.device,
                half=self.half
            )

            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)

            # Keep only last 100 inference times for moving average
            if len(self.inference_times) > 100:
                self.inference_times.pop(0)

            # Parse results
            detections = []

            if len(results) > 0:
                result = results[0]

                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)

                    for bbox, conf, class_id in zip(boxes, confidences, class_ids):
                        class_name = self.class_names.get(int(class_id), f'class_{class_id}')
                        
                        # Unify "Coke Diet" and "Coke Zero" to "Coke"
                        if class_name.lower() in ["coke diet", "coke zero"]:
                            class_name = "Coke"
                            
                        detection = {
                            'class_id': int(class_id),
                            'class_name': class_name,
                            'confidence': float(conf),
                            'bbox': [float(x) for x in bbox]  # [x1, y1, x2, y2]
                        }
                        detections.append(detection)

            # Secondary model (Custom Coke model) inference
            if self.secondary_model is not None:
                sec_results = self.secondary_model.predict(
                    source=frame,
                    imgsz=self.imgsz,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    verbose=False,
                    device=self.device,
                    half=self.half
                )
                
                if len(sec_results) > 0:
                    sec_result = sec_results[0]
                    if sec_result.boxes is not None and len(sec_result.boxes) > 0:
                        boxes = sec_result.boxes.xyxy.cpu().numpy()
                        confidences = sec_result.boxes.conf.cpu().numpy()
                        class_ids = sec_result.boxes.cls.cpu().numpy().astype(int)
                        
                        for bbox, conf, class_id in zip(boxes, confidences, class_ids):
                            # Ensure custom model outputs are classified solely as 'Coke'
                            # e.g., mapping 'coke' or 'can' from new model to 'Coke'
                            detection = {
                                'class_id': 9999,  # Arbitrary ID to distinguish combined Coke, or could map directly
                                'class_name': 'Coke',
                                'confidence': float(conf),
                                'bbox': [float(x) for x in bbox]
                            }
                            detections.append(detection)

            logger.debug(f"YOLO inference: {len(detections)} detections in {inference_time*1000:.1f}ms")
            return detections

        except Exception as e:
            # Do NOT fall back to mock — return empty so callers get accurate (empty) results
            logger.error(f"YOLO inference error: {e}", exc_info=True)
            return []

    def _generate_mock_detections(self, frame: np.ndarray) -> List[dict]:
        """
        Generate realistic mock detections for demo purposes.
        Uses deterministic randomization for consistent results.

        Args:
            frame: Input frame (used for sizing bounding boxes)

        Returns:
            List of mock detection dictionaries
        """
        start_time = time.time()
        h, w = frame.shape[:2] if frame is not None else (720, 1280)

        # Use frame hash for semi-deterministic results
        if frame is not None:
            # Simple hash based on a few pixels for variation
            pixel_sum = int(frame[h//4, w//4, 0]) + int(frame[h//2, w//2, 1])
            random.seed(pixel_sum % 1000)
        else:
            random.seed(self._random_seed)

        # Generate 8-15 detections
        num_detections = random.randint(8, 15)
        detections = []

        for i in range(num_detections):
            class_id = random.randint(0, len(self.class_names) - 1)

            # Generate realistic bounding box (poke bowls are roughly square)
            box_size = random.randint(int(min(h, w) * 0.08), int(min(h, w) * 0.15))
            x1 = random.randint(50, max(51, w - box_size - 50))
            y1 = random.randint(50, max(51, h - box_size - 50))
            x2 = x1 + box_size
            y2 = y1 + box_size

            detection = {
                'class_id': class_id,
                'class_name': self.class_names.get(class_id, f'product_{class_id}'),
                'confidence': round(random.uniform(0.75, 0.98), 3),
                'bbox': [float(x1), float(y1), float(x2), float(y2)]
            }
            detections.append(detection)

        # Track mock inference time
        inference_time = time.time() - start_time + 0.015  # Add simulated delay
        self.inference_times.append(inference_time)
        if len(self.inference_times) > 100:
            self.inference_times.pop(0)

        return detections
    
    def get_average_inference_time(self) -> float:
        """
        Get average inference time in seconds
        
        Returns:
            Average inference time over last 100 frames
        """
        if not self.inference_times:
            return 0.0
        return float(np.mean(self.inference_times))
    
    def get_fps(self) -> float:
        """
        Get average FPS based on inference time
        
        Returns:
            Frames per second
        """
        avg_time = self.get_average_inference_time()
        return 1.0 / avg_time if avg_time > 0 else 0.0
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[dict],
        show_conf: bool = True,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: Input image
            detections: List of detection dictionaries from detect()
            show_conf: Whether to show confidence scores
            color: BGR color for boxes
            thickness: Line thickness
            
        Returns:
            Annotated frame
        """
        import cv2
        
        annotated = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
            
            # Prepare label
            label = det['class_name']
            if show_conf:
                label += f" {det['confidence']:.2f}"
            
            # Draw label background
            (label_w, label_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                annotated,
                (x1, y1 - label_h - 8),
                (x1 + label_w + 4, y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated,
                label,
                (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA
            )
        
        return annotated
    
    def update_thresholds(self, conf: Optional[float] = None, iou: Optional[float] = None):
        """
        Update detection thresholds at runtime
        
        Args:
            conf: New confidence threshold
            iou: New IoU threshold
        """
        if conf is not None:
            self.conf_threshold = conf
            logger.info(f"Confidence threshold updated to {conf}")
        
        if iou is not None:
            self.iou_threshold = iou
            logger.info(f"IoU threshold updated to {iou}")
    
    def get_info(self) -> dict:
        """
        Get detector information and statistics

        Returns:
            Dictionary with detector properties
        """
        info = {
            "model_path": str(self.model_path),
            "is_loaded": self.is_loaded,
            "mock_mode": self.mock_mode,
            "device": self.device,
            "half_precision": self.half,
            "conf_threshold": self.conf_threshold,
            "iou_threshold": self.iou_threshold,
            "imgsz": self.imgsz,
            "num_classes": len(self.class_names),
            "class_names": list(self.class_names.values()) if self.class_names else [],
            "avg_inference_time": f"{self.get_average_inference_time():.4f}s",
            "avg_fps": f"{self.get_fps():.1f}"
        }

        if self.mock_mode:
            info["mock_reason"] = self.mock_reason
            info["mode"] = "MOCK"
        else:
            info["mode"] = "YOLO"

        return info

    def warmup(self, num_iterations: int = 10):
        """
        Warm up the model with dummy inferences.
        Works for both real YOLO and mock mode.

        Args:
            num_iterations: Number of warmup iterations
        """
        if not self.is_loaded:
            logger.warning("Cannot warmup: detector not initialized")
            return

        mode = "mock" if self.mock_mode else "YOLO"
        logger.info(f"Warming up {mode} detector with {num_iterations} iterations...")

        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)

        for i in range(num_iterations):
            self.detect(dummy_frame)

        avg_time = self.get_average_inference_time()
        logger.info(f"Warmup complete. Avg inference: {avg_time:.4f}s ({self.get_fps():.1f} FPS)")

    def is_mock(self) -> bool:
        """Check if detector is running in mock mode."""
        return self.mock_mode

    def get_mode(self) -> str:
        """Get current detector mode: 'yolo' or 'mock'."""
        return 'mock' if self.mock_mode else 'yolo'

