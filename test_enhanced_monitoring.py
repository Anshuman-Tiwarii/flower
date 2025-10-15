#!/usr/bin/env python3
"""
Quick test script for enhanced monitoring
"""

import time
import sys
from example_enhanced_tasks import *


def test_enhanced_monitoring():
    print("🚀 Testing Enhanced Task Monitoring")
    print("=" * 50)

    try:
        print("\n1. Testing Heavy Single Task...")
        task1 = heavy_single_task.delay(num_records=50)  # Smaller for quick testing
        print(f"   ✅ Heavy Single Task started: {task1.id}")

        print("\n2. Testing Parent with Subtasks...")
        task2 = sync_data_parent_task.delay(num_records=20)  # Smaller for quick testing
        print(f"   ✅ Parent Task started: {task2.id}")

        print("\n3. Testing Chain Task...")
        task3 = crawl_page.delay("https://example.com")
        print(f"   ✅ Chain Task started: {task3.id}")

        print("\n4. Testing Multi-level Hierarchy...")
        task4 = multi_level_hierarchy_task.delay(depth=2, children_per_level=2)
        print(f"   ✅ Hierarchy Task started: {task4.id}")

        print(f"\n🎯 ALL TASKS STARTED SUCCESSFULLY!")
        print("=" * 50)
        print("📋 Task Summary:")
        print(f"   Heavy Single: {task1.id}")
        print(f"   Parent/Subtasks: {task2.id}")
        print(f"   Chain: {task3.id}")
        print(f"   Hierarchy: {task4.id}")

        print(f"\n🌸 Open Flower dashboard:")
        print(f"   http://localhost:5555")
        print(f"   Click on any task ID above to see enhanced monitoring!")

        print(f"\n⏱️  Monitoring progress...")
        for i in range(10):
            print(f"   Checking status... ({i+1}/10)")

            # Check task states
            states = []
            for task in [task1, task2, task3, task4]:
                try:
                    states.append(f"{task.id[:8]}...{task.state}")
                except:
                    states.append(f"{task.id[:8]}...PENDING")

            print(f"   Status: {' | '.join(states)}")
            time.sleep(3)

        print(f"\n✅ Test completed! Check the tasks in Flower dashboard.")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure Redis and Celery worker are running!")
        sys.exit(1)


if __name__ == "__main__":
    test_enhanced_monitoring()
