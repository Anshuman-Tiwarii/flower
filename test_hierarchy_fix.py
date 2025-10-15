#!/usr/bin/env python3

"""
Quick test for hierarchy task fix
"""

from example_enhanced_tasks import multi_level_hierarchy_task, sync_data_parent_task


def test_hierarchy():
    print("🧪 Testing Multi-Level Hierarchy Task Fix")
    print("=" * 50)

    try:
        # Test multi-level hierarchy
        print("1. Testing multi-level hierarchy task...")
        task = multi_level_hierarchy_task.delay(depth=2, children_per_level=2)
        print(f"   ✅ Multi-level task started: {task.id}")

        # Test parent with subtasks
        print("\n2. Testing parent with subtasks...")
        task2 = sync_data_parent_task.delay(num_records=3)
        print(f"   ✅ Parent task started: {task2.id}")

        print(f"\n🎯 SUCCESS! Both tasks submitted without errors")
        print(f"📋 Task IDs:")
        print(f"   Multi-level: {task.id}")
        print(f"   Parent: {task2.id}")

        print(f"\n🌸 Check Flower dashboard: http://localhost:5556/tasks")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True


if __name__ == "__main__":
    test_hierarchy()
