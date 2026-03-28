#!/bin/bash
set -e

echo "🚀 Starting AI News Aggregator..."

# Set Python path
export PYTHONPATH="${PYTHONPATH}:/opt/render/project/src"

# Run migration
echo "🔧 Running database migration..."
python scripts/migrate_search.py

# Start the application
echo "✨ Starting web server..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
