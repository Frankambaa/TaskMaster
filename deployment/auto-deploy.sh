#!/bin/bash

# Fully Automated Deployment Script for RAG Chatbot
# This script sets up continuous deployment with zero manual intervention

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up Fully Automated Deployment${NC}"
echo -e "${BLUE}=========================================${NC}"

# Configuration
REPO_URL="https://github.com/your-username/your-repo.git"
BRANCH="main"
APP_NAME="rag-chatbot"
DEPLOY_PATH="/opt/$APP_NAME"
WEBHOOK_PORT="9000"

# Get configuration from environment or prompt
prompt_config() {
    echo -e "${YELLOW}📋 Configuration Setup${NC}"
    
    # Get GitHub repository URL
    if [ -z "$GITHUB_REPO" ]; then
        read -p "GitHub Repository URL: " REPO_URL
    else
        REPO_URL="$GITHUB_REPO"
    fi
    
    # Get OpenAI API Key
    if [ -z "$OPENAI_API_KEY" ]; then
        read -p "OpenAI API Key: " OPENAI_API_KEY
    fi
    
    # Get webhook secret
    if [ -z "$WEBHOOK_SECRET" ]; then
        WEBHOOK_SECRET=$(openssl rand -hex 32)
        echo "Generated webhook secret: $WEBHOOK_SECRET"
    fi
    
    # Get database password
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 32)
        echo "Generated database password: $DB_PASSWORD"
    fi
    
    # Get domain name (optional)
    if [ -z "$DOMAIN_NAME" ]; then
        read -p "Domain name (optional): " DOMAIN_NAME
    fi
}

# Install system dependencies
install_dependencies() {
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
        net-tools \
        nodejs \
        npm \
        supervisor
    
    # Install Docker
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
        sudo apt install -y docker-ce docker-ce-cli containerd.io
        sudo usermod -aG docker ubuntu
    fi
    
    # Install Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

# Setup database
setup_database() {
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
    
    echo -e "${GREEN}✅ Database setup completed${NC}"
}

# Setup firewall
setup_firewall() {
    echo -e "${YELLOW}🔒 Configuring firewall...${NC}"
    
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow $WEBHOOK_PORT/tcp
    sudo ufw --force enable
    
    echo -e "${GREEN}✅ Firewall configured${NC}"
}

# Create deployment directory
create_deployment_directory() {
    echo -e "${YELLOW}📁 Creating deployment directory...${NC}"
    
    sudo mkdir -p $DEPLOY_PATH
    sudo chown ubuntu:ubuntu $DEPLOY_PATH
    
    # Create logs directory
    mkdir -p $DEPLOY_PATH/logs
    
    echo -e "${GREEN}✅ Deployment directory created${NC}"
}

# Setup webhook listener
setup_webhook() {
    echo -e "${YELLOW}🔗 Setting up webhook listener...${NC}"
    
    # Create webhook listener script
    cat > $DEPLOY_PATH/webhook-listener.js << 'EOF'
const http = require('http');
const crypto = require('crypto');
const { exec } = require('child_process');
const fs = require('fs');

const PORT = process.env.WEBHOOK_PORT || 9000;
const SECRET = process.env.WEBHOOK_SECRET;
const DEPLOY_PATH = process.env.DEPLOY_PATH || '/opt/rag-chatbot';

const server = http.createServer((req, res) => {
    if (req.method !== 'POST') {
        res.statusCode = 405;
        res.end('Method Not Allowed');
        return;
    }

    if (req.url !== '/webhook') {
        res.statusCode = 404;
        res.end('Not Found');
        return;
    }

    let body = '';
    req.on('data', (chunk) => {
        body += chunk.toString();
    });

    req.on('end', () => {
        // Verify webhook signature
        const signature = req.headers['x-hub-signature-256'];
        if (signature) {
            const expectedSignature = 'sha256=' + crypto
                .createHmac('sha256', SECRET)
                .update(body)
                .digest('hex');
            
            if (signature !== expectedSignature) {
                res.statusCode = 401;
                res.end('Unauthorized');
                return;
            }
        }

        try {
            const payload = JSON.parse(body);
            
            // Check if it's a push to main branch
            if (payload.ref === 'refs/heads/main' || payload.ref === 'refs/heads/master') {
                console.log('Received push to main branch, deploying...');
                
                // Log the deployment
                const logEntry = `${new Date().toISOString()} - Deployment triggered by ${payload.pusher.name}\n`;
                fs.appendFileSync(`${DEPLOY_PATH}/logs/deployment.log`, logEntry);
                
                // Execute deployment script
                exec(`cd ${DEPLOY_PATH} && ./deploy.sh`, (error, stdout, stderr) => {
                    if (error) {
                        console.error(`Deployment error: ${error}`);
                        fs.appendFileSync(`${DEPLOY_PATH}/logs/deployment.log`, `ERROR: ${error}\n`);
                    } else {
                        console.log('Deployment completed successfully');
                        fs.appendFileSync(`${DEPLOY_PATH}/logs/deployment.log`, `SUCCESS: Deployment completed\n`);
                    }
                });
                
                res.statusCode = 200;
                res.end('Deployment triggered');
            } else {
                res.statusCode = 200;
                res.end('Not a main branch push, ignoring');
            }
        } catch (error) {
            console.error('Error parsing webhook payload:', error);
            res.statusCode = 400;
            res.end('Bad Request');
        }
    });
});

server.listen(PORT, () => {
    console.log(`Webhook listener running on port ${PORT}`);
});
EOF

    # Create deployment script
    cat > $DEPLOY_PATH/deploy.sh << 'EOF'
#!/bin/bash

# Automated deployment script
set -e

DEPLOY_PATH="/opt/rag-chatbot"
cd $DEPLOY_PATH

echo "$(date): Starting deployment..." >> logs/deployment.log

# Pull latest changes
git pull origin main

# Build and restart containers
docker-compose build
docker-compose down
docker-compose up -d

# Wait for services to be ready
sleep 30

# Health check
if curl -f -s http://localhost:5000/health > /dev/null; then
    echo "$(date): Deployment successful - Application is healthy" >> logs/deployment.log
else
    echo "$(date): Deployment failed - Application is not responding" >> logs/deployment.log
    exit 1
fi

echo "$(date): Deployment completed successfully" >> logs/deployment.log
EOF

    chmod +x $DEPLOY_PATH/deploy.sh
    
    echo -e "${GREEN}✅ Webhook listener setup completed${NC}"
}

# Setup supervisor for webhook
setup_supervisor() {
    echo -e "${YELLOW}⚙️ Setting up supervisor for webhook...${NC}"
    
    sudo tee /etc/supervisor/conf.d/webhook-listener.conf > /dev/null <<EOF
[program:webhook-listener]
command=node $DEPLOY_PATH/webhook-listener.js
directory=$DEPLOY_PATH
autostart=true
autorestart=true
stderr_logfile=$DEPLOY_PATH/logs/webhook-error.log
stdout_logfile=$DEPLOY_PATH/logs/webhook-access.log
environment=WEBHOOK_PORT="$WEBHOOK_PORT",WEBHOOK_SECRET="$WEBHOOK_SECRET",DEPLOY_PATH="$DEPLOY_PATH"
user=ubuntu
EOF

    sudo supervisorctl reread
    sudo supervisorctl update
    
    echo -e "${GREEN}✅ Supervisor setup completed${NC}"
}

# Clone and setup repository
clone_repository() {
    echo -e "${YELLOW}📥 Cloning repository...${NC}"
    
    cd $DEPLOY_PATH
    
    # Initialize git if not exists
    if [ ! -d ".git" ]; then
        git clone $REPO_URL .
    else
        git pull origin main
    fi
    
    # Copy deployment files
    if [ -d "deployment" ]; then
        cp deployment/docker-compose.yml .
        cp deployment/Dockerfile .
        cp deployment/nginx.conf .
        cp deployment/requirements.txt .
        cp deployment/start.sh .
        chmod +x start.sh
    fi
    
    echo -e "${GREEN}✅ Repository cloned${NC}"
}

# Create environment file
create_environment() {
    echo -e "${YELLOW}⚙️ Creating environment configuration...${NC}"
    
    cat > $DEPLOY_PATH/.env.production << EOF
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

# Webhook Configuration
WEBHOOK_SECRET=$WEBHOOK_SECRET
WEBHOOK_PORT=$WEBHOOK_PORT
EOF

    echo -e "${GREEN}✅ Environment configuration created${NC}"
}

# Setup SSL if domain provided
setup_ssl() {
    if [ -n "$DOMAIN_NAME" ]; then
        echo -e "${YELLOW}🔐 Setting up SSL certificate...${NC}"
        
        # Install certbot
        sudo apt install -y certbot python3-certbot-nginx
        
        # Stop nginx if running
        sudo systemctl stop nginx 2>/dev/null || true
        
        # Get SSL certificate
        sudo certbot certonly --standalone -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
        
        # Update nginx configuration
        sed -i "s/server_name _;/server_name $DOMAIN_NAME;/g" $DEPLOY_PATH/nginx.conf
        sed -i "s/your-domain.com/$DOMAIN_NAME/g" $DEPLOY_PATH/nginx.conf
        
        echo -e "${GREEN}✅ SSL certificate installed${NC}"
    else
        echo -e "${YELLOW}⚠️ No domain provided, using self-signed certificate${NC}"
        
        # Create self-signed certificate
        sudo mkdir -p /etc/nginx/ssl
        sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/nginx/ssl/selfsigned.key \
            -out /etc/nginx/ssl/selfsigned.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        # Update nginx config
        sed -i "s|/etc/letsencrypt/live/your-domain.com/fullchain.pem|/etc/nginx/ssl/selfsigned.crt|g" $DEPLOY_PATH/nginx.conf
        sed -i "s|/etc/letsencrypt/live/your-domain.com/privkey.pem|/etc/nginx/ssl/selfsigned.key|g" $DEPLOY_PATH/nginx.conf
    fi
}

# Start services
start_services() {
    echo -e "${YELLOW}🚀 Starting services...${NC}"
    
    cd $DEPLOY_PATH
    
    # Build and start containers
    docker-compose build
    docker-compose up -d
    
    # Start webhook listener
    sudo supervisorctl start webhook-listener
    
    # Wait for services
    sleep 30
    
    echo -e "${GREEN}✅ Services started${NC}"
}

# Create systemd service for auto-start
create_systemd_service() {
    echo -e "${YELLOW}⚙️ Creating systemd service...${NC}"
    
    sudo tee /etc/systemd/system/$APP_NAME.service > /dev/null <<EOF
[Unit]
Description=RAG Chatbot Application
After=docker.service postgresql.service
Requires=docker.service postgresql.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_PATH
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable $APP_NAME
    
    echo -e "${GREEN}✅ Systemd service created${NC}"
}

# Main execution
main() {
    prompt_config
    install_dependencies
    setup_database
    setup_firewall
    create_deployment_directory
    clone_repository
    create_environment
    setup_webhook
    setup_supervisor
    setup_ssl
    start_services
    create_systemd_service
    
    # Display completion info
    echo
    echo -e "${GREEN}🎉 Fully Automated Deployment Setup Complete!${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo
    echo -e "${YELLOW}📋 Deployment Information:${NC}"
    echo -e "Application URL: ${GREEN}http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)${NC}"
    if [ -n "$DOMAIN_NAME" ]; then
        echo -e "Domain URL: ${GREEN}https://$DOMAIN_NAME${NC}"
    fi
    echo -e "Webhook URL: ${GREEN}http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):$WEBHOOK_PORT/webhook${NC}"
    echo -e "Webhook Secret: ${GREEN}$WEBHOOK_SECRET${NC}"
    echo
    echo -e "${YELLOW}🔧 GitHub Webhook Setup:${NC}"
    echo "1. Go to your GitHub repository settings"
    echo "2. Click 'Webhooks' → 'Add webhook'"
    echo "3. Payload URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):$WEBHOOK_PORT/webhook"
    echo "4. Content type: application/json"
    echo "5. Secret: $WEBHOOK_SECRET"
    echo "6. Select 'Just the push event'"
    echo "7. Click 'Add webhook'"
    echo
    echo -e "${YELLOW}🚀 Automatic Deployment:${NC}"
    echo "- Every push to main branch will trigger automatic deployment"
    echo "- No manual intervention required"
    echo "- Deployment logs: $DEPLOY_PATH/logs/deployment.log"
    echo "- Webhook logs: $DEPLOY_PATH/logs/webhook-access.log"
    echo
    echo -e "${GREEN}✅ Your RAG Chatbot is now fully automated!${NC}"
    echo -e "${GREEN}Just push code to GitHub and it will deploy automatically!${NC}"
}

# Run main function
main "$@"