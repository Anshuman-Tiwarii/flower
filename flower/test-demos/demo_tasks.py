#!/usr/bin/env python3
"""
Demo Tasks for Enhanced Monitoring System
Simple CLI to trigger different types of tasks for demonstration
"""

import time
import random
import argparse
from example_enhanced_tasks import (
    heavy_single_task,
    sync_data_parent_task,
    crawl_page,
    convert_to_markdown,
    chunk_markdown,
    embed_chunks,
    failing_hierarchy_task,
    multi_level_hierarchy_task
)

def print_banner():
    """Print demo banner"""
    print("=" * 60)
    print("  ENHANCED MONITORING SYSTEM - DEMO LAUNCHER")
    print("=" * 60)
    print()

def print_task_info(task_type, task_id, description):
    """Print task information with monitoring link"""
    print(f"🚀 Started: {task_type}")
    print(f"📝 Description: {description}")
    print(f"🆔 Task ID: {task_id}")
    print(f"🌐 Monitor at: http://localhost:5555/task/{task_id}")
    print("-" * 60)
    print()

def demo_single_task():
    """Demo single long-running task with progress tracking"""
    print("Starting SINGLE TASK demo...")
    print("This will show real-time progress tracking with stages")
    print()
    
    # Start task with good demo timing (1-2 minutes)
    task = heavy_single_task.delay(num_records=800)
    
    print_task_info(
        "Single Progress Task",
        task.id,
        "Long-running task with detailed progress and stage tracking"
    )
    
    print("Expected Demo Features:")
    print("• Progress bar: 0% → 100%")
    print("• Status updates: 'Processing record X/800'")
    print("• Stage transitions: setup → processing → validation → completion")
    print("• Real-time updates every 2 seconds")
    print()

def demo_hierarchy_task():
    """Demo parent-child hierarchy with subtasks"""
    print("Starting HIERARCHY TASK demo...")
    print("This will show parent task creating multiple subtasks")
    print()
    
    # Start parent task that creates subtasks (2-3 minutes total)
    task = sync_data_parent_task.delay(num_records=100)
    
    print_task_info(
        "Hierarchy Task (Parent + Children)",
        task.id,
        "Parent task that spawns multiple child subtasks"
    )
    
    print("Expected Demo Features:")
    print("• Progress Tab: Subtask summary boxes with live counts")
    print("• Hierarchy Tab: Visual tree showing parent-child relationships")
    print("• Real-time subtask completion tracking")
    print("• Parent progress updates as children complete")
    print()

def demo_chain_task():
    """Demo chain/pipeline task sequence"""
    print("Starting CHAIN TASK demo...")
    print("This will show sequential pipeline processing")
    print()
    
    # Start chain with good demo timing
    url = "https://example.com/demo-content"
    task = crawl_page.delay(url)
    
    print_task_info(
        "Chain/Pipeline Task",
        task.id,
        "Sequential processing: crawl → convert → chunk → embed"
    )
    
    print("Expected Demo Features:")
    print("• Progress Tab: Pipeline step progression (25% → 50% → 75% → 100%)")
    print("• Current step indicator: 'Step 2 of 4: Converting to markdown'")
    print("• Chain progress tracking across multiple stages")
    print("• Total pipeline completion time: ~2-3 minutes")
    print()

def demo_failure_task():
    """Demo task failure with detailed analysis"""
    print("Starting FAILURE TASK demo...")
    print("This will show comprehensive failure analysis with deep hierarchy")
    print()
    
    # Start failing hierarchy task with specific parameters for demo
    # 4 levels deep, 2 children per level, 25% error rate
    task = failing_hierarchy_task.delay(levels=4, children_per_level=2, fail_percentage=25)
    
    print_task_info(
        "Failure Analysis Task (4-Level Hierarchy)",
        task.id,
        "Multi-level hierarchy (4 levels, 2 children/level, 25% fail rate)"
    )
    
    print("Expected Demo Features:")
    print("• Failure Analysis Tab: Detailed error reports")
    print("• Failed subtask list with expandable details")
    print("• Custom failure metadata and context")
    print("• Interactive error exploration")
    print("• 4-level deep hierarchy with systematic failures (25% rate)")
    print("• Total tasks: ~31 (1 + 2 + 4 + 8 + 16) with ~8 expected failures")
    print("• Failure will occur progressively as hierarchy executes")
    print()

def demo_complex_hierarchy():
    """Demo multi-level deep hierarchy"""
    print("Starting COMPLEX HIERARCHY demo...")
    print("This will show deep multi-level task hierarchy")
    print()
    
    # Start multi-level hierarchy (5+ minutes)
    task = multi_level_hierarchy_task.delay()
    
    print_task_info(
        "Multi-Level Hierarchy Task",
        task.id,
        "Deep hierarchy with multiple levels and complex relationships"
    )
    
    print("Expected Demo Features:")
    print("• Hierarchy Tab: Multi-level tree visualization")
    print("• Progress tracking across all hierarchy levels")
    print("• Complex parent-child-grandchild relationships")
    print("• Total completion time: ~5-6 minutes")
    print()

def demo_all_tasks():
    """Start all task types for comprehensive demo"""
    print("Starting ALL TASKS for comprehensive demo...")
    print("This will start one of each task type")
    print()
    
    tasks = []
    
    # Start each type with delays between them
    print("1. Starting single task...")
    single_task = heavy_single_task.delay(num_records=1500)
    tasks.append(("Single Task", single_task.id))
    time.sleep(2)
    
    print("2. Starting hierarchy task...")
    hierarchy_task = sync_data_parent_task.delay(num_records=120)
    tasks.append(("Hierarchy Task", hierarchy_task.id))
    time.sleep(2)
    
    print("3. Starting chain task...")
    chain_task = crawl_page.delay("https://example.com/demo")
    tasks.append(("Chain Task", chain_task.id))
    time.sleep(2)
    
    print("4. Starting complex hierarchy...")
    complex_task = multi_level_hierarchy_task.delay()
    tasks.append(("Complex Hierarchy", complex_task.id))
    time.sleep(2)
    
    print("5. Starting failing hierarchy...")
    failing_task = failing_hierarchy_task.delay(levels=4, children_per_level=2, fail_percentage=25)
    tasks.append(("Failing Hierarchy", failing_task.id))
    
    print()
    print("=" * 60)
    print("ALL TASKS STARTED - MONITORING LINKS:")
    print("=" * 60)
    
    for task_type, task_id in tasks:
        print(f"{task_type}:")
        print(f"  🌐 http://localhost:5555/task/{task_id}")
        print()
    
    print("Recommended demo order:")
    print("1. Single Task - Show progress tracking")
    print("2. Hierarchy Task - Show parent-child relationships")
    print("3. Chain Task - Show pipeline progression")
    print("4. Complex Hierarchy - Show advanced relationships")
    print("5. Failing Hierarchy - Show failure analysis with 4-level tree")
    print()

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Enhanced Monitoring Demo Task Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_tasks.py single        # Single progress task
  python demo_tasks.py hierarchy     # Parent-child hierarchy
  python demo_tasks.py chain         # Pipeline/chain task
  python demo_tasks.py failure       # 4-level hierarchy failure demo
  python demo_tasks.py complex       # Multi-level hierarchy
  python demo_tasks.py all           # Start all task types
        """
    )
    
    parser.add_argument(
        'task_type',
        choices=['single', 'hierarchy', 'chain', 'failure', 'complex', 'all'],
        help='Type of demo task to start'
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Route to appropriate demo function
    if args.task_type == 'single':
        demo_single_task()
    elif args.task_type == 'hierarchy':
        demo_hierarchy_task()
    elif args.task_type == 'chain':
        demo_chain_task()
    elif args.task_type == 'failure':
        demo_failure_task()
    elif args.task_type == 'complex':
        demo_complex_hierarchy()
    elif args.task_type == 'all':
        demo_all_tasks()
    
    print("Demo task(s) started successfully!")
    print("Navigate to the monitoring links above to watch real-time progress.")
    print()
    print("💡 Tip: Open multiple browser tabs to compare different monitoring features")
    print("💡 Tip: Refresh pages to see real-time updates every 2 seconds")

if __name__ == "__main__":
    main()