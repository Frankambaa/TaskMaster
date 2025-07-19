#!/bin/bash

# Git pull and restart services (for quick updates)
set -e

echo "🔄 Quick Git update and restart..."

# Configuration
GIT_BRANCH="main"
PROJECT_DIR="/home/ubuntu/ragbot"

# Pull latest code
cd $PROJECT_DIR
echo "📥 Pulling latest changes..."
git pull origin $GIT_BRANCH

# Restart containers with updated code
cd deployment_clean
echo "🔄 Restarting services..."
docker-compose down
docker-compose up -d --build

echo "⏳ Waiting for services..."
sleep 20

# Test
if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null)
    echo "✅ Update complete! http://$SERVER_IP"
else
    echo "❌ Issue detected. Checking logs..."
    docker-compose logs app --tail=10
fi