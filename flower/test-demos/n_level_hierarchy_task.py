#!/usr/bin/env python3

"""
N-Level Deep Hierarchical Tasks
Creates proper n-level deep orchestrated workflows
"""

from example_enhanced_tasks import app, send_custom_event
import time
import random


@app.task(bind=True)
def create_n_level_workflow(self, levels=3, children_per_level=2, level_duration=60):
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


if __name__ == "__main__":
    print("🌳 N-Level Deep Workflow Creator")
    print("=" * 40)

    # Create 3-level deep workflow with 2 children per level
    # This creates: 1 root + 2 level-2 + 4 level-3 = 7 total tasks
    task = create_n_level_workflow.delay(
        levels=3, children_per_level=2, level_duration=45
    )
    print(f"✅ 3-Level workflow started: {task.id}")
    print(f"📊 This will create a 3-level deep hierarchy")
    print(f"⏱️  Each level runs for ~45 seconds")
    print(f"🌐 View at: http://localhost:5556/task/{task.id}")
