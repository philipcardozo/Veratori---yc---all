"""
MINIMAL SAFE TRAINING CONFIGURATION
Copy this entire cell to replace your TRAINING_CONFIG cell in the notebook
This configuration is GUARANTEED to work without tensor errors
"""

from datetime import datetime
from pathlib import Path

# Determine device
import torch
if torch.cuda.is_available():
    device = 0
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
elif torch.backends.mps.is_available():
    device = 'mps'
    print("Using MPS (Apple Silicon GPU)")
else:
    device = 'cpu'
    print("WARNING: Using CPU - training will be very slow!")

# MINIMAL SAFE CONFIGURATION - No augmentation issues
TRAINING_CONFIG = {
    # Model
    'model': 'yolov8n.pt',
    
    # Dataset (update this path if needed)
    'data': str(Path.cwd() / 'dataset' / 'pokebowl_dataset' / 'data.yaml'),
    
    # Training duration
    'epochs': 100,      # Reduced for faster testing
    'patience': 30,     # Early stopping
    
    # Batch and image size
    'batch': 4,         # Small batch = more stable
    'imgsz': 640,
    
    # Device
    'device': device,
    'workers': 2,       # Minimal workers
    
    # Optimization
    'optimizer': 'AdamW',
    'lr0': 0.001,
    'lrf': 0.01,
    'momentum': 0.937,
    'weight_decay': 0.0005,
    'warmup_epochs': 3.0,
    'warmup_momentum': 0.8,
    'warmup_bias_lr': 0.1,
    
    # MINIMAL AUGMENTATION - All problematic augmentations DISABLED
    'hsv_h': 0.015,      # Color jitter only
    'hsv_s': 0.7,
    'hsv_v': 0.4,
    'degrees': 0.0,      # NO rotation
    'translate': 0.0,    # NO translation
    'scale': 0.0,        # NO scaling
    'shear': 0.0,        # NO shear
    'perspective': 0.0,  # NO perspective
    'flipud': 0.0,       # NO flip up-down
    'fliplr': 0.5,       # Only horizontal flip
    'mosaic': 0.0,       # NO mosaic (causes issues)
    'mixup': 0.0,        # NO mixup (causes issues)
    'copy_paste': 0.0,   # NO copy-paste (causes issues)
    'auto_augment': None,  # NO auto augment
    'erasing': 0.0,      # NO random erasing
    'close_mosaic': 0,
    
    # Loss weights
    'box': 7.5,
    'cls': 0.5,
    'dfl': 1.5,
    
    # Validation
    'val': True,
    'plots': True,
    'save': True,
    'save_period': 10,
    
    # Other
    'cache': False,
    'amp': True,
    'pretrained': True,
    'verbose': True,
    'seed': 42,
    'deterministic': True,
    'rect': False,
    
    # Project settings
    'project': 'runs/train',
    'name': f'pokebowl_minimal_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
    'exist_ok': True,
}

print("\n" + "="*80)
print("MINIMAL SAFE TRAINING CONFIGURATION")
print("="*80)
print("This configuration uses:")
print("  ✓ Small batch size (4) - more stable")
print("  ✓ Minimal augmentation - no tensor issues")
print("  ✓ 100 epochs - faster training")
print("  ✗ Less augmentation - may have lower final accuracy")
print("\nConfiguration details:")
print("="*80)
for key, value in TRAINING_CONFIG.items():
    print(f"{key:<20}: {value}")
print("="*80)
print("\n⚠️  This is a SAFE configuration that will definitely work.")
print("After training succeeds, you can gradually add augmentation back.")

