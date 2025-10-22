# Celery Tasks Integration Guide for External Enhanced Flower Dashboard

## Overview

This guide shows how to modify **only the Celery tasks** in your existing Flask backend to emit custom events that will be monitored by this enhanced Flower dashboard deployed on a separate machine.

**Architecture:**
```
Flask Backend (Your Repo) → Redis → Enhanced Flower Dashboard (This Repo)
     ↓                        ↓              ↓
Celery Tasks with        Event Bus      Advanced Monitoring
Custom Events                          (Progress/Hierarchy/Failures)
```

## Prerequisites

- Your Flask backend has Celery tasks running
- Redis is accessible from both your Flask backend AND this Flower dashboard
- This enhanced Flower version will be deployed separately

## Part 1: Connection Setup

### 1.1 Network Configuration

**Ensure Redis connectivity between systems:**

```python
# In your Flask backend's Celery config
# Make sure Redis URL is accessible from both systems
CELERY_BROKER_URL = 'redis://YOUR_REDIS_HOST:6379/0'  # Same Redis as Flower will monitor
CELERY_RESULT_BACKEND = None  # Can remain disabled
```

**In this enhanced Flower deployment:**
```bash
# Start Flower pointing to the same Redis
celery -A your_flask_app flower --broker=redis://YOUR_REDIS_HOST:6379/0
```

### 1.2 Event Configuration

**Add to your Flask backend's Celery configuration:**

```python
# In your Flask app's Celery setup
from celery import Celery

celery_app = Celery('your_flask_app')
celery_app.conf.update(
    # Essential for enhanced monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_track_started=True,
    
    # Ensure events reach the monitoring system
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
)
```

## Part 2: Enhanced Task Implementation

### 2.1 Create Event Helper Module

**Create `your_flask_app/monitoring_events.py`:**

```python
import time
from celery import current_task

def send_custom_event(event_type, **kwargs):
    """
    Send custom events to external enhanced Flower dashboard
    
    Args:
        event_type: Type of event (task-custom-progress, task-custom-hierarchy, task-custom-failure)
        **kwargs: Event data
    """
    if current_task:
        current_task.send_event(event_type, **kwargs)

def send_progress_event(progress_percent, status="", **kwargs):
    """Send progress tracking event"""
    send_custom_event(
        "task-custom-progress",
        progress_percent=progress_percent,
        status=status,
        current=kwargs.get('current', 0),
        total=kwargs.get('total', 1),
        stage=kwargs.get('stage', 'processing'),
        stage_description=kwargs.get('stage_description', ''),
        subtasks_created=kwargs.get('subtasks_created', 0),
        subtasks_completed=kwargs.get('subtasks_completed', 0),
        subtasks_failed=kwargs.get('subtasks_failed', 0),
        subtasks_remaining=kwargs.get('subtasks_remaining', 0),
        last_updated=time.time(),
        **kwargs
    )

def send_hierarchy_event(task_type="single", **kwargs):
    """Send task hierarchy information"""
    send_custom_event(
        "task-custom-hierarchy",
        task_type=task_type,
        parent_id=kwargs.get('parent_id'),
        children=kwargs.get('children', []),
        depth=kwargs.get('depth', 0),
        hierarchy_data=kwargs.get('hierarchy_data', {}),
        last_updated=time.time(),
        **kwargs
    )

def send_failure_event(failure_reason, **kwargs):
    """Send enhanced failure tracking event"""
    send_custom_event(
        "task-custom-failure",
        failure_reason=failure_reason,
        failure_metadata=kwargs.get('failure_metadata', {}),
        failure_stage=kwargs.get('failure_stage', ''),
        retry_count=kwargs.get('retry_count', 0),
        last_error=kwargs.get('last_error', ''),
        error_traceback=kwargs.get('error_traceback', ''),
        failed_at=time.time(),
        **kwargs
    )

def send_chain_progress_event(current_step, total_steps, **kwargs):
    """Send chain/pipeline progress event"""
    pipeline_progress = (current_step / total_steps) * 100
    send_custom_event(
        "task-custom-chain-progress",
        current_step=current_step,
        total_steps=total_steps,
        pipeline_progress=pipeline_progress,
        current_stage_name=kwargs.get('current_stage_name', ''),
        status=kwargs.get('status', ''),
        progress_percent=pipeline_progress,
        **kwargs
    )
```

### 2.2 Enhanced Monitoring Decorator

**Add to `your_flask_app/monitoring_events.py`:**

```python
from functools import wraps

def enhanced_monitoring(task_type="single"):
    """
    Decorator to add enhanced monitoring to any Celery task
    
    Usage:
        @celery_app.task(bind=True)
        @enhanced_monitoring(task_type="single")  # or "parent_with_subtasks", "chain_task"
        def your_task(self, ...):
            # Your task code
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Send initial hierarchy event
            send_hierarchy_event(task_type=task_type)
            
            # Send initial progress
            send_progress_event(0, "Task started")
            
            try:
                result = func(self, *args, **kwargs)
                # Send completion
                send_progress_event(100, "Task completed successfully")
                return result
            except Exception as e:
                # Send failure event
                import traceback
                send_failure_event(
                    failure_reason=str(e),
                    failure_stage="execution",
                    error_traceback=traceback.format_exc(),
                    last_error=str(e)
                )
                raise
        return wrapper
    return decorator
```

## Part 3: Task Implementation Patterns

### 3.1 Simple Progress Task

**Example: Convert your existing task to enhanced monitoring:**

```python
# BEFORE (your existing task)
@celery_app.task(bind=True)
def process_data(self, data_list):
    for i, item in enumerate(data_list):
        process_item(item)
    return "done"

# AFTER (with enhanced monitoring)
from monitoring_events import enhanced_monitoring, send_progress_event

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="single")
def process_data(self, data_list):
    total_items = len(data_list)
    
    for i, item in enumerate(data_list):
        # Your existing processing logic
        process_item(item)
        
        # Add progress tracking
        progress = ((i + 1) / total_items) * 100
        send_progress_event(
            progress_percent=progress,
            status=f"Processed {i + 1}/{total_items} items",
            current=i + 1,
            total=total_items,
            stage="processing_items"
        )
    
    return "done"
```

### 3.2 Parent-Child Task Pattern

**Example: Task that creates subtasks:**

```python
from monitoring_events import enhanced_monitoring, send_hierarchy_event, send_progress_event

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="parent_with_subtasks")
def batch_processor(self, total_batches=5):
    # Create subtasks
    subtask_ids = []
    
    for i in range(total_batches):
        subtask = process_batch.delay(i, self.request.id)  # Pass parent ID
        subtask_ids.append(subtask.id)
    
    # Update hierarchy with children
    send_hierarchy_event(
        task_type="parent_with_subtasks",
        children=subtask_ids,
        depth=0
    )
    
    # Update progress with subtask info
    send_progress_event(
        progress_percent=50,
        status=f"Created {total_batches} subtasks",
        subtasks_created=total_batches,
        subtasks_completed=0,
        subtasks_failed=0,
        subtasks_remaining=total_batches
    )
    
    # In production, you'd monitor AsyncResult here
    # For demo, we'll simulate completion
    time.sleep(10)  # Wait for subtasks
    
    send_progress_event(
        progress_percent=100,
        status="All subtasks completed",
        subtasks_created=total_batches,
        subtasks_completed=total_batches,
        subtasks_failed=0,
        subtasks_remaining=0
    )
    
    return {"subtasks_created": total_batches}

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="subtask")
def process_batch(self, batch_id, parent_id):
    from monitoring_events import send_hierarchy_event, send_progress_event
    
    # Send hierarchy event for child
    send_hierarchy_event(
        task_type="subtask",
        parent_id=parent_id,
        children=[],
        depth=1
    )
    
    # Process with progress
    for i in range(10):
        time.sleep(1)
        progress = ((i + 1) / 10) * 100
        send_progress_event(
            progress_percent=progress,
            status=f"Batch {batch_id}: {i + 1}/10",
            current=i + 1,
            total=10
        )
    
    return f"batch_{batch_id}_completed"
```

### 3.3 Chain/Pipeline Task Pattern

**Example: Sequential processing steps:**

```python
from monitoring_events import enhanced_monitoring, send_chain_progress_event

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="chain_task")
def data_pipeline_step1(self, data_id):
    """Step 1: Extract data"""
    send_chain_progress_event(
        current_step=1,
        total_steps=3,
        current_stage_name="extract",
        status="Extracting data from source"
    )
    
    # Your extraction logic
    extracted_data = extract_data(data_id)
    
    # Chain to next step
    return data_pipeline_step2.delay(extracted_data)

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="chain_task")
def data_pipeline_step2(self, data):
    """Step 2: Transform data"""
    send_chain_progress_event(
        current_step=2,
        total_steps=3,
        current_stage_name="transform",
        status="Transforming data"
    )
    
    # Your transformation logic
    transformed_data = transform_data(data)
    
    return data_pipeline_step3.delay(transformed_data)

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="chain_task")
def data_pipeline_step3(self, data):
    """Step 3: Load data"""
    send_chain_progress_event(
        current_step=3,
        total_steps=3,
        current_stage_name="load",
        status="Loading data to destination"
    )
    
    # Your loading logic
    result = load_data(data)
    
    return result
```

### 3.4 Error Handling with Enhanced Failures

**Example: Task with detailed failure reporting:**

```python
@celery_app.task(bind=True)
@enhanced_monitoring(task_type="single")
def risky_processing_task(self, file_path):
    from monitoring_events import send_failure_event, send_progress_event
    
    try:
        # Step 1: Validate file
        send_progress_event(20, "Validating file", stage="validation")
        validate_file(file_path)
        
        # Step 2: Process file
        send_progress_event(50, "Processing file", stage="processing")
        result = process_file(file_path)
        
        # Step 3: Save results
        send_progress_event(80, "Saving results", stage="saving")
        save_results(result)
        
        return result
        
    except FileNotFoundError as e:
        send_failure_event(
            failure_reason="File not found",
            failure_stage="validation",
            failure_metadata={
                "file_path": file_path,
                "error_type": "FileNotFoundError",
                "attempted_operation": "file_validation"
            },
            last_error=str(e)
        )
        raise
        
    except ProcessingError as e:
        send_failure_event(
            failure_reason="Processing failed",
            failure_stage="processing", 
            failure_metadata={
                "file_path": file_path,
                "error_type": "ProcessingError",
                "processing_step": getattr(e, 'step', 'unknown')
            },
            last_error=str(e)
        )
        raise
```

## Part 4: Testing Your Integration

### 4.1 Create Test Tasks

**Add to your Flask app:**

```python
# Test tasks to verify monitoring works
@celery_app.task(bind=True)
@enhanced_monitoring(task_type="single")
def test_progress_task(self):
    """Test basic progress tracking"""
    for i in range(10):
        time.sleep(2)
        send_progress_event(
            progress_percent=(i + 1) * 10,
            status=f"Step {i + 1} of 10 completed",
            current=i + 1,
            total=10
        )
    return "Test completed"

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="parent_with_subtasks") 
def test_hierarchy_task(self):
    """Test parent-child hierarchy"""
    subtasks = []
    for i in range(3):
        task = test_child_task.delay(i, self.request.id)
        subtasks.append(task.id)
    
    send_hierarchy_event(
        task_type="parent_with_subtasks",
        children=subtasks
    )
    
    send_progress_event(
        progress_percent=100,
        subtasks_created=3,
        subtasks_completed=3,
        subtasks_failed=0
    )
    return {"subtasks": 3}

@celery_app.task(bind=True)
def test_child_task(self, index, parent_id):
    """Child task for hierarchy testing"""
    send_hierarchy_event(
        task_type="subtask",
        parent_id=parent_id,
        depth=1
    )
    
    for i in range(5):
        time.sleep(1)
        send_progress_event(
            progress_percent=(i + 1) * 20,
            status=f"Child {index}: step {i + 1}/5"
        )
    return f"child_{index}_done"

# Flask endpoints to trigger tests
@app.route('/test/progress')
def test_progress():
    task = test_progress_task.delay()
    return {"task_id": task.id, "monitor_url": f"http://FLOWER_HOST:5555/task/{task.id}"}

@app.route('/test/hierarchy')  
def test_hierarchy():
    task = test_hierarchy_task.delay()
    return {"task_id": task.id, "monitor_url": f"http://FLOWER_HOST:5555/task/{task.id}"}
```

### 4.2 Verification Steps

1. **Start your enhanced Flower dashboard** (this repo):
   ```bash
   celery -A example_enhanced_tasks flower --broker=redis://YOUR_REDIS_HOST:6379/0 --port=5555
   ```

2. **Trigger test tasks** from your Flask backend:
   ```bash
   curl http://your-flask-app/test/progress
   curl http://your-flask-app/test/hierarchy  
   ```

3. **Check enhanced monitoring** in Flower:
   - Visit the task URLs returned by the test endpoints
   - Verify all tabs work: Overview, Progress, Hierarchy, Failure Analysis
   - Confirm real-time updates appear

## Part 5: Production Deployment

### 5.1 Environment Variables

**In your Flask backend:**

```python
import os

# Control monitoring features
ENHANCED_MONITORING_ENABLED = os.getenv('ENHANCED_MONITORING_ENABLED', 'true').lower() == 'true'

def send_progress_event_safe(*args, **kwargs):
    """Safe wrapper that can be disabled in production"""
    if ENHANCED_MONITORING_ENABLED:
        send_progress_event(*args, **kwargs)
```

### 5.2 Performance Considerations

```python
import time

# Throttle progress updates to avoid overwhelming Redis
class ProgressThrottler:
    def __init__(self, min_interval=1.0):
        self.min_interval = min_interval
        self.last_update = 0
    
    def should_update(self):
        now = time.time()
        if now - self.last_update >= self.min_interval:
            self.last_update = now
            return True
        return False

# Usage in tasks
progress_throttler = ProgressThrottler(min_interval=2.0)  # Max 1 update per 2 seconds

for i in range(1000):
    process_item(i)
    
    if progress_throttler.should_update():
        send_progress_event(
            progress_percent=(i / 1000) * 100,
            status=f"Processed {i}/1000 items"
        )
```

## Summary

This integration requires only:

1. **Add the monitoring_events.py module** to your Flask backend
2. **Decorate your existing Celery tasks** with `@enhanced_monitoring`
3. **Add progress/hierarchy/failure events** within task logic
4. **Deploy this enhanced Flower** pointing to your Redis
5. **Test the connection** with provided test tasks

**No changes needed to:**
- Your existing Flower installation
- Your Flask app structure  
- Your Redis/Celery configuration (except event settings)
- Your existing task logic (just add monitoring calls)

The enhanced Flower dashboard will automatically detect and display the custom events from your Flask backend tasks!