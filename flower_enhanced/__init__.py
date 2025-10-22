"""
Enhanced Task Monitoring Client Utilities

This module provides easy-to-use utilities for integrating enhanced monitoring
features into Celery tasks across different projects.

Usage:
    from flower_enhanced import enhanced_monitoring, send_progress_event

    @enhanced_monitoring(task_type="data_processor")
    def my_task(self, data):
        send_progress_event(progress_percent=50)
        return process_data(data)
"""

__version__ = "1.0.0"
__author__ = "Enhanced Monitoring Team"

# Import main utilities for easy access
from .events import send_progress_event, send_hierarchy_event, send_failure_event
from .decorators import enhanced_monitoring
from .config import config, configure
from .types import ProgressEvent, HierarchyEvent, FailureEvent, TaskType

# Public API
__all__ = [
    # Event functions
    "send_progress_event",
    "send_hierarchy_event",
    "send_failure_event",
    # Decorator
    "enhanced_monitoring",
    # Configuration
    "config",
    "configure",
    # Types
    "ProgressEvent",
    "HierarchyEvent",
    "FailureEvent",
    "TaskType",
]
