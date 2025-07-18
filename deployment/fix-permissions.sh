#!/bin/bash

# Fix deployment permission issues
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Fixing deployment permissions and database issues...${NC}"

# Fix directory permissions first
echo -e "${YELLOW}📁 Fixing directory permissions...${NC}"
sudo chown -R ubuntu:ubuntu /home/ubuntu/deployment
sudo chmod -R 755 /home/ubuntu/deployment
cd /home/ubuntu/deployment

# Fix database user issues
echo -e "${YELLOW}🗄️ Fixing database user conflicts...${NC}"

# Drop existing connections to the database
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'chatbot_db' AND pid <> pg_backend_pid();" 2>/dev/null || true

# Revoke all privileges and drop user safely
sudo -u postgres psql -c "REVOKE ALL PRIVILEGES ON DATABASE chatbot_db FROM chatbot_user;" 2>/dev/null || true
sudo -u postgres psql -c "DROP USER IF EXISTS chatbot_user;" 2>/dev/null || true

# Create fresh database user
DB_PASSWORD=$(openssl rand -base64 16)
sudo -u postgres psql -c "CREATE USER chatbot_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;"
sudo -u postgres psql -c "ALTER USER chatbot_user CREATEDB;"

echo -e "${GREEN}✅ Database user recreated with new password${NC}"

# Create or update .env file
echo -e "${YELLOW}📝 Creating environment file...${NC}"
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:$DB_PASSWORD@localhost:5432/chatbot_db

# OpenAI Configuration  
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Security
ALLOWED_HOSTS=localhost,127.0.0.1
EOF

echo -e "${GREEN}✅ Environment file created${NC}"
echo -e "${YELLOW}⚠️  Please edit .env file and add your OpenAI API key:${NC}"
echo -e "${BLUE}nano .env${NC}"
echo ""
echo -e "${YELLOW}📋 Database password generated: ${GREEN}$DB_PASSWORD${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Edit .env file: nano .env"
echo "2. Replace 'your_openai_api_key_here' with your actual OpenAI API key"
echo "3. Run: docker-compose up -d --build"
echo ""
echo -e "${GREEN}🎉 Permissions fixed! Ready for deployment.${NC}"