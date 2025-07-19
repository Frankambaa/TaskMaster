#!/bin/bash

# Quick fix for Docker deployment issues
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Quick fix for Docker build issues...${NC}"

cd /home/ubuntu/deployment

# Stop any running containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down --volumes --remove-orphans 2>/dev/null || true

# Clean Docker system
echo -e "${YELLOW}🧹 Cleaning Docker system...${NC}"
docker system prune -af

# Create simple environment file
echo -e "${YELLOW}📝 Creating environment file...${NC}"
cat > .env << EOF
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=secure_password_$(date +%s)
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=$(openssl rand -hex 32)
EOF

# Get OpenAI API key
echo -e "${YELLOW}🔑 Please enter your OpenAI API key:${NC}"
read -s OPENAI_KEY
sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env

# Use the simple Docker setup
echo -e "${YELLOW}🐳 Using simplified Docker configuration...${NC}"
cp docker-compose-simple.yml docker-compose.yml

# Build and start with simplified setup
echo -e "${YELLOW}🏗️ Building with simplified requirements...${NC}"
docker-compose up -d --build

# Wait for services
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 30

# Check status
echo -e "${YELLOW}🔍 Checking service status...${NC}"
docker-compose ps

# Configure Nginx
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Test deployment
echo -e "${YELLOW}🔍 Testing deployment...${NC}"
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")

if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Containers are running${NC}"
    if curl -s "http://localhost" | grep -q "html\|HTML"; then
        echo -e "${GREEN}✅ Application is accessible${NC}"
    else
        echo -e "${YELLOW}⚠️  Application starting up...${NC}"
    fi
else
    echo -e "${RED}❌ Containers failed to start${NC}"
    echo "Logs:"
    docker-compose logs --tail=10
fi

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo -e "${YELLOW}📋 Access your application:${NC}"
echo -e "🌐 Website: http://$SERVER_IP"
echo -e "👨‍💼 Admin Panel: http://$SERVER_IP/admin"
echo -e "💬 Chatbot: http://$SERVER_IP/chatbot"
echo ""
echo -e "${YELLOW}📋 Troubleshooting:${NC}"
echo "docker-compose ps        # Check status"
echo "docker-compose logs -f   # View logs"
echo "docker-compose restart   # Restart all services"