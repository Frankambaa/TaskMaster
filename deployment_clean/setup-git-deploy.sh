#!/bin/bash

# Setup Git-based deployment - Run this once to configure
set -e

echo "🔧 Setting up Git-based deployment..."

# Get repository URL from user
echo "Enter your Git repository URL (e.g., https://github.com/username/repo.git):"
read -r GIT_REPO_URL

echo "Enter your Git branch name (default: main):"
read -r GIT_BRANCH
GIT_BRANCH=${GIT_BRANCH:-main}

# Update quick-deploy.sh with actual repository details
sed -i "s|GIT_REPO_URL=\"https://github.com/yourusername/your-repo.git\"|GIT_REPO_URL=\"$GIT_REPO_URL\"|" quick-deploy.sh
sed -i "s|GIT_BRANCH=\"main\"|GIT_BRANCH=\"$GIT_BRANCH\"|" quick-deploy.sh

echo "✅ Git deployment configured!"
echo "Repository: $GIT_REPO_URL"
echo "Branch: $GIT_BRANCH"
echo ""
echo "Now you can deploy with: ./quick-deploy.sh"
echo "It will automatically pull the latest code and deploy!"