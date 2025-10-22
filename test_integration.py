#!/usr/bin/env python3
"""
Integration test for flower_enhanced client utilities

This script tests the client utilities with actual Celery tasks to ensure
they integrate properly with the enhanced monitoring system.
"""

from celery import Celery
import sys
import os
import time

# Import and configure enhanced monitoring
from flower_enhanced import (
    enhanced_monitoring,
    send_progress_event,
    send_hierarchy_event,
    send_failure_event,
    TaskType,
    configure,
)

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Celery app
app = Celery("integration_test")
app.conf.broker_url = "redis://localhost:6379/0"
app.conf.result_backend = "redis://localhost:6379/0"

# Configure enhanced monitoring
configure(redis_url="redis://localhost:6379/0", enabled=True, debug=True)


@app.task(bind=True)
@enhanced_monitoring(task_type=TaskType.DATA_PROCESSOR, auto_progress=True)
def test_progress_task(self, items_count=10):
    """Test task with manual progress reporting"""
    print(f"Starting progress test with {items_count} items")

    for i in range(items_count):
        time.sleep(0.3)  # Simulate work

        progress = ((i + 1) / items_count) * 100
        send_progress_event(
            progress_percent=progress,
            status=f"Processing item {i + 1}/{items_count}",
            current=i + 1,
            total=items_count,
            stage="processing",
        )

        print(f"  Progress: {progress:.1f}%")

    return {"status": "completed", "items_processed": items_count}


@app.task(bind=True)
@enhanced_monitoring(task_type=TaskType.WORKFLOW_COORDINATOR, auto_hierarchy=True)
def test_hierarchy_task(self, subtask_count=3):
    """Test task that creates hierarchy"""
    print(f"Starting hierarchy test with {subtask_count} subtasks")

    # Create subtasks
    subtask_ids = []
    for i in range(subtask_count):
        subtask = test_child_task.delay(f"child_{i}", self.request.id)
        subtask_ids.append(subtask.id)
        print(f"  Created subtask {i + 1}: {subtask.id}")

    # Send hierarchy event
    send_hierarchy_event(
        task_type=TaskType.WORKFLOW_COORDINATOR, children=subtask_ids, depth=0
    )

    # Track coordination progress
    send_progress_event(
        progress_percent=100,
        status="All subtasks created",
        subtasks_created=len(subtask_ids),
        stage="coordination",
    )

    return {
        "coordinator_id": self.request.id,
        "subtasks_created": subtask_ids,
        "count": len(subtask_ids),
    }


@app.task(bind=True)
@enhanced_monitoring(task_type=TaskType.CHILD, auto_progress=True)
def test_child_task(self, data, parent_id):
    """Test child task with hierarchy"""
    print(f"Starting child task: {data} (parent: {parent_id})")

    # Send hierarchy to establish parent relationship
    send_hierarchy_event(task_type=TaskType.CHILD, parent_id=parent_id, depth=1)

    # Simulate work with progress
    for i in range(3):
        time.sleep(0.5)
        progress = ((i + 1) / 3) * 100
        send_progress_event(
            progress_percent=progress,
            status=f"Child {data} step {i + 1}/3",
            current=i + 1,
            total=3,
        )

    return {"data": data, "parent": parent_id, "status": "completed"}


@app.task(bind=True)
@enhanced_monitoring(task_type=TaskType.DATA_PROCESSOR, auto_failure=True)
def test_failure_task(self, should_fail=True):
    """Test task that demonstrates failure tracking"""
    print(f"Starting failure test (will_fail: {should_fail})")

    send_progress_event(
        progress_percent=25, status="Starting failure test...", stage="initialization"
    )

    time.sleep(0.5)

    if should_fail:
        # Send custom failure event
        send_failure_event(
            failure_reason="Intentional test failure",
            failure_stage="processing",
            failure_metadata={
                "test_run": True,
                "failure_type": "intentional",
                "recovery_hint": "Set should_fail=False",
            },
        )

        raise ValueError("This is an intentional test failure")

    send_progress_event(
        progress_percent=100, status="Test completed successfully", stage="completion"
    )

    return {"status": "success", "test": "passed"}


def test_client_integration():
    """Test the integration by running actual tasks"""
    print("Testing flower_enhanced integration with Celery\n")

    # Test 1: Progress tracking
    print("1. Testing progress tracking...")
    try:
        result = test_progress_task.delay(5)
        print(f"   Task ID: {result.id}")
        print(f"   Monitor at: http://localhost:5555/task/{result.id}")
        print("   Progress task started\n")
    except Exception as e:
        print(f"   Progress task failed: {e}\n")

    # Test 2: Hierarchy tracking
    print("2. Testing hierarchy tracking...")
    try:
        result = test_hierarchy_task.delay(2)
        print(f"   Task ID: {result.id}")
        print(f"   Monitor at: http://localhost:5555/task/{result.id}")
        print("   Hierarchy task started\n")
    except Exception as e:
        print(f"   Hierarchy task failed: {e}\n")

    # Test 3: Failure tracking
    print("3. Testing failure tracking...")
    try:
        result = test_failure_task.delay(True)  # Will fail
        print(f"   Task ID: {result.id}")
        print(f"   Monitor at: http://localhost:5555/task/{result.id}")
        print("   Failure task started (will fail intentionally)\n")
    except Exception as e:
        print(f"   Failure task failed to start: {e}\n")

    # Test 4: Success case
    print("4. Testing success case...")
    try:
        result = test_failure_task.delay(False)  # Will succeed
        print(f"   Task ID: {result.id}")
        print(f"   Monitor at: http://localhost:5555/task/{result.id}")
        print("   Success task started\n")
    except Exception as e:
        print(f"   Success task failed: {e}\n")

    print("Integration test completed!")
    print("\nTo monitor these tasks:")
    print("1. Ensure Flower is running: celery -A integration_test flower")
    print("2. Open http://localhost:5555 in your browser")
    print("3. Navigate to the task URLs shown above")
    print("4. Check the Progress, Hierarchy, and Failure Analysis tabs")


def main():
    """Main test function"""
    print("flower_enhanced Integration Test\n")

    # Test basic functionality first
    print("Testing basic client utilities...")
    from flower_enhanced.events import test_connection

    if not test_connection():
        print("Redis connection failed. Ensure Redis is running.")
        return 1
    print("Redis connection working\n")

    # Run integration test
    test_client_integration()

    print("\nIntegration test completed successfully!")
    print("\nNext steps:")
    print("1. Check the Flower dashboard for real-time monitoring")
    print("2. Verify all three monitoring types (Progress, Hierarchy, Failure)")
    print("3. Test the enhanced monitoring in your own projects")

    return 0


if __name__ == "__main__":
    sys.exit(main())
