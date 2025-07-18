# RAG Chatbot Server Deployment Guide

This guide will help you deploy the RAG chatbot on your Ubuntu server step by step.

## Prerequisites

- Ubuntu 20.04 or 22.04 server
- Root or sudo access
- Your OpenAI API key
- Domain name (optional, for SSL)

## Step 1: Initial Server Setup

```bash
# 1. Update your server
sudo apt update && sudo apt upgrade -y

# 2. Create deployment directory
mkdir -p /home/ubuntu/deployment
cd /home/ubuntu/deployment

# 3. Download the deployment files (if not already present)
# You should have these files in your deployment directory:
# - docker-compose.yml
# - Dockerfile
# - nginx.conf
# - requirements.txt
```

## Step 2: Install Required Software

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to docker group
sudo usermod -aG docker ubuntu

# Install other required packages
sudo apt install -y nginx postgresql postgresql-contrib certbot python3-certbot-nginx
```

## Step 3: Setup Database

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database (skip if already exists)
sudo -u postgres psql -c "CREATE DATABASE chatbot_db;" || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER chatbot_user WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;"
sudo -u postgres psql -c "ALTER USER chatbot_user CREATEDB;"
```

## Step 4: Configure Environment

```bash
# Create .env file
cat > /home/ubuntu/deployment/.env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:your_secure_password@localhost:5432/chatbot_db

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here

# Security
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
EOF

# Replace with your actual values
nano /home/ubuntu/deployment/.env
```

## Step 5: Deploy with Docker

```bash
# Navigate to deployment directory
cd /home/ubuntu/deployment

# IMPORTANT: Logout and login again for docker group changes
# Or run: newgrp docker

# Build and start containers
docker-compose up -d --build

# Check if containers are running
docker-compose ps
```

## Step 6: Configure Nginx

```bash
# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/chatbot

# Enable the site
sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/

# Remove default nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Step 7: Configure Firewall

```bash
# Setup firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

## Step 8: Setup SSL (Optional)

```bash
# Only if you have a domain name
sudo certbot --nginx -d your-domain.com

# For automatic renewal
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Step 9: Verify Deployment

```bash
# Check all services
docker-compose ps

# Check logs
docker-compose logs -f app

# Test the application
curl http://localhost
curl http://your-server-ip
```

## Common Issues and Solutions

### Issue 1: Permission Denied
```bash
sudo chown -R ubuntu:ubuntu /home/ubuntu/deployment
chmod -R 755 /home/ubuntu/deployment
```

### Issue 2: Docker Permission Denied
```bash
sudo usermod -aG docker ubuntu
# Then logout and login again
```

### Issue 3: Database Connection Error
```bash
# Check database status
sudo systemctl status postgresql

# Reset database password
sudo -u postgres psql -c "ALTER USER chatbot_user WITH PASSWORD 'new_password';"
# Update .env file with new password
```

### Issue 4: Port Already in Use
```bash
# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl disable apache2

# Or kill process using port 80
sudo lsof -i :80
sudo kill -9 <PID>
```

### Issue 5: Container Build Fails
```bash
# Clean up and rebuild
docker-compose down
docker system prune -a
docker-compose up -d --build
```

## Useful Commands

```bash
# View application logs
docker-compose logs -f app

# Restart application
docker-compose restart app

# Stop all services
docker-compose down

# Update application
docker-compose up -d --build app

# Check nginx status
sudo systemctl status nginx

# Check database
docker-compose exec app python -c "
import os
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('Database connection successful')
conn.close()
"
```

## Final Verification

After deployment, your chatbot should be accessible at:
- **HTTP**: http://your-server-ip
- **HTTPS**: https://your-domain.com (if SSL configured)

The admin panel is at: `/admin`
The chatbot interface is at: `/chatbot`

## Support

If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Verify all services are running: `docker-compose ps`
3. Check firewall settings: `sudo ufw status`
4. Verify nginx configuration: `sudo nginx -t`

Your RAG chatbot with widget size configuration is now deployed and ready to use!