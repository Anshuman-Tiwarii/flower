# Testing Enhanced Task Monitoring

## Quick Start Testing Guide

This guide will help you test the enhanced task monitoring implementation.

## Prerequisites

1. **Redis running**: `redis-server`
2. **Celery worker running**: `celery -A example_enhanced_tasks worker --loglevel=info -E`
3. **Flower running**: `celery -A example_enhanced_tasks flower`

## Test Scenarios

### 1. Long Running Single Task (Type A)

```python
# In Python shell or script:
from example_enhanced_tasks import heavy_single_task

# Start a heavy single task
result = heavy_single_task.delay(num_records=500)
print(f"Task ID: {result.id}")
```

**Expected behavior**:
- Progress tab shows detailed progression through stages
- Performance metrics display (records/sec, elapsed time, remaining time)
- Stage progress bar shows current stage completion
- Overall progress bar shows total completion

### 2. Parent Task with Subtasks (Type B)

```python
from example_enhanced_tasks import sync_data_parent_task

# Start a parent task that creates subtasks
result = sync_data_parent_task.delay(num_records=300)
print(f"Parent Task ID: {result.id}")
```

**Expected behavior**:
- Progress tab shows subtask summary (created/completed/failed/remaining)
- Hierarchy tab shows parent-child relationships
- Real-time updates of subtask completion rates
- Failure analysis if some subtasks fail (5% failure rate built in)

### 3. Chain Tasks (Type C)

```python
from example_enhanced_tasks import crawl_page, convert_to_markdown, chunk_markdown, embed_chunks

# Start a chain task
result1 = crawl_page.delay("https://example.com")
print(f"Chain Task ID: {result1.id}")

# You can also run individual steps to see chain progression
```

**Expected behavior**:
- Progress tab shows pipeline progression (Step X of Y)
- Current stage name displayed
- Pipeline progress bar shows overall chain completion

### 4. Multi-Level Hierarchy (Type D)

```python
from example_enhanced_tasks import multi_level_hierarchy_task

# Start a multi-level hierarchy task
result = multi_level_hierarchy_task.delay(depth=3, children_per_level=2)
print(f"Root Task ID: {result.id}")
```

**Expected behavior**:
- Hierarchy tab shows expandable tree structure
- Multiple levels of tasks visible
- Each level shows its own progress
- Click on child tasks to navigate

## Testing Steps

### Step 1: Start Services

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
cd /path/to/flower-fork
celery -A example_enhanced_tasks worker --loglevel=info -E

# Terminal 3: Start Flower
cd /path/to/flower-fork/flower
python -m flower --broker=redis://localhost:6379/0
```

### Step 2: Run Test Tasks

```python
# In Python shell
import sys
sys.path.append('/path/to/flower-fork')

from example_enhanced_tasks import *

# Test each task type
task1 = heavy_single_task.delay(num_records=200)
task2 = sync_data_parent_task.delay(num_records=100) 
task3 = crawl_page.delay("https://example.com")
task4 = multi_level_hierarchy_task.delay(depth=2, children_per_level=2)

print("Task IDs:")
print(f"Heavy Single: {task1.id}")
print(f"Parent/Subtasks: {task2.id}")
print(f"Chain: {task3.id}")
print(f"Hierarchy: {task4.id}")
```

### Step 3: View in Flower

1. Open browser to `http://localhost:5555`
2. Go to Tasks tab
3. Click on any task ID from above
4. You should see the enhanced tabs:
   - **Overview**: Original task information
   - **Progress**: Real-time progress tracking with bars and metrics
   - **Hierarchy**: Task relationship visualization
   - **Failure Analysis**: Detailed failure information (for failed tasks)

## Expected UI Features

### Progress Tab
- **Main progress bar**: Overall task completion
- **Stage progress bar**: Current stage completion (for staged tasks)
- **Pipeline progress bar**: Chain step completion (for chain tasks)
- **Subtask summary**: Created/Completed/Failed/Remaining counts
- **Performance metrics**: Speed, elapsed time, remaining time

### Hierarchy Tab
- **Tree visualization**: Hierarchical task relationships
- **Task states**: Color-coded task states (Success=green, Failure=red, etc.)
- **Progress indicators**: Mini progress bars for each task
- **Clickable nodes**: Click to navigate to child tasks

### Failure Analysis Tab
- **Automated analysis**: Pattern detection and suggestions
- **Custom metadata**: JSON display of custom failure data
- **Failure events**: Timeline of failure-related events
- **Traceback**: Full error traceback when available

## Debugging

### Common Issues

1. **No enhanced monitoring badge**: Tasks may not be sending custom events
   - Check that tasks are using `send_custom_event()` helper
   - Verify Celery worker is receiving events (`-E` flag)

2. **Tabs show loading spinners**: API endpoints may be failing
   - Check browser developer console for errors
   - Verify API endpoints are accessible: `/api/task/{task_id}/progress`

3. **Real-time updates not working**: JavaScript may have errors
   - Check browser console for JavaScript errors
   - Verify `enhanced-monitoring.js` is loaded

### API Testing

You can test the API endpoints directly:

```bash
# Replace {task_id} with actual task ID
curl http://localhost:5555/api/task/{task_id}/progress
curl http://localhost:5555/api/task/{task_id}/hierarchy
curl http://localhost:5555/api/task/{task_id}/failure-analysis
curl http://localhost:5555/api/task/{task_id}/metadata
```

### Browser Developer Tools

1. Open browser dev tools (F12)
2. Check Console tab for JavaScript errors
3. Check Network tab to see if API calls are successful
4. Look for 404 errors on enhanced monitoring endpoints

## Success Criteria

✅ **Enhanced monitoring badge** appears for tasks with custom events
✅ **Progress tab** shows real-time progress updates
✅ **Hierarchy tab** displays task relationships
✅ **Failure Analysis tab** shows detailed failure information
✅ **Real-time updates** refresh every 3 seconds
✅ **API endpoints** return JSON data
✅ **Task navigation** works via hierarchy clicks

## Next Steps

Once basic functionality is working:

1. **Add D3.js visualization** for more sophisticated hierarchy rendering
2. **Implement WebSocket updates** for true real-time monitoring
3. **Add custom filtering** for different monitoring types
4. **Enhance failure analysis** with more pattern recognition
5. **Add export functionality** for progress data

## Troubleshooting

If you encounter issues:

1. Check all services are running (Redis, Celery worker, Flower)
2. Verify task events are being sent (`worker_send_task_events=True`)
3. Check browser console for JavaScript errors
4. Test API endpoints manually with curl
5. Verify custom events are being stored in Flower's event state