"""
Enhanced Task Monitoring for Flower

A simple package that provides enhanced monitoring capabilities for Celery tasks
through Flower dashboard. Uses Celery's native event system for real-time updates.

Quick Start:
    from flower_enhanced import enhanced_monitoring, send_progress_event

    @celery_app.task(bind=True)
    @enhanced_monitoring(task_type="data_processor", auto_progress=True)
    def process_data(self, data_list):
        for i, item in enumerate(data_list):
            process_item(item)
            send_progress_event(progress_percent=(i+1)/len(data_list)*100)
        return "completed"
"""

__version__ = "1.0.0"
__author__ = "Growth & Platform Team - Edra"
__description__ = "Enhanced monitoring for Celery tasks via Flower dashboard"

# Core event functions
from .events import (
    send_custom_event,
    send_progress_event,
    send_hierarchy_event,
    send_failure_event,
    bulk_send_events,
    test_connection,
)

# Decorators
from .decorators import (
    enhanced_monitoring,
    hierarchy_task,
    progress_task,
    failure_tracking_task,
)

# Types and schemas
from .types import (
    TaskType,
    FailureStage,
    ProgressEventSchema,
    HierarchyEventSchema,
    FailureEventSchema,
    EVENT_TYPES,
    TASK_TYPE_DESCRIPTIONS,
    COMMON_STAGES,
    ERROR_SEVERITY,
)

# Configuration
from .config import (
    configure,
    get_config,
    is_enabled,
)

# Main exports for direct import
__all__ = [
    # Event functions
    "send_custom_event",
    "send_progress_event",
    "send_hierarchy_event",
    "send_failure_event",
    "bulk_send_events",
    "test_connection",
    # Decorators
    "enhanced_monitoring",
    "hierarchy_task",
    "progress_task",
    "failure_tracking_task",
    # Types
    "TaskType",
    "FailureStage",
    "ProgressEventSchema",
    "HierarchyEventSchema",
    "FailureEventSchema",
    "EVENT_TYPES",
    "TASK_TYPE_DESCRIPTIONS",
    "COMMON_STAGES",
    "ERROR_SEVERITY",
    # Config
    "configure",
    "get_config",
    "is_enabled",
]
