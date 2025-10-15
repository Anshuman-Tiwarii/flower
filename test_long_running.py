#!/usr/bin/env python3

"""
Test long-running task behavior with event limits
"""

from example_enhanced_tasks import app, send_custom_event
import time

@app.task(bind=True)
def long_running_test_task(self, num_events=100):
    """
    Test task that generates many events to test the 50-event limit
    """
    
    for i in range(num_events):
        # Send a progress event
        send_custom_event('task-custom-progress',
                         progress_percent=(i / num_events) * 100,
                         current=i + 1,
                         total=num_events,
                         stage='testing',
                         stage_description=f'Testing event {i+1}',
                         status=f"Event {i+1}/{num_events} - Testing event history limit")
        
        print(f"Sent event {i+1}/{num_events}")
        time.sleep(0.1)  # Small delay to simulate work
    
    return {
        "status": "completed",
        "total_events_sent": num_events,
        "test_purpose": "Verify event history limit behavior"
    }

if __name__ == "__main__":
    print("🧪 Testing Long-Running Task with Many Events")
    print("=" * 50)
    
    # Test with 75 events (more than 50 limit)
    task = long_running_test_task.delay(num_events=75)
    print(f"✅ Long-running test task started: {task.id}")
    print(f"📊 This task will send 75 events (more than 50-event limit)")
    print(f"🔍 Check API: curl http://localhost:5556/api/task/{task.id}/progress")
    print(f"📜 Event history should only show last 50 events")
    print(f"📊 But current progress should always be available!")