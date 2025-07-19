#!/bin/bash

# Fix Nginx configuration to serve the RAG chatbot
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Fixing Nginx configuration...${NC}"

# Check if Docker services are running
echo -e "${YELLOW}🔍 Checking Docker services...${NC}"
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}🐳 Starting Docker services first...${NC}"
    docker-compose up -d --build
    sleep 10
fi

# Show current Docker status
echo -e "${YELLOW}📊 Current Docker status:${NC}"
docker-compose ps

# Configure Nginx properly
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"

# Remove default Nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Copy our configuration
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/

# Test Nginx configuration
echo -e "${YELLOW}🔍 Testing Nginx configuration...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✅ Nginx configuration is valid${NC}"
    sudo systemctl reload nginx
else
    echo -e "${RED}❌ Nginx configuration error${NC}"
    exit 1
fi

# Wait a moment for services to be ready
sleep 5

# Test the application
echo -e "${YELLOW}🔍 Testing application...${NC}"

# Check if Docker container is responding
if docker-compose exec -T app curl -s http://localhost:5000 > /dev/null; then
    echo -e "${GREEN}✅ Docker container is responding${NC}"
else
    echo -e "${RED}❌ Docker container not responding${NC}"
    echo "Container logs:"
    docker-compose logs app --tail=20
    exit 1
fi

# Check if Nginx is proxying correctly
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}')

echo -e "${YELLOW}🔍 Testing external access...${NC}"
if curl -s "http://$SERVER_IP" | grep -q "RAG\|Chatbot\|Admin"; then
    echo -e "${GREEN}✅ Application is accessible externally${NC}"
else
    echo -e "${YELLOW}⚠️  Application might need a moment to start${NC}"
    echo "Nginx is serving, but application content not detected yet"
fi

echo ""
echo -e "${GREEN}🎉 Configuration complete!${NC}"
echo -e "${YELLOW}📋 Access your application:${NC}"
echo -e "🌐 Website: http://$SERVER_IP"
echo -e "👨‍💼 Admin Panel: http://$SERVER_IP/admin" 
echo -e "💬 Chatbot: http://$SERVER_IP/chatbot"
echo ""
echo -e "${YELLOW}📋 Troubleshooting commands:${NC}"
echo "Check Docker: docker-compose ps"
echo "View logs: docker-compose logs -f app"
echo "Test internally: docker-compose exec app curl http://localhost:5000"
echo "Restart services: docker-compose restart"