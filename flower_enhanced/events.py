"""
Enhanced Task Monitoring - Event Sending Functions

Core functions for sending monitoring events to Redis for Flower to consume.
These functions are used by Celery tasks to report progress, hierarchy, and failures.
"""

import json
import time
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from .config import config
from .types import EVENT_TYPES

logger = logging.getLogger(__name__)

# Global Redis connection (lazy loaded)
_redis_connection = None


def _get_redis_connection():
    """Get or create Redis connection with retry logic"""
    global _redis_connection

    if not config.enabled:
        return None

    if _redis_connection is None:
        try:
            import redis

            connection_params = config.get_redis_connection_params()
            _redis_connection = redis.Redis(**connection_params)

            # Test connection
            _redis_connection.ping()

            if config.debug:
                logger.info(f"Connected to Redis: {config.redis_url}")

        except ImportError:
            logger.error("Redis package not installed. Run: pip install redis")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None

    return _redis_connection


def _get_current_task_id() -> Optional[str]:
    """Get current Celery task ID"""
    try:
        from celery import current_task

        if current_task and current_task.request:
            return current_task.request.id
    except ImportError:
        logger.warning("Celery not available. Cannot get task ID.")
    except Exception as e:
        if config.debug:
            logger.debug(f"Could not get current task ID: {e}")

    return None


def _sanitize_data(data: Any, max_size: int = None) -> Any:
    """Sanitize data for safe JSON serialization"""
    if not config.sanitize_data:
        return data

    max_size = max_size or config.max_payload_size

    try:
        # Convert to JSON to check size and serializability
        json_str = json.dumps(data, default=str)

        if len(json_str) > max_size:
            # Truncate large data
            truncated = f"[TRUNCATED: {len(json_str)} bytes > {max_size} limit]"
            if isinstance(data, str):
                return data[: max_size - len(truncated)] + truncated
            elif isinstance(data, dict):
                return {"error": truncated, "original_keys": list(data.keys())[:10]}
            else:
                return truncated

        return data

    except (TypeError, ValueError) as e:
        logger.warning(f"Data sanitization failed: {e}")
        return f"[SERIALIZATION_ERROR: {str(e)}]"


@contextmanager
def _error_handling(operation: str):
    """Context manager for consistent error handling"""
    try:
        yield
    except Exception as e:
        if config.debug:
            logger.error(f"Enhanced monitoring {operation} failed: {e}")
        elif not isinstance(e, (ImportError, ConnectionError)):
            logger.warning(f"Enhanced monitoring {operation} failed silently")


def _send_event(
    event_type: str, task_id: str, event_data: Dict[str, Any], retry_count: int = 0
) -> bool:
    """Send event to Redis with retry logic"""

    if not config.enabled:
        return False

    with _error_handling(f"event send ({event_type})"):
        redis_conn = _get_redis_connection()
        if not redis_conn:
            return False

        # Prepare event payload
        timestamp = time.time()
        payload = {
            "uuid": task_id,
            "type": event_type,
            "hostname": _get_hostname(),
            "timestamp": timestamp,
            "local_received": timestamp,
            **event_data,
        }

        # Sanitize payload
        payload = _sanitize_data(payload)

        try:
            # Send event to Redis
            event_key = f"{config.event_prefix}:{task_id}"
            redis_conn.lpush(event_key, json.dumps(payload, default=str))
            redis_conn.expire(event_key, 3600)  # Expire after 1 hour

            if config.debug:
                logger.debug(f"Sent {event_type} event for task {task_id}")

            return True

        except Exception as e:
            if retry_count < config.retry_attempts:
                time.sleep(config.retry_delay)
                return _send_event(event_type, task_id, event_data, retry_count + 1)
            else:
                logger.error(f"Failed to send event after {retry_count} retries: {e}")
                return False


def _get_hostname() -> str:
    """Get current hostname"""
    try:
        import socket

        return socket.gethostname()
    except Exception:
        return "unknown"


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
    task_id: Optional[str] = None,
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
        task_id: Task ID (auto-detected if not provided)

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
    task_id = task_id or _get_current_task_id()
    if not task_id:
        if config.debug:
            logger.warning("No task ID available for progress event")
        return False

    # Calculate remaining subtasks if not provided
    if subtasks_remaining is None and subtasks_created > 0:
        subtasks_remaining = subtasks_created - subtasks_completed - subtasks_failed

    event_data = {
        "progress_percent": float(progress_percent),
        "status": status,
        "current": current,
        "total": total,
        "stage": stage,
        "stage_description": stage_description,
        "stage_progress": stage_progress,
        "subtasks_created": subtasks_created,
        "subtasks_completed": subtasks_completed,
        "subtasks_failed": subtasks_failed,
        "subtasks_remaining": subtasks_remaining,
        "current_step": current_step,
        "total_steps": total_steps,
        "current_stage_name": current_stage_name,
        "custom_data": custom_data or {},
    }

    return _send_event(EVENT_TYPES["PROGRESS"], task_id, event_data)


def send_hierarchy_event(
    task_type: str,
    parent_id: Optional[str] = None,
    children: Optional[List[str]] = None,
    depth: int = 0,
    hierarchy_data: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
) -> bool:
    """
    Send task hierarchy information

    Args:
        task_type: Type of task (single, parent, child, chain_step, etc.)
        parent_id: Parent task ID if this is a subtask
        children: List of child task IDs if this creates subtasks
        depth: Depth level in hierarchy (0 for root)
        hierarchy_data: Additional hierarchy metadata
        task_id: Task ID (auto-detected if not provided)

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
    task_id = task_id or _get_current_task_id()
    if not task_id:
        if config.debug:
            logger.warning("No task ID available for hierarchy event")
        return False

    # Auto-detect parent from Celery context if not provided
    if parent_id is None:
        try:
            from celery import current_task

            if current_task and hasattr(current_task.request, "parent_id"):
                parent_id = current_task.request.parent_id
        except (ImportError, AttributeError):
            pass

    event_data = {
        "task_type": task_type,
        "parent_id": parent_id,
        "children": children or [],
        "depth": depth,
        "hierarchy_data": hierarchy_data or {},
    }

    return _send_event(EVENT_TYPES["HIERARCHY"], task_id, event_data)


def send_failure_event(
    failure_reason: str,
    failure_stage: Optional[str] = None,
    failure_metadata: Optional[Dict[str, Any]] = None,
    system_metrics: Optional[Dict[str, Any]] = None,
    retry_context: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
) -> bool:
    """
    Send task failure metadata

    Args:
        failure_reason: Description of the failure
        failure_stage: Stage where failure occurred
        failure_metadata: Additional failure context and metadata
        system_metrics: System metrics at time of failure
        retry_context: Retry-related information
        task_id: Task ID (auto-detected if not provided)

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
    task_id = task_id or _get_current_task_id()
    if not task_id:
        if config.debug:
            logger.warning("No task ID available for failure event")
        return False

    # Collect system metrics if not provided
    if system_metrics is None:
        system_metrics = _collect_system_metrics()

    # Auto-detect retry context from Celery if not provided
    if retry_context is None:
        try:
            from celery import current_task

            if current_task and current_task.request:
                retry_context = {
                    "retries": getattr(current_task.request, "retries", 0),
                    "eta": getattr(current_task.request, "eta", None),
                    "expires": getattr(current_task.request, "expires", None),
                }
        except (ImportError, AttributeError):
            retry_context = {}

    event_data = {
        "failure_reason": failure_reason,
        "failure_stage": failure_stage,
        "failure_metadata": failure_metadata or {},
        "system_metrics": system_metrics or {},
        "retry_context": retry_context or {},
    }

    return _send_event(EVENT_TYPES["FAILURE"], task_id, event_data)


def _collect_system_metrics() -> Dict[str, Any]:
    """Collect basic system metrics"""
    metrics = {}

    try:
        import psutil

        # CPU and memory
        metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        metrics["memory_percent"] = memory.percent
        metrics["memory_available_gb"] = round(memory.available / (1024**3), 2)

        # Load average (Unix only)
        if hasattr(psutil, "getloadavg"):
            load_avg = psutil.getloadavg()
            metrics["load_average_1min"] = round(load_avg[0], 2)

        # Hostname
        metrics["hostname"] = _get_hostname()

    except ImportError:
        if config.debug:
            logger.debug("psutil not available for system metrics")
        metrics["error"] = "psutil not installed"
    except Exception as e:
        if config.debug:
            logger.debug(f"Failed to collect system metrics: {e}")
        metrics["error"] = str(e)

    return metrics


def bulk_send_events(events: List[Dict[str, Any]]) -> int:
    """
    Send multiple events in a batch for better performance

    Args:
        events: List of event dictionaries with 'type', 'task_id', and 'data' keys

    Returns:
        int: Number of events successfully sent
    """
    if not config.enabled or not events:
        return 0

    success_count = 0

    with _error_handling("bulk event send"):
        for event in events:
            event_type = event.get("type")
            task_id = event.get("task_id")
            event_data = event.get("data", {})

            if event_type and task_id:
                if _send_event(event_type, task_id, event_data):
                    success_count += 1

    return success_count


def test_connection() -> bool:
    """
    Test Redis connection and configuration

    Returns:
        bool: True if connection is working
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            redis_conn.ping()
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")

    return False
