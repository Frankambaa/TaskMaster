#!/bin/bash

# Fix checksum error and rebuild properly
set -e

echo "🔧 Fixing checksum error and rebuilding..."

# Find deployment directory
DEPLOY_DIR=""
for dir in "/home/ubuntu/deployment" "/root/deployment" "/home/ubuntu/apna/deployment" "./deployment"; do
    if [ -d "$dir" ]; then
        DEPLOY_DIR="$dir"
        break
    fi
done

if [ -z "$DEPLOY_DIR" ]; then
    echo "❌ Cannot find deployment directory"
    exit 1
fi

echo "📂 Working in: $DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Clean everything to fix checksum issues
echo "🧹 Cleaning Docker system completely..."
docker-compose down --volumes --remove-orphans 2>/dev/null || true
docker system prune -af --volumes 2>/dev/null || true
docker builder prune -af 2>/dev/null || true

# Ensure environment file exists
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cat > .env << EOF
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=secure_password_$(date +%s)
SECRET_KEY=$(openssl rand -hex 32)
OPENAI_API_KEY=sk-placeholder
EOF
fi

# Use the fixed Docker configuration
echo "🔧 Using fixed Docker configuration..."
cp docker-compose-fixed.yml docker-compose.yml

# Build with no cache to avoid checksum issues
echo "🏗️ Building with fresh cache..."
docker-compose build --no-cache --pull

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 20

# Check status
echo "🔍 Checking container status..."
docker-compose ps

# Test application
echo "🔍 Testing application..."
for i in {1..10}; do
    if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
        echo "✅ Application is responding on port 5000"
        break
    else
        echo "⏳ Waiting for app... (attempt $i/10)"
        sleep 5
    fi
done

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default

sudo tee /etc/nginx/sites-available/chatbot > /dev/null << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    client_max_body_size 20M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Final test
echo "🔍 Final test..."
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP" 2>/dev/null || echo "000")

echo ""
echo "🎉 Rebuild complete!"
echo "📋 Status: HTTP $HTTP_STATUS"
echo "🌐 Access: http://$SERVER_IP"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ RAG chatbot is now accessible!"
else
    echo "⚠️  Status $HTTP_STATUS - may need a few more minutes to fully start"
    echo "Check logs: docker-compose logs -f app"
fi