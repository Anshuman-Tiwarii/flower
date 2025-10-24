"""
Enhanced Task Monitoring - Type Definitions and Event Schemas

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
class ProgressEventSchema:
    """Schema for progress tracking events"""

    progress_percent: float  # 0-100 completion percentage
    status: Optional[str] = None  # Human-readable status message
    current: Optional[int] = None  # Current item being processed
    total: Optional[int] = None  # Total items to process
    stage: Optional[str] = None  # Current processing stage name
    stage_description: Optional[str] = None  # Description of current stage
    stage_progress: Optional[float] = None  # Progress within current stage (0-100)
    subtasks_created: int = 0  # Number of subtasks created
    subtasks_completed: int = 0  # Number of subtasks completed
    subtasks_failed: int = 0  # Number of subtasks that failed
    subtasks_remaining: Optional[int] = None  # Number of subtasks remaining
    current_step: Optional[int] = None  # Current step in pipeline (for chain tasks)
    total_steps: Optional[int] = None  # Total steps in pipeline
    current_stage_name: Optional[str] = None  # Name of current stage in pipeline
    custom_data: Optional[Dict[str, Any]] = None  # Additional custom progress data


@dataclass
class HierarchyEventSchema:
    """Schema for hierarchy tracking events"""

    task_type: Union[str, TaskType]  # Type of task (single, parent, child, etc.)
    parent_id: Optional[str] = None  # Parent task ID if this is a subtask
    children: Optional[List[str]] = None  # List of child task IDs
    depth: int = 0  # Depth level in hierarchy (0 for root)
    hierarchy_data: Optional[Dict[str, Any]] = None  # Additional hierarchy metadata


@dataclass
class FailureEventSchema:
    """Schema for failure analysis events"""

    failure_reason: str  # Description of the failure
    failure_stage: Optional[Union[str, FailureStage]] = (
        None  # Stage where failure occurred
    )
    failure_metadata: Optional[Dict[str, Any]] = None  # Additional failure context
    retry_context: Optional[Dict[str, Any]] = None  # Retry-related information


# Event type constants (matches working test demos)
EVENT_TYPES = {
    "PROGRESS": "task-custom-progress",
    "HIERARCHY": "task-custom-hierarchy",
    "FAILURE": "task-custom-failure",
}

# Configuration constants
DEFAULT_CONFIG = {
    "event_prefix": "task-custom",
    "enabled": True,
    "debug": False,
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
