"""
Enhanced Task Monitoring - Simple Configuration

Basic configuration for enhanced monitoring. Since we use Celery's native
event system, minimal configuration is needed.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EnhancedMonitoringConfig:
    """Simple configuration for enhanced monitoring"""

    def __init__(self):
        # Event prefix for custom events
        self.event_prefix: str = "task-custom"

        # Enable/disable monitoring
        self.enabled: bool = self._get_bool_env("ENHANCED_MONITORING_ENABLED", True)

        # Debug logging
        self.debug: bool = self._get_bool_env("ENHANCED_MONITORING_DEBUG", False)

        if self.debug:
            logger.info(f"Enhanced monitoring initialized: enabled={self.enabled}")

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

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "event_prefix": self.event_prefix,
            "enabled": self.enabled,
            "debug": self.debug,
        }

    def __repr__(self) -> str:
        return f"EnhancedMonitoringConfig(enabled={self.enabled}, debug={self.debug})"


# Global configuration instance
config = EnhancedMonitoringConfig()


def configure(**kwargs) -> None:
    """
    Configure enhanced monitoring globally

    Args:
        enabled: Enable/disable monitoring
        debug: Enable debug logging
        **kwargs: Additional configuration parameters
    """
    config.update(**kwargs)


def get_config() -> EnhancedMonitoringConfig:
    """Get the global configuration instance"""
    return config


def is_enabled() -> bool:
    """Check if enhanced monitoring is enabled"""
    return config.enabled
