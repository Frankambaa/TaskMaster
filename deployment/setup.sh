#!/bin/bash

# AWS EC2 RAG Chatbot Deployment Script
# This script sets up a complete production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting RAG Chatbot Deployment Setup${NC}"

# Update system
echo -e "${YELLOW}📦 Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install required packages
echo -e "${YELLOW}🔧 Installing required packages...${NC}"
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
    certbot \
    python3-certbot-nginx \
    ufw \
    htop \
    fail2ban

# Install Docker
echo -e "${YELLOW}🐳 Installing Docker...${NC}"
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
echo -e "${YELLOW}🐳 Installing Docker Compose...${NC}"
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Setup PostgreSQL
echo -e "${YELLOW}🗄️ Setting up PostgreSQL...${NC}"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE chatbot_db;"
sudo -u postgres psql -c "CREATE USER chatbot_user WITH PASSWORD 'secure_password_$(date +%s)';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;"
sudo -u postgres psql -c "ALTER USER chatbot_user CREATEDB;"

# Configure firewall
echo -e "${YELLOW}🔒 Configuring firewall...${NC}"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Setup fail2ban
echo -e "${YELLOW}🛡️ Setting up fail2ban...${NC}"
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Create application directory
echo -e "${YELLOW}📁 Creating application directory...${NC}"
sudo mkdir -p /opt/rag-chatbot
sudo chown ubuntu:ubuntu /opt/rag-chatbot

# Setup log rotation
echo -e "${YELLOW}📋 Setting up log rotation...${NC}"
sudo tee /etc/logrotate.d/rag-chatbot > /dev/null <<EOF
/opt/rag-chatbot/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        /bin/kill -USR1 \$(cat /opt/rag-chatbot/app.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
EOF

# Create systemd service for auto-start
echo -e "${YELLOW}⚙️ Creating systemd service...${NC}"
sudo tee /etc/systemd/system/rag-chatbot.service > /dev/null <<EOF
[Unit]
Description=RAG Chatbot Application
After=docker.service postgresql.service
Requires=docker.service postgresql.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/rag-chatbot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable auto-start
sudo systemctl daemon-reload
sudo systemctl enable rag-chatbot

# Setup backup script
echo -e "${YELLOW}💾 Setting up backup script...${NC}"
sudo tee /opt/rag-chatbot/backup.sh > /dev/null <<'EOF'
#!/bin/bash

# Backup script for RAG Chatbot
BACKUP_DIR="/opt/rag-chatbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Database backup
sudo -u postgres pg_dump chatbot_db > $BACKUP_DIR/db_backup_$DATE.sql

# Application files backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz -C /opt/rag-chatbot --exclude=backups .

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -type f -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/rag-chatbot/backup.sh

# Setup daily backup cron job
echo -e "${YELLOW}⏰ Setting up daily backups...${NC}"
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/rag-chatbot/backup.sh >> /var/log/backup.log 2>&1") | crontab -

# Create monitoring script
echo -e "${YELLOW}📊 Setting up monitoring...${NC}"
sudo tee /opt/rag-chatbot/monitor.sh > /dev/null <<'EOF'
#!/bin/bash

# Simple health check script
HEALTH_URL="http://localhost:5000/health"
LOG_FILE="/var/log/rag-chatbot-monitor.log"

# Check if application is responding
if curl -f -s $HEALTH_URL > /dev/null; then
    echo "$(date): Application is healthy" >> $LOG_FILE
else
    echo "$(date): Application is down, attempting restart" >> $LOG_FILE
    cd /opt/rag-chatbot
    sudo docker-compose restart app
fi

# Check disk usage
DISK_USAGE=$(df /opt/rag-chatbot | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "$(date): Warning: Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -gt 90 ]; then
    echo "$(date): Warning: Memory usage is ${MEMORY_USAGE}%" >> $LOG_FILE
fi
EOF

chmod +x /opt/rag-chatbot/monitor.sh

# Setup monitoring cron job (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/rag-chatbot/monitor.sh") | crontab -

# Create update script
echo -e "${YELLOW}🔄 Creating update script...${NC}"
sudo tee /opt/rag-chatbot/update.sh > /dev/null <<'EOF'
#!/bin/bash

# Update script for RAG Chatbot
cd /opt/rag-chatbot

echo "Pulling latest changes..."
git pull origin main

echo "Building new images..."
sudo docker-compose build

echo "Stopping services..."
sudo docker-compose down

echo "Starting services..."
sudo docker-compose up -d

echo "Update completed!"
EOF

chmod +x /opt/rag-chatbot/update.sh

# Setup automatic security updates
echo -e "${YELLOW}🔒 Setting up automatic security updates...${NC}"
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Create deployment info
echo -e "${YELLOW}📄 Creating deployment info...${NC}"
sudo tee /opt/rag-chatbot/DEPLOYMENT_INFO.txt > /dev/null <<EOF
RAG Chatbot Deployment Information
==================================

Deployment Date: $(date)
Server IP: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)

Services:
- Application: Docker container on port 5000
- Database: PostgreSQL on port 5432
- Web Server: Nginx on ports 80/443

Important Files:
- Application: /opt/rag-chatbot/
- Nginx config: /etc/nginx/sites-available/default
- Environment: /opt/rag-chatbot/.env.production
- Logs: /opt/rag-chatbot/logs/
- Backups: /opt/rag-chatbot/backups/

Commands:
- Start: sudo systemctl start rag-chatbot
- Stop: sudo systemctl stop rag-chatbot
- Restart: sudo systemctl restart rag-chatbot
- Update: /opt/rag-chatbot/update.sh
- Backup: /opt/rag-chatbot/backup.sh
- Monitor: /opt/rag-chatbot/monitor.sh

Next Steps:
1. Clone your application code to /opt/rag-chatbot/
2. Configure .env.production file
3. Run: sudo docker-compose up -d
4. Setup SSL certificate if using domain
EOF

echo -e "${GREEN}✅ Basic setup completed!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Clone your application code to /opt/rag-chatbot/"
echo "2. Configure .env.production file with your API keys"
echo "3. Run: sudo docker-compose up -d"
echo "4. Setup SSL certificate if using a domain"
echo ""
echo -e "${GREEN}🎉 Your server is ready for RAG Chatbot deployment!${NC}"