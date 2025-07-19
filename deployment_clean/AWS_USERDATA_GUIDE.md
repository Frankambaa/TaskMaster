# AWS EC2 UserData Deployment Guide

## How to Deploy TaskMaster with UserData (Fully Automated)

### Step 1: Prepare UserData Script
Copy this entire script into the UserData field when creating your EC2 instance:

```bash
#!/bin/bash

# Set your OpenAI API key here
export OPENAI_API_KEY="sk-your-actual-openai-key-here"

# Download and run TaskMaster deployment
curl -sSL https://raw.githubusercontent.com/Frankambaa/TaskMaster/main/deployment_clean/userdata-deploy.sh | bash
```

### Step 2: EC2 Instance Configuration
- **AMI**: Ubuntu 22.04 LTS
- **Instance Type**: t3.medium or larger (minimum 4GB RAM)
- **Security Group**: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **UserData**: Paste the script from Step 1 (with your OpenAI key)

### Step 3: Launch Instance
- Click "Launch Instance"
- Wait 5-10 minutes for automatic deployment
- Access your TaskMaster chatbot at `http://your-instance-ip`

### Step 4: Verify Deployment
```bash
# SSH into your instance to check status
ssh -i your-key.pem ubuntu@your-instance-ip

# Check if deployment completed
cat /home/ubuntu/deployment-complete.txt

# View deployment logs
sudo tail -f /var/log/taskmaster-deploy.log

# Check services
cd /home/ubuntu/taskmaster/deployment_clean
docker-compose ps
```

## Alternative: Environment Variable Method

If you prefer not to put the API key in UserData script, set it as an environment variable:

### In EC2 UserData:
```bash
#!/bin/bash

# Set environment variable
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> /etc/environment
source /etc/environment

# Deploy TaskMaster
curl -sSL https://raw.githubusercontent.com/Frankambaa/TaskMaster/main/deployment_clean/userdata-deploy.sh | bash
```

## What Happens Automatically:
1. ✅ System updates and package installation
2. ✅ Docker and Nginx installation  
3. ✅ TaskMaster repository cloning
4. ✅ Environment configuration with your OpenAI key
5. ✅ Docker container build and startup
6. ✅ Nginx web server configuration
7. ✅ Service testing and verification
8. ✅ Deployment logging and completion marker

## Access Your Application:
- **Main Site**: `http://your-instance-ip`
- **Admin Panel**: `http://your-instance-ip/admin`
- **Chat Interface**: `http://your-instance-ip/chatbot`
- **Widget Example**: `http://your-instance-ip/widget_example.html`

## Troubleshooting:
- **Deployment Logs**: `sudo cat /var/log/taskmaster-deploy.log`
- **Service Status**: `docker-compose ps`
- **Application Logs**: `docker-compose logs -f app`
- **Completion Check**: `cat /home/ubuntu/deployment-complete.txt`

Your TaskMaster RAG chatbot will be fully deployed and running within 10 minutes of instance launch!