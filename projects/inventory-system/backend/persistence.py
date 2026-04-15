"""
Data Persistence Layer for Inventory System
Provides SQLite-based storage for inventory snapshots, freshness tracking, and sales logs
"""

import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import pytz
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# US Eastern Time zone for sales log timestamps
EST = pytz.timezone('US/Eastern')


class PersistenceManager:
    """
    Manages SQLite database for inventory persistence
    Handles inventory snapshots, freshness tracking, and sales logs
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize persistence manager
        
        Args:
            db_path: Path to SQLite database file (default: data/inventory.db)
        """
        if db_path is None:
            # Default to project_root/data/inventory.db
            project_root = Path(__file__).parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / 'inventory.db'
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = None
        self._initialize_database()
        self._run_startup_maintenance()
        
        logger.info(f"Persistence manager initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections
        Ensures proper transaction handling and connection cleanup
        Uses WAL mode for better concurrency and crash recovery
        """
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        # Enable WAL mode for better concurrency and safety
        conn.execute('PRAGMA journal_mode=WAL')
        # Use NORMAL synchronous mode (safe with WAL)
        conn.execute('PRAGMA synchronous=NORMAL')
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """
        Create database schema if it doesn't exist
        Sets up tables and indexes for inventory, freshness, and sales
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Inventory snapshots table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inventory_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp_utc REAL NOT NULL,
                        frame_number INTEGER NOT NULL,
                        total_items INTEGER NOT NULL,
                        inventory_json TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)
                
                # Index for timestamp lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_inventory_timestamp 
                    ON inventory_snapshots(timestamp_utc DESC)
                """)
                
                # Freshness tracking table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS product_freshness (
                        product_name TEXT PRIMARY KEY,
                        first_seen_utc REAL NOT NULL,
                        last_seen_utc REAL NOT NULL,
                        is_expired BOOLEAN DEFAULT 0,
                        expiration_days INTEGER DEFAULT 5,
                        updated_at REAL NOT NULL
                    )
                """)
                
                # Sales log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sales_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp_utc REAL NOT NULL,
                        timestamp_est TEXT NOT NULL,
                        product_name TEXT NOT NULL,
                        quantity_delta INTEGER NOT NULL,
                        inventory_before INTEGER,
                        inventory_after INTEGER,
                        created_at REAL NOT NULL
                    )
                """)

                # Migration: add session_id column if not present
                cursor.execute("PRAGMA table_info(sales_log)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'session_id' not in columns:
                    cursor.execute("ALTER TABLE sales_log ADD COLUMN session_id TEXT")
                
                # Index for sales log timestamp lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sales_timestamp 
                    ON sales_log(timestamp_utc DESC)
                """)
                
                # Index for sales by product
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sales_product 
                    ON sales_log(product_name, timestamp_utc DESC)
                """)
                
                # Alerts log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alerts_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp_utc REAL NOT NULL,
                        timestamp_est TEXT NOT NULL,
                        alert_type TEXT NOT NULL,
                        product_name TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        metadata_json TEXT,
                        acknowledged BOOLEAN DEFAULT 0,
                        created_at REAL NOT NULL
                    )
                """)
                
                # Index for alerts by timestamp
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                    ON alerts_log(timestamp_utc DESC)
                """)
                
                # Index for alerts by product and type
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_product_type 
                    ON alerts_log(product_name, alert_type, timestamp_utc DESC)
                """)
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
    
    def _run_startup_maintenance(self, retention_days: int = 30):
        """
        Run maintenance tasks on startup
        Cleans up old data to prevent unbounded growth
        
        Args:
            retention_days: Number of days of data to retain (default: 30)
        """
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Count records before cleanup
                cursor.execute("SELECT COUNT(*) as count FROM inventory_snapshots")
                snapshots_before = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM alerts_log")
                alerts_before = cursor.fetchone()['count']
                
                # Delete old inventory snapshots (keep recent for state restoration)
                cursor.execute("""
                    DELETE FROM inventory_snapshots 
                    WHERE timestamp_utc < ? 
                    AND id NOT IN (
                        SELECT id FROM inventory_snapshots 
                        ORDER BY timestamp_utc DESC 
                        LIMIT 100
                    )
                """, (cutoff_time,))
                snapshots_deleted = cursor.rowcount
                
                # Delete old alerts (keep recent for reference)
                cursor.execute("""
                    DELETE FROM alerts_log 
                    WHERE timestamp_utc < ?
                    AND id NOT IN (
                        SELECT id FROM alerts_log 
                        ORDER BY timestamp_utc DESC 
                        LIMIT 100
                    )
                """, (cutoff_time,))
                alerts_deleted = cursor.rowcount
                
                if snapshots_deleted > 0 or alerts_deleted > 0:
                    logger.info(f"Startup maintenance: deleted {snapshots_deleted} old snapshots, "
                              f"{alerts_deleted} old alerts (retention: {retention_days} days)")
                
        except Exception as e:
            logger.warning(f"Startup maintenance failed (non-critical): {e}")
    
    def save_inventory_snapshot(
        self,
        inventory: Dict[str, int],
        frame_number: int,
        timestamp_utc: Optional[float] = None
    ) -> bool:
        """
        Save inventory snapshot to database
        
        Args:
            inventory: Dictionary mapping product names to counts
            frame_number: Current frame number
            timestamp_utc: UTC timestamp (defaults to now)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if timestamp_utc is None:
                timestamp_utc = datetime.now(timezone.utc).timestamp()
            
            total_items = sum(inventory.values())
            inventory_json = json.dumps(inventory, sort_keys=True)
            created_at = datetime.now(timezone.utc).timestamp()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory_snapshots 
                    (timestamp_utc, frame_number, total_items, inventory_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (timestamp_utc, frame_number, total_items, inventory_json, created_at))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save inventory snapshot: {e}")
            return False
    
    def get_latest_inventory(self) -> Optional[Dict[str, int]]:
        """
        Retrieve the most recent inventory snapshot
        
        Returns:
            Dictionary mapping product names to counts, or None if no data
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT inventory_json 
                    FROM inventory_snapshots 
                    ORDER BY timestamp_utc DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    return json.loads(row['inventory_json'])
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve latest inventory: {e}")
            return None
    
    def get_inventory_history(
        self,
        limit: int = 100,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict]:
        """
        Retrieve inventory history within time range
        
        Args:
            limit: Maximum number of snapshots to return
            start_time: Start timestamp (UTC)
            end_time: End timestamp (UTC)
            
        Returns:
            List of inventory snapshot dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM inventory_snapshots WHERE 1=1"
                params = []
                
                if start_time is not None:
                    query += " AND timestamp_utc >= ?"
                    params.append(start_time)
                
                if end_time is not None:
                    query += " AND timestamp_utc <= ?"
                    params.append(end_time)
                
                query += " ORDER BY timestamp_utc DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                snapshots = []
                for row in cursor.fetchall():
                    snapshots.append({
                        'id': row['id'],
                        'timestamp_utc': row['timestamp_utc'],
                        'frame_number': row['frame_number'],
                        'total_items': row['total_items'],
                        'inventory': json.loads(row['inventory_json'])
                    })
                
                return snapshots
                
        except Exception as e:
            logger.error(f"Failed to retrieve inventory history: {e}")
            return []
    
    def update_product_freshness(
        self,
        product_name: str,
        first_seen_utc: Optional[float] = None,
        expiration_days: int = 5
    ) -> bool:
        """
        Update or create freshness tracking for a product
        
        Args:
            product_name: Name of the product
            first_seen_utc: UTC timestamp when first detected (defaults to now)
            expiration_days: Days until expiration
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            now_utc = datetime.now(timezone.utc).timestamp()
            
            if first_seen_utc is None:
                first_seen_utc = now_utc
            
            # Calculate if expired
            age_seconds = now_utc - first_seen_utc
            age_days = age_seconds / 86400  # seconds per day
            is_expired = age_days > expiration_days
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Try to insert, or update if exists
                cursor.execute("""
                    INSERT INTO product_freshness 
                    (product_name, first_seen_utc, last_seen_utc, is_expired, expiration_days, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(product_name) DO UPDATE SET
                        last_seen_utc = excluded.last_seen_utc,
                        is_expired = excluded.is_expired,
                        updated_at = excluded.updated_at
                """, (product_name, first_seen_utc, now_utc, is_expired, expiration_days, now_utc))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update product freshness for {product_name}: {e}")
            return False
    
    def get_product_freshness(self, product_name: str) -> Optional[Dict]:
        """
        Get freshness data for a specific product
        
        Args:
            product_name: Name of the product
            
        Returns:
            Dictionary with freshness data, or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM product_freshness WHERE product_name = ?
                """, (product_name,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'product_name': row['product_name'],
                        'first_seen_utc': row['first_seen_utc'],
                        'last_seen_utc': row['last_seen_utc'],
                        'is_expired': bool(row['is_expired']),
                        'expiration_days': row['expiration_days'],
                        'age_days': (datetime.now(timezone.utc).timestamp() - row['first_seen_utc']) / 86400
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve freshness for {product_name}: {e}")
            return None
    
    def get_all_freshness(self) -> Dict[str, Dict]:
        """
        Get freshness data for all tracked products
        
        Returns:
            Dictionary mapping product names to freshness data
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM product_freshness")
                
                freshness_data = {}
                now_utc = datetime.now(timezone.utc).timestamp()
                
                for row in cursor.fetchall():
                    freshness_data[row['product_name']] = {
                        'first_seen_utc': row['first_seen_utc'],
                        'last_seen_utc': row['last_seen_utc'],
                        'is_expired': bool(row['is_expired']),
                        'expiration_days': row['expiration_days'],
                        'age_days': (now_utc - row['first_seen_utc']) / 86400
                    }
                
                return freshness_data
                
        except Exception as e:
            logger.error(f"Failed to retrieve all freshness data: {e}")
            return {}
    
    def log_sale(
        self,
        product_name: str,
        quantity_delta: int,
        inventory_before: Optional[int] = None,
        inventory_after: Optional[int] = None,
        timestamp_utc: Optional[float] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Log a sales event (inventory decrease)

        Args:
            product_name: Name of the product sold
            quantity_delta: Number of items sold (positive number)
            inventory_before: Inventory count before sale
            inventory_after: Inventory count after sale
            timestamp_utc: UTC timestamp (defaults to now)
            session_id: Optional video session identifier

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            if timestamp_utc is None:
                timestamp_utc = datetime.now(timezone.utc).timestamp()

            # Convert UTC to EST for display
            dt_utc = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc)
            dt_est = dt_utc.astimezone(EST)
            timestamp_est = dt_est.strftime('%Y-%m-%d %I:%M:%S %p EST')

            created_at = datetime.now(timezone.utc).timestamp()

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sales_log
                    (timestamp_utc, timestamp_est, product_name, quantity_delta,
                     inventory_before, inventory_after, session_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp_utc, timestamp_est, product_name, quantity_delta,
                      inventory_before, inventory_after, session_id, created_at))

            logger.info(f"Sale logged: {product_name} x{quantity_delta} at {timestamp_est}")
            return True

        except Exception as e:
            logger.error(f"Failed to log sale: {e}")
            return False

    def get_sales_by_session(self, session_id: str) -> List[Dict]:
        """
        Retrieve all sales log entries for a specific video session

        Args:
            session_id: Video session UUID

        Returns:
            List of sales log entry dictionaries ordered by timestamp ascending
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sales_log WHERE session_id = ? ORDER BY timestamp_utc ASC
                """, (session_id,))

                sales = []
                for row in cursor.fetchall():
                    sales.append({
                        'id': row['id'],
                        'timestamp_utc': row['timestamp_utc'],
                        'timestamp_est': row['timestamp_est'],
                        'product_name': row['product_name'],
                        'quantity_delta': row['quantity_delta'],
                        'inventory_before': row['inventory_before'],
                        'inventory_after': row['inventory_after'],
                        'session_id': row['session_id']
                    })

                return sales

        except Exception as e:
            logger.error(f"Failed to retrieve sales by session {session_id}: {e}")
            return []
    
    def get_sales_log(
        self,
        limit: int = 100,
        product_name: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict]:
        """
        Retrieve sales log entries
        
        Args:
            limit: Maximum number of entries to return
            product_name: Filter by product name (optional)
            start_time: Start timestamp (UTC, optional)
            end_time: End timestamp (UTC, optional)
            
        Returns:
            List of sales log entry dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM sales_log WHERE 1=1"
                params = []
                
                if product_name is not None:
                    query += " AND product_name = ?"
                    params.append(product_name)
                
                if start_time is not None:
                    query += " AND timestamp_utc >= ?"
                    params.append(start_time)
                
                if end_time is not None:
                    query += " AND timestamp_utc <= ?"
                    params.append(end_time)
                
                query += " ORDER BY timestamp_utc DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                sales = []
                for row in cursor.fetchall():
                    sales.append({
                        'id': row['id'],
                        'timestamp_utc': row['timestamp_utc'],
                        'timestamp_est': row['timestamp_est'],
                        'product_name': row['product_name'],
                        'quantity_delta': row['quantity_delta'],
                        'inventory_before': row['inventory_before'],
                        'inventory_after': row['inventory_after']
                    })
                
                return sales
                
        except Exception as e:
            logger.error(f"Failed to retrieve sales log: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Tuple[int, int, int]:
        """
        Remove old data to prevent database bloat
        
        Args:
            days_to_keep: Number of days of data to retain
            
        Returns:
            Tuple of (snapshots_deleted, freshness_deleted, sales_deleted)
        """
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (days_to_keep * 86400)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old inventory snapshots
                cursor.execute("""
                    DELETE FROM inventory_snapshots WHERE timestamp_utc < ?
                """, (cutoff_time,))
                snapshots_deleted = cursor.rowcount
                
                # Delete freshness records for products not seen recently
                cursor.execute("""
                    DELETE FROM product_freshness WHERE last_seen_utc < ?
                """, (cutoff_time,))
                freshness_deleted = cursor.rowcount
                
                # Delete old sales log entries
                cursor.execute("""
                    DELETE FROM sales_log WHERE timestamp_utc < ?
                """, (cutoff_time,))
                sales_deleted = cursor.rowcount
                
                # Vacuum to reclaim space
                cursor.execute("VACUUM")
                
                logger.info(f"Cleanup complete: {snapshots_deleted} snapshots, "
                           f"{freshness_deleted} freshness records, {sales_deleted} sales deleted")
                
                return (snapshots_deleted, freshness_deleted, sales_deleted)
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return (0, 0, 0)
    
    def get_database_stats(self) -> Dict:
        """
        Get database statistics
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Count records in each table
                cursor.execute("SELECT COUNT(*) as count FROM inventory_snapshots")
                snapshot_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM product_freshness")
                freshness_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM sales_log")
                sales_count = cursor.fetchone()['count']
                
                # Get database file size
                db_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
                db_size_mb = db_size_bytes / (1024 * 1024)
                
                return {
                    'database_path': str(self.db_path),
                    'database_size_mb': round(db_size_mb, 2),
                    'snapshot_count': snapshot_count,
                    'freshness_count': freshness_count,
                    'sales_count': sales_count
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def log_alert(
        self,
        alert_type: str,
        product_name: str,
        severity: str,
        message: str,
        timestamp_utc: float,
        timestamp_est: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Log an alert event to database
        
        Args:
            alert_type: Type of alert (low_stock, expiration)
            product_name: Product that triggered alert
            severity: Severity level (info, warning, critical)
            message: Alert message
            timestamp_utc: UTC timestamp
            timestamp_est: EST formatted timestamp
            metadata: Additional alert metadata
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            created_at = datetime.now(timezone.utc).timestamp()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alerts_log 
                    (timestamp_utc, timestamp_est, alert_type, product_name, 
                     severity, message, metadata_json, acknowledged, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (timestamp_utc, timestamp_est, alert_type, product_name,
                      severity, message, metadata_json, created_at))
            
            logger.info(f"Alert logged: {alert_type} - {product_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
            return False
    
    def get_alerts_log(
        self,
        limit: int = 100,
        alert_type: Optional[str] = None,
        product_name: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Dict]:
        """
        Retrieve alerts log entries
        
        Args:
            limit: Maximum number of entries to return
            alert_type: Filter by alert type (optional)
            product_name: Filter by product name (optional)
            start_time: Start timestamp (UTC, optional)
            end_time: End timestamp (UTC, optional)
            acknowledged: Filter by acknowledged status (optional)
            
        Returns:
            List of alert log entry dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM alerts_log WHERE 1=1"
                params = []
                
                if alert_type is not None:
                    query += " AND alert_type = ?"
                    params.append(alert_type)
                
                if product_name is not None:
                    query += " AND product_name = ?"
                    params.append(product_name)
                
                if start_time is not None:
                    query += " AND timestamp_utc >= ?"
                    params.append(start_time)
                
                if end_time is not None:
                    query += " AND timestamp_utc <= ?"
                    params.append(end_time)
                
                if acknowledged is not None:
                    query += " AND acknowledged = ?"
                    params.append(1 if acknowledged else 0)
                
                query += " ORDER BY timestamp_utc DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                alerts = []
                for row in cursor.fetchall():
                    metadata = json.loads(row['metadata_json']) if row['metadata_json'] else {}
                    alerts.append({
                        'id': row['id'],
                        'timestamp_utc': row['timestamp_utc'],
                        'timestamp_est': row['timestamp_est'],
                        'alert_type': row['alert_type'],
                        'product_name': row['product_name'],
                        'severity': row['severity'],
                        'message': row['message'],
                        'metadata': metadata,
                        'acknowledged': bool(row['acknowledged'])
                    })
                
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to retrieve alerts log: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        Mark an alert as acknowledged
        
        Args:
            alert_id: Alert ID to acknowledge
            
        Returns:
            True if acknowledged successfully, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alerts_log SET acknowledged = 1 WHERE id = ?
                """, (alert_id,))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def close(self):
        """
        Close database connection and cleanup
        """
        logger.info("Persistence manager closed")
