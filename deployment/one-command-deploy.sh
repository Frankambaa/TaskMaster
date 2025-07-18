#!/bin/bash

# One-Command RAG Chatbot Deployment Script
# Run this script with: bash one-command-deploy.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 RAG Chatbot One-Command Deployment${NC}"
echo -e "${BLUE}This script will set up everything for you!${NC}"
echo ""

# Function to prompt for input
prompt_for_input() {
    local prompt="$1"
    local var_name="$2"
    local default_value="$3"
    
    if [ -n "$default_value" ]; then
        read -p "$prompt [$default_value]: " value
        value=${value:-$default_value}
    else
        read -p "$prompt: " value
    fi
    
    eval "$var_name='$value'"
}

# Get user inputs
echo -e "${YELLOW}📋 Please provide the following information:${NC}"
prompt_for_input "Enter your OpenAI API key" OPENAI_API_KEY
prompt_for_input "Enter database password" DB_PASSWORD "$(openssl rand -base64 12)"
prompt_for_input "Enter your domain name (optional, press Enter to skip)" DOMAIN_NAME ""

echo ""
echo -e "${GREEN}🔧 Starting deployment...${NC}"

# Step 1: Update system
echo -e "${YELLOW}📦 Updating system...${NC}"
sudo apt update -y

# Step 2: Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    rm get-docker.sh
fi

# Step 3: Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}🐳 Installing Docker Compose...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Step 4: Install other required packages
echo -e "${YELLOW}📦 Installing required packages...${NC}"
sudo apt install -y nginx postgresql postgresql-contrib certbot python3-certbot-nginx

# Step 5: Setup PostgreSQL
echo -e "${YELLOW}🗄️ Setting up database...${NC}"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database (handle if already exists)
sudo -u postgres psql -c "CREATE DATABASE chatbot_db;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "DROP USER IF EXISTS chatbot_user;"
sudo -u postgres psql -c "CREATE USER chatbot_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;"
sudo -u postgres psql -c "ALTER USER chatbot_user CREATEDB;"

# Step 6: Create environment file
echo -e "${YELLOW}📝 Creating environment configuration...${NC}"
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:$DB_PASSWORD@localhost:5432/chatbot_db

# OpenAI Configuration
OPENAI_API_KEY=$OPENAI_API_KEY

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Security
ALLOWED_HOSTS=localhost,127.0.0.1${DOMAIN_NAME:+,$DOMAIN_NAME}
EOF

# Step 7: Fix permissions
echo -e "${YELLOW}🔧 Setting up permissions...${NC}"
sudo chown -R ubuntu:ubuntu /home/ubuntu/deployment
chmod -R 755 /home/ubuntu/deployment

# Step 8: Start Docker services
echo -e "${YELLOW}🐳 Starting Docker services...${NC}"
# Check if user is in docker group
if ! groups ubuntu | grep -q docker; then
    echo -e "${YELLOW}⚠️  Adding user to docker group...${NC}"
    sudo usermod -aG docker ubuntu
fi

# Start services with proper group permissions
sg docker -c "docker-compose down" 2>/dev/null || true
sg docker -c "docker-compose up -d --build"

# Step 9: Configure Nginx
echo -e "${YELLOW}🌐 Configuring web server...${NC}"
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Step 10: Setup firewall
echo -e "${YELLOW}🔒 Configuring firewall...${NC}"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Step 11: Setup SSL if domain provided
if [ -n "$DOMAIN_NAME" ]; then
    echo -e "${YELLOW}🔒 Setting up SSL certificate...${NC}"
    sudo certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos --email admin@$DOMAIN_NAME
    
    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
fi

# Step 12: Wait for services to start
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 15

# Step 13: Test the deployment
echo -e "${YELLOW}🔍 Testing deployment...${NC}"
if sg docker -c "docker-compose ps | grep -q 'Up'"; then
    echo -e "${GREEN}✅ Docker services are running${NC}"
else
    echo -e "${RED}❌ Docker services failed to start${NC}"
    sg docker -c "docker-compose logs"
    exit 1
fi

# Test web server
if curl -s http://localhost > /dev/null; then
    echo -e "${GREEN}✅ Web server is responding${NC}"
else
    echo -e "${RED}❌ Web server is not responding${NC}"
    exit 1
fi

# Final success message
echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}📋 Your RAG Chatbot is now running:${NC}"
echo ""
if [ -n "$DOMAIN_NAME" ]; then
    echo -e "🌐 Website: ${GREEN}https://$DOMAIN_NAME${NC}"
    echo -e "👨‍💼 Admin Panel: ${GREEN}https://$DOMAIN_NAME/admin${NC}"
    echo -e "💬 Chatbot: ${GREEN}https://$DOMAIN_NAME/chatbot${NC}"
else
    SERVER_IP=$(curl -s http://checkip.amazonaws.com)
    echo -e "🌐 Website: ${GREEN}http://$SERVER_IP${NC}"
    echo -e "👨‍💼 Admin Panel: ${GREEN}http://$SERVER_IP/admin${NC}"
    echo -e "💬 Chatbot: ${GREEN}http://$SERVER_IP/chatbot${NC}"
fi
echo ""
echo -e "${YELLOW}📋 Useful commands:${NC}"
echo -e "View logs: ${BLUE}docker-compose logs -f${NC}"
echo -e "Stop services: ${BLUE}docker-compose down${NC}"
echo -e "Restart services: ${BLUE}docker-compose restart${NC}"
echo -e "Update app: ${BLUE}docker-compose up -d --build app${NC}"
echo ""
echo -e "${GREEN}✅ All widget size configurations are working!${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

# Show next steps
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Visit the admin panel to upload documents"
echo "2. Configure your AI tools for API integration"
echo "3. Test the chatbot interface"
echo "4. Customize widget sizes and branding"
echo ""
echo -e "${GREEN}🎉 Your RAG Chatbot is ready to use!${NC}"