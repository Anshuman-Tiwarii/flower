#!/bin/bash

# Quick Demo Launcher for Enhanced Monitoring System
echo "=========================================="
echo "  ENHANCED MONITORING - QUICK DEMO"
echo "=========================================="
echo

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "🔄 Activating virtual environment..."
    source ../flower-env/bin/activate
fi

echo "Available demo tasks:"
echo "1. single    - Single task with progress tracking (2-3 min)"
echo "2. hierarchy - Parent task with subtasks (3-4 min)"
echo "3. chain     - Pipeline task sequence (3-4 min)"
echo "4. failure   - Failure analysis demo (1-2 min)"
echo "5. complex   - Multi-level hierarchy (5-6 min)"
echo "6. all       - Start all task types"
echo

if [ $# -eq 0 ]; then
    echo "Usage: ./quick_demo.sh [task_type]"
    echo "Example: ./quick_demo.sh single"
    echo
    echo "Or run interactively:"
    read -p "Enter task type (1-6 or name): " choice
    
    case $choice in
        1|single) task_type="single" ;;
        2|hierarchy) task_type="hierarchy" ;;
        3|chain) task_type="chain" ;;
        4|failure) task_type="failure" ;;
        5|complex) task_type="complex" ;;
        6|all) task_type="all" ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
else
    task_type=$1
fi

echo "🚀 Starting $task_type demo task..."
echo

# Run the demo
python demo_tasks.py $task_type

echo
echo "📊 Flower Dashboard: http://localhost:5555"
echo "🔍 Monitor your tasks using the links above!"
echo
echo "💡 Demo Tips:"
echo "• Keep Flower dashboard open in browser"
echo "• Check Progress, Hierarchy, and Failure Analysis tabs"
echo "• Watch real-time updates every 2 seconds"
echo "• Try different tasks to see various monitoring features"