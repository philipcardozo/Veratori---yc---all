"""
Sales Attribution Module
Provides per-product sales detection with temporal validation and noise resistance
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class SalesAttributionEngine:
    """
    Detects and attributes sales to specific products using temporal validation
    Compares consecutive inventory snapshots to identify reliable decreases
    """
    
    def __init__(
        self,
        confirm_intervals: int = 2,
        min_delta_threshold: int = 1,
        cooldown_seconds: float = 10.0,
        snapshot_interval: float = 5.0
    ):
        """
        Initialize sales attribution engine
        
        Args:
            confirm_intervals: Number of consecutive intervals a decrease must persist (default: 2)
            min_delta_threshold: Minimum quantity change to consider (default: 1)
            cooldown_seconds: Seconds to wait before recording another sale for same product
            snapshot_interval: Seconds between inventory snapshots (must match persistence layer)
        """
        self.confirm_intervals = confirm_intervals
        self.min_delta_threshold = min_delta_threshold
        self.cooldown_seconds = cooldown_seconds
        self.snapshot_interval = snapshot_interval
        
        # History buffer for temporal validation
        # Format: deque of (timestamp, inventory_dict) tuples
        self.snapshot_history: deque = deque(maxlen=confirm_intervals + 1)
        
        # Track last sale time per product for cooldown
        self.last_sale_time: Dict[str, float] = {}
        
        # Track pending decreases for validation
        # Format: {product_name: [(timestamp, delta), ...]}
        self.pending_decreases: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        
        # Statistics
        self.total_sales_detected = 0
        self.sales_by_product: Dict[str, int] = defaultdict(int)
        self.false_positives_filtered = 0
        
        logger.info(f"Sales attribution initialized: confirm_intervals={confirm_intervals}, "
                   f"min_delta_threshold={min_delta_threshold}, cooldown={cooldown_seconds}s")
    
    def process_snapshot(
        self,
        inventory: Dict[str, int],
        timestamp: float
    ) -> List[Dict]:
        """
        Process a new inventory snapshot and detect attributed sales
        
        Args:
            inventory: Current inventory dictionary {product_name: count}
            timestamp: Current timestamp (UTC)
            
        Returns:
            List of sale event dictionaries with product attribution
        """
        # Add snapshot to history
        self.snapshot_history.append((timestamp, inventory.copy()))
        
        # Need at least 2 snapshots to detect changes
        if len(self.snapshot_history) < 2:
            return []
        
        # Detect sales with temporal validation
        sales_events = self._detect_attributed_sales(timestamp)
        
        # Update statistics
        self.total_sales_detected += len(sales_events)
        for sale in sales_events:
            self.sales_by_product[sale['product_name']] += sale['quantity_delta']
        
        return sales_events
    
    def _detect_attributed_sales(self, current_timestamp: float) -> List[Dict]:
        """
        Detect sales by comparing recent snapshots with temporal validation
        
        Args:
            current_timestamp: Current timestamp
            
        Returns:
            List of validated sale events
        """
        sales_events = []
        
        # Get current and previous snapshots
        current_time, current_inventory = self.snapshot_history[-1]
        previous_time, previous_inventory = self.snapshot_history[-2]
        
        # Compute per-product deltas
        all_products = set(current_inventory.keys()) | set(previous_inventory.keys())
        
        for product_name in all_products:
            current_count = current_inventory.get(product_name, 0)
            previous_count = previous_inventory.get(product_name, 0)
            delta = current_count - previous_count
            
            # Check for decrease or stable low count
            if delta < 0 and abs(delta) >= self.min_delta_threshold:
                # Decrease detected - add to pending
                self.pending_decreases[product_name].append((current_timestamp, delta))
                logger.info(f"Attribution: {product_name} delta={delta}, pending={len(self.pending_decreases[product_name])}")
            elif delta == 0 and product_name in self.pending_decreases:
                # Count stable - check if we should validate
                logger.debug(f"Attribution: {product_name} stable at decreased level, pending validation")
                pass  # Keep pending, will validate below
            elif delta > 0:
                # Increase detected - clear any pending decreases for this product
                if product_name in self.pending_decreases:
                    logger.debug(f"Attribution: {product_name} increased, clearing pending")
                    self.pending_decreases[product_name].clear()
            
            # Check if this product has a validated decrease
            if product_name in self.pending_decreases and len(self.pending_decreases[product_name]) > 0:
                if self._validate_decrease(product_name, current_timestamp):
                    # Check cooldown
                    if self._check_cooldown(product_name, current_timestamp):
                        # Get the total decrease amount
                        quantity_sold = abs(delta) if delta < 0 else abs(self.pending_decreases[product_name][0][1])
                        
                        # Record sale
                        sale_event = {
                            'product_name': product_name,
                            'quantity_delta': quantity_sold,
                            'inventory_before': previous_count + quantity_sold if delta == 0 else previous_count,
                            'inventory_after': current_count,
                            'timestamp_utc': current_timestamp,
                            'validated': True
                        }
                        sales_events.append(sale_event)
                        
                        # Update last sale time
                        self.last_sale_time[product_name] = current_timestamp
                        
                        # Clear pending for this product
                        self.pending_decreases[product_name].clear()
                        
                        logger.info(f"✓ Sale attributed: {product_name} x{quantity_sold} "
                                  f"({sale_event['inventory_before']} → {current_count})")
                    else:
                        logger.info(f"⊗ Sale suppressed by cooldown: {product_name} "
                                  f"(last sale {current_timestamp - self.last_sale_time[product_name]:.1f}s ago)")
        
        # Clean up old pending decreases
        self._cleanup_pending_decreases(current_timestamp)
        
        # Check for unattributed total decrease (fallback)
        total_current = sum(current_inventory.values())
        total_previous = sum(previous_inventory.values())
        total_delta = total_current - total_previous
        
        if total_delta < 0 and not sales_events:
            # Total inventory decreased but no specific product attributed
            # This could be detection noise - apply strict validation
            if self._validate_total_decrease(total_delta, current_timestamp):
                # Record as "Unknown" sale after validation
                sale_event = {
                    'product_name': 'Unknown',
                    'quantity_delta': abs(total_delta),
                    'inventory_before': total_previous,
                    'inventory_after': total_current,
                    'timestamp_utc': current_timestamp,
                    'validated': False
                }
                sales_events.append(sale_event)
                
                logger.warning(f"Unattributed sale detected: {abs(total_delta)} items "
                             f"({total_previous} → {total_current})")
        
        return sales_events
    
    def _validate_decrease(self, product_name: str, current_timestamp: float) -> bool:
        """
        Validate that a decrease has persisted for required number of intervals
        
        Args:
            product_name: Product to validate
            current_timestamp: Current timestamp
            
        Returns:
            True if decrease is validated, False otherwise
        """
        # Check if we have enough snapshot history
        if len(self.snapshot_history) < self.confirm_intervals + 1:
            return False
        
        # Get recent snapshots
        recent_snapshots = list(self.snapshot_history)[-(self.confirm_intervals + 1):]
        
        # Extract counts for this product across snapshots
        counts = [inv.get(product_name, 0) for _, inv in recent_snapshots]
        
        # Check if count has been consistently decreasing or stable at lower level
        initial_count = counts[0]
        
        for count in counts[1:]:
            if count > initial_count:
                # Count increased - not a persistent decrease
                return False
            if count == initial_count:
                # Count returned to initial - not a persistent decrease
                return False
        
        # Count has remained at or below the decreased level
        return True
    
    def _validate_total_decrease(self, total_delta: int, current_timestamp: float) -> bool:
        """
        Validate unattributed total inventory decrease
        More strict validation to avoid false positives from noise
        
        Args:
            total_delta: Total inventory change (negative)
            current_timestamp: Current timestamp
            
        Returns:
            True if validated, False otherwise
        """
        # For unattributed decreases, require larger threshold
        if abs(total_delta) < self.min_delta_threshold * 2:
            self.false_positives_filtered += 1
            return False
        
        # Check if we have enough history
        if len(self.snapshot_history) < self.confirm_intervals + 1:
            return False
        
        # Verify total has been consistently decreasing
        recent_snapshots = list(self.snapshot_history)[-self.confirm_intervals-1:]
        totals = [sum(inv.values()) for _, inv in recent_snapshots]
        
        # Check for consistent decrease trend
        for i in range(1, len(totals)):
            if totals[i] >= totals[i-1]:
                # Not consistently decreasing
                self.false_positives_filtered += 1
                return False
        
        return True
    
    def _check_cooldown(self, product_name: str, current_timestamp: float) -> bool:
        """
        Check if enough time has passed since last sale for this product
        
        Args:
            product_name: Product to check
            current_timestamp: Current timestamp
            
        Returns:
            True if cooldown period has passed, False otherwise
        """
        if product_name not in self.last_sale_time:
            return True
        
        time_since_last_sale = current_timestamp - self.last_sale_time[product_name]
        
        if time_since_last_sale < self.cooldown_seconds:
            logger.debug(f"Sale cooldown active for {product_name}: "
                        f"{time_since_last_sale:.1f}s < {self.cooldown_seconds}s")
            return False
        
        return True
    
    def _cleanup_pending_decreases(self, current_timestamp: float):
        """
        Remove old pending decreases that are no longer relevant
        
        Args:
            current_timestamp: Current timestamp
        """
        max_age = self.snapshot_interval * (self.confirm_intervals + 2)
        
        for product_name in list(self.pending_decreases.keys()):
            # Filter out old entries
            self.pending_decreases[product_name] = [
                (ts, delta) for ts, delta in self.pending_decreases[product_name]
                if current_timestamp - ts < max_age
            ]
            
            # Remove empty entries
            if not self.pending_decreases[product_name]:
                del self.pending_decreases[product_name]
    
    def get_statistics(self) -> Dict:
        """
        Get sales attribution statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_sales_detected': self.total_sales_detected,
            'sales_by_product': dict(self.sales_by_product),
            'false_positives_filtered': self.false_positives_filtered,
            'pending_validations': sum(len(p) for p in self.pending_decreases.values()),
            'products_on_cooldown': len([
                p for p, t in self.last_sale_time.items()
                if time.time() - t < self.cooldown_seconds
            ]),
            'config': {
                'confirm_intervals': self.confirm_intervals,
                'min_delta_threshold': self.min_delta_threshold,
                'cooldown_seconds': self.cooldown_seconds
            }
        }
    
    def reset(self):
        """
        Reset attribution engine state
        """
        self.snapshot_history.clear()
        self.last_sale_time.clear()
        self.pending_decreases.clear()
        self.total_sales_detected = 0
        self.sales_by_product.clear()
        self.false_positives_filtered = 0
        
        logger.info("Sales attribution engine reset")


class SalesEvent:
    """
    Immutable sales event record
    """
    
    def __init__(
        self,
        product_name: str,
        quantity_delta: int,
        inventory_before: int,
        inventory_after: int,
        timestamp_utc: float,
        validated: bool = True
    ):
        """
        Initialize sales event
        
        Args:
            product_name: Name of product sold
            quantity_delta: Number of items sold
            inventory_before: Inventory count before sale
            inventory_after: Inventory count after sale
            timestamp_utc: UTC timestamp of sale
            validated: Whether sale was validated via temporal check
        """
        self.product_name = product_name
        self.quantity_delta = quantity_delta
        self.inventory_before = inventory_before
        self.inventory_after = inventory_after
        self.timestamp_utc = timestamp_utc
        self.validated = validated
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary for persistence
        
        Returns:
            Dictionary representation
        """
        return {
            'product_name': self.product_name,
            'quantity_delta': self.quantity_delta,
            'inventory_before': self.inventory_before,
            'inventory_after': self.inventory_after,
            'timestamp_utc': self.timestamp_utc,
            'validated': self.validated
        }
    
    def __repr__(self) -> str:
        status = "✓" if self.validated else "?"
        return (f"SalesEvent({status} {self.product_name} x{self.quantity_delta}, "
                f"{self.inventory_before}→{self.inventory_after})")
