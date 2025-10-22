"""
Enhanced Task Monitoring - Configuration Management

Manages configuration for enhanced monitoring client utilities.
Auto-detects Redis URL from Celery configuration when possible.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EnhancedMonitoringConfig:
    """Configuration manager for enhanced monitoring client utilities"""

    def __init__(self):
        self.redis_url: str = self._detect_redis_url()
        self.event_prefix: str = "task-custom"
        self.enabled: bool = self._get_bool_env("ENHANCED_MONITORING_ENABLED", True)
        self.timeout: float = float(os.getenv("ENHANCED_MONITORING_TIMEOUT", "5.0"))
        self.retry_attempts: int = int(
            os.getenv("ENHANCED_MONITORING_RETRY_ATTEMPTS", "3")
        )
        self.retry_delay: float = float(
            os.getenv("ENHANCED_MONITORING_RETRY_DELAY", "1.0")
        )
        self.debug: bool = self._get_bool_env("ENHANCED_MONITORING_DEBUG", False)

        # Performance settings
        self.batch_size: int = int(os.getenv("ENHANCED_MONITORING_BATCH_SIZE", "100"))
        self.buffer_timeout: float = float(
            os.getenv("ENHANCED_MONITORING_BUFFER_TIMEOUT", "1.0")
        )

        # Security settings
        self.max_payload_size: int = int(
            os.getenv("ENHANCED_MONITORING_MAX_PAYLOAD", "65536")
        )  # 64KB
        self.sanitize_data: bool = self._get_bool_env(
            "ENHANCED_MONITORING_SANITIZE", True
        )

        if self.debug:
            logger.info(
                f"Enhanced monitoring initialized: redis_url={self.redis_url}, enabled={self.enabled}"
            )

    def _detect_redis_url(self) -> str:
        """Auto-detect Redis URL from various sources"""

        # 1. Explicit environment variable
        if redis_url := os.getenv("ENHANCED_MONITORING_REDIS_URL"):
            return redis_url

        # 2. Standard Redis environment variables
        if redis_url := os.getenv("REDIS_URL"):
            return redis_url

        # 3. Try to get from Celery configuration
        try:
            from celery import current_app

            if hasattr(current_app, "conf") and current_app.conf.broker_url:
                broker_url = current_app.conf.broker_url
                if broker_url.startswith("redis://"):
                    return broker_url
                elif broker_url.startswith("rediss://"):
                    return broker_url
        except (ImportError, AttributeError) as e:
            if self._get_bool_env("ENHANCED_MONITORING_DEBUG", False):
                logger.debug(f"Could not detect Redis from Celery: {e}")

        # 4. Try component-based environment variables
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_password = os.getenv("REDIS_PASSWORD")

        if redis_password:
            return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        else:
            return f"redis://{redis_host}:{redis_port}/{redis_db}"

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on", "enabled")

    def update(self, **kwargs) -> None:
        """Update configuration parameters"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                if self.debug:
                    logger.info(f"Updated config: {key}={value}")
            else:
                logger.warning(f"Unknown configuration key: {key}")

    def get_redis_connection_params(self) -> Dict[str, Any]:
        """Get Redis connection parameters for redis-py"""
        from urllib.parse import urlparse

        parsed = urlparse(self.redis_url)

        params = {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 6379,
            "db": int(parsed.path.lstrip("/")) if parsed.path else 0,
            "socket_timeout": self.timeout,
            "socket_connect_timeout": self.timeout,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }

        if parsed.password:
            params["password"] = parsed.password

        if parsed.scheme == "rediss":
            params["ssl"] = True

        return params

    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Test Redis URL parsing
            self.get_redis_connection_params()

            # Validate ranges
            if not 0 < self.timeout <= 60:
                raise ValueError(f"Invalid timeout: {self.timeout}")

            if not 0 <= self.retry_attempts <= 10:
                raise ValueError(f"Invalid retry_attempts: {self.retry_attempts}")

            if not 0 < self.retry_delay <= 10:
                raise ValueError(f"Invalid retry_delay: {self.retry_delay}")

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "redis_url": self.redis_url,
            "event_prefix": self.event_prefix,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "debug": self.debug,
            "batch_size": self.batch_size,
            "buffer_timeout": self.buffer_timeout,
            "max_payload_size": self.max_payload_size,
            "sanitize_data": self.sanitize_data,
        }

    def __repr__(self) -> str:
        # Hide password in repr
        safe_url = self.redis_url
        if "@" in safe_url:
            parts = safe_url.split("@")
            if len(parts) == 2:
                protocol_auth = parts[0]
                if ":" in protocol_auth:
                    protocol, auth = protocol_auth.rsplit(":", 1)
                    safe_url = f"{protocol}:***@{parts[1]}"

        return (
            f"EnhancedMonitoringConfig(redis_url='{safe_url}', enabled={self.enabled})"
        )


# Global configuration instance
config = EnhancedMonitoringConfig()


def configure(**kwargs) -> None:
    """
    Configure enhanced monitoring globally

    Args:
        redis_url: Redis connection URL
        enabled: Enable/disable monitoring
        timeout: Connection timeout in seconds
        retry_attempts: Number of retry attempts
        retry_delay: Delay between retries in seconds
        debug: Enable debug logging
        **kwargs: Additional configuration parameters
    """
    config.update(**kwargs)


def get_config() -> EnhancedMonitoringConfig:
    """Get the global configuration instance"""
    return config


def is_enabled() -> bool:
    """Check if enhanced monitoring is enabled"""
    return config.enabled and config.validate()
