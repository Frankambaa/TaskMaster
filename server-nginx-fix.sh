#!/bin/bash

# Server Nginx fix for RAG chatbot deployment
set -e

echo "🔧 Fixing Nginx configuration for RAG chatbot..."

# Remove default Nginx site
sudo rm -f /etc/nginx/sites-enabled/default
echo "✅ Removed default Nginx site"

# Create proper Nginx configuration for your chatbot
sudo tee /etc/nginx/sites-available/chatbot > /dev/null << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    client_max_body_size 20M;
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    # All other requests to Flask app
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

# Enable the site
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
echo "✅ Created and enabled chatbot Nginx configuration"

# Test Nginx configuration
if sudo nginx -t; then
    echo "✅ Nginx configuration is valid"
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
else
    echo "❌ Nginx configuration error"
    exit 1
fi

# Wait a moment for changes to take effect
sleep 3

# Test the deployment
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")
echo "🔍 Testing deployment on $SERVER_IP..."

# Test HTTP response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "✅ Server responding with HTTP $HTTP_CODE"
    
    # Check if it's actually the chatbot
    CONTENT=$(curl -s "http://$SERVER_IP" 2>/dev/null || echo "")
    if echo "$CONTENT" | grep -q "chatbot\|admin\|RAG\|Flask" -i; then
        echo "✅ RAG Chatbot is now accessible!"
    else
        echo "⚠️  Server responding but content needs verification"
    fi
else
    echo "⚠️  Server returned HTTP $HTTP_CODE"
fi

echo ""
echo "🎉 Nginx configuration complete!"
echo "📋 Your RAG chatbot should be accessible at:"
echo "🌐 Main site: http://$SERVER_IP"
echo "👨‍💼 Admin panel: http://$SERVER_IP/admin"
echo "💬 Chatbot interface: http://$SERVER_IP/chatbot"
echo "📏 Widget size demo: http://$SERVER_IP/test_widget_sizes.html"
echo ""
echo "🔧 If still not working, check:"
echo "sudo systemctl status nginx"
echo "sudo systemctl status docker"
echo "sudo docker ps"