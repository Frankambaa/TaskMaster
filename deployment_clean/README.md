# RAG Chatbot Deployment

Clean, production-ready deployment for the RAG chatbot with widget size configuration.

## Quick Setup

1. **Upload all files to your server:**
   ```bash
   # Upload the complete project
   scp -r . ubuntu@your-server-ip:/home/ubuntu/ragbot/
   ```

2. **Run the deployment:**
   ```bash
   ssh ubuntu@your-server-ip
   cd /home/ubuntu/ragbot/deployment_clean
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Access your chatbot:**
   - Main site: `http://your-server-ip`
   - Admin panel: `http://your-server-ip/admin`
   - Chatbot: `http://your-server-ip/chatbot`

## Files Included

- `Dockerfile` - Container configuration
- `docker-compose.yml` - Service orchestration
- `requirements.txt` - Python dependencies
- `nginx.conf` - Web server configuration
- `deploy.sh` - Automated deployment script
- `.env.example` - Environment template

## Requirements

- Docker and Docker Compose
- Nginx
- OpenAI API key
- Ubuntu/Debian server

## Features

- Complete RAG chatbot with document processing
- Widget size configuration (small, medium, large)
- Admin panel for document management
- PostgreSQL database
- Production-ready security settings

## Troubleshooting

```bash
# Check container status
docker-compose ps

# View application logs
docker-compose logs -f app

# Restart services
docker-compose restart

# Test direct access
curl http://localhost:5000
```