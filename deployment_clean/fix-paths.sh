#!/bin/bash

# Fix Docker build paths and deploy
set -e

echo "🔧 Fixing Docker build paths..."

# Stop any running containers
docker-compose down 2>/dev/null || true

# Clean Docker cache
docker system prune -f 2>/dev/null || true

# Create environment file if needed
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    POSTGRES_PASSWORD="chatbot_$(date +%s)"
    SECRET_KEY=$(openssl rand -hex 32)
    
    cat > .env << EOF
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
OPENAI_API_KEY=sk-placeholder
SECRET_KEY=$SECRET_KEY
EOF

    echo "🔑 Please enter your OpenAI API key:"
    read -s OPENAI_KEY
    if [ ! -z "$OPENAI_KEY" ]; then
        sed -i "s/sk-placeholder/$OPENAI_KEY/" .env
    fi
fi

# Build with no cache to avoid path issues
echo "🏗️ Building containers with correct paths..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for startup
echo "⏳ Waiting for services..."
sleep 25

# Check status
echo "🔍 Checking status..."
docker-compose ps

# Test app
if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Application is responding"
else
    echo "⚠️ Application may need more time"
    docker-compose logs app --tail=10
fi

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server")
echo ""
echo "✅ Fixed and deployed!"
echo "🌐 Access: http://$SERVER_IP"