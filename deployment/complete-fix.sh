#!/bin/bash

# Complete fix for deployment issues
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Complete deployment fix...${NC}"

# Fix permissions first
echo -e "${YELLOW}📁 Fixing permissions...${NC}"
sudo chown -R ubuntu:ubuntu /home/ubuntu/deployment
cd /home/ubuntu/deployment

# Create the missing .env.production file
echo -e "${YELLOW}📝 Creating .env.production file...${NC}"
DB_PASSWORD="chatbot_$(date +%s)"

cat > .env.production << EOF
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:$DB_PASSWORD@postgres:5432/chatbot_db
PGPASSWORD=$DB_PASSWORD

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Security
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL Database Config
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user  
POSTGRES_PASSWORD=$DB_PASSWORD
EOF

# Also create regular .env file
cp .env.production .env

echo -e "${YELLOW}🔑 Please enter your OpenAI API key:${NC}"
read -s OPENAI_KEY
sed -i "s/your_openai_api_key_here/$OPENAI_KEY/g" .env.production
sed -i "s/your_openai_api_key_here/$OPENAI_KEY/g" .env

# Clean up any existing containers
echo -e "${YELLOW}🧹 Cleaning up existing containers...${NC}"
docker-compose down --volumes --remove-orphans 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# Start fresh containers
echo -e "${YELLOW}🐳 Starting fresh containers...${NC}"
docker-compose up -d --build

# Wait for services
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 15

# Check container status
echo -e "${YELLOW}🔍 Checking container status...${NC}"
docker-compose ps

# Configure Nginx
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Test the deployment
echo -e "${YELLOW}🔍 Testing deployment...${NC}"
sleep 5

if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Containers are running${NC}"
    
    # Test internal connection
    if docker-compose exec -T app curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is responding internally${NC}"
    else
        echo -e "${RED}❌ Application not responding internally${NC}"
        echo "App container logs:"
        docker-compose logs app --tail=10
    fi
else
    echo -e "${RED}❌ Containers failed to start${NC}"
    docker-compose logs --tail=20
fi

# Get server IP and show access URLs
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")

echo ""
echo -e "${GREEN}🎉 Deployment fix complete!${NC}"
echo -e "${YELLOW}📋 Access your RAG chatbot:${NC}"
echo -e "🌐 Website: http://$SERVER_IP"
echo -e "👨‍💼 Admin Panel: http://$SERVER_IP/admin"
echo -e "💬 Chatbot: http://$SERVER_IP/chatbot"
echo -e "📏 Widget Size Test: http://$SERVER_IP/test_widget_sizes.html"
echo ""
echo -e "${YELLOW}📋 Useful commands:${NC}"
echo "docker-compose ps        # Check status"
echo "docker-compose logs -f   # View logs"
echo "docker-compose restart   # Restart services"