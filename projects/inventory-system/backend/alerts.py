"""
Alerts and Notifications Module
Provides debounced alerting for low stock and expiration conditions with email delivery
"""

import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from collections import defaultdict, deque
import time

logger = logging.getLogger(__name__)


class AlertType:
    """Alert type constants"""
    LOW_STOCK = "low_stock"
    EXPIRATION = "expiration"


class AlertSeverity:
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    """
    Immutable alert record
    """
    
    def __init__(
        self,
        alert_type: str,
        product_name: str,
        severity: str,
        message: str,
        timestamp_utc: float,
        metadata: Optional[Dict] = None
    ):
        """
        Initialize alert
        
        Args:
            alert_type: Type of alert (low_stock, expiration)
            product_name: Product that triggered alert
            severity: Severity level (info, warning, critical)
            message: Human-readable alert message
            timestamp_utc: UTC timestamp when alert was triggered
            metadata: Additional alert-specific data
        """
        self.alert_type = alert_type
        self.product_name = product_name
        self.severity = severity
        self.message = message
        self.timestamp_utc = timestamp_utc
        self.metadata = metadata or {}
        self.alert_id = f"{alert_type}_{product_name}_{int(timestamp_utc)}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for persistence"""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'product_name': self.product_name,
            'severity': self.severity,
            'message': self.message,
            'timestamp_utc': self.timestamp_utc,
            'metadata': self.metadata
        }
    
    def __repr__(self) -> str:
        return f"Alert({self.alert_type}: {self.product_name} - {self.message})"


class EmailNotifier:
    """
    Handles email notifications via SMTP
    Configured through environment variables
    """
    
    def __init__(self):
        """
        Initialize email notifier from environment variables
        """
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.notify_to = os.getenv('NOTIFY_TO')
        self.notify_from = os.getenv('NOTIFY_FROM', self.smtp_user)
        
        self.enabled = self._validate_config()
        
        if self.enabled:
            logger.info(f"Email notifications enabled: {self.notify_from} → {self.notify_to}")
        else:
            logger.warning("Email notifications disabled: missing or invalid SMTP configuration")
    
    def _validate_config(self) -> bool:
        """
        Validate SMTP configuration
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.smtp_host:
            logger.warning("SMTP_HOST not configured")
            return False
        
        if not self.smtp_user:
            logger.warning("SMTP_USER not configured")
            return False
        
        if not self.smtp_pass:
            logger.warning("SMTP_PASS not configured")
            return False
        
        if not self.notify_to:
            logger.warning("NOTIFY_TO not configured")
            return False
        
        return True
    
    def send_alert(self, alert: Alert, timestamp_est: str) -> bool:
        """
        Send alert via email
        
        Args:
            alert: Alert to send
            timestamp_est: Formatted EST timestamp for display
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Email disabled, skipping alert: {alert.product_name}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity.upper()}] {alert.alert_type.replace('_', ' ').title()}: {alert.product_name}"
            msg['From'] = self.notify_from
            msg['To'] = self.notify_to
            
            # Create email body
            text_body = self._create_text_body(alert, timestamp_est)
            html_body = self._create_html_body(alert, timestamp_est)
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info(f"✓ Email sent: {alert.alert_type} - {alert.product_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _create_text_body(self, alert: Alert, timestamp_est: str) -> str:
        """Create plain text email body"""
        lines = [
            f"Alert: {alert.alert_type.replace('_', ' ').title()}",
            f"Product: {alert.product_name}",
            f"Severity: {alert.severity.upper()}",
            f"Time: {timestamp_est}",
            "",
            f"Message: {alert.message}",
            ""
        ]
        
        if alert.metadata:
            lines.append("Details:")
            for key, value in alert.metadata.items():
                lines.append(f"  {key}: {value}")
        
        lines.extend([
            "",
            "---",
            "Jetson Orin Inventory Vision System",
            "Automated Alert Notification"
        ])
        
        return "\n".join(lines)
    
    def _create_html_body(self, alert: Alert, timestamp_est: str) -> str:
        """Create HTML email body"""
        severity_colors = {
            'info': '#17a2b8',
            'warning': '#ffc107',
            'critical': '#dc3545'
        }
        color = severity_colors.get(alert.severity, '#6c757d')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{alert.alert_type.replace('_', ' ').title()}</h2>
                </div>
                <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 120px;">Product:</td>
                            <td style="padding: 8px;">{alert.product_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Severity:</td>
                            <td style="padding: 8px;"><span style="background: {color}; color: white; padding: 2px 8px; border-radius: 3px;">{alert.severity.upper()}</span></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Time:</td>
                            <td style="padding: 8px;">{timestamp_est}</td>
                        </tr>
                    </table>
                    <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-left: 4px solid {color};">
                        <p style="margin: 0;"><strong>Message:</strong></p>
                        <p style="margin: 10px 0 0 0;">{alert.message}</p>
                    </div>
        """
        
        if alert.metadata:
            html += """
                    <div style="margin-top: 20px;">
                        <p style="font-weight: bold; margin-bottom: 10px;">Details:</p>
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            """
            for key, value in alert.metadata.items():
                html += f"""
                            <tr>
                                <td style="padding: 5px; border-bottom: 1px solid #eee;">{key}:</td>
                                <td style="padding: 5px; border-bottom: 1px solid #eee;">{value}</td>
                            </tr>
                """
            html += """
                        </table>
                    </div>
            """
        
        html += """
                </div>
                <div style="margin-top: 20px; padding: 15px; text-align: center; color: #6c757d; font-size: 12px;">
                    <p style="margin: 0;">Jetson Orin Inventory Vision System</p>
                    <p style="margin: 5px 0 0 0;">Automated Alert Notification</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html


class AlertEngine:
    """
    Evaluates inventory and freshness state to generate debounced alerts
    """
    
    def __init__(
        self,
        low_stock_thresholds: Dict[str, int],
        low_stock_confirm_intervals: int = 2,
        expiration_confirm_intervals: int = 2,
        alert_cooldown_seconds: float = 3600.0,  # 1 hour default
        enable_email_alerts: bool = True,
        persistence_manager=None
    ):
        """
        Initialize alert engine
        
        Args:
            low_stock_thresholds: Dict mapping product names to threshold counts
            low_stock_confirm_intervals: Intervals to confirm low stock
            expiration_confirm_intervals: Intervals to confirm expiration
            alert_cooldown_seconds: Cooldown between alerts for same product+type
            enable_email_alerts: Enable email notifications
            persistence_manager: PersistenceManager instance for logging
        """
        self.low_stock_thresholds = low_stock_thresholds
        self.low_stock_confirm_intervals = low_stock_confirm_intervals
        self.expiration_confirm_intervals = expiration_confirm_intervals
        self.alert_cooldown_seconds = alert_cooldown_seconds
        self.enable_email_alerts = enable_email_alerts
        self.persistence = persistence_manager
        
        # Email notifier
        self.email_notifier = EmailNotifier() if enable_email_alerts else None
        
        # Tracking state
        self.pending_low_stock: Dict[str, deque] = defaultdict(lambda: deque(maxlen=low_stock_confirm_intervals + 1))
        self.pending_expiration: Dict[str, deque] = defaultdict(lambda: deque(maxlen=expiration_confirm_intervals + 1))
        
        # Cooldown tracking: {(alert_type, product_name): last_alert_time}
        self.last_alert_time: Dict[tuple, float] = {}
        
        # Active alerts cache
        self.active_alerts: Dict[str, Alert] = {}
        
        # Statistics
        self.total_alerts_triggered = 0
        self.alerts_by_type: Dict[str, int] = defaultdict(int)
        self.alerts_suppressed_by_cooldown = 0
        
        logger.info(f"Alert engine initialized: low_stock_thresholds={len(low_stock_thresholds)}, "
                   f"confirm_intervals={low_stock_confirm_intervals}, cooldown={alert_cooldown_seconds}s")
    
    def evaluate(
        self,
        inventory: Dict[str, int],
        freshness_state: Dict[str, Dict],
        timestamp_utc: float
    ) -> List[Alert]:
        """
        Evaluate current state and generate alerts
        
        Args:
            inventory: Current inventory dictionary
            freshness_state: Current freshness state
            timestamp_utc: Current UTC timestamp
            
        Returns:
            List of new alerts triggered
        """
        alerts = []
        
        # Evaluate low stock alerts
        low_stock_alerts = self._evaluate_low_stock(inventory, timestamp_utc)
        alerts.extend(low_stock_alerts)
        
        # Evaluate expiration alerts
        expiration_alerts = self._evaluate_expiration(freshness_state, timestamp_utc)
        alerts.extend(expiration_alerts)
        
        # Send notifications and persist
        for alert in alerts:
            self._process_alert(alert, timestamp_utc)
        
        return alerts
    
    def _evaluate_low_stock(self, inventory: Dict[str, int], timestamp_utc: float) -> List[Alert]:
        """
        Evaluate low stock conditions
        
        Args:
            inventory: Current inventory
            timestamp_utc: Current timestamp
            
        Returns:
            List of low stock alerts
        """
        alerts = []
        
        for product_name, threshold in self.low_stock_thresholds.items():
            current_count = inventory.get(product_name, 0)
            
            # Check if below threshold
            if current_count <= threshold:
                # Add to pending
                self.pending_low_stock[product_name].append((timestamp_utc, current_count))
                
                # Validate if confirmed
                if self._validate_low_stock(product_name, threshold):
                    # Check cooldown
                    if self._check_cooldown(AlertType.LOW_STOCK, product_name, timestamp_utc):
                        # Create alert
                        severity = AlertSeverity.CRITICAL if current_count == 0 else AlertSeverity.WARNING
                        message = f"Low stock alert: {product_name} count is {current_count} (threshold: {threshold})"
                        
                        alert = Alert(
                            alert_type=AlertType.LOW_STOCK,
                            product_name=product_name,
                            severity=severity,
                            message=message,
                            timestamp_utc=timestamp_utc,
                            metadata={
                                'current_count': current_count,
                                'threshold': threshold,
                                'status': 'out_of_stock' if current_count == 0 else 'low_stock'
                            }
                        )
                        
                        alerts.append(alert)
                        
                        # Update cooldown
                        self.last_alert_time[(AlertType.LOW_STOCK, product_name)] = timestamp_utc
                        
                        # Clear pending
                        self.pending_low_stock[product_name].clear()
                        
                        logger.info(f"✓ Low stock alert triggered: {product_name} ({current_count} ≤ {threshold})")
            else:
                # Above threshold - clear pending
                if product_name in self.pending_low_stock:
                    self.pending_low_stock[product_name].clear()
        
        return alerts
    
    def _evaluate_expiration(self, freshness_state: Dict[str, Dict], timestamp_utc: float) -> List[Alert]:
        """
        Evaluate expiration conditions
        
        Args:
            freshness_state: Current freshness state
            timestamp_utc: Current timestamp
            
        Returns:
            List of expiration alerts
        """
        alerts = []
        
        for product_name, freshness_data in freshness_state.items():
            is_expired = freshness_data.get('is_expired', False)
            age_days = freshness_data.get('age_days', 0)
            
            if is_expired:
                # Add to pending
                self.pending_expiration[product_name].append((timestamp_utc, age_days))
                
                # Validate if confirmed
                if self._validate_expiration(product_name):
                    # Check cooldown
                    if self._check_cooldown(AlertType.EXPIRATION, product_name, timestamp_utc):
                        # Create alert
                        message = f"Expiration alert: {product_name} has expired ({age_days:.1f} days old)"
                        
                        alert = Alert(
                            alert_type=AlertType.EXPIRATION,
                            product_name=product_name,
                            severity=AlertSeverity.WARNING,
                            message=message,
                            timestamp_utc=timestamp_utc,
                            metadata={
                                'age_days': round(age_days, 1),
                                'expiration_days': freshness_data.get('expiration_days', 5),
                                'first_seen_utc': freshness_data.get('first_seen_utc')
                            }
                        )
                        
                        alerts.append(alert)
                        
                        # Update cooldown
                        self.last_alert_time[(AlertType.EXPIRATION, product_name)] = timestamp_utc
                        
                        # Clear pending
                        self.pending_expiration[product_name].clear()
                        
                        logger.info(f"✓ Expiration alert triggered: {product_name} ({age_days:.1f} days)")
            else:
                # Not expired - clear pending
                if product_name in self.pending_expiration:
                    self.pending_expiration[product_name].clear()
        
        return alerts
    
    def _validate_low_stock(self, product_name: str, threshold: int) -> bool:
        """
        Validate low stock condition has persisted
        
        Args:
            product_name: Product to validate
            threshold: Low stock threshold
            
        Returns:
            True if validated, False otherwise
        """
        pending = self.pending_low_stock[product_name]
        
        if len(pending) < self.low_stock_confirm_intervals:
            return False
        
        # Check all recent observations are below threshold
        for _, count in pending:
            if count > threshold:
                return False
        
        return True
    
    def _validate_expiration(self, product_name: str) -> bool:
        """
        Validate expiration condition has persisted
        
        Args:
            product_name: Product to validate
            
        Returns:
            True if validated, False otherwise
        """
        pending = self.pending_expiration[product_name]
        
        if len(pending) < self.expiration_confirm_intervals:
            return False
        
        # All observations show expired
        return True
    
    def _check_cooldown(self, alert_type: str, product_name: str, current_time: float) -> bool:
        """
        Check if alert cooldown has passed
        
        Args:
            alert_type: Type of alert
            product_name: Product name
            current_time: Current timestamp
            
        Returns:
            True if cooldown passed, False otherwise
        """
        key = (alert_type, product_name)
        
        if key not in self.last_alert_time:
            return True
        
        time_since_last = current_time - self.last_alert_time[key]
        
        if time_since_last < self.alert_cooldown_seconds:
            self.alerts_suppressed_by_cooldown += 1
            logger.debug(f"⊗ Alert suppressed by cooldown: {alert_type} - {product_name} "
                        f"({time_since_last:.0f}s < {self.alert_cooldown_seconds:.0f}s)")
            return False
        
        return True
    
    def _process_alert(self, alert: Alert, timestamp_utc: float):
        """
        Process alert: send notification and persist
        
        Args:
            alert: Alert to process
            timestamp_utc: Current timestamp
        """
        # Update statistics
        self.total_alerts_triggered += 1
        self.alerts_by_type[alert.alert_type] += 1
        
        # Add to active alerts
        self.active_alerts[alert.alert_id] = alert
        
        # Format EST timestamp
        from datetime import datetime
        import pytz
        dt_utc = datetime.fromtimestamp(timestamp_utc, tz=timezone.utc)
        dt_est = dt_utc.astimezone(pytz.timezone('US/Eastern'))
        timestamp_est = dt_est.strftime('%Y-%m-%d %I:%M:%S %p EST')
        
        # Send email notification
        if self.email_notifier:
            self.email_notifier.send_alert(alert, timestamp_est)
        
        # Persist to database
        if self.persistence:
            try:
                self.persistence.log_alert(
                    alert_type=alert.alert_type,
                    product_name=alert.product_name,
                    severity=alert.severity,
                    message=alert.message,
                    timestamp_utc=timestamp_utc,
                    timestamp_est=timestamp_est,
                    metadata=alert.metadata
                )
            except Exception as e:
                logger.error(f"Failed to persist alert: {e}")
    
    def get_active_alerts(self) -> List[Dict]:
        """
        Get currently active alerts
        
        Returns:
            List of active alert dictionaries
        """
        return [alert.to_dict() for alert in self.active_alerts.values()]
    
    def acknowledge_alert(self, alert_id: str):
        """
        Acknowledge an alert (remove from active)
        
        Args:
            alert_id: Alert ID to acknowledge
        """
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            logger.info(f"Alert acknowledged: {alert_id}")
    
    def get_statistics(self) -> Dict:
        """
        Get alert engine statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_alerts_triggered': self.total_alerts_triggered,
            'alerts_by_type': dict(self.alerts_by_type),
            'alerts_suppressed_by_cooldown': self.alerts_suppressed_by_cooldown,
            'active_alerts_count': len(self.active_alerts),
            'email_enabled': self.email_notifier.enabled if self.email_notifier else False,
            'config': {
                'low_stock_thresholds': self.low_stock_thresholds,
                'low_stock_confirm_intervals': self.low_stock_confirm_intervals,
                'expiration_confirm_intervals': self.expiration_confirm_intervals,
                'alert_cooldown_seconds': self.alert_cooldown_seconds
            }
        }
