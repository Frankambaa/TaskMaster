#!/bin/bash

# Final Nginx configuration fix
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Final Nginx configuration fix...${NC}"

# Find the correct deployment directory
DEPLOY_DIR=""
if [ -d "/home/ubuntu/deployment" ]; then
    DEPLOY_DIR="/home/ubuntu/deployment"
elif [ -d "/root/deployment" ]; then
    DEPLOY_DIR="/root/deployment"
elif [ -d "./deployment" ]; then
    DEPLOY_DIR="./deployment"
else
    echo -e "${RED}❌ Cannot find deployment directory${NC}"
    exit 1
fi

echo -e "${YELLOW}📂 Using deployment directory: $DEPLOY_DIR${NC}"
cd "$DEPLOY_DIR"

# Check Docker containers status
echo -e "${YELLOW}🐳 Checking Docker containers...${NC}"
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}🚀 Starting Docker containers...${NC}"
    docker-compose up -d 2>/dev/null || true
    sleep 15
fi

# Show container status
docker-compose ps 2>/dev/null || echo "Docker-compose not found in current directory"

# Test if app container is responding
echo -e "${YELLOW}🔍 Testing app container...${NC}"
if docker-compose exec -T app curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ App container responding${NC}"
else
    echo -e "${YELLOW}⚠️  App container may need more time${NC}"
    docker-compose logs app --tail=5 2>/dev/null || true
fi

# Remove default Nginx configuration
echo -e "${YELLOW}🗑️  Removing default Nginx site...${NC}"
sudo rm -f /etc/nginx/sites-enabled/default

# Create and install correct Nginx configuration
echo -e "${YELLOW}📝 Creating Nginx configuration...${NC}"
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

# Enable the site
echo -e "${YELLOW}🔗 Enabling Nginx site...${NC}"
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/

# Test Nginx configuration
echo -e "${YELLOW}🔍 Testing Nginx configuration...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✅ Nginx configuration valid${NC}"
    sudo systemctl reload nginx
    echo -e "${GREEN}✅ Nginx reloaded${NC}"
else
    echo -e "${RED}❌ Nginx configuration error${NC}"
    exit 1
fi

# Wait a moment and test
sleep 5

# Test the deployment
echo -e "${YELLOW}🔍 Testing external access...${NC}"
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")

# First check if port 5000 is accessible directly
if docker-compose exec -T app curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ App running on port 5000${NC}"
else
    echo -e "${YELLOW}⚠️  App may not be running on port 5000${NC}"
fi

# Check external access
if curl -f -s "http://$SERVER_IP" | grep -q "<!DOCTYPE html>"; then
    if curl -s "http://$SERVER_IP" | grep -q "chatbot\|admin\|RAG\|Flask" -i; then
        echo -e "${GREEN}✅ RAG Chatbot is accessible!${NC}"
    else
        echo -e "${YELLOW}⚠️  Web server responding but may not be chatbot${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Testing response...${NC}"
    curl -s "http://$SERVER_IP" | head -3
fi

echo ""
echo -e "${GREEN}🎉 Configuration complete!${NC}"
echo -e "${YELLOW}📋 Access your RAG chatbot:${NC}"
echo -e "🌐 Main site: http://$SERVER_IP"
echo -e "👨‍💼 Admin panel: http://$SERVER_IP/admin"
echo -e "💬 Chatbot: http://$SERVER_IP/chatbot"
echo ""
echo -e "${YELLOW}🔧 Troubleshooting:${NC}"
echo "sudo systemctl status nginx    # Check Nginx status"
echo "docker-compose ps              # Check containers"
echo "docker-compose logs -f app     # View app logs"
echo "curl http://localhost:5000     # Test direct app access"