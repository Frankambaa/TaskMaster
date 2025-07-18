#!/bin/bash

# Fix deployment issues and deploy properly
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Fixing deployment issues...${NC}"

# Fix directory permissions
echo -e "${YELLOW}📁 Fixing directory permissions...${NC}"
sudo chown -R ubuntu:ubuntu /home/ubuntu/deployment
chmod -R 755 /home/ubuntu/deployment

# Check if database exists and handle accordingly
echo -e "${YELLOW}🗄️ Checking database status...${NC}"
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw chatbot_db; then
    echo -e "${GREEN}✅ Database 'chatbot_db' already exists, skipping creation${NC}"
else
    echo -e "${YELLOW}🗄️ Creating database...${NC}"
    sudo -u postgres psql -c "CREATE DATABASE chatbot_db;"
    sudo -u postgres psql -c "CREATE USER chatbot_user WITH PASSWORD 'secure_password_$(date +%s)';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;"
    sudo -u postgres psql -c "ALTER USER chatbot_user CREATEDB;"
fi

# Check if user is in docker group
echo -e "${YELLOW}🐳 Checking Docker permissions...${NC}"
if groups ubuntu | grep -q docker; then
    echo -e "${GREEN}✅ User ubuntu is already in docker group${NC}"
else
    echo -e "${YELLOW}🐳 Adding ubuntu to docker group...${NC}"
    sudo usermod -aG docker ubuntu
    echo -e "${YELLOW}⚠️  You need to logout and login again for docker group changes to take effect${NC}"
fi

# Set proper environment variables
echo -e "${YELLOW}🔧 Setting up environment variables...${NC}"
cat > /home/ubuntu/deployment/.env << EOF
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:secure_password_$(date +%s)@localhost:5432/chatbot_db

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Security
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
EOF

echo -e "${GREEN}✅ Environment file created at /home/ubuntu/deployment/.env${NC}"
echo -e "${YELLOW}⚠️  Please edit the .env file and add your OpenAI API key${NC}"

# Make scripts executable
chmod +x /home/ubuntu/deployment/*.sh

echo -e "${GREEN}🎉 Deployment issues fixed!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Edit /home/ubuntu/deployment/.env and add your OpenAI API key"
echo "2. If you added ubuntu to docker group, logout and login again"
echo "3. Run: cd /home/ubuntu/deployment && ./quick-deploy.sh"