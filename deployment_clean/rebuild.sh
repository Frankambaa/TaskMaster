#!/bin/bash

# Rebuild with all required files
set -e

echo "🔧 Rebuilding with missing files..."

# Stop containers
docker-compose down 2>/dev/null || true

# Clean build cache
docker-compose build --no-cache

# Start services
docker-compose up -d

# Wait for startup
echo "⏳ Waiting for services..."
sleep 25

# Check status
docker-compose ps

# Test application
if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Application is now working"
    
    # Configure Nginx
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo cp nginx.conf /etc/nginx/sites-available/chatbot
    sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx
    
    SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null)
    echo "🌐 RAG Chatbot: http://$SERVER_IP"
    echo "👨‍💼 Admin: http://$SERVER_IP/admin"
else
    echo "❌ Still having issues. Container logs:"
    docker-compose logs app --tail=15
fi