#!/bin/bash

# TaskMaster RAG Chatbot - AWS EC2 UserData deployment script
# This script runs automatically when EC2 instance starts
# Set OPENAI_API_KEY environment variable before launching instance

set -e
exec > >(tee /var/log/taskmaster-deploy.log) 2>&1

echo "🚀 Starting TaskMaster deployment via UserData..."

# Wait for instance to be ready
sleep 30

# Update system
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y

# Install Docker and dependencies
echo "📦 Installing Docker and dependencies..."
apt-get install -y docker.io docker-compose nginx openssl curl git
systemctl start docker
systemctl enable docker
systemctl start nginx  
systemctl enable nginx

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Configuration
GIT_REPO_URL="https://github.com/Frankambaa/TaskMaster.git"
GIT_BRANCH="main"
PROJECT_DIR="/home/ubuntu/taskmaster"

# Clone TaskMaster repository
echo "📥 Cloning TaskMaster repository..."
rm -rf $PROJECT_DIR
git clone -b $GIT_BRANCH $GIT_REPO_URL $PROJECT_DIR
chown -R ubuntu:ubuntu $PROJECT_DIR
cd $PROJECT_DIR/deployment_clean

# Create environment file with environment variables
echo "🔧 Setting up environment..."
POSTGRES_PASSWORD="taskmaster_$(date +%s)"
SECRET_KEY=$(openssl rand -hex 32)

# Get OpenAI key from environment variable (set in EC2 launch)
if [ -z "$OPENAI_API_KEY" ]; then
    OPENAI_KEY="sk-placeholder-set-environment-variable"
    echo "⚠️  Warning: OPENAI_API_KEY environment variable not set"
else
    OPENAI_KEY="$OPENAI_API_KEY"
    echo "✅ OpenAI API key found in environment"
fi

cat > .env << EOF
POSTGRES_DB=taskmaster_db
POSTGRES_USER=taskmaster_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SECRET_KEY=$SECRET_KEY
OPENAI_API_KEY=$OPENAI_KEY
EOF

chown ubuntu:ubuntu .env

# Build and start services
echo "🏗️ Building TaskMaster containers..."
docker-compose up -d --build

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 60

# Test application
echo "🧪 Testing application..."
docker-compose ps

if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ TaskMaster application responding"
else
    echo "❌ Application not responding. Logs:"
    docker-compose logs app --tail=20
fi

# Configure Nginx
echo "🌐 Configuring Nginx..."
rm -f /etc/nginx/sites-enabled/default
cp nginx.conf /etc/nginx/sites-available/taskmaster
ln -sf /etc/nginx/sites-available/taskmaster /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Get server IP and log completion
SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "unknown")

echo ""
echo "✅ TaskMaster RAG Chatbot deployment completed!"
echo "🌐 Access: http://$SERVER_IP"
echo "👨‍💼 Admin: http://$SERVER_IP/admin" 
echo "💬 Chat: http://$SERVER_IP/chatbot"
echo "🔧 Widget: http://$SERVER_IP/widget_example.html"
echo ""
echo "📋 Deployment logs saved to: /var/log/taskmaster-deploy.log"

# Create completion marker
echo "$(date): TaskMaster deployment completed successfully" > /home/ubuntu/deployment-complete.txt
chown ubuntu:ubuntu /home/ubuntu/deployment-complete.txt