"""
Enhanced Task Monitoring - Type Definitions

Defines event schemas, constants, and type hints for enhanced monitoring.
"""

from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Predefined task types for classification"""

    SINGLE = "single"
    PARENT = "parent"
    CHILD = "child"
    CHAIN_STEP = "chain_step"
    DATA_PROCESSOR = "data_processor"
    ETL_PIPELINE = "etl_pipeline"
    WORKFLOW_COORDINATOR = "workflow_coordinator"
    COMPONENT_ANALYZER = "component_analyzer"
    BATCH_PROCESSOR = "batch_processor"


class FailureStage(Enum):
    """Common failure stages"""

    INITIALIZATION = "initialization"
    PROCESSING = "processing"
    VALIDATION = "validation"
    FINALIZATION = "finalization"
    COMMUNICATION = "communication"
    CLEANUP = "cleanup"


@dataclass
class ProgressEvent:
    """Schema for progress tracking events"""

    progress_percent: float
    status: Optional[str] = None
    current: Optional[int] = None
    total: Optional[int] = None
    stage: Optional[str] = None
    stage_description: Optional[str] = None
    stage_progress: Optional[float] = None
    subtasks_created: int = 0
    subtasks_completed: int = 0
    subtasks_failed: int = 0
    subtasks_remaining: Optional[int] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    current_stage_name: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None


@dataclass
class HierarchyEvent:
    """Schema for hierarchy tracking events"""

    task_type: Union[str, TaskType]
    parent_id: Optional[str] = None
    children: Optional[List[str]] = None
    depth: int = 0
    hierarchy_data: Optional[Dict[str, Any]] = None


@dataclass
class FailureEvent:
    """Schema for failure analysis events"""

    failure_reason: str
    failure_stage: Optional[Union[str, FailureStage]] = None
    failure_metadata: Optional[Dict[str, Any]] = None
    system_metrics: Optional[Dict[str, Any]] = None
    retry_context: Optional[Dict[str, Any]] = None


# Event type constants
EVENT_TYPES = {
    "PROGRESS": "task-custom-progress",
    "HIERARCHY": "task-custom-hierarchy",
    "FAILURE": "task-custom-failure",
}

# Configuration constants
DEFAULT_CONFIG = {
    "redis_url": "redis://localhost:6379/0",
    "event_prefix": "task-custom",
    "enabled": True,
    "timeout": 5.0,
    "retry_attempts": 3,
    "retry_delay": 1.0,
}

# Task classification helpers
TASK_TYPE_DESCRIPTIONS = {
    TaskType.SINGLE: "Standalone task with no children",
    TaskType.PARENT: "Parent task that creates subtasks",
    TaskType.CHILD: "Child task created by a parent",
    TaskType.CHAIN_STEP: "Step in a task chain/pipeline",
    TaskType.DATA_PROCESSOR: "Data processing task",
    TaskType.ETL_PIPELINE: "Extract-Transform-Load pipeline",
    TaskType.WORKFLOW_COORDINATOR: "Coordinates multiple tasks",
    TaskType.COMPONENT_ANALYZER: "Analyzes individual components",
    TaskType.BATCH_PROCESSOR: "Processes data in batches",
}

# Common stage names
COMMON_STAGES = {
    "SETUP": "setup",
    "PROCESSING": "processing",
    "VALIDATION": "validation",
    "COMPLETION": "completion",
    "CLEANUP": "cleanup",
}

# Error severity levels
ERROR_SEVERITY = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}
