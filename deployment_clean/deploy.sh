#!/bin/bash

# RAG Chatbot Deployment Script
set -e

echo "🚀 Starting RAG Chatbot deployment..."

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cp .env.example .env
    
    # Generate secure values
    POSTGRES_PASSWORD="chatbot_$(date +%s)"
    SECRET_KEY=$(openssl rand -hex 32)
    
    sed -i "s/your_secure_password_here/$POSTGRES_PASSWORD/" .env
    sed -i "s/your_secret_key_here/$SECRET_KEY/" .env
    
    echo "🔑 Please enter your OpenAI API key:"
    read -s OPENAI_KEY
    sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env
    
    echo "✅ Environment file created"
fi

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down --volumes --remove-orphans 2>/dev/null || true

# Build and start containers
echo "🏗️ Building and starting containers..."
docker-compose up -d --build

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 30

# Check container status
echo "🔍 Checking container status..."
docker-compose ps

# Test application
echo "🔍 Testing application..."
for i in {1..10}; do
    if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
        echo "✅ Application is responding"
        break
    else
        echo "⏳ Waiting for app (attempt $i/10)..."
        sleep 5
    fi
done

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/

if sudo nginx -t; then
    sudo systemctl reload nginx
    echo "✅ Nginx configured successfully"
else
    echo "❌ Nginx configuration error"
    exit 1
fi

# Final test
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")
echo ""
echo "🎉 Deployment complete!"
echo "📋 Your RAG chatbot is accessible at:"
echo "🌐 Main site: http://$SERVER_IP"
echo "👨‍💼 Admin panel: http://$SERVER_IP/admin"
echo "💬 Chatbot: http://$SERVER_IP/chatbot"
echo "📏 Widget sizes: http://$SERVER_IP/test_widget_sizes.html"
echo ""
echo "🛠️ Management commands:"
echo "docker-compose ps              # Check status"
echo "docker-compose logs -f app     # View logs"
echo "docker-compose restart         # Restart services"