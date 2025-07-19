#!/bin/bash

# Install Docker and dependencies on fresh Ubuntu server
set -e

echo "Installing Docker and dependencies..."

# Update system
sudo apt update
sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose nginx openssl curl

# Start and enable services
sudo systemctl start docker
sudo systemctl enable docker
sudo systemctl start nginx
sudo systemctl enable nginx

# Add user to docker group
sudo usermod -aG docker ubuntu

# Test Docker
sudo docker --version
sudo docker-compose --version

echo "✅ Docker, Nginx, and dependencies installed successfully!"
echo "Please logout and login again for docker group changes to take effect."
echo "Then upload your code and run: ./quick-deploy.sh"