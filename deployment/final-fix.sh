#!/bin/bash

# Final deployment fix
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Final deployment fix...${NC}"

cd /home/ubuntu/deployment

# Check if containers are running
echo -e "${YELLOW}🔍 Checking current status...${NC}"
if docker-compose ps 2>/dev/null | grep -q "Up"; then
    echo -e "${GREEN}✅ Containers are running${NC}"
else
    echo -e "${YELLOW}⚠️  Starting containers...${NC}"
    docker-compose up -d 2>/dev/null || true
    sleep 10
fi

# Fix any remaining Docker issues
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}🔧 Fixing Docker setup...${NC}"
    
    # Use the working simple configuration
    docker-compose down 2>/dev/null || true
    
    # Make sure we have the environment file
    if [ ! -f .env ]; then
        cat > .env << EOF
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=secure_password_$(date +%s)
SECRET_KEY=$(openssl rand -hex 32)
OPENAI_API_KEY=${OPENAI_API_KEY:-sk-placeholder}
EOF
    fi
    
    # Start with simplified compose
    cp docker-compose-simple.yml docker-compose.yml
    docker-compose up -d --build
    sleep 20
fi

# Ensure Nginx is properly configured
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/

# Test and reload Nginx
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo -e "${GREEN}✅ Nginx configured successfully${NC}"
else
    echo -e "${RED}❌ Nginx configuration error${NC}"
fi

# Test the deployment
echo -e "${YELLOW}🔍 Testing deployment...${NC}"
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "13.233.129.111")

# Check Docker containers
docker-compose ps

# Test internal connection
if docker-compose exec -T app curl -s http://localhost:5000 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Application responding internally${NC}"
else
    echo -e "${YELLOW}⚠️  Application may still be starting${NC}"
    echo "App logs:"
    docker-compose logs app --tail=5
fi

# Test external access
sleep 3
if curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP" | grep -q "200\|302"; then
    echo -e "${GREEN}✅ Application accessible externally${NC}"
else
    echo -e "${YELLOW}⚠️  Testing external access...${NC}"
    curl_output=$(curl -s "http://$SERVER_IP" || echo "Connection failed")
    if echo "$curl_output" | grep -q "html\|HTML\|nginx\|Welcome"; then
        echo -e "${GREEN}✅ Web server responding${NC}"
    else
        echo -e "${YELLOW}⚠️  Web server may need more time${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 Deployment status complete!${NC}"
echo -e "${YELLOW}📋 Your RAG chatbot should be accessible at:${NC}"
echo -e "🌐 Main site: http://$SERVER_IP"
echo -e "👨‍💼 Admin panel: http://$SERVER_IP/admin"
echo -e "💬 Chatbot interface: http://$SERVER_IP/chatbot"
echo -e "📏 Widget size test: http://$SERVER_IP/test_widget_sizes.html"
echo ""
echo -e "${YELLOW}🛠️  Troubleshooting commands:${NC}"
echo "docker-compose ps                    # Check container status"
echo "docker-compose logs -f app           # View application logs"
echo "curl http://localhost                # Test local access"
echo "sudo systemctl status nginx         # Check Nginx status"
echo "docker-compose restart              # Restart all services"