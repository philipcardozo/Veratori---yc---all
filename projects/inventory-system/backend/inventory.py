"""
Inventory Management System with Temporal Smoothing
Tracks product counts per class with noise reduction
"""

import logging
from collections import deque, defaultdict
from typing import List, Dict
import numpy as np

logger = logging.getLogger(__name__)


class InventoryTracker:
    """
    Tracks product inventory from detection results
    Applies temporal smoothing to reduce counting noise
    """
    
    def __init__(
        self,
        smoothing_window: int = 10,
        smoothing_method: str = 'median',
        class_names: Dict[int, str] = None
    ):
        """
        Initialize inventory tracker
        
        Args:
            smoothing_window: Number of frames to use for smoothing
            smoothing_method: 'median', 'mean', or 'mode'
            class_names: Mapping of class IDs to names
        """
        self.smoothing_window = smoothing_window
        self.smoothing_method = smoothing_method
        self.class_names = class_names or {}
        
        # History buffer: stores count per class for last N frames
        # Format: {class_id: deque([count1, count2, ...])}
        self.history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=self.smoothing_window))
        
        # Current smoothed inventory snapshot
        self.current_inventory: Dict[int, int] = {}
        
        # Total frames processed
        self.frame_count = 0
        
        # Statistics
        self.total_detections = 0
        
    def update(self, detections: List[dict]):
        """
        Update inventory with new detections from a frame
        
        Args:
            detections: List of detection dicts with 'class_id' key
        """
        self.frame_count += 1
        self.total_detections += len(detections)
        
        # Count detections per class in current frame
        frame_counts = defaultdict(int)
        for det in detections:
            class_id = det['class_id']
            frame_counts[class_id] += 1
        
        # Update history for all known classes
        # Add 0 for classes not detected in this frame
        all_classes = set(self.history.keys()) | set(frame_counts.keys())
        
        for class_id in all_classes:
            count = frame_counts.get(class_id, 0)
            self.history[class_id].append(count)
        
        # Compute smoothed inventory
        self._compute_smoothed_inventory()
    
    def _compute_smoothed_inventory(self):
        """
        Compute smoothed inventory counts using configured method
        """
        self.current_inventory = {}
        
        for class_id, counts in self.history.items():
            if len(counts) == 0:
                continue
            
            counts_array = np.array(list(counts))
            
            if self.smoothing_method == 'median':
                smoothed = int(np.median(counts_array))
            elif self.smoothing_method == 'mean':
                smoothed = int(np.round(np.mean(counts_array)))
            elif self.smoothing_method == 'mode':
                # Use most common value
                values, counts_per_value = np.unique(counts_array, return_counts=True)
                smoothed = int(values[np.argmax(counts_per_value)])
            else:
                # Default to median
                smoothed = int(np.median(counts_array))
            
            # Only include non-zero counts in current inventory
            if smoothed > 0:
                self.current_inventory[class_id] = smoothed
    
    def get_inventory(self) -> Dict[str, int]:
        """
        Get current smoothed inventory with class names
        
        Returns:
            Dictionary mapping class names to counts
        """
        inventory = {}
        
        for class_id, count in self.current_inventory.items():
            class_name = self.class_names.get(class_id, f'class_{class_id}')
            inventory[class_name] = count
        
        return inventory
    
    def get_inventory_by_id(self) -> Dict[int, int]:
        """
        Get current smoothed inventory with class IDs
        
        Returns:
            Dictionary mapping class IDs to counts
        """
        return self.current_inventory.copy()
    
    def get_total_items(self) -> int:
        """
        Get total number of items across all classes
        
        Returns:
            Sum of all counts
        """
        return sum(self.current_inventory.values())
    
    def get_class_count(self, class_id: int) -> int:
        """
        Get count for a specific class
        
        Args:
            class_id: Class ID to query
            
        Returns:
            Smoothed count for the class
        """
        return self.current_inventory.get(class_id, 0)
    
    def get_inventory_sorted(self, by: str = 'count') -> List[tuple]:
        """
        Get inventory sorted by count or name
        
        Args:
            by: 'count' (descending) or 'name' (alphabetical)
            
        Returns:
            List of (class_name, count) tuples
        """
        inventory = self.get_inventory()
        
        if by == 'count':
            return sorted(inventory.items(), key=lambda x: x[1], reverse=True)
        elif by == 'name':
            return sorted(inventory.items(), key=lambda x: x[0])
        else:
            return list(inventory.items())
    
    def reset(self):
        """
        Reset all tracking history and counters
        """
        self.history.clear()
        self.current_inventory.clear()
        self.frame_count = 0
        self.total_detections = 0
        logger.info("Inventory tracker reset")
    
    def update_class_names(self, class_names: Dict[int, str]):
        """
        Update class name mapping
        
        Args:
            class_names: New mapping of class IDs to names
        """
        self.class_names = class_names
        logger.info(f"Updated class names: {len(class_names)} classes")
    
    def get_statistics(self) -> dict:
        """
        Get tracker statistics
        
        Returns:
            Dictionary with tracking stats
        """
        return {
            'frame_count': self.frame_count,
            'total_detections': self.total_detections,
            'avg_detections_per_frame': self.total_detections / max(self.frame_count, 1),
            'unique_classes_tracked': len(self.history),
            'current_unique_classes': len(self.current_inventory),
            'current_total_items': self.get_total_items(),
            'smoothing_window': self.smoothing_window,
            'smoothing_method': self.smoothing_method
        }
    
    def get_raw_history(self, class_id: int, n: int = None) -> List[int]:
        """
        Get raw count history for a class (for debugging/analysis)
        
        Args:
            class_id: Class ID to query
            n: Number of recent frames (None for all)
            
        Returns:
            List of counts
        """
        if class_id not in self.history:
            return []
        
        history = list(self.history[class_id])
        
        if n is not None:
            return history[-n:]
        
        return history
    
    def get_confidence_score(self, class_id: int) -> float:
        """
        Get confidence score for a class count (based on variance)
        Lower variance = higher confidence
        
        Args:
            class_id: Class ID to query
            
        Returns:
            Confidence score between 0 and 1
        """
        if class_id not in self.history or len(self.history[class_id]) < 2:
            return 0.0
        
        counts = np.array(list(self.history[class_id]))
        std_dev = np.std(counts)
        mean = np.mean(counts)
        
        if mean == 0:
            return 1.0 if std_dev == 0 else 0.0
        
        # Coefficient of variation (inverted and normalized)
        cv = std_dev / mean
        confidence = 1.0 / (1.0 + cv)
        
        return float(confidence)


class InventorySnapshot:
    """
    Immutable snapshot of inventory state at a point in time
    """
    
    def __init__(self, inventory: Dict[str, int], timestamp: float, frame_number: int):
        """
        Initialize snapshot
        
        Args:
            inventory: Dictionary of class names to counts
            timestamp: Unix timestamp
            frame_number: Frame number when snapshot was taken
        """
        self.inventory = inventory.copy()
        self.timestamp = timestamp
        self.frame_number = frame_number
        self.total_items = sum(inventory.values())
    
    def to_dict(self) -> dict:
        """
        Convert snapshot to dictionary
        
        Returns:
            Dictionary representation
        """
        return {
            'inventory': self.inventory,
            'timestamp': self.timestamp,
            'frame_number': self.frame_number,
            'total_items': self.total_items
        }
    
    def __repr__(self) -> str:
        return f"InventorySnapshot(frame={self.frame_number}, items={self.total_items}, ts={self.timestamp:.2f})"

