import sys
import os
import cv2
import numpy as np

# Add backend to path for imports
sys.path.insert(0, os.path.abspath('projects/inventory-system'))
from backend.detector import YOLODetector

def run_test():
    print("Testing detector initialization with dual models...")
    detector = YOLODetector(
        model_path='projects/inventory-system/models/best.pt',
        secondary_model_path='projects/inventory-system/models/coke_best.pt',
        enable_mock_fallback=False
    )
    
    success = detector.load()
    if not success:
        print("Failed to load models!")
        sys.exit(1)
        
    print(f"Primary classes: {len(detector.class_names)}")
    print(f"Secondary classes: {len(detector.secondary_class_names)}")
    
    # Create dummy frame
    dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    # Run mock detection
    print("Running test detection...")
    detections = detector.detect(dummy_frame)
    print(f"Detections returned: {len(detections)}")
    for d in detections:
        print(f" - {d['class_name']} ({d['confidence']:.2f})")
        
    print("Test passed!")

if __name__ == '__main__':
    run_test()
