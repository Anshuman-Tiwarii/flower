#!/bin/bash

# Celery Health Monitor Script
# Monitors Celery worker health and restarts if needed

set -e

source ../flower-env/bin/activate

echo "🔍 Celery Health Check"
echo "====================="

# Check if workers are active
echo "Checking active workers..."
if celery -A example_enhanced_tasks inspect active >/dev/null 2>&1; then
    echo "✅ Workers are responding"
    
    # Show worker stats
    echo ""
    echo "Worker Statistics:"
    celery -A example_enhanced_tasks inspect stats 2>/dev/null || echo "Stats unavailable"
    
    echo ""
    echo "Active Tasks:"
    celery -A example_enhanced_tasks inspect active 2>/dev/null || echo "No active tasks"
    
else
    echo "❌ No workers responding"
    echo "💡 Run './start_celery.sh' to start a worker"
fi

echo ""
echo "Queue Status:"
celery -A example_enhanced_tasks inspect reserved 2>/dev/null || echo "Queue status unavailable"