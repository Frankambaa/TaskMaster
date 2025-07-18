#!/bin/bash

# Quick deployment script for RAG Chatbot
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Quick Deployment...${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create .env file with your configuration"
    exit 1
fi

# Check if OpenAI API key is set
if grep -q "your_openai_api_key_here" .env; then
    echo -e "${RED}❌ Please set your OpenAI API key in .env file${NC}"
    exit 1
fi

# Stop existing containers if running
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down || true

# Build and start containers
echo -e "${YELLOW}🏗️ Building and starting containers...${NC}"
docker-compose up -d --build

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Check if services are running
echo -e "${YELLOW}🔍 Checking service status...${NC}"
docker-compose ps

# Test database connection
echo -e "${YELLOW}🗄️ Testing database connection...${NC}"
if docker-compose exec -T app python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    echo -e "${GREEN}✅ Database connection successful${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
fi

# Configure Nginx
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Setup SSL (optional)
echo -e "${YELLOW}🔒 SSL Setup (optional)...${NC}"
read -p "Do you want to setup SSL with Let's Encrypt? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your domain name: " domain
    sudo certbot --nginx -d $domain
fi

# Show final status
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${YELLOW}📋 Service URLs:${NC}"
echo "HTTP: http://your-server-ip"
echo "HTTPS: https://your-domain.com (if SSL configured)"
echo ""
echo -e "${YELLOW}📋 Useful commands:${NC}"
echo "View logs: docker-compose logs -f"
echo "Stop services: docker-compose down"
echo "Restart services: docker-compose restart"
echo "Update app: docker-compose up -d --build app"
echo ""
echo -e "${GREEN}✅ Your RAG Chatbot is now deployed and running!${NC}"