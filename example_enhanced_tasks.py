"""
Example Enhanced Celery Tasks with Custom Event Publishing
These tasks demonstrate the enhanced monitoring capabilities.
"""

import time
import random
import os
from celery import Celery, current_task

# Try to import psutil for better metrics, fallback to basic commands
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Initialize Celery app
app = Celery("enhanced_tasks", broker="redis://localhost:6379/0")

# Configure Celery to send events
app.conf.update(
    worker_send_task_events=True,
    task_send_sent_event=True,
)


# System metrics collector
def get_system_metrics():
    """Get lightweight system metrics for failure analysis"""
    metrics = {
        "hostname": os.environ.get(
            "HOSTNAME", os.environ.get("COMPUTERNAME", "unknown")
        )
    }

    try:
        # Try psutil first (most reliable)
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Quick sample
            memory = psutil.virtual_memory()
            metrics.update(
                {
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_percent": round(memory.percent, 1),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                }
            )
        else:
            # Fallback to system commands (Unix/Linux/Mac)
            try:
                # Try to get load average (simple CPU indicator)
                if hasattr(os, "getloadavg"):
                    load_avg = os.getloadavg()[0]
                    metrics["load_average_1min"] = round(load_avg, 2)

                # Try basic memory info from /proc/meminfo (Linux)
                if os.path.exists("/proc/meminfo"):
                    with open("/proc/meminfo", "r") as f:
                        meminfo = f.read()
                        for line in meminfo.split("\n"):
                            if line.startswith("MemTotal:"):
                                total_kb = int(line.split()[1])
                            elif line.startswith("MemAvailable:"):
                                available_kb = int(line.split()[1])
                                metrics.update(
                                    {
                                        "memory_percent": round(
                                            100 - (available_kb / total_kb * 100), 1
                                        ),
                                        "memory_available_gb": round(
                                            available_kb / (1024**2), 2
                                        ),
                                    }
                                )
                                break
            except Exception:
                pass  # Skip if system commands fail

        # Load average (Unix/Linux/Mac)
        try:
            if hasattr(os, "getloadavg"):
                load_avg = os.getloadavg()[0]  # 1-minute load average
                metrics["load_average_1min"] = round(load_avg, 2)
        except (OSError, AttributeError):
            pass  # Windows doesn't have getloadavg

        # Redis connection check (simple, no extra dependencies)
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=1)
            r.ping()
            redis_info = r.info()
            metrics["redis_status"] = {
                "connected": True,
                "memory_used": redis_info.get("used_memory_human", "unknown"),
                "connected_clients": redis_info.get("connected_clients", 0),
            }
        except Exception:
            metrics["redis_status"] = {"connected": False, "error": "connection_failed"}

        # Get hostname properly
        if hasattr(os, "uname"):
            metrics["hostname"] = os.uname().nodename

        return metrics

    except Exception as e:
        # Ultimate fallback - minimal info
        return {
            "error": f"metrics_collection_failed: {str(e)[:100]}",
            "hostname": os.environ.get(
                "HOSTNAME", os.environ.get("COMPUTERNAME", "unknown")
            ),
        }


def send_custom_event(event_type, include_system_metrics=None, **kwargs):
    """
    Helper function to send custom events to Flower

    Args:
        event_type: Type of event to send
        include_system_metrics: True/False to force include/exclude metrics,
                               None for automatic (includes for failure events)
        **kwargs: Additional event data
    """
    if current_task:
        # Automatically include system metrics for failure events
        if include_system_metrics is None:
            include_system_metrics = event_type == "task-custom-failure"

        if include_system_metrics:
            kwargs["system_metrics"] = get_system_metrics()

        current_task.send_event(event_type, **kwargs)


@app.task(bind=True)
def heavy_single_task(self, num_records=1000):
    """
    Type A: Long running task with no subtasks
    Demonstrates detailed progress tracking with stages and subtask monitoring
    """

    # Send hierarchy event to indicate this is a single task
    send_custom_event(
        "task-custom-hierarchy",
        task_type="single_long_running",
        parent_id=None,
        children=[],
        depth=0,
    )

    stages = [
        ("initializing", "Setting up data structures", 0.05),
        ("loading", "Loading and validating data", 0.15),
        ("processing", "Processing records with heavy computation", 0.7),
        ("finalizing", "Finalizing and cleanup", 0.1),
    ]

    overall_progress = 0
    records_processed = 0
    start_time = time.time()

    for stage_name, stage_desc, stage_portion in stages:
        stage_records = int(num_records * stage_portion)

        for i in range(stage_records):
            # Simulate work (longer duration for UI testing)
            time.sleep(random.uniform(1.0, 2.0))
            records_processed += 1

            # Calculate progress
            stage_progress = (i + 1) / stage_records
            overall_progress = (records_processed / num_records) * 100

            # Update progress every 10 records or at stage boundaries
            if i % 10 == 0 or i == stage_records - 1:
                # Send custom progress event
                send_custom_event(
                    "task-custom-progress",
                    progress_percent=overall_progress,
                    current=records_processed,
                    total=num_records,
                    stage=stage_name,
                    stage_description=stage_desc,
                    stage_progress=stage_progress * 100,
                    status=f"{stage_desc}: {records_processed}/{num_records} records ({overall_progress:.1f}%)",
                )

    # Final result
    total_time = time.time() - start_time
    return {
        "status": "completed",
        "records_processed": num_records,
        "total_time": f"{total_time:.2f}s",
        "average_speed": f"{num_records / total_time:.2f} records/sec",
        "stages_completed": len(stages),
        "task_type": "heavy_single",
    }


@app.task(bind=True)
def sync_data_parent_task(self, num_records=100):
    """
    Type B: A long task that spawns multiple child subtasks (2 level deep hierarchy)
    Demonstrates parent-child task monitoring with subtask progress tracking
    """

    # Send hierarchy event
    send_custom_event(
        "task-custom-hierarchy",
        task_type="parent_with_subtasks",
        parent_id=None,
        children=[],  # Will be updated as children are created
        depth=0,
    )

    # Initial setup
    send_custom_event(
        "task-custom-progress",
        status="Creating subtasks...",
        subtasks_created=0,
        subtasks_completed=0,
        subtasks_failed=0,
        progress_percent=0,
    )

    # Create subtasks
    subtask_jobs = []
    # Dynamic batch sizing
    target_records_per_batch = 1000
    batch_size = max(100, min(5000, target_records_per_batch))
    if num_records > 50000:
        batch_size = max(batch_size, num_records // 50)

    for i in range(0, num_records, batch_size):
        batch_end = min(i + batch_size, num_records)
        batch_size_actual = batch_end - i

        # Create subtask
        subtask = sync_data_subtask.delay(
            start_index=i, count=batch_size_actual, parent_task_id=self.request.id
        )
        subtask_jobs.append(subtask.id)

    subtasks_created = len(subtask_jobs)

    # Update hierarchy with children
    send_custom_event(
        "task-custom-hierarchy",
        task_type="parent_with_subtasks",
        parent_id=None,
        children=subtask_jobs,
        depth=0,
    )

    # Update with subtasks created
    send_custom_event(
        "task-custom-progress",
        status=f"Created {subtasks_created} subtasks, monitoring progress...",
        subtasks_created=subtasks_created,
        subtasks_completed=0,
        subtasks_failed=0,
        progress_percent=10,
    )

    # Monitor subtasks completion
    completed = 0
    failed = 0

    while completed + failed < subtasks_created:
        time.sleep(1)  # Check every second

        completed = 0
        failed = 0

        # Note: Using event-based monitoring instead of AsyncResult
        # since result backend is disabled
        progress = 10 + (90 * len(subtask_jobs) / subtasks_created)

        send_custom_event(
            "task-custom-progress",
            status=f"All {subtasks_created} subtasks submitted successfully",
            subtasks_created=subtasks_created,
            subtasks_completed=len(subtask_jobs),
            subtasks_failed=0,
            progress_percent=100,
            subtasks_remaining=0,
        )

    # Enhanced failure handling for subtasks
    # Check for any failures in the created subtasks and send comprehensive failure metadata
    # This would typically be done with result backend, but for demonstration:
    failed_subtask_count = 0
    if failed_subtask_count > 0:
        send_custom_event(
            "task-custom-failure",
            failure_reason=f"Parent task monitoring detected {failed_subtask_count} failed subtasks",
            failure_metadata={
                "subtasks_created": subtasks_created,
                "subtasks_failed": failed_subtask_count,
                "subtasks_completed": completed,
                "failure_rate": (failed_subtask_count / subtasks_created) * 100,
                "failure_type": "subtask_failures",
                "monitoring_method": "parent_task_tracking",
                "subtask_ids": (
                    subtask_jobs[:3] if len(subtask_jobs) > 3 else subtask_jobs
                ),  # Sample of failed IDs
            },
            failure_stage="subtask_monitoring",
        )

    # Final result
    return {
        "status": "completed",
        "subtasks_created": subtasks_created,
        "subtasks_completed": len(subtask_jobs),
        "subtasks_failed": 0,
        "success_rate": "100%",
        "task_type": "parallel_subtasks",
    }


@app.task(bind=True)
def sync_data_subtask(self, start_index, count, parent_task_id):
    """Subtask for the parent task - demonstrates child task monitoring"""

    # Send hierarchy event for child task
    send_custom_event(
        "task-custom-hierarchy",
        task_type="subtask",
        parent_id=parent_task_id,
        children=[],
        depth=1,
    )

    # Simulate processing time
    processing_time = random.uniform(30.0, 60.0)  # 30-60 seconds for UI testing

    # Small chance of failure for realistic testing
    if random.random() < 0.05:  # 5% failure rate
        time.sleep(processing_time * 0.3)

        # Send comprehensive failure event with detailed metadata
        error_details = {
            "batch_info": {
                "start_index": start_index,
                "batch_size": count,
                "items_processed": int(count * 0.3),  # Partial processing
                "remaining_items": count - int(count * 0.3),
            },
            "timing": {
                "total_allocated_time": processing_time,
                "time_before_failure": processing_time * 0.3,
                "estimated_completion_time": processing_time,
            },
            "failure_context": {
                "worker_load": "medium",
                "memory_usage": "normal",
                "network_status": "stable",
            },
        }

        send_custom_event(
            "task-custom-failure",
            failure_reason=f"Simulated failure during batch processing (items {start_index}-{start_index + count})",
            failure_metadata=error_details,
            failure_stage="batch_processing",
        )

        raise Exception(
            f"Subtask failed processing batch {start_index}-{start_index + count}"
        )

    # Simulate work with progress updates
    for i in range(count):
        time.sleep(processing_time / count)

        # Update progress
        progress = ((i + 1) / count) * 100
        send_custom_event(
            "task-custom-progress",
            progress_percent=progress,
            status=f"Processing item {start_index + i + 1}",
            current=i + 1,
            total=count,
            stage="processing_batch",
        )

    return {
        "batch_start": start_index,
        "batch_size": count,
        "items_processed": count,
        "processing_time": f"{processing_time:.2f}s",
        "task_type": "subtask",
    }


@app.task(bind=True)
def crawl_page(self, url):
    """
    Type C: Chain task - Step 1 of RAG pipeline
    Demonstrates chain task progression tracking
    """

    # Send chain progress event
    send_custom_event(
        "task-custom-chain-progress",
        current_step=1,
        total_steps=4,
        pipeline_progress=25,
        current_stage="crawling",
        current_stage_name="crawl_page",
        status="Crawling webpage content...",
        url=url,
        progress_percent=25,
    )

    # Send hierarchy for chain task
    send_custom_event(
        "task-custom-hierarchy",
        task_type="chain_task",
        parent_id=None,
        children=[],  # Chain tasks don't have traditional children
        depth=0,
    )

    # Simulate crawling
    time.sleep(random.uniform(2, 4))

    content = f"<html><body><h1>Content from {url}</h1><p>This is the crawled content...</p></body></html>"

    return {
        "url": url,
        "content": content,
        "content_length": len(content),
        "step": "crawl_page",
        "step_number": 1,
        "task_type": "chain_task",
    }


@app.task(bind=True)
def convert_to_markdown(self, crawl_result):
    """Type C: Chain task - Step 2 of RAG pipeline"""

    send_custom_event(
        "task-custom-chain-progress",
        current_step=2,
        total_steps=4,
        pipeline_progress=50,
        current_stage="converting",
        current_stage_name="convert_to_markdown",
        status="Converting HTML to Markdown...",
        url=crawl_result["url"],
        progress_percent=50,
    )

    # Simulate conversion
    time.sleep(random.uniform(1, 3))

    # Simple HTML to markdown conversion
    content = crawl_result["content"]
    markdown = content.replace("<h1>", "# ").replace("</h1>", "\n")
    markdown = markdown.replace("<p>", "").replace("</p>", "\n")
    markdown = markdown.replace("<html><body>", "").replace("</body></html>", "")

    return {
        "url": crawl_result["url"],
        "markdown": markdown,
        "markdown_length": len(markdown),
        "step": "convert_to_markdown",
        "step_number": 2,
        "task_type": "chain_task",
    }


@app.task(bind=True)
def chunk_markdown(self, markdown_result):
    """Type C: Chain task - Step 3 of RAG pipeline"""

    send_custom_event(
        "task-custom-chain-progress",
        current_step=3,
        total_steps=4,
        pipeline_progress=75,
        current_stage="chunking",
        current_stage_name="chunk_markdown",
        status="Chunking markdown content...",
        url=markdown_result["url"],
        progress_percent=75,
    )

    # Simulate chunking
    time.sleep(random.uniform(1, 2))

    markdown = markdown_result["markdown"]
    chunk_size = 200
    chunks = [markdown[i : i + chunk_size] for i in range(0, len(markdown), chunk_size)]

    return {
        "url": markdown_result["url"],
        "chunks": chunks,
        "chunk_count": len(chunks),
        "step": "chunk_markdown",
        "step_number": 3,
        "task_type": "chain_task",
    }


@app.task(bind=True)
def embed_chunks(self, chunk_result):
    """Type C: Chain task - Step 4 of RAG pipeline"""

    send_custom_event(
        "task-custom-chain-progress",
        current_step=4,
        total_steps=4,
        pipeline_progress=90,
        current_stage="embedding",
        current_stage_name="embed_chunks",
        status="Generating embeddings...",
        url=chunk_result["url"],
        progress_percent=90,
    )

    # Simulate embedding generation
    time.sleep(random.uniform(2, 5))

    chunks = chunk_result["chunks"]
    embeddings = []

    for i, chunk in enumerate(chunks):
        # Simulate embedding
        embedding = [random.random() for _ in range(384)]
        embeddings.append(
            {
                "chunk_id": i,
                "chunk_text": chunk[:50] + "..." if len(chunk) > 50 else chunk,
                "embedding_dim": len(embedding),
            }
        )

    # Final progress update
    send_custom_event(
        "task-custom-chain-progress",
        current_step=4,
        total_steps=4,
        pipeline_progress=100,
        current_stage="completed",
        current_stage_name="embed_chunks",
        status="Pipeline completed successfully",
        url=chunk_result["url"],
        progress_percent=100,
    )

    return {
        "url": chunk_result["url"],
        "embeddings": embeddings,
        "embedding_count": len(embeddings),
        "total_chunks": len(chunks),
        "step": "embed_chunks",
        "step_number": 4,
        "pipeline_status": "completed",
        "task_type": "chain_task",
    }


@app.task(bind=True)
def create_n_level_workflow(
    self, levels=3, children_per_level=2, level_duration=60, **kwargs
):
    """
    Creates an n-level deep workflow by creating child tasks
    that in turn create their own children.

    Args:
        levels: How many levels deep (1 = just this task, 2 = this + children, etc.)
        children_per_level: How many children each level spawns
        level_duration: How long each task should run (seconds)
    """

    current_level = self.request.kwargs.get("_current_level", 1)
    parent_id = self.request.kwargs.get("_parent_id", None)

    # Send hierarchy event
    send_custom_event(
        "task-custom-hierarchy",
        task_type=f"n_level_workflow_L{current_level}",
        parent_id=parent_id,
        children=[],
        depth=current_level - 1,
        hierarchy_data={
            "max_levels": levels,
            "children_per_level": children_per_level,
            "current_level": current_level,
        },
    )

    # Send initial progress
    send_custom_event(
        "task-custom-progress",
        status=f"Level {current_level} workflow starting...",
        progress_percent=0,
        stage=f"level_{current_level}_init",
        stage_description=f"Initializing level {current_level} workflow",
    )

    # Do work at this level
    work_items = random.randint(5, 10)
    for i in range(work_items):
        time.sleep(level_duration / (work_items * 2))  # Spread time across work items

        progress = (i + 1) / work_items * 50  # Use 50% for own work
        send_custom_event(
            "task-custom-progress",
            status=f"Level {current_level}: processing item {i+1}/{work_items}",
            progress_percent=progress,
            current=i + 1,
            total=work_items,
            stage=f"level_{current_level}_processing",
        )

    child_tasks = []

    # Create children if not at max depth
    if current_level < levels:
        for i in range(children_per_level):
            # Create child task with increased level
            child_task = create_n_level_workflow.delay(
                levels=levels,
                children_per_level=children_per_level,
                level_duration=level_duration,
                _current_level=current_level + 1,
                _parent_id=self.request.id,
            )
            child_tasks.append(child_task.id)

            # Update progress as children are created
            child_progress = 50 + ((i + 1) / children_per_level * 25)
            send_custom_event(
                "task-custom-progress",
                status=f"Level {current_level}: created child {i+1}/{children_per_level}",
                progress_percent=child_progress,
                subtasks_created=len(child_tasks),
                stage=f"level_{current_level}_spawning",
            )

        # Update hierarchy with children
        send_custom_event(
            "task-custom-hierarchy",
            task_type=f"n_level_workflow_L{current_level}",
            parent_id=parent_id,
            children=child_tasks,
            depth=current_level - 1,
            hierarchy_data={
                "max_levels": levels,
                "children_per_level": children_per_level,
                "current_level": current_level,
                "children_spawned": len(child_tasks),
            },
        )

        # Simulate monitoring children (simplified)
        time.sleep(level_duration / 4)  # Wait a bit for children to start

        send_custom_event(
            "task-custom-progress",
            status=f"Level {current_level}: monitoring {len(child_tasks)} children",
            progress_percent=75,
            subtasks_created=len(child_tasks),
            stage=f"level_{current_level}_monitoring",
        )

    # Final completion
    time.sleep(level_duration / 8)  # Final processing time

    send_custom_event(
        "task-custom-progress",
        status=f"Level {current_level} completed!",
        progress_percent=100,
        stage=f"level_{current_level}_completed",
    )

    return {
        "level": current_level,
        "max_levels": levels,
        "children_spawned": len(child_tasks),
        "work_items_processed": work_items,
        "task_type": f"n_level_workflow_L{current_level}",
        "children_ids": child_tasks,
    }


@app.task(bind=True)
def multi_level_hierarchy_task(self, **kwargs):
    """
    Type D: Multi-level task hierarchy (n levels deep)
    Demonstrates complex hierarchical task relationships
    """

    # Extract parameters from kwargs with defaults
    depth = kwargs.get("depth", 3)
    children_per_level = kwargs.get("children_per_level", 2)
    current_depth = kwargs.get("current_depth", 0)
    parent_id = kwargs.get("parent_id", None)

    # Send hierarchy event
    send_custom_event(
        "task-custom-hierarchy",
        task_type="multi_level_hierarchy",
        parent_id=parent_id,
        children=[],  # Will be updated as children are created
        depth=current_depth,
        hierarchy_data={
            "max_depth": depth,
            "children_per_level": children_per_level,
            "current_depth": current_depth,
        },
    )

    # Send initial progress
    send_custom_event(
        "task-custom-progress",
        status=f"Starting level {current_depth} task...",
        progress_percent=0,
        stage=f"level_{current_depth}",
        stage_description=f"Processing level {current_depth} of {depth}",
    )

    # Do some work at this level
    work_items = random.randint(5, 15)
    for i in range(work_items):
        time.sleep(random.uniform(0.1, 0.3))
        progress = ((i + 1) / work_items) * 50  # 50% for own work

        send_custom_event(
            "task-custom-progress",
            status=f"Level {current_depth}: processing item {i+1}/{work_items}",
            progress_percent=progress,
            current=i + 1,
            total=work_items,
            stage=f"level_{current_depth}_processing",
        )

    # If not at max depth, spawn children
    child_tasks = []
    if current_depth < depth:
        for i in range(children_per_level):
            # Create child task - debugging the arguments
            child_kwargs = {
                "depth": depth,  # Keep the max depth the same
                "children_per_level": children_per_level,
                "current_depth": current_depth + 1,  # Increment current depth
                "parent_id": self.request.id,
            }
            child = multi_level_hierarchy_task.apply_async(kwargs=child_kwargs)
            child_tasks.append(child.id)

        # Update hierarchy with children
        send_custom_event(
            "task-custom-hierarchy",
            task_type="multi_level_hierarchy",
            parent_id=parent_id,
            children=child_tasks,
            depth=current_depth,
            hierarchy_data={
                "max_depth": depth,
                "children_per_level": children_per_level,
                "current_depth": current_depth,
                "spawned_children": len(child_tasks),
            },
        )

        # Simplified monitoring for event-based system
        # Note: Children will report their own progress via events
        child_progress = 75  # Assume children are progressing
        send_custom_event(
            "task-custom-progress",
            status=f"Level {current_depth}: Created {len(child_tasks)} children, monitoring via events",
            progress_percent=child_progress,
            subtasks_created=len(child_tasks),
            subtasks_completed=len(child_tasks),
            subtasks_failed=0,
            subtasks_remaining=0,
        )

    # Final progress
    send_custom_event(
        "task-custom-progress",
        status=f"Level {current_depth} completed",
        progress_percent=100,
        stage=f"level_{current_depth}_completed",
    )

    return {
        "level": current_depth,
        "max_depth": depth,
        "children_spawned": len(child_tasks),
        "work_items_processed": work_items,
        "task_type": "multi_level_hierarchy",
    }


# Utility functions for testing
def run_heavy_single_task():
    """Run a heavy single task example"""
    return heavy_single_task.delay(num_records=1000)


def run_parent_subtask_example():
    """Run a parent task with subtasks example"""
    return sync_data_parent_task.delay(num_records=500)


def run_chain_task_example():
    """Run a chain task example"""
    # Start the chain
    result1 = crawl_page.delay("https://example.com")
    # You would chain these in a real workflow
    return result1


def run_multi_level_hierarchy_example():
    """Run a multi-level hierarchy example"""
    return multi_level_hierarchy_task.delay(depth=3, children_per_level=2)


@app.task(bind=True)
def failing_hierarchy_task(
    self, levels=2, children_per_level=2, fail_percentage=30, **kwargs
):
    """
    Task hierarchy that demonstrates failure tracking
    Some subtasks will fail intentionally to test failure analysis
    """

    current_level = self.request.kwargs.get("_current_level", 1)
    parent_id = self.request.kwargs.get("_parent_id", None)

    # Send hierarchy event
    send_custom_event(
        "task-custom-hierarchy",
        task_type=f"failing_hierarchy_L{current_level}",
        parent_id=parent_id,
        children=[],
        depth=current_level - 1,
    )

    # Send initial progress event with subtask tracking
    total_subtasks = children_per_level if current_level < levels else 0
    send_custom_event(
        "task-custom-progress",
        progress_percent=0,
        status=f"Level {current_level}: Starting (may fail)",
        stage=f"level_{current_level}_init",
        subtasks_created=0,
        subtasks_completed=0,
        subtasks_failed=0,
        subtasks_remaining=total_subtasks,
    )

    # Randomly decide if this task should fail
    if random.randint(1, 100) <= fail_percentage:
        # Send failure metadata before failing
        send_custom_event(
            "task-custom-failure",
            failure_reason=f"Simulated failure at level {current_level}",
            failure_stage=f"level_{current_level}_processing",
            failure_metadata={
                "level": current_level,
                "failure_type": "random_simulation",
                "worker_load": random.choice(["low", "medium", "high"]),
                "batch_size": random.randint(100, 1000),
            },
        )

        # Simulate different types of failures
        failure_types = [
            ValueError(f"Processing failed at level {current_level}"),
            ConnectionError(f"Database connection lost at level {current_level}"),
            TimeoutError(f"Operation timed out at level {current_level}"),
        ]
        raise random.choice(failure_types)

    # Do some work with incremental progress updates
    send_custom_event(
        "task-custom-progress",
        progress_percent=25,
        status=f"Level {current_level}: Initializing...",
        stage=f"level_{current_level}_setup",
        subtasks_created=0,
        subtasks_completed=0,
        subtasks_failed=0,
        subtasks_remaining=total_subtasks,
    )
    time.sleep(1)
    
    send_custom_event(
        "task-custom-progress",
        progress_percent=50,
        status=f"Level {current_level}: Processing...",
        stage=f"level_{current_level}_processing",
        subtasks_created=0,
        subtasks_completed=0,
        subtasks_failed=0,
        subtasks_remaining=total_subtasks,
    )
    time.sleep(2)

    child_tasks = []

    # Create children if not at max depth
    if current_level < levels:
        send_custom_event(
            "task-custom-progress",
            progress_percent=75,
            status=f"Level {current_level}: Creating {children_per_level} subtasks...",
            stage=f"level_{current_level}_spawning",
            subtasks_created=0,
            subtasks_completed=0,
            subtasks_failed=0,
            subtasks_remaining=children_per_level,
        )
        
        for i in range(children_per_level):
            child_task = failing_hierarchy_task.delay(
                levels=levels,
                children_per_level=children_per_level,
                fail_percentage=fail_percentage,
                _current_level=current_level + 1,
                _parent_id=self.request.id,
            )
            child_tasks.append(child_task.id)
            
            # Update progress as each subtask is created
            send_custom_event(
                "task-custom-progress",
                progress_percent=75 + (i + 1) * 15 // children_per_level,
                status=f"Level {current_level}: Created {i + 1}/{children_per_level} subtasks",
                stage=f"level_{current_level}_spawning",
                subtasks_created=i + 1,
                subtasks_completed=0,
                subtasks_failed=0,
                subtasks_remaining=children_per_level - (i + 1),
            )
            time.sleep(0.5)  # Small delay to show incremental progress

        # Update hierarchy with children
        send_custom_event(
            "task-custom-hierarchy",
            task_type=f"failing_hierarchy_L{current_level}",
            parent_id=parent_id,
            children=child_tasks,
            depth=current_level - 1,
        )

    # Final progress
    send_custom_event(
        "task-custom-progress",
        progress_percent=100,
        status=f"Level {current_level}: Completed successfully",
        stage=f"level_{current_level}_completed",
        subtasks_created=len(child_tasks),
        subtasks_completed=len(child_tasks),
        subtasks_failed=0,
        subtasks_remaining=0,
    )

    return {
        "level": current_level,
        "levels": levels,
        "children_spawned": len(child_tasks),
        "task_type": f"failing_hierarchy_L{current_level}",
        "children_ids": child_tasks,
    }


if __name__ == "__main__":
    print("Enhanced Task Examples")
    print("1. Heavy Single Task:", run_heavy_single_task())
    print("2. Parent with Subtasks:", run_parent_subtask_example())
    print("3. Chain Task:", run_chain_task_example())
    print("4. Multi-level Hierarchy:", run_multi_level_hierarchy_example())
