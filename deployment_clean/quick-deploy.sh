#!/bin/bash

# Quick deploy with fixed requirements
set -e

echo "🔧 Quick deploy with fixed dependencies..."

# Clean everything
docker-compose down --volumes --remove-orphans 2>/dev/null || true
docker system prune -af 2>/dev/null || true

# Create environment file
if [ ! -f .env ]; then
    POSTGRES_PASSWORD="chatbot_$(date +%s)"
    SECRET_KEY=$(openssl rand -hex 32)
    
    cat > .env << EOF
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SECRET_KEY=$SECRET_KEY
OPENAI_API_KEY=sk-placeholder
EOF

    echo "Enter your OpenAI API key:"
    read -s OPENAI_KEY
    if [ ! -z "$OPENAI_KEY" ]; then
        sed -i "s/sk-placeholder/$OPENAI_KEY/" .env
    fi
fi

# Build and start
echo "🏗️ Building with fixed dependencies..."
docker-compose up -d --build

# Wait and test
echo "⏳ Waiting for services..."
sleep 30

docker-compose ps

# Test application
if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Application responding"
else
    echo "App logs:"
    docker-compose logs app --tail=10
fi

# Configure Nginx
echo "🌐 Setting up Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null)
echo ""
echo "✅ Deployment complete!"
echo "🌐 Access: http://$SERVER_IP"
echo "👨‍💼 Admin: http://$SERVER_IP/admin"
echo "💬 Chat: http://$SERVER_IP/chatbot"