# RAG Chatbot AWS Deployment

This directory contains all the necessary files to deploy the RAG Chatbot application to AWS EC2 with complete isolation and production-ready configuration.

## Quick Start (Recommended)

For the fastest deployment, use the automated script:

```bash
# 1. Launch EC2 instance (Ubuntu 22.04 LTS, t3.medium)
# 2. Connect via SSH
# 3. Clone your repository
# 4. Run the quick deployment script

chmod +x deployment/quick-deploy.sh
./deployment/quick-deploy.sh
```

This script will:
- ✅ Install all dependencies (Docker, PostgreSQL, Nginx, etc.)
- ✅ Configure firewall and security
- ✅ Set up SSL certificates
- ✅ Create database and user
- ✅ Build and start all services
- ✅ Set up automated backups
- ✅ Configure monitoring and health checks

## Manual Deployment

If you prefer step-by-step control:

### 1. Prepare EC2 Instance

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Run setup script
curl -fsSL https://raw.githubusercontent.com/your-repo/deployment/setup.sh | bash
```

### 2. Deploy Application

```bash
# Clone repository
git clone https://github.com/your-repo/rag-chatbot.git /opt/rag-chatbot
cd /opt/rag-chatbot

# Copy deployment files
cp deployment/* .

# Configure environment
cp .env.example .env.production
nano .env.production  # Add your API keys and configuration

# Start services
docker-compose up -d
```

### 3. Configure SSL (Optional)

```bash
# If you have a domain name
sudo certbot --nginx -d your-domain.com

# Update nginx configuration
sudo nano nginx.conf
```

## Architecture Overview

```
Internet → [AWS ALB] → [EC2 Instance]
                           ├── Nginx (Port 80/443)
                           ├── Flask App (Port 5000)
                           ├── PostgreSQL (Port 5432)
                           └── Redis (Port 6379)
```

## Files Description

- **`aws_deploy.md`** - Complete deployment guide
- **`quick-deploy.sh`** - Automated deployment script
- **`setup.sh`** - System setup and dependencies
- **`docker-compose.yml`** - Multi-container orchestration
- **`Dockerfile`** - Application container configuration
- **`nginx.conf`** - Reverse proxy and SSL configuration
- **`requirements.txt`** - Python dependencies
- **`start.sh`** - Application startup script

## Security Features

- 🔒 **Firewall**: UFW with minimal required ports
- 🔐 **SSL/TLS**: Let's Encrypt or self-signed certificates
- 🛡️ **Rate Limiting**: Nginx-based API protection
- 🔑 **Database Security**: Isolated PostgreSQL with strong passwords
- 🚫 **Access Control**: Admin panel IP restrictions (optional)

## Monitoring & Maintenance

### Health Checks
```bash
# Check all services
docker-compose ps

# Check application health
curl -f http://localhost:5000/health

# View logs
docker-compose logs -f app
```

### Backups
```bash
# Manual backup
./backup.sh

# Automated daily backups are set up via cron
```

### Updates
```bash
# Update application
git pull origin main
docker-compose build
docker-compose up -d
```

## Scaling Options

### Vertical Scaling
- Upgrade to larger EC2 instance (t3.large, c5.large)
- Increase storage capacity
- Optimize database configuration

### Horizontal Scaling
- Use Application Load Balancer
- Multiple EC2 instances
- Shared RDS database
- S3 for file storage
- ElastiCache for Redis

## Cost Optimization

### Production (24/7)
- **t3.medium**: ~$30/month
- **Storage**: ~$5/month
- **Data Transfer**: ~$10/month
- **Total**: ~$45/month

### Development (8 hours/day)
- **t3.medium** (scheduled): ~$12/month
- **Storage**: ~$2/month
- **Total**: ~$14/month

### Cost Saving Tips
1. Use spot instances for development
2. Schedule automatic shutdown
3. Monitor unused resources
4. Use AWS Free Tier when possible

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   docker-compose logs
   docker-compose down && docker-compose up -d
   ```

2. **Database connection issues**
   ```bash
   docker-compose exec db psql -U chatbot_user -d chatbot_db
   ```

3. **SSL certificate issues**
   ```bash
   sudo certbot renew --dry-run
   ```

4. **High memory usage**
   ```bash
   free -h
   docker stats
   ```

### Log Locations
- Application: `docker-compose logs app`
- Nginx: `docker-compose logs nginx`
- Database: `docker-compose logs db`
- System: `/var/log/syslog`

## Support

For issues or questions:
1. Check application logs
2. Review system resources
3. Verify configuration files
4. Test with minimal setup

Remember to:
- Keep your API keys secure
- Regular backups
- Monitor system resources
- Update dependencies regularly