"""
Alert handlers for configuration monitoring system.

This module provides various alert handlers that can be used to notify
administrators about configuration validation failures and health check issues.
"""

import logging
import smtplib
import json
import os
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class AlertHandler:
    """Base class for alert handlers."""
    
    def __init__(self, name: str):
        """
        Initialize the alert handler.
        
        Args:
            name: Name of the alert handler
        """
        self.name = name
        self.enabled = True
    
    def handle_alert(self, alert_type: str, details: Dict[str, Any]) -> None:
        """
        Handle an alert.
        
        Args:
            alert_type: Type of alert
            details: Alert details
        """
        if not self.enabled:
            return
        
        try:
            self._handle_alert_impl(alert_type, details)
        except Exception as e:
            logger.error(f"Error in alert handler {self.name}: {e}")
    
    def _handle_alert_impl(self, alert_type: str, details: Dict[str, Any]) -> None:
        """
        Implementation-specific alert handling.
        
        Args:
            alert_type: Type of alert
            details: Alert details
        """
        raise NotImplementedError("Subclasses must implement _handle_alert_impl")


class ConsoleAlertHandler(AlertHandler):
    """Alert handler that prints alerts to console."""
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize console alert handler.
        
        Args:
            use_colors: Whether to use colored output
        """
        super().__init__("console")
        self.use_colors = use_colors
    
    def _handle_alert_impl(self, alert_type: str, details: Dict[str, Any]) -> None:
        """Print alert to console."""
        timestamp = details.get("timestamp", datetime.now().isoformat())
        service = details.get("service", "unknown")
        
        # Format alert message
        if self.use_colors:
            alert_msg = f"\n🚨 \033[91mALERT\033[0m: {alert_type}"
            service_msg = f"📡 Service: \033[93m{service}\033[0m"
            time_msg = f"⏰ Time: \033[94m{timestamp}\033[0m"
        else:
            alert_msg = f"\nALERT: {alert_type}"
            service_msg = f"Service: {service}"
            time_msg = f"Time: {timestamp}"
        
        print("=" * 60)
        print(alert_msg)
        print(service_msg)
        print(time_msg)
        
        # Print specific details based on alert type
        if details.get("alert_type") == "validation_failure":
            failure_count = details.get("failure_count", 0)
            window_minutes = details.get("window_minutes", 0)
            errors = details.get("errors", [])
            
            print(f"Failures: {failure_count} in {window_minutes} minutes")
            print("\nValidation Errors:")
            for i, error in enumerate(errors, 1):
                section = error.get("section", "unknown")
                key = error.get("key", "")
                message = error.get("message", "")
                if key:
                    print(f"  {i}. [{section}].{key}: {message}")
                else:
                    print(f"  {i}. [{section}]: {message}")
        
        elif details.get("alert_type") == "health_check_failure":
            failure_count = details.get("failure_count", 0)
            window_minutes = details.get("window_minutes", 0)
            error_message = details.get("error_message", "")
            
            print(f"Failures: {failure_count} in {window_minutes} minutes")
            print(f"Error: {error_message}")
            
            health_details = details.get("health_details", {})
            if health_details:
                print("Health Check Details:")
                for key, value in health_details.items():
                    print(f"  {key}: {value}")
        
        print("=" * 60)


class FileAlertHandler(AlertHandler):
    """Alert handler that writes alerts to a file."""
    
    def __init__(self, alert_file: str, max_file_size_mb: int = 10):
        """
        Initialize file alert handler.
        
        Args:
            alert_file: Path to alert file
            max_file_size_mb: Maximum file size before rotation
        """
        super().__init__("file")
        self.alert_file = Path(alert_file)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        # Ensure directory exists
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _handle_alert_impl(self, alert_type: str, details: Dict[str, Any]) -> None:
        """Write alert to file."""
        # Check if file rotation is needed
        if self.alert_file.exists() and self.alert_file.stat().st_size > self.max_file_size_bytes:
            self._rotate_file()
        
        # Format alert as JSON for structured logging
        alert_record = {
            "timestamp": details.get("timestamp", datetime.now().isoformat()),
            "alert_type": alert_type,
            "details": details
        }
        
        try:
            with open(self.alert_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_record) + "\n")
        except Exception as e:
            logger.error(f"Failed to write alert to file {self.alert_file}: {e}")
    
    def _rotate_file(self) -> None:
        """Rotate the alert file."""
        try:
            backup_file = self.alert_file.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            self.alert_file.rename(backup_file)
            logger.info(f"Rotated alert file to {backup_file}")
        except Exception as e:
            logger.error(f"Failed to rotate alert file: {e}")


class EmailAlertHandler(AlertHandler):
    """Alert handler that sends alerts via email."""
    
    def __init__(self,
                 smtp_host: str,
                 smtp_port: int,
                 username: str,
                 password: str,
                 from_email: str,
                 to_emails: List[str],
                 use_tls: bool = True):
        """
        Initialize email alert handler.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_email: From email address
            to_emails: List of recipient email addresses
            use_tls: Whether to use TLS encryption
        """
        super().__init__("email")
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls
    
    def _handle_alert_impl(self, alert_type: str, details: Dict[str, Any]) -> None:
        """Send alert via email."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)
            msg["Subject"] = f"Sync2NAS Alert: {alert_type}"
            
            # Create email body
            body = self._format_email_body(alert_type, details)
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Alert email sent to {len(self.to_emails)} recipients")
        
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
    
    def _format_email_body(self, alert_type: str, details: Dict[str, Any]) -> str:
        """Format alert details into email body."""
        timestamp = details.get("timestamp", datetime.now().isoformat())
        service = details.get("service", "unknown")
        
        body = f"""
Sync2NAS Configuration Alert

Alert Type: {alert_type}
Service: {service}
Timestamp: {timestamp}

"""
        
        if details.get("alert_type") == "validation_failure":
            failure_count = details.get("failure_count", 0)
            window_minutes = details.get("window_minutes", 0)
            errors = details.get("errors", [])
            
            body += f"""
Validation Failures: {failure_count} in {window_minutes} minutes

Errors:
"""
            for i, error in enumerate(errors, 1):
                section = error.get("section", "unknown")
                key = error.get("key", "")
                message = error.get("message", "")
                if key:
                    body += f"  {i}. [{section}].{key}: {message}\n"
                else:
                    body += f"  {i}. [{section}]: {message}\n"
        
        elif details.get("alert_type") == "health_check_failure":
            failure_count = details.get("failure_count", 0)
            window_minutes = details.get("window_minutes", 0)
            error_message = details.get("error_message", "")
            
            body += f"""
Health Check Failures: {failure_count} in {window_minutes} minutes

Error: {error_message}

"""
            health_details = details.get("health_details", {})
            if health_details:
                body += "Health Check Details:\n"
                for key, value in health_details.items():
                    body += f"  {key}: {value}\n"
        
        body += """

Please check your Sync2NAS configuration and resolve the issues above.

This is an automated alert from Sync2NAS configuration monitoring.
"""
        
        return body


class WebhookAlertHandler(AlertHandler):
    """Alert handler that sends alerts to a webhook URL."""
    
    def __init__(self, webhook_url: str, timeout: int = 10):
        """
        Initialize webhook alert handler.
        
        Args:
            webhook_url: Webhook URL to send alerts to
            timeout: Request timeout in seconds
        """
        super().__init__("webhook")
        self.webhook_url = webhook_url
        self.timeout = timeout
    
    def _handle_alert_impl(self, alert_type: str, details: Dict[str, Any]) -> None:
        """Send alert to webhook."""
        try:
            import httpx
            
            payload = {
                "alert_type": alert_type,
                "timestamp": details.get("timestamp", datetime.now().isoformat()),
                "service": details.get("service", "unknown"),
                "details": details
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            
            logger.info(f"Alert sent to webhook: {self.webhook_url}")
        
        except Exception as e:
            logger.error(f"Failed to send alert to webhook {self.webhook_url}: {e}")


class AlertManager:
    """Manages multiple alert handlers."""
    
    def __init__(self):
        """Initialize the alert manager."""
        self.handlers: List[AlertHandler] = []
    
    def add_handler(self, handler: AlertHandler) -> None:
        """
        Add an alert handler.
        
        Args:
            handler: Alert handler to add
        """
        self.handlers.append(handler)
        logger.info(f"Added alert handler: {handler.name}")
    
    def remove_handler(self, handler_name: str) -> bool:
        """
        Remove an alert handler by name.
        
        Args:
            handler_name: Name of handler to remove
            
        Returns:
            True if handler was removed, False if not found
        """
        for i, handler in enumerate(self.handlers):
            if handler.name == handler_name:
                del self.handlers[i]
                logger.info(f"Removed alert handler: {handler_name}")
                return True
        return False
    
    def handle_alert(self, alert_type: str, details: Dict[str, Any]) -> None:
        """
        Send alert to all registered handlers.
        
        Args:
            alert_type: Type of alert
            details: Alert details
        """
        if not self.handlers:
            logger.warning("No alert handlers configured")
            return
        
        for handler in self.handlers:
            handler.handle_alert(alert_type, details)
    
    def get_handler_names(self) -> List[str]:
        """
        Get names of all registered handlers.
        
        Returns:
            List of handler names
        """
        return [handler.name for handler in self.handlers]


def create_default_alert_manager() -> AlertManager:
    """
    Create an alert manager with default handlers.
    
    Returns:
        AlertManager with console and file handlers
    """
    manager = AlertManager()
    
    # Always add console handler
    manager.add_handler(ConsoleAlertHandler())
    
    # Add file handler if alerts directory exists or can be created
    try:
        alerts_dir = Path("logs/alerts")
        alerts_dir.mkdir(parents=True, exist_ok=True)
        manager.add_handler(FileAlertHandler(alerts_dir / "config_alerts.log"))
    except Exception as e:
        logger.warning(f"Could not create file alert handler: {e}")
    
    return manager


def create_email_alert_handler_from_env() -> Optional[EmailAlertHandler]:
    """
    Create email alert handler from environment variables.
    
    Environment variables:
    - SYNC2NAS_ALERT_SMTP_HOST
    - SYNC2NAS_ALERT_SMTP_PORT
    - SYNC2NAS_ALERT_SMTP_USERNAME
    - SYNC2NAS_ALERT_SMTP_PASSWORD
    - SYNC2NAS_ALERT_FROM_EMAIL
    - SYNC2NAS_ALERT_TO_EMAILS (comma-separated)
    - SYNC2NAS_ALERT_USE_TLS (true/false)
    
    Returns:
        EmailAlertHandler if all required env vars are set, None otherwise
    """
    required_vars = [
        "SYNC2NAS_ALERT_SMTP_HOST",
        "SYNC2NAS_ALERT_SMTP_PORT",
        "SYNC2NAS_ALERT_SMTP_USERNAME",
        "SYNC2NAS_ALERT_SMTP_PASSWORD",
        "SYNC2NAS_ALERT_FROM_EMAIL",
        "SYNC2NAS_ALERT_TO_EMAILS"
    ]
    
    # Check if all required variables are set
    env_values = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            return None
        env_values[var] = value
    
    try:
        return EmailAlertHandler(
            smtp_host=env_values["SYNC2NAS_ALERT_SMTP_HOST"],
            smtp_port=int(env_values["SYNC2NAS_ALERT_SMTP_PORT"]),
            username=env_values["SYNC2NAS_ALERT_SMTP_USERNAME"],
            password=env_values["SYNC2NAS_ALERT_SMTP_PASSWORD"],
            from_email=env_values["SYNC2NAS_ALERT_FROM_EMAIL"],
            to_emails=[email.strip() for email in env_values["SYNC2NAS_ALERT_TO_EMAILS"].split(",")],
            use_tls=os.getenv("SYNC2NAS_ALERT_USE_TLS", "true").lower() == "true"
        )
    except Exception as e:
        logger.error(f"Failed to create email alert handler from environment: {e}")
        return None