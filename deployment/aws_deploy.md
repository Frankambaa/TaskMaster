# AWS EC2 Deployment Guide for RAG Chatbot

## Quick Deployment Overview

This guide provides a complete setup for deploying the RAG chatbot to AWS EC2 with:
- Docker containerization for isolation
- Nginx reverse proxy with SSL
- PostgreSQL database
- Automatic backups
- Health monitoring
- Auto-scaling ready

## Prerequisites

- AWS Account with EC2 access
- Domain name (optional, for SSL)
- Basic Linux command knowledge

## Step 1: Launch EC2 Instance

### Recommended Instance Configuration:
- **Instance Type**: `t3.medium` (2 vCPU, 4GB RAM) minimum
- **Operating System**: Ubuntu 22.04 LTS
- **Storage**: 20GB gp3 SSD minimum
- **Security Group**: Allow ports 80, 443, 22

### Security Group Rules:
```
Port 22 (SSH): Your IP only
Port 80 (HTTP): 0.0.0.0/0
Port 443 (HTTPS): 0.0.0.0/0
Port 5432 (PostgreSQL): Internal only
```

## Step 2: Initial Server Setup

Connect to your EC2 instance:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

Run the automated setup script:
```bash
curl -fsSL https://raw.githubusercontent.com/your-repo/deployment/setup.sh | bash
```

## Step 3: Configure Environment Variables

Create production environment file:
```bash
sudo nano /opt/rag-chatbot/.env.production
```

Add the following variables:
```env
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:secure_password@localhost:5432/chatbot_db
PGDATABASE=chatbot_db
PGUSER=chatbot_user
PGPASSWORD=secure_password
PGHOST=localhost
PGPORT=5432

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your_super_secret_key_here
SESSION_SECRET=your_session_secret_here

# Security
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

## Step 4: SSL Certificate Setup (Optional)

If you have a domain name:
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Step 5: Start Services

```bash
cd /opt/rag-chatbot
sudo docker-compose up -d
```

## Step 6: Verify Deployment

Check all services are running:
```bash
sudo docker-compose ps
```

Test the application:
```bash
curl -I http://your-domain.com
```

## Monitoring and Maintenance

### View Logs:
```bash
sudo docker-compose logs -f app
```

### Backup Database:
```bash
sudo -u postgres pg_dump chatbot_db > backup_$(date +%Y%m%d).sql
```

### Update Application:
```bash
cd /opt/rag-chatbot
git pull origin main
sudo docker-compose build
sudo docker-compose up -d
```

## Performance Optimization

### For High Traffic:
- Upgrade to `t3.large` or `c5.large`
- Use RDS PostgreSQL instead of local database
- Add CloudFront CDN
- Implement Redis for session storage

### Cost Optimization:
- Use spot instances for development
- Schedule automatic shutdown during off-hours
- Monitor CloudWatch metrics

## Security Best Practices

1. **Firewall**: UFW configured automatically
2. **SSH**: Key-based authentication only
3. **SSL**: Let's Encrypt certificates
4. **Database**: Local access only
5. **Updates**: Automatic security updates enabled

## Troubleshooting

### Common Issues:

1. **Port 80/443 blocked**: Check security group rules
2. **Database connection failed**: Verify PostgreSQL is running
3. **SSL certificate failed**: Ensure domain DNS points to EC2
4. **Out of memory**: Upgrade instance type

### Log Locations:
- Application: `sudo docker-compose logs app`
- Nginx: `sudo docker-compose logs nginx`
- Database: `sudo docker-compose logs db`

## Scaling Considerations

### Horizontal Scaling:
- Use Application Load Balancer
- Multiple EC2 instances
- Shared RDS database
- S3 for file storage

### Vertical Scaling:
- Upgrade instance type
- Add more storage
- Optimize database queries

## Cost Estimation

### Monthly AWS Costs (US East):
- t3.medium: ~$30
- 20GB storage: ~$2
- Data transfer: ~$5-20
- **Total**: ~$37-52/month

### Additional Costs:
- Domain name: ~$12/year
- SSL certificate: Free (Let's Encrypt)
- Backup storage: ~$1-5/month