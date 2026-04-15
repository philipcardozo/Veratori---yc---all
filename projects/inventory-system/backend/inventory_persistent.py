"""
Enhanced Inventory Tracker with Persistence
Extends base InventoryTracker with database persistence for snapshots, freshness, and sales
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone

from inventory import InventoryTracker
from persistence import PersistenceManager
from sales_attribution import SalesAttributionEngine
from alerts import AlertEngine

logger = logging.getLogger(__name__)


class PersistentInventoryTracker(InventoryTracker):
    """
    Inventory tracker with automatic persistence
    Extends base tracker with database storage for state restoration and analytics
    """
    
    # Products to track for freshness (configurable)
    # Set to None to track ALL products, or provide a list to track specific ones
    FRESHNESS_TRACKED_PRODUCTS = None  # Track all products
    
    def __init__(
        self,
        smoothing_window: int = 10,
        smoothing_method: str = 'median',
        class_names: Dict[int, str] = None,
        db_path: Optional[str] = None,
        snapshot_interval: float = 5.0,
        expiration_days: int = 5,
        enable_persistence: bool = True,
        sales_confirm_intervals: int = 2,
        sales_min_delta: int = 1,
        sales_cooldown_seconds: float = 10.0,
        enable_alerts: bool = True,
        low_stock_thresholds: Optional[Dict[str, int]] = None,
        alert_confirm_intervals: int = 2,
        alert_cooldown_seconds: float = 3600.0
    ):
        """
        Initialize persistent inventory tracker
        
        Args:
            smoothing_window: Number of frames for smoothing
            smoothing_method: Smoothing method ('median', 'mean', 'mode')
            class_names: Mapping of class IDs to names
            db_path: Path to SQLite database (None for default)
            snapshot_interval: Seconds between inventory snapshots
            expiration_days: Days until products expire
            enable_persistence: Enable/disable persistence (for testing)
            sales_confirm_intervals: Number of intervals to confirm sale
            sales_min_delta: Minimum quantity change to consider
            sales_cooldown_seconds: Cooldown between sales for same product
            enable_alerts: Enable/disable alert system
            low_stock_thresholds: Dict mapping product names to threshold counts
            alert_confirm_intervals: Number of intervals to confirm alert
            alert_cooldown_seconds: Cooldown between alerts for same product+type
        """
        # Initialize base tracker
        super().__init__(smoothing_window, smoothing_method, class_names)
        
        # Persistence configuration
        self.enable_persistence = enable_persistence
        self.snapshot_interval = snapshot_interval
        self.expiration_days = expiration_days
        
        # Initialize persistence manager
        self.persistence = None
        if self.enable_persistence:
            try:
                self.persistence = PersistenceManager(db_path)
                logger.info("Persistence layer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize persistence: {e}")
                self.enable_persistence = False
        
        # Session tracking for video playback
        self.current_session_id: Optional[str] = None

        # Tracking for snapshots and sales detection
        self.last_snapshot_time = 0
        self.last_inventory_snapshot: Dict[str, int] = {}
        
        # Freshness tracking state (in-memory cache)
        self.freshness_state: Dict[str, Dict] = {}
        
        # Initialize sales attribution engine
        self.sales_attribution = None
        if self.enable_persistence:
            try:
                self.sales_attribution = SalesAttributionEngine(
                    confirm_intervals=sales_confirm_intervals,
                    min_delta_threshold=sales_min_delta,
                    cooldown_seconds=sales_cooldown_seconds,
                    snapshot_interval=snapshot_interval
                )
                logger.info("Sales attribution engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize sales attribution: {e}")
        
        # Initialize alert engine
        self.alert_engine = None
        self.enable_alerts = enable_alerts and self.enable_persistence
        if self.enable_alerts:
            try:
                # Use provided thresholds or defaults
                if low_stock_thresholds is None:
                    low_stock_thresholds = {
                        'mango': 3,
                        'watermelon': 2,
                        'pineapple': 2,
                        'passion fruit': 2,
                        'maui custard': 2,
                        'lemon cake': 2
                    }
                
                self.alert_engine = AlertEngine(
                    low_stock_thresholds=low_stock_thresholds,
                    low_stock_confirm_intervals=alert_confirm_intervals,
                    expiration_confirm_intervals=alert_confirm_intervals,
                    alert_cooldown_seconds=alert_cooldown_seconds,
                    enable_email_alerts=True,
                    persistence_manager=self.persistence
                )
                logger.info(f"Alert engine initialized with {len(low_stock_thresholds)} thresholds")
            except Exception as e:
                logger.error(f"Failed to initialize alert engine: {e}")
                self.enable_alerts = False
        
        # Load persisted state on initialization
        if self.enable_persistence:
            self._restore_state()
    
    def set_session_id(self, session_id: str):
        """Set the current video session ID for sales attribution."""
        self.current_session_id = session_id
        logger.info(f"Session ID set: {session_id}")

    def _restore_state(self):
        """
        Restore inventory and freshness state from database on startup
        """
        if not self.persistence:
            return
        
        try:
            # Restore latest inventory snapshot
            latest_inventory = self.persistence.get_latest_inventory()
            if latest_inventory:
                logger.info(f"Restored inventory snapshot: {sum(latest_inventory.values())} items")
                self.last_inventory_snapshot = latest_inventory
            
            # Restore freshness tracking
            freshness_data = self.persistence.get_all_freshness()
            if freshness_data:
                self.freshness_state = freshness_data
                logger.info(f"Restored freshness data for {len(freshness_data)} products")
                
                # Log any expired products
                for product, data in freshness_data.items():
                    if data['is_expired']:
                        logger.warning(f"Product expired: {product} ({data['age_days']:.1f} days old)")
        
        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
    
    def update(self, detections: List[dict]):
        """
        Update inventory with detections and handle persistence
        
        Args:
            detections: List of detection dictionaries
        """
        # Call base class update
        super().update(detections)
        
        if not self.enable_persistence:
            return
        
        # Get current inventory
        current_inventory = self.get_inventory()
        current_time = time.time()
        
        # Update freshness tracking for detected products
        self._update_freshness_tracking(current_inventory, current_time)
        
        # Check if it's time to save a snapshot
        if current_time - self.last_snapshot_time >= self.snapshot_interval:
            self._save_snapshot(current_inventory, current_time)
            self._detect_and_log_sales(current_inventory, current_time)
            self._evaluate_alerts(current_inventory, current_time)
            self.last_snapshot_time = current_time
    
    def _update_freshness_tracking(self, inventory: Dict[str, int], current_time: float):
        """
        Update freshness tracking for products in current inventory
        
        Args:
            inventory: Current inventory dictionary
            current_time: Current timestamp
        """
        if not self.persistence:
            return
        
        try:
            for product_name, count in inventory.items():
                # Normalize product name for matching
                product_lower = product_name.lower()
                
                # Check if this product should be tracked for freshness
                if self.FRESHNESS_TRACKED_PRODUCTS is None:
                    # Track all products
                    is_tracked = True
                else:
                    # Track only specific products
                    is_tracked = any(tracked.lower() in product_lower 
                                   for tracked in self.FRESHNESS_TRACKED_PRODUCTS)
                
                if is_tracked and count > 0:
                    # Check if we already have freshness data
                    if product_name not in self.freshness_state:
                        # First time seeing this product - initialize freshness
                        self.persistence.update_product_freshness(
                            product_name,
                            first_seen_utc=current_time,
                            expiration_days=self.expiration_days
                        )
                        
                        # Update in-memory cache
                        freshness_data = self.persistence.get_product_freshness(product_name)
                        if freshness_data:
                            self.freshness_state[product_name] = freshness_data
                            logger.info(f"Started freshness tracking: {product_name}")
                    else:
                        # Update existing freshness record (updates last_seen)
                        first_seen = self.freshness_state[product_name]['first_seen_utc']
                        self.persistence.update_product_freshness(
                            product_name,
                            first_seen_utc=first_seen,
                            expiration_days=self.expiration_days
                        )
                        
                        # Refresh in-memory cache
                        freshness_data = self.persistence.get_product_freshness(product_name)
                        if freshness_data:
                            self.freshness_state[product_name] = freshness_data
        
        except Exception as e:
            logger.error(f"Failed to update freshness tracking: {e}")
    
    def _save_snapshot(self, inventory: Dict[str, int], current_time: float):
        """
        Save inventory snapshot to database
        
        Args:
            inventory: Current inventory dictionary
            current_time: Current timestamp
        """
        if not self.persistence:
            return
        
        try:
            success = self.persistence.save_inventory_snapshot(
                inventory=inventory,
                frame_number=self.frame_count,
                timestamp_utc=current_time
            )
            
            if success:
                logger.debug(f"Saved inventory snapshot: {sum(inventory.values())} items")
        
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
    
    def _detect_and_log_sales(self, current_inventory: Dict[str, int], current_time: float):
        """
        Detect sales using attribution engine and log to database
        
        Args:
            current_inventory: Current inventory dictionary
            current_time: Current timestamp
        """
        if not self.persistence or not self.sales_attribution:
            return
        
        try:
            # Process snapshot through attribution engine
            sales_events = self.sales_attribution.process_snapshot(
                inventory=current_inventory,
                timestamp=current_time
            )
            
            # Log validated sales to database
            for sale_event in sales_events:
                self.persistence.log_sale(
                    product_name=sale_event['product_name'],
                    quantity_delta=sale_event['quantity_delta'],
                    inventory_before=sale_event.get('inventory_before'),
                    inventory_after=sale_event.get('inventory_after'),
                    timestamp_utc=sale_event['timestamp_utc'],
                    session_id=self.current_session_id
                )
        
        except Exception as e:
            logger.error(f"Failed to detect and log sales: {e}")
    
    def _evaluate_alerts(self, current_inventory: Dict[str, int], current_time: float):
        """
        Evaluate alert conditions and trigger notifications
        
        Args:
            current_inventory: Current inventory dictionary
            current_time: Current timestamp
        """
        if not self.enable_alerts or not self.alert_engine:
            return
        
        try:
            # Evaluate alerts using current inventory and freshness state
            alerts = self.alert_engine.evaluate(
                inventory=current_inventory,
                freshness_state=self.freshness_state,
                timestamp_utc=current_time
            )
            
            if alerts:
                logger.info(f"Generated {len(alerts)} alerts")
        
        except Exception as e:
            logger.error(f"Failed to evaluate alerts: {e}")
    
    def get_active_alerts(self) -> List[Dict]:
        """
        Get currently active alerts
        
        Returns:
            List of active alert dictionaries
        """
        if not self.alert_engine:
            return []
        
        try:
            return self.alert_engine.get_active_alerts()
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """
        Get recent alerts from database
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        if not self.persistence:
            return []
        
        try:
            return self.persistence.get_alerts_log(limit=limit)
        except Exception as e:
            logger.error(f"Failed to retrieve recent alerts: {e}")
            return []
    
    def get_freshness_state(self) -> Dict[str, Dict]:
        """
        Get current freshness state for all tracked products
        
        Returns:
            Dictionary mapping product names to freshness data
        """
        return self.freshness_state.copy()
    
    def get_sales_history(self, limit: int = 100) -> List[Dict]:
        """
        Get recent sales history from database
        
        Args:
            limit: Maximum number of sales to return
            
        Returns:
            List of sales log entries
        """
        if not self.persistence:
            return []
        
        try:
            return self.persistence.get_sales_log(limit=limit)
        except Exception as e:
            logger.error(f"Failed to retrieve sales history: {e}")
            return []
    
    def get_persistence_stats(self) -> Dict:
        """
        Get persistence layer statistics
        
        Returns:
            Dictionary with database statistics
        """
        if not self.persistence:
            return {'enabled': False}
        
        try:
            stats = self.persistence.get_database_stats()
            stats['enabled'] = True
            stats['snapshot_interval'] = self.snapshot_interval
            stats['expiration_days'] = self.expiration_days
            return stats
        except Exception as e:
            logger.error(f"Failed to get persistence stats: {e}")
            return {'enabled': True, 'error': str(e)}
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict:
        """
        Clean up old data from database
        
        Args:
            days_to_keep: Number of days of data to retain
            
        Returns:
            Dictionary with cleanup results
        """
        if not self.persistence:
            return {'enabled': False}
        
        try:
            snapshots, freshness, sales = self.persistence.cleanup_old_data(days_to_keep)
            return {
                'enabled': True,
                'snapshots_deleted': snapshots,
                'freshness_deleted': freshness,
                'sales_deleted': sales,
                'days_kept': days_to_keep
            }
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {'enabled': True, 'error': str(e)}
    
    def close(self):
        """
        Close persistence layer and cleanup resources
        """
        if self.persistence:
            try:
                # Save final snapshot
                final_inventory = self.get_inventory()
                if final_inventory:
                    self.persistence.save_inventory_snapshot(
                        inventory=final_inventory,
                        frame_number=self.frame_count,
                        timestamp_utc=time.time()
                    )
                
                self.persistence.close()
                logger.info("Persistence layer closed")
            except Exception as e:
                logger.error(f"Error closing persistence layer: {e}")
