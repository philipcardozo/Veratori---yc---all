"""
Veratori Inventory System - Backend Package
Production-ready computer vision inventory tracking for Jetson Orin Nano
"""

__version__ = "1.0.0"
__author__ = "Veratori Inventory Team"

# Package-level imports for convenience
from .camera import USBCamera
from .detector import YOLODetector
from .inventory import InventoryTracker, InventorySnapshot
from .server import VideoStreamServer, StreamManager

__all__ = [
    'USBCamera',
    'YOLODetector',
    'InventoryTracker',
    'InventorySnapshot',
    'VideoStreamServer',
    'StreamManager'
]

