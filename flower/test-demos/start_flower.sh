#!/bin/bash

# Flower Monitoring Interface Startup Script

set -e  # Exit on error

echo "🌸 Starting Flower Monitoring Interface..."

# Activate virtual environment  
source ../flower-env/bin/activate

# Start Flower
exec celery -A example_enhanced_tasks flower \
    --broker=redis://localhost:6379/0 \
    --port=5555