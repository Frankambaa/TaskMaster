# TaskMaster RAG Chatbot - AWS EC2 Deployment Guide

Repository: https://github.com/Frankambaa/TaskMaster

## Step 1: Create AWS EC2 Instance
- Launch Ubuntu 22.04 LTS instance
- Choose t3.medium or larger (minimum 4GB RAM)
- Configure security group: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Download your key pair (.pem file)

## Step 2: Connect to Server
```bash
ssh -i your-key.pem ubuntu@your-server-ip
```

## Step 3: Install Docker (One-time setup)
```bash
sudo apt update
sudo apt install -y docker.io docker-compose nginx
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
sudo systemctl start docker
```

## Step 4: Deploy TaskMaster (Single Command)
```bash
ssh -i your-key.pem ubuntu@your-server-ip

# Download and run TaskMaster deployment
curl -sSL https://raw.githubusercontent.com/Frankambaa/TaskMaster/main/deployment_clean/deploy-taskmaster.sh | bash
```

**OR** manually:
```bash
ssh -i your-key.pem ubuntu@your-server-ip
git clone https://github.com/Frankambaa/TaskMaster.git /home/ubuntu/taskmaster
cd /home/ubuntu/taskmaster/deployment_clean
./deploy-taskmaster.sh
```

## Step 6: Quick Updates (After initial setup)
```bash
# For quick code updates without full rebuild
./git-deploy-only.sh
```

## Step 7: Access Your Application
- Main site: `http://your-server-ip`
- Admin panel: `http://your-server-ip/admin`
- Chatbot: `http://your-server-ip/chatbot`

## What Gets Installed Automatically:
- ✅ PostgreSQL database (via Docker)
- ✅ Flask application (via Docker)
- ✅ All Python dependencies
- ✅ Nginx web server configuration

## You Only Need:
1. Your OpenAI API key
2. This deployment folder
3. AWS EC2 instance

## Troubleshooting Commands:
```bash
# Check if services are running
docker-compose ps

# View application logs
docker-compose logs -f app

# Restart everything
docker-compose restart

# Check Nginx status
sudo systemctl status nginx
```

## Files You Need to Upload:
- All Python files (app.py, main.py, etc.)
- static/ folder (CSS, JS files)
- templates/ folder (HTML files)
- deployment_clean/ folder (Docker configuration)

That's it! Your RAG chatbot will be live and accessible worldwide.