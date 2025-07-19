#!/bin/bash

# TaskMaster RAG Chatbot - Complete deployment script
set -e

echo "🚀 Deploying TaskMaster RAG Chatbot from GitHub..."

# Configuration
GIT_REPO_URL="https://github.com/Frankambaa/TaskMaster.git"
GIT_BRANCH="main"
PROJECT_DIR="/home/ubuntu/taskmaster"

# Pull latest code from Git
echo "📥 Pulling latest TaskMaster code..."
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "Repository exists, pulling latest changes..."
    cd $PROJECT_DIR
    git fetch origin
    git reset --hard origin/$GIT_BRANCH
    git pull origin $GIT_BRANCH
else
    echo "Cloning TaskMaster repository..."
    rm -rf $PROJECT_DIR
    git clone -b $GIT_BRANCH $GIT_REPO_URL $PROJECT_DIR
    cd $PROJECT_DIR
fi

echo "✅ Code updated from Git"
cd $PROJECT_DIR/deployment_clean

# Clean everything
docker-compose down --volumes --remove-orphans 2>/dev/null || true
docker system prune -af 2>/dev/null || true

# Create environment file
if [ ! -f .env ]; then
    POSTGRES_PASSWORD="taskmaster_$(date +%s)"
    SECRET_KEY=$(openssl rand -hex 32)
    
    cat > .env << EOF
POSTGRES_DB=taskmaster_db
POSTGRES_USER=taskmaster_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SECRET_KEY=$SECRET_KEY
OPENAI_API_KEY=sk-placeholder
EOF

    echo "Enter your OpenAI API key:"
    read -s OPENAI_KEY
    if [ ! -z "$OPENAI_KEY" ]; then
        sed -i "s/sk-placeholder/$OPENAI_KEY/" .env
    fi
fi

# Build and start
echo "🏗️ Building TaskMaster with dependencies..."
docker-compose up -d --build

# Wait and test
echo "⏳ Waiting for TaskMaster services..."
sleep 30

docker-compose ps

# Test application
if curl -f -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ TaskMaster responding"
else
    echo "TaskMaster logs:"
    docker-compose logs app --tail=10
fi

# Configure Nginx
echo "🌐 Setting up Nginx for TaskMaster..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/taskmaster
sudo ln -sf /etc/nginx/sites-available/taskmaster /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

SERVER_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null)
echo ""
echo "✅ TaskMaster RAG Chatbot deployed successfully!"
echo "🌐 Access: http://$SERVER_IP"
echo "👨‍💼 Admin: http://$SERVER_IP/admin"
echo "💬 Chat: http://$SERVER_IP/chatbot"
echo "🔧 Widget: http://$SERVER_IP/widget_example.html"