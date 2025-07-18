#!/bin/bash

# Simple deployment script - handles all common issues
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Simple RAG Chatbot Deployment${NC}"

# Get current directory
CURRENT_DIR=$(pwd)
echo -e "${YELLOW}📁 Current directory: $CURRENT_DIR${NC}"

# Step 1: Fix permissions
echo -e "${YELLOW}🔧 Fixing permissions...${NC}"
sudo chown -R ubuntu:ubuntu $CURRENT_DIR
chmod -R 755 $CURRENT_DIR

# Step 2: Handle database issues
echo -e "${YELLOW}🗄️ Setting up database...${NC}"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Clean up any database conflicts
echo -e "${YELLOW}🧹 Cleaning up database conflicts...${NC}"
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'chatbot_db' AND pid <> pg_backend_pid();" 2>/dev/null || true
sudo -u postgres psql -c "REVOKE ALL PRIVILEGES ON DATABASE chatbot_db FROM chatbot_user;" 2>/dev/null || true
sudo -u postgres psql -c "DROP USER IF EXISTS chatbot_user;" 2>/dev/null || true

# Create fresh database setup
DB_PASSWORD="chatbot_$(date +%s)"
sudo -u postgres psql -c "CREATE USER chatbot_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;"
sudo -u postgres psql -c "ALTER USER chatbot_user CREATEDB;"

echo -e "${GREEN}✅ Database setup complete${NC}"

# Step 3: Create environment file
echo -e "${YELLOW}📝 Creating environment file...${NC}"
cat > .env << EOF
DATABASE_URL=postgresql://chatbot_user:$DB_PASSWORD@localhost:5432/chatbot_db
OPENAI_API_KEY=your_openai_api_key_here
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_HOSTS=localhost,127.0.0.1
EOF

# Step 4: Get OpenAI API key from user
echo -e "${YELLOW}🔑 OpenAI API Key Required${NC}"
echo "Please enter your OpenAI API key:"
read -s OPENAI_KEY
sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env

# Step 5: Install Docker if needed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    rm get-docker.sh
fi

# Step 6: Install Docker Compose if needed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker Compose...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Step 7: Install Nginx
echo -e "${YELLOW}🌐 Installing Nginx...${NC}"
sudo apt update
sudo apt install -y nginx

# Step 8: Add user to docker group and start services
echo -e "${YELLOW}🐳 Starting Docker services...${NC}"
sudo usermod -aG docker ubuntu

# Use sg to run docker commands with proper group
sg docker -c "docker-compose down" 2>/dev/null || true
sg docker -c "docker-compose up -d --build"

# Step 9: Configure Nginx
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Step 10: Configure firewall
echo -e "${YELLOW}🔒 Configuring firewall...${NC}"
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Step 11: Wait and test
echo -e "${YELLOW}⏳ Waiting for services...${NC}"
sleep 10

# Test services
echo -e "${YELLOW}🔍 Testing services...${NC}"
if sg docker -c "docker-compose ps | grep -q 'Up'"; then
    echo -e "${GREEN}✅ Docker services running${NC}"
else
    echo -e "${RED}❌ Docker services failed${NC}"
    sg docker -c "docker-compose logs --tail=20"
fi

# Get server IP
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}')

# Final message
echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${YELLOW}📋 Access your chatbot:${NC}"
echo -e "🌐 Website: ${GREEN}http://$SERVER_IP${NC}"
echo -e "👨‍💼 Admin Panel: ${GREEN}http://$SERVER_IP/admin${NC}"
echo -e "💬 Chatbot: ${GREEN}http://$SERVER_IP/chatbot${NC}"
echo ""
echo -e "${YELLOW}📋 Useful commands:${NC}"
echo "Check status: docker-compose ps"
echo "View logs: docker-compose logs -f"
echo "Restart: docker-compose restart"
echo ""
echo -e "${GREEN}✅ Your RAG chatbot with widget sizes is ready!${NC}"