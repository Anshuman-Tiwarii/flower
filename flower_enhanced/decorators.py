"""
Enhanced Task Monitoring - Decorators

Simple decorators for automatic monitoring integration with Celery tasks.
"""

import functools
import traceback
from typing import Optional, Union

from .events import send_hierarchy_event, send_progress_event, send_failure_event
from .types import TaskType


def enhanced_monitoring(
    task_type: Union[str, TaskType] = "single",
    auto_hierarchy: bool = True,
    auto_progress: bool = False,
    auto_failure: bool = True,
    depth: int = 0,
    parent_id: Optional[str] = None,
    **hierarchy_data,
):
    """
    Decorator to automatically add enhanced monitoring to Celery tasks

    Args:
        task_type: Type of task for classification
        auto_hierarchy: Automatically send hierarchy events on task start
        auto_progress: Automatically send initial and final progress events
        auto_failure: Automatically send failure events on exceptions
        depth: Hierarchy depth level (0 for root tasks)
        parent_id: Parent task ID (auto-detected if not provided)
        **hierarchy_data: Additional hierarchy metadata

    Example:
        @celery_app.task(bind=True)
        @enhanced_monitoring(
            task_type="data_processor",
            auto_hierarchy=True,
            auto_progress=True
        )
        def process_data(self, data_list):
            # Task automatically sends hierarchy and progress events
            for i, item in enumerate(data_list):
                process_item(item)
                # Manual progress updates still available
                send_progress_event(progress_percent=(i+1)/len(data_list)*100)
            return "completed"
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            task_type_str = (
                task_type.value if isinstance(task_type, TaskType) else task_type
            )

            # Send initial hierarchy event
            if auto_hierarchy:
                send_hierarchy_event(
                    task_type=task_type_str,
                    parent_id=parent_id,
                    children=[],  # Will be updated when children are created
                    depth=depth,
                    hierarchy_data=hierarchy_data,
                )

            # Send initial progress event
            if auto_progress:
                send_progress_event(
                    progress_percent=0,
                    status=f"Starting {task_type_str} task",
                    stage="initialization",
                )

            try:
                # Execute the actual task
                result = func(self, *args, **kwargs)

                # Send completion progress event
                if auto_progress:
                    send_progress_event(
                        progress_percent=100,
                        status=f"Completed {task_type_str} task",
                        stage="completed",
                    )

                return result

            except Exception as e:
                # Send failure event if auto_failure is enabled
                if auto_failure:
                    send_failure_event(
                        failure_reason=str(e),
                        failure_stage="execution",
                        failure_metadata={
                            "exception_type": type(e).__name__,
                            "exception_message": str(e),
                            "task_type": task_type_str,
                            "traceback": traceback.format_exc(),
                        },
                    )

                # Re-raise the exception
                raise

        return wrapper

    return decorator


def hierarchy_task(
    task_type: Union[str, TaskType] = "parent",
    depth: int = 0,
    parent_id: Optional[str] = None,
    **hierarchy_data,
):
    """
    Simplified decorator specifically for hierarchy tracking

    Args:
        task_type: Type of task for classification
        depth: Hierarchy depth level (0 for root tasks)
        parent_id: Parent task ID (auto-detected if not provided)
        **hierarchy_data: Additional hierarchy metadata

    Example:
        @celery_app.task(bind=True)
        @hierarchy_task(task_type="workflow_coordinator", depth=0)
        def coordinate_workflow(self, workflow_config):
            # Automatically sends hierarchy event
            subtasks = []
            for item in workflow_config.items:
                subtask = process_item.delay(item, parent_id=self.request.id)
                subtasks.append(subtask.id)

            # Update hierarchy with children
            send_hierarchy_event(
                task_type="workflow_coordinator",
                children=subtasks,
                depth=0
            )
            return subtasks
    """
    return enhanced_monitoring(
        task_type=task_type,
        auto_hierarchy=True,
        auto_progress=False,
        auto_failure=True,
        depth=depth,
        parent_id=parent_id,
        **hierarchy_data,
    )


def progress_task(
    task_type: Union[str, TaskType] = "single",
    auto_failure: bool = True,
    **hierarchy_data,
):
    """
    Simplified decorator specifically for progress tracking

    Args:
        task_type: Type of task for classification
        auto_failure: Automatically send failure events on exceptions
        **hierarchy_data: Additional hierarchy metadata

    Example:
        @celery_app.task(bind=True)
        @progress_task(task_type="data_processor")
        def process_large_dataset(self, dataset):
            # Automatically sends initial and final progress events
            for i, record in enumerate(dataset):
                process_record(record)
                # Manual progress updates
                send_progress_event(
                    progress_percent=(i+1)/len(dataset)*100,
                    current=i+1,
                    total=len(dataset),
                    status=f"Processed {i+1}/{len(dataset)} records"
                )
            return "completed"
    """
    return enhanced_monitoring(
        task_type=task_type,
        auto_hierarchy=True,  # All tasks are hierarchy tasks (even with 0 children)
        auto_progress=True,
        auto_failure=auto_failure,
        depth=0,
        **hierarchy_data,
    )


def failure_tracking_task(task_type: Union[str, TaskType] = "single", **hierarchy_data):
    """
    Simplified decorator specifically for failure tracking

    Args:
        task_type: Type of task for classification
        **hierarchy_data: Additional hierarchy metadata

    Example:
        @celery_app.task(bind=True)
        @failure_tracking_task(task_type="critical_operation")
        def critical_database_operation(self, operation_config):
            # Automatically sends failure events with detailed metadata
            try:
                return perform_database_operation(operation_config)
            except DatabaseError as e:
                # Additional manual failure context
                send_failure_event(
                    failure_reason=f"Database operation failed: {e}",
                    failure_stage="database_connection",
                    failure_metadata={
                        "operation_type": operation_config.type,
                        "database_host": operation_config.host,
                        "error_code": getattr(e, 'error_code', None)
                    }
                )
                raise
    """
    return enhanced_monitoring(
        task_type=task_type,
        auto_hierarchy=True,  # All tasks are hierarchy tasks
        auto_progress=False,
        auto_failure=True,
        depth=0,
        **hierarchy_data,
    )
