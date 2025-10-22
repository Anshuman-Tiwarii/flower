# Flask Enhanced Monitoring Integration Guide

## Overview

This guide provides a complete roadmap for integrating the enhanced task monitoring system (progress tracking, hierarchy visualization, and failure analysis) from this Flower fork into an existing Flask backend with Celery and Redis.

## Prerequisites

Your Flask application should already have:
- ✅ Flask backend server
- ✅ Celery for background tasks
- ✅ Redis as message broker
- ✅ Flower monitoring tool

## Integration Architecture

```
Flask App → Celery Tasks → Redis Events → Enhanced Flower Dashboard
    ↓           ↓              ↓              ↓
 Endpoints   Enhanced      Custom         Advanced
           Event System   Events       Monitoring UI
```

## Phase 1: Core Event System Setup

### 1.1 Copy Enhanced Event System Files

**From this repo, copy these files to your Flask project:**

```bash
# Core event handling
cp flower/events.py your_flask_app/monitoring/
cp flower/api/enhanced_monitoring.py your_flask_app/monitoring/api/

# Frontend assets
cp flower/static/js/enhanced-monitoring.js your_flask_app/static/js/
cp flower/templates/task.html your_flask_app/templates/monitoring/
```

### 1.2 Update Flower Configuration

**In your existing Flower setup, modify these components:**

1. **Replace `flower/events.py`** with the enhanced version
2. **Add API endpoints** to your Flower app routing
3. **Update task template** with enhanced monitoring tabs

### 1.3 Celery Configuration Updates

**Add to your Flask app's Celery config:**

```python
# In your celery_config.py or wherever Celery is configured
from celery import Celery

app = Celery('your_flask_app')
app.conf.update(
    # Essential for enhanced monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_track_started=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Event routing (ensure events reach Flower)
    worker_hijack_root_logger=False,
    worker_log_color=False,
)
```

## Phase 2: Enhanced Task Implementation

### 2.1 Create Enhanced Task Base Class

**Create `your_flask_app/monitoring/enhanced_task.py`:**

```python
import time
from celery import current_task
from your_app import celery_app  # Your existing Celery instance

class EnhancedTaskMixin:
    """Mixin for adding enhanced monitoring to Celery tasks"""
    
    def send_custom_event(self, event_type, **kwargs):
        """Send custom events to Flower monitoring"""
        if current_task:
            current_task.send_event(event_type, **kwargs)
    
    def send_progress_event(self, progress_percent, status="", **kwargs):
        """Send progress tracking event"""
        self.send_custom_event(
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
    
    def send_hierarchy_event(self, task_type="single", **kwargs):
        """Send task hierarchy information"""
        self.send_custom_event(
            "task-custom-hierarchy",
            task_type=task_type,
            parent_id=kwargs.get('parent_id'),
            children=kwargs.get('children', []),
            depth=kwargs.get('depth', 0),
            hierarchy_data=kwargs.get('hierarchy_data', {}),
            last_updated=time.time(),
            **kwargs
        )
    
    def send_failure_event(self, failure_reason, **kwargs):
        """Send enhanced failure tracking event"""
        self.send_custom_event(
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
    
    def send_chain_progress_event(self, current_step, total_steps, **kwargs):
        """Send chain/pipeline progress event"""
        pipeline_progress = (current_step / total_steps) * 100
        self.send_custom_event(
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

### 2.2 Enhanced Task Decorator

**Create `your_flask_app/monitoring/decorators.py`:**

```python
from functools import wraps
from celery import current_task
from .enhanced_task import EnhancedTaskMixin

def enhanced_monitoring(task_type="single"):
    """Decorator to add enhanced monitoring to any Celery task"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Add enhanced monitoring methods to task instance
            for attr in dir(EnhancedTaskMixin):
                if not attr.startswith('_'):
                    setattr(self, attr, getattr(EnhancedTaskMixin(), attr))
            
            # Send initial hierarchy event
            self.send_hierarchy_event(task_type=task_type)
            
            # Send initial progress
            self.send_progress_event(0, "Task started")
            
            try:
                result = func(self, *args, **kwargs)
                # Send completion
                self.send_progress_event(100, "Task completed successfully")
                return result
            except Exception as e:
                # Send failure event
                self.send_failure_event(
                    failure_reason=str(e),
                    failure_stage="execution",
                    error_traceback=str(e)
                )
                raise
        return wrapper
    return decorator
```

## Phase 3: Flask Endpoint Integration Patterns

### 3.1 Single Long-Running Task Pattern

**For CPU-intensive or long-running operations:**

```python
from your_app import celery_app
from monitoring.decorators import enhanced_monitoring

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="single")
def process_large_dataset(self, dataset_id, total_records):
    """Example: Process large dataset with progress tracking"""
    
    # Get dataset
    dataset = get_dataset(dataset_id)
    
    for i, record in enumerate(dataset):
        # Process each record
        process_record(record)
        
        # Update progress
        progress = ((i + 1) / total_records) * 100
        self.send_progress_event(
            progress_percent=progress,
            status=f"Processed {i + 1}/{total_records} records",
            current=i + 1,
            total=total_records,
            stage="processing_records"
        )
    
    return {"processed": total_records, "status": "completed"}

# Flask endpoint
@app.route('/api/process-dataset', methods=['POST'])
def start_dataset_processing():
    dataset_id = request.json.get('dataset_id')
    task = process_large_dataset.delay(dataset_id, 1000)
    return {"task_id": task.id, "status": "started"}
```

### 3.2 Parent-Child Task Pattern

**For tasks that spawn multiple subtasks:**

```python
@celery_app.task(bind=True)
@enhanced_monitoring(task_type="parent_with_subtasks")
def batch_data_processing(self, batch_size=100):
    """Example: Parent task that creates multiple subtasks"""
    
    # Create subtasks
    subtask_ids = []
    total_batches = 10
    
    for i in range(total_batches):
        subtask = process_batch_subtask.delay(i, batch_size, self.request.id)
        subtask_ids.append(subtask.id)
    
    # Update hierarchy with children
    self.send_hierarchy_event(
        task_type="parent_with_subtasks",
        children=subtask_ids,
        depth=0
    )
    
    # Monitor progress
    self.send_progress_event(
        progress_percent=50,
        status=f"Created {total_batches} subtasks",
        subtasks_created=total_batches,
        subtasks_completed=0,
        subtasks_failed=0,
        subtasks_remaining=total_batches
    )
    
    # Simulate monitoring (in real app, you'd check AsyncResult)
    time.sleep(30)  # Wait for subtasks
    
    self.send_progress_event(
        progress_percent=100,
        status="All subtasks completed",
        subtasks_created=total_batches,
        subtasks_completed=total_batches,
        subtasks_failed=0,
        subtasks_remaining=0
    )
    
    return {"subtasks_created": total_batches, "status": "completed"}

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="subtask")
def process_batch_subtask(self, batch_index, batch_size, parent_id):
    """Subtask for batch processing"""
    
    # Send hierarchy event
    self.send_hierarchy_event(
        task_type="subtask",
        parent_id=parent_id,
        children=[],
        depth=1
    )
    
    try:
        # Process batch
        for i in range(batch_size):
            time.sleep(0.1)  # Simulate work
            progress = ((i + 1) / batch_size) * 100
            self.send_progress_event(
                progress_percent=progress,
                status=f"Batch {batch_index}: {i + 1}/{batch_size}",
                current=i + 1,
                total=batch_size
            )
        
        return {"batch": batch_index, "processed": batch_size}
    
    except Exception as e:
        self.send_failure_event(
            failure_reason=f"Batch {batch_index} failed: {str(e)}",
            failure_stage="batch_processing",
            failure_metadata={"batch_index": batch_index, "batch_size": batch_size}
        )
        raise
```

### 3.3 Chain/Pipeline Task Pattern

**For sequential processing pipelines:**

```python
@celery_app.task(bind=True)
@enhanced_monitoring(task_type="chain_task")
def data_pipeline_step1(self, data_id):
    """Step 1: Data extraction"""
    self.send_chain_progress_event(
        current_step=1,
        total_steps=4,
        current_stage_name="extract_data",
        status="Extracting data from source"
    )
    
    # Extract data
    extracted_data = extract_data(data_id)
    
    # Chain to next step
    return data_pipeline_step2.delay(extracted_data)

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="chain_task")
def data_pipeline_step2(self, data):
    """Step 2: Data transformation"""
    self.send_chain_progress_event(
        current_step=2,
        total_steps=4,
        current_stage_name="transform_data",
        status="Transforming data"
    )
    
    # Transform data
    transformed_data = transform_data(data)
    
    return data_pipeline_step3.delay(transformed_data)

# ... continue pattern for steps 3 and 4
```

## Phase 4: Flower Integration Updates

### 4.1 Update Flower Application

**In your existing Flower app, add these routes:**

```python
# In your flower app configuration
from monitoring.api.enhanced_monitoring import (
    TaskProgressHandler,
    TaskHierarchyHandler,
    TaskFailureAnalysisHandler,
    TaskMetadataHandler
)

# Add these to your Flower app routes
handlers = [
    # ... existing routes ...
    (r"/api/task/([^/]+)/progress", TaskProgressHandler),
    (r"/api/task/([^/]+)/hierarchy", TaskHierarchyHandler),
    (r"/api/task/([^/]+)/failure-analysis", TaskFailureAnalysisHandler),
    (r"/api/task/([^/]+)/metadata", TaskMetadataHandler),
]
```

### 4.2 Update Task Template

**Replace your existing task template with the enhanced version that includes:**
- Progress tab with Subtask Overview
- Hierarchy tab with visualization
- Failure Analysis tab with detailed error reporting

## Phase 5: Testing & Validation

### 5.1 Create Test Tasks

**Create `your_flask_app/monitoring/test_tasks.py`:**

```python
# Test tasks for each monitoring pattern
@celery_app.task(bind=True)
@enhanced_monitoring(task_type="single")
def test_single_task(self):
    """Test single task with progress"""
    for i in range(10):
        time.sleep(1)
        self.send_progress_event(
            progress_percent=(i + 1) * 10,
            status=f"Step {i + 1}/10 completed"
        )
    return "completed"

@celery_app.task(bind=True)
@enhanced_monitoring(task_type="parent_with_subtasks")
def test_parent_task(self):
    """Test parent-child task pattern"""
    subtasks = []
    for i in range(3):
        task = test_child_task.delay(i, self.request.id)
        subtasks.append(task.id)
    
    self.send_hierarchy_event(
        task_type="parent_with_subtasks",
        children=subtasks
    )
    return {"subtasks": len(subtasks)}

# Add test endpoints
@app.route('/api/test/single')
def test_single():
    task = test_single_task.delay()
    return {"task_id": task.id}

@app.route('/api/test/parent')
def test_parent():
    task = test_parent_task.delay()
    return {"task_id": task.id}
```

### 5.2 Validation Checklist

After integration, verify these features work:

**Progress Tracking:**
- [ ] Progress bar updates in real-time
- [ ] Status messages appear correctly
- [ ] Subtask summary shows accurate counts
- [ ] Progress percentages are accurate

**Hierarchy Visualization:**
- [ ] Parent-child relationships display correctly
- [ ] Task tree structure is accurate
- [ ] Depth levels are properly shown
- [ ] Interactive navigation works

**Failure Analysis:**
- [ ] Failed tasks show in failure tab
- [ ] Error details are comprehensive
- [ ] Failure metadata is captured
- [ ] Retry information is accurate
- [ ] Clickable task names expand error details

## Phase 6: Production Considerations

### 6.1 Performance Optimization

- **Event Frequency**: Limit progress updates to avoid overwhelming Redis
- **Cleanup**: Implement cleanup for old task metadata
- **Memory Management**: Monitor memory usage in enhanced events storage

### 6.2 Error Handling

```python
def safe_send_event(self, event_type, **kwargs):
    """Safely send events with error handling"""
    try:
        self.send_custom_event(event_type, **kwargs)
    except Exception as e:
        # Log error but don't fail the main task
        logger.warning(f"Failed to send monitoring event: {e}")
```

### 6.3 Configuration

**Add environment variables for monitoring control:**

```python
# Environment variables
ENHANCED_MONITORING_ENABLED = os.getenv('ENHANCED_MONITORING_ENABLED', 'true').lower() == 'true'
PROGRESS_UPDATE_INTERVAL = int(os.getenv('PROGRESS_UPDATE_INTERVAL', '1'))  # seconds
MAX_HIERARCHY_DEPTH = int(os.getenv('MAX_HIERARCHY_DEPTH', '5'))
```

## Summary

This integration provides:

1. **Full Compatibility**: Works with your existing Flask + Celery + Redis + Flower setup
2. **Universal Support**: Handles all task patterns (single, parent-child, chains)
3. **Real-time Monitoring**: Live progress updates and status tracking
4. **Comprehensive Analysis**: Detailed failure reporting and hierarchy visualization
5. **Easy Integration**: Decorator-based approach for minimal code changes

## Implementation Order

1. **Start with Phase 1**: Copy core files and update Flower
2. **Test with Phase 5**: Create test tasks to verify basic functionality
3. **Implement Phase 2-3**: Add enhanced monitoring to your actual tasks
4. **Optimize with Phase 6**: Add production considerations

## Support

If you encounter issues during integration:
- Check Redis connectivity and event routing
- Verify Celery configuration includes required event settings
- Ensure all API endpoints are properly registered
- Test with simple tasks before complex hierarchies

This guide provides everything needed to transform your Flask backend into a fully monitored system with the same advanced capabilities demonstrated in this Flower fork.