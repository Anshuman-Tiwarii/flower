"""
Enhanced Task Monitoring - Decorators

Provides decorators for automatic monitoring integration with Celery tasks.
"""

import functools
import time
import logging
from typing import Optional, Dict, Any, Callable, Union

from .events import send_hierarchy_event, send_progress_event, send_failure_event
from .types import TaskType
from .config import config

logger = logging.getLogger(__name__)


def enhanced_monitoring(
    task_type: Union[str, TaskType] = TaskType.SINGLE,
    auto_hierarchy: bool = True,
    auto_progress: bool = False,
    auto_failure: bool = True,
    progress_stages: Optional[Dict[str, str]] = None,
    custom_metadata: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to automatically enable enhanced monitoring for a Celery task

    Args:
        task_type: Type of task for classification (single, parent, child, etc.)
        auto_hierarchy: Automatically send hierarchy events
        auto_progress: Automatically track basic progress (start/end)
        auto_failure: Automatically send failure events on exceptions
        progress_stages: Dict mapping stage names to descriptions
        custom_metadata: Additional metadata to include in events

    Returns:
        Decorated function with enhanced monitoring capabilities

    Example:
        @enhanced_monitoring(
            task_type=TaskType.DATA_PROCESSOR,
            auto_progress=True,
            progress_stages={
                "validation": "Validating input data",
                "processing": "Processing data records",
                "completion": "Finalizing results"
            }
        )
        def process_data(self, data):
            # Task automatically participates in enhanced monitoring
            send_progress_event(progress_percent=50, stage="processing")
            return process_data_logic(data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not config.enabled:
                # If monitoring is disabled, just run the original function
                return func(self, *args, **kwargs)

            # Get task information
            task_id = getattr(self.request, "id", None)
            parent_id = getattr(self.request, "parent_id", None)

            if not task_id:
                logger.warning("No task ID available for enhanced monitoring")
                return func(self, *args, **kwargs)

            # Calculate depth from parent chain
            depth = _calculate_task_depth(parent_id)

            # Convert TaskType enum to string if needed
            task_type_str = (
                task_type.value if isinstance(task_type, TaskType) else task_type
            )

            # Send initial hierarchy event
            if auto_hierarchy:
                hierarchy_success = send_hierarchy_event(
                    task_type=task_type_str,
                    parent_id=parent_id,
                    depth=depth,
                    hierarchy_data=custom_metadata or {},
                )

                if config.debug and hierarchy_success:
                    logger.debug(
                        f"Sent hierarchy event for task {task_id} (type: {task_type_str})"
                    )

            # Send initial progress event
            if auto_progress:
                send_progress_event(
                    progress_percent=0,
                    status="Task started",
                    stage="initialization",
                    custom_data=custom_metadata,
                )

            start_time = time.time()

            try:
                # Execute the original task
                result = func(self, *args, **kwargs)

                # Send completion progress if auto_progress enabled
                if auto_progress:
                    execution_time = time.time() - start_time
                    send_progress_event(
                        progress_percent=100,
                        status="Task completed successfully",
                        stage="completion",
                        custom_data={
                            **(custom_metadata or {}),
                            "execution_time": round(execution_time, 2),
                        },
                    )

                return result

            except Exception as e:
                # Send failure event if auto_failure enabled
                if auto_failure:
                    execution_time = time.time() - start_time

                    # Determine failure stage
                    failure_stage = "execution"
                    if execution_time < 1.0:
                        failure_stage = "initialization"
                    elif hasattr(e, "__cause__") and e.__cause__:
                        failure_stage = "processing"

                    # Collect failure metadata
                    failure_metadata = {
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "execution_time": round(execution_time, 2),
                        "task_type": task_type_str,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())[
                            :10
                        ],  # Limit to first 10 keys
                        **(custom_metadata or {}),
                    }

                    # Add retry information if available
                    retry_context = {}
                    if hasattr(self.request, "retries"):
                        retry_context["current_retries"] = self.request.retries
                    if hasattr(self, "max_retries"):
                        retry_context["max_retries"] = self.max_retries

                    failure_success = send_failure_event(
                        failure_reason=f"{type(e).__name__}: {str(e)}",
                        failure_stage=failure_stage,
                        failure_metadata=failure_metadata,
                        retry_context=retry_context,
                    )

                    if config.debug and failure_success:
                        logger.debug(
                            f"Sent failure event for task {task_id}: {type(e).__name__}"
                        )

                # Re-raise the original exception
                raise

        return wrapper

    return decorator


def progress_stages(*stages):
    """
    Decorator to define progress stages for a task

    Args:
        *stages: Stage names in execution order

    Example:
        @progress_stages("validation", "processing", "finalization")
        @enhanced_monitoring(auto_progress=True)
        def process_data(self, data):
            # Stages are automatically tracked
            return process_data_logic(data)
    """

    def decorator(func: Callable) -> Callable:
        func._progress_stages = stages
        return func

    return decorator


def failure_recovery(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    recovery_strategy: str = "exponential_backoff",
):
    """
    Decorator to add failure recovery capabilities with enhanced monitoring

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries
        recovery_strategy: Strategy for retry delays (linear, exponential_backoff)

    Example:
        @failure_recovery(max_retries=3, retry_delay=2.0)
        @enhanced_monitoring(auto_failure=True)
        def unreliable_task(self, data):
            # Task will be retried with monitoring on failures
            return process_unreliable_data(data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        # Calculate delay based on strategy
                        if recovery_strategy == "exponential_backoff":
                            delay = retry_delay * (2 ** (attempt - 1))
                        else:  # linear
                            delay = retry_delay * attempt

                        # Send retry progress event
                        send_progress_event(
                            progress_percent=0,
                            status=f"Retrying task (attempt {attempt + 1}/{max_retries + 1})",
                            stage="retry",
                            custom_data={
                                "retry_attempt": attempt,
                                "retry_delay": delay,
                                "last_failure": (
                                    str(last_exception) if last_exception else None
                                ),
                            },
                        )

                        time.sleep(delay)

                    # Execute the task
                    return func(self, *args, **kwargs)

                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        # Send retry failure event (but don't raise yet)
                        send_failure_event(
                            failure_reason=f"Attempt {attempt + 1} failed: {str(e)}",
                            failure_stage="retry_attempt",
                            failure_metadata={
                                "attempt_number": attempt + 1,
                                "max_retries": max_retries,
                                "will_retry": True,
                                "exception_type": type(e).__name__,
                            },
                        )
                    else:
                        # Final failure - let the enhanced_monitoring decorator handle it
                        raise

            # Should never reach here, but just in case
            raise last_exception

        return wrapper

    return decorator


def batch_processor(batch_size: int = 100, progress_frequency: int = 10):
    """
    Decorator for batch processing tasks with automatic progress reporting

    Args:
        batch_size: Size of each batch to process
        progress_frequency: Report progress every N batches

    Example:
        @batch_processor(batch_size=50, progress_frequency=5)
        @enhanced_monitoring(task_type=TaskType.BATCH_PROCESSOR)
        def process_records(self, records):
            # Automatic batching and progress reporting
            results = []
            for batch in batch_iterator(records, batch_size):
                batch_result = process_batch(batch)
                results.extend(batch_result)
            return results
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, data, *args, **kwargs):
            # If data is not iterable, just run normally
            if not hasattr(data, "__iter__") or isinstance(data, (str, bytes)):
                return func(self, data, *args, **kwargs)

            # Convert to list if needed to get length
            if not hasattr(data, "__len__"):
                data = list(data)

            total_items = len(data)
            total_batches = (total_items + batch_size - 1) // batch_size

            results = []

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_items)
                batch_data = data[start_idx:end_idx]

                # Process batch
                batch_result = func(self, batch_data, *args, **kwargs)
                if batch_result:
                    results.extend(
                        batch_result
                        if hasattr(batch_result, "__iter__")
                        else [batch_result]
                    )

                # Report progress
                if (
                    batch_num + 1
                ) % progress_frequency == 0 or batch_num == total_batches - 1:
                    progress_percent = ((batch_num + 1) / total_batches) * 100
                    send_progress_event(
                        progress_percent=progress_percent,
                        status=f"Processed batch {batch_num + 1}/{total_batches}",
                        current=batch_num + 1,
                        total=total_batches,
                        stage="batch_processing",
                        custom_data={
                            "batch_size": len(batch_data),
                            "items_processed": end_idx,
                            "total_items": total_items,
                        },
                    )

            return results

        return wrapper

    return decorator


def _calculate_task_depth(parent_id: Optional[str]) -> int:
    """Calculate task depth in hierarchy based on parent chain"""
    if not parent_id:
        return 0

    # For now, we'll do a simple calculation
    # In a more sophisticated implementation, we could query Redis
    # to trace the full parent chain
    return 1


def _get_stage_description(
    stage: str, progress_stages: Optional[Dict[str, str]]
) -> Optional[str]:
    """Get description for a progress stage"""
    if progress_stages and stage in progress_stages:
        return progress_stages[stage]
    return None
