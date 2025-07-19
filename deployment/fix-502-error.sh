#!/bin/bash

# Fix 502 Bad Gateway error and ensure RAG chatbot is accessible
set -e

echo "🔧 Fixing 502 Bad Gateway error..."

# Find correct deployment directory
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

echo "📂 Using deployment directory: $DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Check current container status
echo "🔍 Checking Docker container status..."
docker-compose ps 2>/dev/null || echo "No containers found"

# Restart containers if they're not healthy
echo "🔄 Restarting containers to ensure they're running properly..."
docker-compose down 2>/dev/null || true
sleep 5

# Make sure we have the environment file
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cat > .env << EOF
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=secure_password_123
OPENAI_API_KEY=sk-placeholder
SECRET_KEY=$(openssl rand -hex 32)
EOF
fi

# Start containers with simple compose
echo "🚀 Starting containers..."
if [ -f "docker-compose-simple.yml" ]; then
    cp docker-compose-simple.yml docker-compose.yml
fi

docker-compose up -d --build
echo "⏳ Waiting for containers to fully start..."
sleep 30

# Check container logs
echo "📋 Container status:"
docker-compose ps

echo "📋 App container logs (last 10 lines):"
docker-compose logs app --tail=10

# Test internal connectivity
echo "🔍 Testing internal app connectivity..."
for i in {1..5}; do
    if docker-compose exec -T app curl -f -s http://localhost:5000 >/dev/null 2>&1; then
        echo "✅ App responding internally on attempt $i"
        break
    else
        echo "⏳ App not responding yet (attempt $i/5)..."
        sleep 10
    fi
done

# Test port 5000 from host
echo "🔍 Testing port 5000 from host..."
if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Port 5000 accessible from host"
else
    echo "❌ Port 5000 not accessible from host"
    echo "Checking if port is bound..."
    netstat -tlnp | grep :5000 || echo "Port 5000 not bound"
fi

# Fix Nginx configuration to use correct upstream
echo "🌐 Updating Nginx configuration..."
sudo tee /etc/nginx/sites-available/chatbot > /dev/null << 'EOF'
upstream app_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    client_max_body_size 20M;
    
    location / {
        proxy_pass http://app_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
        
        # Add error handling
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Test and reload Nginx
echo "🔍 Testing Nginx configuration..."
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo "✅ Nginx configuration updated and reloaded"
else
    echo "❌ Nginx configuration error"
    sudo nginx -t
fi

# Final connectivity tests
echo "🔍 Final connectivity tests..."
sleep 5

# Test internal Docker app
if docker-compose exec -T app curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Internal Docker app: Working"
else
    echo "❌ Internal Docker app: Not responding"
fi

# Test Nginx health endpoint
if curl -f -s http://localhost/health >/dev/null 2>&1; then
    echo "✅ Nginx health endpoint: Working"
else
    echo "❌ Nginx health endpoint: Not working"
fi

# Test external access
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "unknown")
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP" 2>/dev/null || echo "000")

echo "🌐 External access test: HTTP $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ RAG Chatbot is accessible!"
elif [ "$HTTP_STATUS" = "502" ]; then
    echo "⚠️  Still getting 502 - app may need more time to start"
    echo "Checking Docker port mapping..."
    docker-compose port app 5000 2>/dev/null || echo "Port 5000 not mapped"
elif [ "$HTTP_STATUS" = "000" ]; then
    echo "⚠️  Connection failed - checking network"
else
    echo "⚠️  Unexpected status: $HTTP_STATUS"
fi

echo ""
echo "🎉 Troubleshooting complete!"
echo "📋 Your RAG chatbot should be accessible at:"
echo "🌐 Main site: http://$SERVER_IP"
echo "👨‍💼 Admin panel: http://$SERVER_IP/admin"
echo "💬 Chatbot: http://$SERVER_IP/chatbot"
echo ""
echo "🛠️  If still not working, try:"
echo "docker-compose logs -f app     # View real-time app logs"
echo "docker-compose restart         # Restart all services"
echo "sudo systemctl restart nginx  # Restart Nginx"