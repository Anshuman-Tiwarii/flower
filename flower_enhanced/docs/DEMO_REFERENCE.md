# Demo Reference Card

## Quick Commands

### Start Demo Tasks
```bash
# Easy way - interactive
./quick_demo.sh

# Direct commands
python demo_tasks.py single      # 1-2 min progress demo
python demo_tasks.py hierarchy   # 2-3 min parent-child demo  
python demo_tasks.py chain       # 2-3 min pipeline demo
python demo_tasks.py failure     # 1-2 min failure analysis
python demo_tasks.py complex     # 5-6 min multi-level hierarchy
python demo_tasks.py all         # All tasks at once
```

### Flower Dashboard
- **Main URL**: http://localhost:5555
- **Task URL**: http://localhost:5555/task/{TASK_ID}

## Demo Flow Recommendation

### 1. Single Task Demo (1-2 minutes)
```bash
python demo_tasks.py single
```
**Show:**
- Progress tab with live progress bar
- Status updates: "Processing record X/800"
- Stage transitions: setup → processing → validation → completion
- Real-time updates every 2 seconds

### 2. Hierarchy Task Demo (2-3 minutes)
```bash
python demo_tasks.py hierarchy
```
**Show:**
- Progress tab: Subtask summary boxes with live counts
- Hierarchy tab: Visual tree showing parent-child relationships
- Real-time subtask completion tracking

### 3. Chain Task Demo (2-3 minutes)
```bash
python demo_tasks.py chain
```
**Show:**
- Progress tab: Pipeline step progression (25% → 50% → 75% → 100%)
- Current step indicator: "Step 2 of 4: Converting to markdown"
- Chain progress tracking across stages

### 4. Failure Analysis Demo (2-3 minutes)
```bash
python demo_tasks.py failure
```
**Show:**
- Failure Analysis tab: Detailed error reports
- Failed subtask list with expandable details
- Custom failure metadata and context
- Click task names to expand error details
- 4-level deep hierarchy with 2 children per level
- 25% systematic failure rate (~8 failures out of ~31 total tasks)
- Progressive failures as hierarchy executes

## Key Demo Points

### Progress Tracking
- **Live Updates**: Progress bars move in real-time
- **Detailed Status**: Human-readable status messages
- **Stage Tracking**: Visual indication of current processing stage
- **Metrics**: Current/total counters and percentages

### Hierarchy Visualization
- **Tree Structure**: Visual parent-child relationships
- **Interactive Navigation**: Click to navigate between tasks
- **Depth Indicators**: Visual depth levels
- **Real-time Updates**: Tree updates as tasks complete

### Failure Analysis
- **Comprehensive Reports**: Beyond standard Celery exceptions
- **Business Context**: Custom metadata and failure reasons
- **Interactive Details**: Expandable error information
- **Hierarchy Failures**: Failed subtasks across entire tree

## Technical Highlights

### Architecture Benefits
- **Event-Driven**: Uses existing Celery/Redis infrastructure
- **Memory Efficient**: Current-state-only storage
- **Real-time**: 2-second polling for smooth updates
- **Scalable**: Works with any number of tasks/workers

### Integration
- **Zero Infrastructure**: No additional databases required
- **Backward Compatible**: Doesn't break existing Celery functionality
- **Easy Integration**: Simple decorator-based approach
- **Universal**: Works with any task type

## Troubleshooting

### If tasks don't appear:
1. Check Celery worker is running: `celery -A example_enhanced_tasks worker`
2. Check Flower is running: `celery -A example_enhanced_tasks flower --port=5555`
3. Check Redis is accessible
4. Verify task IDs in Flower dashboard

### If monitoring doesn't update:
1. Refresh the browser page
2. Check browser console for JavaScript errors
3. Verify API endpoints are accessible
4. Check task is actually running (not completed immediately)

## Quick Reference URLs

- **Flower Dashboard**: http://localhost:5555
- **Worker Status**: http://localhost:5555/workers
- **All Tasks**: http://localhost:5555/tasks
- **API Documentation**: Built-in Flower API docs

## Demo Timing

- **Single Task**: 1-2 minutes (good for progress demo)
- **Hierarchy Task**: 2-3 minutes (good for subtask relationships)
- **Chain Task**: 2-3 minutes (good for pipeline progression)
- **Failure Task**: 2-3 minutes (4-level hierarchy failure analysis)
- **Complex Hierarchy**: 5-6 minutes (advanced relationships)

**Total Demo Time**: 13-17 minutes for all features