"""
Enhanced Task Monitoring - Event Sending Functions

Core functions for sending monitoring events via Celery's native event system.
These functions are used by Celery tasks to report progress, hierarchy, and failures.
"""

import logging
import threading
from typing import Optional, Dict, Any, List
from celery import current_task

from .types import EVENT_TYPES

logger = logging.getLogger(__name__)

# Thread-local storage for context propagation
_local = threading.local()


def _get_task_context():
    """Smart task context resolution with fallback mechanisms"""
    # Primary: Current Celery task context
    if current_task:
        return current_task, current_task.request.id
    
    # Fallback: Thread-local context (for threaded scenarios)
    if hasattr(_local, 'task_context'):
        task_obj, task_id = _local.task_context
        logger.debug(f"Using thread-local task context: {task_id}")
        return task_obj, task_id
    
    return None, None


def set_thread_task_context(task_obj, task_id):
    """Set task context for thread-local propagation"""
    _local.task_context = (task_obj, task_id)
    logger.debug(f"Set thread-local task context: {task_id}")


def clear_thread_task_context():
    """Clear thread-local task context"""
    if hasattr(_local, 'task_context'):
        delattr(_local, 'task_context')


def send_custom_event(event_type: str, **kwargs) -> bool:
    """Send custom events via Celery's native event system with smart context resolution"""
    try:
        task_obj, task_id = _get_task_context()
        
        if task_obj:
            # Add task_id to event data for debugging
            kwargs['_task_id'] = task_id
            task_obj.send_event(event_type, **kwargs)
            logger.debug(f"Sent {event_type} event from task {task_id}")
            return True
        else:
            logger.warning(f"No task context available to send {event_type} event. Available kwargs: {list(kwargs.keys())}")
            return False
    except Exception as e:
        logger.error(f"Failed to send {event_type} event: {e}")
        return False


def send_progress_event(
    progress_percent: float,
    status: Optional[str] = None,
    current: Optional[int] = None,
    total: Optional[int] = None,
    stage: Optional[str] = None,
    stage_description: Optional[str] = None,
    stage_progress: Optional[float] = None,
    subtasks_created: int = 0,
    subtasks_completed: int = 0,
    subtasks_failed: int = 0,
    subtasks_remaining: Optional[int] = None,
    current_step: Optional[int] = None,
    total_steps: Optional[int] = None,
    current_stage_name: Optional[str] = None,
    custom_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send progress update for current task

    Args:
        progress_percent: Completion percentage (0-100)
        status: Human-readable status message
        current: Current item being processed
        total: Total items to process
        stage: Current processing stage name
        stage_description: Description of current stage
        stage_progress: Progress within current stage (0-100)
        subtasks_created: Number of subtasks created
        subtasks_completed: Number of subtasks completed
        subtasks_failed: Number of subtasks that failed
        subtasks_remaining: Number of subtasks remaining
        current_step: Current step in pipeline (for chain tasks)
        total_steps: Total steps in pipeline
        current_stage_name: Name of current stage in pipeline
        custom_data: Additional custom progress data

    Returns:
        bool: True if event was sent successfully

    Example:
        send_progress_event(
            progress_percent=75.0,
            status="Processing batch 3/4",
            current=750,
            total=1000,
            stage="data_transformation",
            subtasks_completed=3,
            subtasks_created=4
        )
    """
    # Calculate remaining subtasks if not provided
    if subtasks_remaining is None and subtasks_created > 0:
        subtasks_remaining = subtasks_created - subtasks_completed - subtasks_failed

    return send_custom_event(
        EVENT_TYPES["PROGRESS"],
        progress_percent=float(progress_percent),
        status=status,
        current=current,
        total=total,
        stage=stage,
        stage_description=stage_description,
        stage_progress=stage_progress,
        subtasks_created=subtasks_created,
        subtasks_completed=subtasks_completed,
        subtasks_failed=subtasks_failed,
        subtasks_remaining=subtasks_remaining,
        current_step=current_step,
        total_steps=total_steps,
        current_stage_name=current_stage_name,
        custom_data=custom_data or {},
    )


def send_hierarchy_event(
    task_type: str,
    parent_id: Optional[str] = None,
    children: Optional[List[str]] = None,
    depth: int = 0,
    hierarchy_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send task hierarchy information

    Args:
        task_type: Type of task (single, parent, child, chain_step, etc.)
        parent_id: Parent task ID if this is a subtask
        children: List of child task IDs if this creates subtasks
        depth: Depth level in hierarchy (0 for root)
        hierarchy_data: Additional hierarchy metadata

    Returns:
        bool: True if event was sent successfully

    Example:
        # Parent task
        send_hierarchy_event(
            task_type="workflow_coordinator",
            children=["child-1", "child-2", "child-3"],
            depth=0
        )

        # Child task
        send_hierarchy_event(
            task_type="data_processor",
            parent_id="parent-task-id",
            depth=1
        )
    """
    # Smart task ID resolution with debugging
    task_obj, current_task_id = _get_task_context()
    
    # Auto-detect parent from Celery context if not provided
    if parent_id is None:
        try:
            if task_obj and hasattr(task_obj.request, "parent_id"):
                parent_id = task_obj.request.parent_id
                logger.debug(f"Auto-detected parent_id: {parent_id} for task: {current_task_id}")
        except (ImportError, AttributeError):
            pass

    # Enhanced debugging for hierarchy events
    logger.debug(f"Sending hierarchy event: task_type={task_type}, current_task={current_task_id}, parent_id={parent_id}, children={len(children or [])}")

    return send_custom_event(
        EVENT_TYPES["HIERARCHY"],
        task_type=task_type,
        parent_id=parent_id,
        children=children or [],
        depth=depth,
        hierarchy_data=hierarchy_data or {},
        _current_task_id=current_task_id,  # Include for debugging
    )


def send_failure_event(
    failure_reason: str,
    failure_stage: Optional[str] = None,
    failure_metadata: Optional[Dict[str, Any]] = None,
    retry_context: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send task failure metadata

    Args:
        failure_reason: Description of the failure
        failure_stage: Stage where failure occurred
        failure_metadata: Additional failure context and metadata
        retry_context: Retry-related information

    Returns:
        bool: True if event was sent successfully

    Example:
        send_failure_event(
            failure_reason="Database connection timeout",
            failure_stage="data_retrieval",
            failure_metadata={
                "error_code": "DB_TIMEOUT",
                "timeout_duration": 30,
                "affected_tables": ["users", "orders"]
            },
            retry_context={
                "retry_count": 3,
                "next_retry_in": 60
            }
        )
    """
    # Auto-detect retry context from Celery if not provided
    if retry_context is None:
        try:
            if current_task and current_task.request:
                retry_context = {
                    "retries": getattr(current_task.request, "retries", 0),
                    "eta": getattr(current_task.request, "eta", None),
                    "expires": getattr(current_task.request, "expires", None),
                }
        except (ImportError, AttributeError):
            retry_context = {}

    return send_custom_event(
        EVENT_TYPES["FAILURE"],
        failure_reason=failure_reason,
        failure_stage=failure_stage,
        failure_metadata=failure_metadata or {},
        retry_context=retry_context or {},
    )


def bulk_send_events(events: List[Dict[str, Any]]) -> int:
    """
    Send multiple events in a batch for better performance

    Args:
        events: List of event dictionaries with 'type' and 'data' keys

    Returns:
        int: Number of events successfully sent
    """
    if not events:
        return 0

    success_count = 0
    for event in events:
        event_type = event.get("type")
        event_data = event.get("data", {})

        if event_type:
            if send_custom_event(event_type, **event_data):
                success_count += 1

    return success_count


def test_connection() -> bool:
    """
    Test if we can send events (check if current_task is available)

    Returns:
        bool: True if event sending is available
    """
    try:
        return current_task is not None
    except Exception:
        return False
