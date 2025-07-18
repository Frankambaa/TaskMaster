#!/bin/bash

# Production startup script for RAG Chatbot

set -e

echo "Starting RAG Chatbot in production mode..."

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
    sleep 1
done
echo "Database is ready!"

# Run database migrations if needed
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created/updated')
"

# Create necessary directories
mkdir -p uploads faiss_index logs static/widget_icons

# Start the application with gunicorn
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 300 \
    --keep-alive 2 \
    --log-level info \
    --log-file logs/gunicorn.log \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --capture-output \
    --enable-stdio-inheritance \
    --reuse-port \
    main:app