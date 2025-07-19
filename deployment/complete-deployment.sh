#!/bin/bash

# Complete RAG Chatbot Deployment Script
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting complete RAG chatbot deployment...${NC}"

# Move to deployment directory
cd /home/ubuntu/deployment || cd /root/deployment || cd ./deployment

# Stop any existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down --volumes --remove-orphans 2>/dev/null || true

# Clean Docker system
echo -e "${YELLOW}🧹 Cleaning Docker system...${NC}"
docker system prune -f 2>/dev/null || true

# Create environment file with secure settings
echo -e "${YELLOW}📝 Creating production environment file...${NC}"
POSTGRES_PASSWORD="chatbot_$(date +%s)"
SECRET_KEY=$(openssl rand -hex 32)

cat > .env << EOF
# Database Configuration
POSTGRES_DB=chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql://chatbot_user:$POSTGRES_PASSWORD@postgres:5432/chatbot_db

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY

# OpenAI Configuration (you'll need to update this)
OPENAI_API_KEY=sk-placeholder-update-with-real-key

# Security Settings
ALLOWED_HOSTS=*
EOF

echo -e "${YELLOW}🔑 Please enter your OpenAI API key (or press Enter to keep placeholder):${NC}"
read -s OPENAI_KEY
if [ ! -z "$OPENAI_KEY" ]; then
    sed -i "s/sk-placeholder-update-with-real-key/$OPENAI_KEY/" .env
    echo -e "${GREEN}✅ OpenAI API key updated${NC}"
fi

# Use the simplified Docker configuration
echo -e "${YELLOW}🐳 Using simplified Docker configuration...${NC}"
cp docker-compose-simple.yml docker-compose.yml

# Build and start containers
echo -e "${YELLOW}🏗️ Building and starting containers...${NC}"
docker-compose up -d --build

# Wait for services to start
echo -e "${YELLOW}⏳ Waiting for services to initialize...${NC}"
sleep 30

# Check container status
echo -e "${YELLOW}🔍 Checking container status...${NC}"
docker-compose ps

# Test application health
echo -e "${YELLOW}🏥 Testing application health...${NC}"
for i in {1..10}; do
    if docker-compose exec -T app curl -f -s http://localhost:5000 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is responding on port 5000${NC}"
        break
    else
        echo -e "${YELLOW}⏳ Attempt $i/10 - waiting for app to start...${NC}"
        sleep 5
    fi
done

# Configure Nginx
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Create chatbot site configuration
sudo tee /etc/nginx/sites-available/chatbot > /dev/null << 'NGINX_EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    client_max_body_size 20M;
    
    # Root location - proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering off;
    }
}
NGINX_EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/

# Test and reload Nginx
echo -e "${YELLOW}🔍 Testing Nginx configuration...${NC}"
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo -e "${GREEN}✅ Nginx configured and reloaded${NC}"
else
    echo -e "${RED}❌ Nginx configuration error${NC}"
    sudo nginx -t
    exit 1
fi

# Final connectivity test
echo -e "${YELLOW}🔍 Final connectivity test...${NC}"
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "your-server-ip")

# Test internal Docker connection
if docker-compose exec -T app curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Internal Docker connection working${NC}"
else
    echo -e "${RED}❌ Internal Docker connection failed${NC}"
    echo "Application logs:"
    docker-compose logs app --tail=10
fi

# Test external HTTP connection
sleep 3
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP" 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "301" ]; then
    echo -e "${GREEN}✅ External HTTP connection working (Status: $HTTP_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️  External HTTP status: $HTTP_STATUS${NC}"
fi

# Display final results
echo ""
echo -e "${GREEN}🎉 RAG Chatbot Deployment Complete!${NC}"
echo -e "${YELLOW}📋 Access your application:${NC}"
echo -e "🌐 Main Site: http://$SERVER_IP"
echo -e "👨‍💼 Admin Panel: http://$SERVER_IP/admin"
echo -e "💬 Chatbot Interface: http://$SERVER_IP/chatbot"
echo -e "📏 Widget Size Demo: http://$SERVER_IP/test_widget_sizes.html"
echo ""
echo -e "${YELLOW}🛠️  Management Commands:${NC}"
echo "docker-compose ps              # Check container status"
echo "docker-compose logs -f app     # View application logs"
echo "docker-compose restart         # Restart all services"
echo "sudo systemctl status nginx   # Check Nginx status"
echo "curl http://localhost:5000     # Test direct app access"
echo ""

if [ "$OPENAI_KEY" = "" ]; then
    echo -e "${YELLOW}⚠️  Remember to update your OpenAI API key in .env file!${NC}"
fi

echo -e "${GREEN}✅ Your RAG chatbot with widget size configuration is now live!${NC}"