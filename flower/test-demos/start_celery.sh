#!/bin/bash

# Stable Celery Worker Startup Script
# This script starts Celery worker with optimized settings for macOS

set -e  # Exit on error

echo "🚀 Starting Celery Worker with stable configuration..."

# Activate virtual environment
source ../flower-env/bin/activate

# Start worker with stable settings
exec celery -A example_enhanced_tasks worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --pool=prefork \
    --without-gossip \
    --without-mingle \
    --without-heartbeat