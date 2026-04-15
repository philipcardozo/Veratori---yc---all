"""
Restock Manager - Handles employee restock submissions
Stores submissions, detection results, and manages moderation workflow
"""

import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import hashlib

logger = logging.getLogger(__name__)


class RestockManager:
    """
    Manages restock submissions from mobile app
    """
    
    def __init__(self, db_path: Optional[Path] = None, photos_dir: Optional[Path] = None):
        """
        Initialize restock manager
        
        Args:
            db_path: Path to SQLite database (default: restock_submissions.db in project root)
            photos_dir: Directory to store uploaded photos (default: restock_photos/ in project root)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'veratori_restock.db'
        if photos_dir is None:
            photos_dir = Path(__file__).parent.parent / 'restock_photos'
        
        self.db_path = db_path
        self.photos_dir = photos_dir
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restock_submissions (
                submission_id TEXT PRIMARY KEY,
                employee_username TEXT NOT NULL,
                franchise_id TEXT NOT NULL,
                station TEXT NOT NULL,
                product TEXT NOT NULL,
                notes TEXT,
                device_id TEXT,
                latitude REAL,
                longitude REAL,
                timestamp REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by TEXT,
                reviewed_at REAL,
                feedback TEXT,
                detection_results TEXT,
                created_at REAL NOT NULL
            )
        ''')
        
        # Photos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restock_photos (
                photo_id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                photo_index INTEGER NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES restock_submissions(submission_id) ON DELETE CASCADE
            )
        ''')
        
        # Notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restock_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_username TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                submission_id TEXT,
                read INTEGER DEFAULT 0,
                timestamp_utc REAL NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES restock_submissions(submission_id) ON DELETE SET NULL
            )
        ''')
        
        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restock_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id TEXT NOT NULL,
                action TEXT NOT NULL,
                performed_by TEXT NOT NULL,
                timestamp REAL NOT NULL,
                details TEXT,
                FOREIGN KEY (submission_id) REFERENCES restock_submissions(submission_id) ON DELETE CASCADE
            )
        ''')
        
        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_submissions_employee ON restock_submissions(employee_username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_submissions_franchise ON restock_submissions(franchise_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_submissions_status ON restock_submissions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_submissions_timestamp ON restock_submissions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_photos_submission ON restock_photos(submission_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_employee ON restock_notifications(employee_username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_read ON restock_notifications(read)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Restock database initialized at {self.db_path}")
    
    def create_submission(
        self,
        employee_username: str,
        franchise_id: str,
        station: str,
        product: str,
        notes: Optional[str] = None,
        device_id: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        photos: List[bytes] = None,
        detection_results: Optional[Dict] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new restock submission
        
        Args:
            employee_username: Employee username
            franchise_id: Franchise ID
            station: Station name
            product: Product name
            notes: Optional notes
            device_id: Optional device ID
            latitude: Optional latitude
            longitude: Optional longitude
            photos: List of photo bytes
            detection_results: Optional detection results dict
        
        Returns:
            Tuple of (success, message, submission_id)
        """
        if photos is None or len(photos) < 3:
            return False, "Minimum 3 photos required", None
        
        # Check for duplicate submission (within 10 minutes)
        if self._check_duplicate_submission(employee_username, station, product, time.time()):
            return False, "Duplicate submission detected. Please wait before submitting again.", None
        
        submission_id = str(uuid.uuid4())
        timestamp = time.time()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert submission
            cursor.execute('''
                INSERT INTO restock_submissions (
                    submission_id, employee_username, franchise_id, station, product,
                    notes, device_id, latitude, longitude, timestamp,
                    detection_results, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                submission_id, employee_username, franchise_id, station, product,
                notes, device_id, latitude, longitude, timestamp,
                json.dumps(detection_results) if detection_results else None,
                timestamp
            ))
            
            # Save photos
            for idx, photo_data in enumerate(photos):
                photo_id = str(uuid.uuid4())
                filename = f"{submission_id}_{idx}.jpg"
                file_path = self.photos_dir / filename
                
                # Write photo file
                with open(file_path, 'wb') as f:
                    f.write(photo_data)
                
                # Insert photo record
                cursor.execute('''
                    INSERT INTO restock_photos (photo_id, submission_id, filename, file_path, photo_index)
                    VALUES (?, ?, ?, ?, ?)
                ''', (photo_id, submission_id, filename, str(file_path), idx))
            
            # Log creation
            cursor.execute('''
                INSERT INTO restock_audit_log (submission_id, action, performed_by, timestamp, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (submission_id, 'created', employee_username, timestamp, json.dumps({'station': station, 'product': product})))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Restock submission created: {submission_id} by {employee_username}")
            return True, "Submission created successfully", submission_id
            
        except Exception as e:
            logger.error(f"Error creating submission: {e}")
            return False, f"Error creating submission: {str(e)}", None
    
    def _check_duplicate_submission(
        self,
        employee_username: str,
        station: str,
        product: str,
        current_time: float,
        cooldown_seconds: int = 600  # 10 minutes
    ) -> bool:
        """Check if a similar submission was made recently"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM restock_submissions
            WHERE employee_username = ? AND station = ? AND product = ?
            AND timestamp > ?
        ''', (employee_username, station, product, current_time - cooldown_seconds))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def get_employee_submissions(self, employee_username: str) -> List[Dict]:
        """Get all submissions for an employee"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, GROUP_CONCAT(p.filename) as photos
            FROM restock_submissions s
            LEFT JOIN restock_photos p ON s.submission_id = p.submission_id
            WHERE s.employee_username = ?
            GROUP BY s.submission_id
            ORDER BY s.timestamp DESC
        ''', (employee_username,))
        
        rows = cursor.fetchall()
        conn.close()
        
        submissions = []
        for row in rows:
            submission = dict(row)
            submission['photos'] = submission['photos'].split(',') if submission['photos'] else []
            if submission['detection_results']:
                submission['detection_results'] = json.loads(submission['detection_results'])
            submissions.append(submission)
        
        return submissions
    
    def get_all_submissions(
        self,
        franchise_id: Optional[str] = None,
        status: Optional[str] = None,
        employee: Optional[str] = None
    ) -> List[Dict]:
        """Get all submissions (manager view)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT s.*, GROUP_CONCAT(p.filename) as photos
            FROM restock_submissions s
            LEFT JOIN restock_photos p ON s.submission_id = p.submission_id
            WHERE 1=1
        '''
        params = []
        
        if franchise_id:
            query += ' AND s.franchise_id = ?'
            params.append(franchise_id)
        
        if status:
            query += ' AND s.status = ?'
            params.append(status)
        
        if employee:
            query += ' AND s.employee_username = ?'
            params.append(employee)
        
        query += ' GROUP BY s.submission_id ORDER BY s.timestamp DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        submissions = []
        for row in rows:
            submission = dict(row)
            submission['photos'] = submission['photos'].split(',') if submission['photos'] else []
            if submission['detection_results']:
                submission['detection_results'] = json.loads(submission['detection_results'])
            submissions.append(submission)
        
        return submissions
    
    def update_submission_status(
        self,
        submission_id: str,
        status: str,
        reviewed_by: str,
        feedback: Optional[str] = None
    ) -> bool:
        """Update submission status (manager action)"""
        valid_statuses = ['pending', 'approved', 'flagged', 'adjustment_required']
        if status not in valid_statuses:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get employee username for notification
            cursor.execute('SELECT employee_username FROM restock_submissions WHERE submission_id = ?', (submission_id,))
            result = cursor.fetchone()
            if not result:
                return False
            
            employee_username = result[0]
            review_time = time.time()
            
            # Update submission
            cursor.execute('''
                UPDATE restock_submissions
                SET status = ?, reviewed_by = ?, reviewed_at = ?, feedback = ?
                WHERE submission_id = ?
            ''', (status, reviewed_by, review_time, feedback, submission_id))
            
            # Create notification
            status_messages = {
                'approved': 'Your restock submission has been approved.',
                'flagged': 'Your restock submission has been flagged for review.',
                'adjustment_required': 'Your restock submission requires adjustment.',
            }
            
            title = f"Submission {status.replace('_', ' ').title()}"
            message = status_messages.get(status, f"Your submission status has been updated to {status}.")
            if feedback:
                message += f"\n\nManager: {feedback}"
            
            cursor.execute('''
                INSERT INTO restock_notifications (employee_username, title, message, submission_id, timestamp_utc)
                VALUES (?, ?, ?, ?, ?)
            ''', (employee_username, title, message, submission_id, review_time))
            
            # Log action
            cursor.execute('''
                INSERT INTO restock_audit_log (submission_id, action, performed_by, timestamp, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (submission_id, f'status_update_{status}', reviewed_by, review_time, json.dumps({'status': status, 'feedback': feedback})))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Submission {submission_id} status updated to {status} by {reviewed_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating submission status: {e}")
            conn.rollback()
            conn.close()
            return False
    
    def get_notifications(self, employee_username: str) -> List[Dict]:
        """Get notifications for an employee"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM restock_notifications
            WHERE employee_username = ?
            ORDER BY timestamp_utc DESC
            LIMIT 50
        ''', (employee_username,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_notification_count(self, employee_username: str) -> int:
        """Get unread notification count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM restock_notifications
            WHERE employee_username = ? AND read = 0
        ''', (employee_username,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE restock_notifications SET read = 1 WHERE id = ?
            ''', (notification_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error marking notification read: {e}")
            conn.close()
            return False
    
    def get_photo_path(self, filename: str) -> Optional[Path]:
        """Get path to photo file"""
        file_path = self.photos_dir / filename
        if file_path.exists():
            return file_path
        return None
    
    def update_detection_results(self, submission_id: str, detection_results: Dict):
        """Update detection results for a submission"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE restock_submissions
                SET detection_results = ?
                WHERE submission_id = ?
            ''', (json.dumps(detection_results), submission_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating detection results: {e}")
            conn.close()