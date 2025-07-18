#!/bin/bash

# Quick deployment script for RAG Chatbot on AWS EC2
# This script automates the entire deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 RAG Chatbot Quick Deployment Script${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   exit 1
fi

# Function to prompt for user input
prompt_user() {
    local prompt="$1"
    local var_name="$2"
    local default_value="$3"
    
    if [ -n "$default_value" ]; then
        read -p "$prompt [$default_value]: " input
        input=${input:-$default_value}
    else
        read -p "$prompt: " input
    fi
    
    eval "$var_name='$input'"
}

# Get configuration from user
echo -e "${YELLOW}📋 Configuration Setup${NC}"
echo "Please provide the following information:"
echo

prompt_user "Domain name (optional, for SSL)" "DOMAIN_NAME" ""
prompt_user "OpenAI API Key" "OPENAI_API_KEY" ""
prompt_user "Admin email for SSL certificates" "ADMIN_EMAIL" "admin@example.com"
prompt_user "Application name" "APP_NAME" "rag-chatbot"
prompt_user "Database password" "DB_PASSWORD" "$(openssl rand -base64 32)"

echo
echo -e "${YELLOW}📦 Installing system dependencies...${NC}"

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    nginx \
    postgresql \
    postgresql-contrib \
    ufw \
    htop \
    net-tools

# Install Docker
echo -e "${YELLOW}🐳 Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✅ Docker installed successfully${NC}"
else
    echo -e "${GREEN}✅ Docker is already installed${NC}"
fi

# Install Docker Compose
echo -e "${YELLOW}🐳 Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✅ Docker Compose installed successfully${NC}"
else
    echo -e "${GREEN}✅ Docker Compose is already installed${NC}"
fi

# Setup PostgreSQL
echo -e "${YELLOW}🗄️ Setting up PostgreSQL...${NC}"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "DROP DATABASE IF EXISTS chatbot_db;"
sudo -u postgres psql -c "DROP USER IF EXISTS chatbot_user;"
sudo -u postgres psql -c "CREATE DATABASE chatbot_db;"
sudo -u postgres psql -c "CREATE USER chatbot_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;"
sudo -u postgres psql -c "ALTER USER chatbot_user CREATEDB;"

echo -e "${GREEN}✅ PostgreSQL setup completed${NC}"

# Configure firewall
echo -e "${YELLOW}🔒 Configuring firewall...${NC}"
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo -e "${GREEN}✅ Firewall configured${NC}"

# Create application directory
echo -e "${YELLOW}📁 Setting up application directory...${NC}"
sudo mkdir -p /opt/$APP_NAME
sudo chown $USER:$USER /opt/$APP_NAME
cd /opt/$APP_NAME

# Copy deployment files
echo -e "${YELLOW}📋 Copying deployment files...${NC}"
cp ~/deployment/* . 2>/dev/null || true

# Create environment file
echo -e "${YELLOW}⚙️ Creating environment configuration...${NC}"
cat > .env.production << EOF
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:$DB_PASSWORD@db:5432/chatbot_db
PGDATABASE=chatbot_db
PGUSER=chatbot_user
PGPASSWORD=$DB_PASSWORD
PGHOST=db
PGPORT=5432

# OpenAI Configuration
OPENAI_API_KEY=$OPENAI_API_KEY

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 32)
SESSION_SECRET=$(openssl rand -base64 32)

# Security
ALLOWED_HOSTS=${DOMAIN_NAME:-localhost}
EOF

# Copy application files
echo -e "${YELLOW}📁 Copying application files...${NC}"
cp -r ~/workspace/* . 2>/dev/null || true

# Make scripts executable
chmod +x start.sh 2>/dev/null || true

# Install SSL certificate if domain is provided
if [ -n "$DOMAIN_NAME" ]; then
    echo -e "${YELLOW}🔐 Installing SSL certificate...${NC}"
    
    # Install certbot
    sudo apt install -y certbot python3-certbot-nginx
    
    # Stop nginx if running
    sudo systemctl stop nginx 2>/dev/null || true
    
    # Get SSL certificate
    sudo certbot certonly --standalone -d $DOMAIN_NAME --non-interactive --agree-tos --email $ADMIN_EMAIL
    
    # Update nginx configuration with domain
    sed -i "s/server_name _;/server_name $DOMAIN_NAME;/g" nginx.conf
    sed -i "s/your-domain.com/$DOMAIN_NAME/g" nginx.conf
    
    echo -e "${GREEN}✅ SSL certificate installed${NC}"
else
    echo -e "${YELLOW}⚠️ No domain provided, using self-signed certificate${NC}"
    # Create self-signed certificate
    sudo mkdir -p /etc/nginx/ssl
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/selfsigned.key \
        -out /etc/nginx/ssl/selfsigned.crt \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    # Update nginx config for self-signed cert
    sed -i "s|/etc/letsencrypt/live/your-domain.com/fullchain.pem|/etc/nginx/ssl/selfsigned.crt|g" nginx.conf
    sed -i "s|/etc/letsencrypt/live/your-domain.com/privkey.pem|/etc/nginx/ssl/selfsigned.key|g" nginx.conf
fi

# Create health check endpoint
echo -e "${YELLOW}🏥 Creating health check endpoint...${NC}"
cat >> app.py << 'EOF'

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
EOF

# Build and start services
echo -e "${YELLOW}🚀 Building and starting services...${NC}"
docker-compose build
docker-compose up -d

# Wait for services to start
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 30

# Check service status
echo -e "${YELLOW}📊 Checking service status...${NC}"
docker-compose ps

# Test the application
echo -e "${YELLOW}🧪 Testing application...${NC}"
if curl -f -s http://localhost:5000/health > /dev/null; then
    echo -e "${GREEN}✅ Application is responding${NC}"
else
    echo -e "${RED}❌ Application is not responding${NC}"
    echo "Checking logs..."
    docker-compose logs app
fi

# Setup backup cron job
echo -e "${YELLOW}💾 Setting up automated backups...${NC}"
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/rag-chatbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U chatbot_user chatbot_db > $BACKUP_DIR/db_backup_$DATE.sql

# Application files backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz --exclude=backups --exclude=node_modules .

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -type f -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/$APP_NAME/backup.sh >> /var/log/backup.log 2>&1") | crontab -

# Create systemd service
echo -e "${YELLOW}⚙️ Creating systemd service...${NC}"
sudo tee /etc/systemd/system/$APP_NAME.service > /dev/null <<EOF
[Unit]
Description=RAG Chatbot Application
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/$APP_NAME
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME

# Display deployment information
echo
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}=====================================${NC}"
echo
echo -e "${YELLOW}📋 Deployment Information:${NC}"
echo -e "Application URL: ${GREEN}http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)${NC}"
if [ -n "$DOMAIN_NAME" ]; then
    echo -e "Domain URL: ${GREEN}https://$DOMAIN_NAME${NC}"
fi
echo -e "Admin Panel: ${GREEN}http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/admin${NC}"
echo -e "Application Directory: ${GREEN}/opt/$APP_NAME${NC}"
echo
echo -e "${YELLOW}🔧 Management Commands:${NC}"
echo -e "Start: ${GREEN}sudo systemctl start $APP_NAME${NC}"
echo -e "Stop: ${GREEN}sudo systemctl stop $APP_NAME${NC}"
echo -e "Restart: ${GREEN}sudo systemctl restart $APP_NAME${NC}"
echo -e "Status: ${GREEN}docker-compose ps${NC}"
echo -e "Logs: ${GREEN}docker-compose logs -f app${NC}"
echo -e "Backup: ${GREEN}./backup.sh${NC}"
echo
echo -e "${YELLOW}📁 Important Files:${NC}"
echo -e "Environment: ${GREEN}/opt/$APP_NAME/.env.production${NC}"
echo -e "Docker Compose: ${GREEN}/opt/$APP_NAME/docker-compose.yml${NC}"
echo -e "Nginx Config: ${GREEN}/opt/$APP_NAME/nginx.conf${NC}"
echo -e "Logs: ${GREEN}/opt/$APP_NAME/logs/${NC}"
echo -e "Backups: ${GREEN}/opt/$APP_NAME/backups/${NC}"
echo
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. Update your DNS records to point to this server IP"
echo "2. Upload your documents through the admin panel"
echo "3. Configure API tools if needed"
echo "4. Test the chatbot widget on your website"
echo
echo -e "${GREEN}✅ Your RAG Chatbot is now live and ready to use!${NC}"