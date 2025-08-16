# Docker Guide for New Tab

This guide provides comprehensive instructions for running New Tab using Docker, from development to production deployment.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## 🔧 Prerequisites

### Required Software

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Git**: For cloning the repository

### System Requirements

- **RAM**: Minimum 2GB, recommended 4GB
- **Storage**: Minimum 5GB free space
- **CPU**: 2+ cores recommended
- **OS**: Linux, macOS, or Windows with WSL2

### Installation

#### Linux (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

#### macOS
```bash
# Install Docker Desktop
brew install --cask docker

# Start Docker Desktop
open -a Docker
```

#### Windows
1. Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)
2. Enable WSL2 integration
3. Restart your system

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd newtab

# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env  # Set your ARK_API_TOKEN
```

### 2. Run with Docker Compose

```bash
# Start all services (production mode)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Access Services

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Extension Files**: http://localhost:80/extension/

### 4. Test the Setup

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test indexing (replace with your API token)
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "title": "Test Page",
    "content": "This is test content"
  }'

# Test search
curl "http://localhost:8000/search?query=test"
```

## 🛠️ Development Setup

### Development Mode

Use the development docker-compose file for live reloading and debugging:

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build

# Start with specific services
docker-compose -f docker-compose.dev.yml up backend-dev extension-server

# Run tests
docker-compose -f docker-compose.dev.yml --profile testing up test-runner
```

### Development Features

- **Live Reloading**: Code changes trigger automatic restarts
- **Debug Port**: Port 5678 exposed for debugpy
- **Volume Mounts**: Source code mounted for real-time editing
- **Development Database**: Separate dev database file

### Code Changes

When developing, your local code is mounted into the container:

```bash
# Edit code locally
vim backend/src/main.py

# Changes are automatically reflected in the running container
# Check logs for restart confirmation
docker-compose -f docker-compose.dev.yml logs -f backend-dev
```

### Running Tests

```bash
# Run all tests
docker-compose -f docker-compose.dev.yml --profile testing run --rm test-runner

# Run specific test types
docker-compose -f docker-compose.dev.yml --profile testing run --rm test-runner pytest tests/ -m "unit"
docker-compose -f docker-compose.dev.yml --profile testing run --rm test-runner pytest tests/ -m "integration"
docker-compose -f docker-compose.dev.yml --profile testing run --rm test-runner pytest tests/ -m "e2e"
```

## 🚀 Production Deployment

### Production Checklist

Before deploying to production:

1. **Security Configuration**
   ```bash
   # Set secure environment variables
   ARK_API_TOKEN=your-production-token
   LOG_LEVEL=info
   RELOAD=false
   ```

2. **Resource Limits**
   ```yaml
   # Add to docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 512M
             cpus: '0.5'
   ```

3. **Health Checks**
   ```bash
   # Verify health endpoints work
   curl http://localhost:8000/health/ready
   curl http://localhost:8000/health/live
   ```

### Production Commands

```bash
# Build and start production services
docker-compose up -d --build

# Update to latest images
docker-compose pull
docker-compose up -d

# Scale backend services
docker-compose up -d --scale backend=3

# Rolling update
docker-compose up -d --no-deps backend
```

### SSL/HTTPS Setup

For production HTTPS:

1. **Obtain SSL certificates**
   ```bash
   # Using Let's Encrypt with Certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **Update nginx configuration**
   ```nginx
   # Add to nginx/conf.d/default.conf
   server {
       listen 443 ssl;
       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;
       # ... rest of config
   }
   ```

3. **Mount certificates**
   ```yaml
   # Add to docker-compose.yml
   nginx:
     volumes:
       - /etc/letsencrypt/live/your-domain.com:/etc/nginx/ssl:ro
   ```

## ⚙️ Configuration

### Environment Variables

Key environment variables for Docker deployment:

```bash
# Required
ARK_API_TOKEN=your-ark-api-token

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
WORKERS=1

# Database Configuration
DATABASE_FILE=/app/data/web_memory.db
QUERY_CACHE_FILE=/app/data/query_embeddings_cache.json

# Vector Configuration
VECTOR_DIMENSION=2048

# Cache Configuration
QUERY_CACHE_CAPACITY=1000
QUERY_CACHE_TTL_DAYS=7

# Development
RELOAD=false
DEVELOPMENT=false
```

### Volume Configuration

Persistent data is stored in Docker volumes:

```yaml
volumes:
  # Backend data (database, cache)
  backend_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./data/backend

  # Logs
  backend_logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./logs/backend
```

### Service Profiles

Use profiles to control which services start:

```bash
# Start with monitoring (Prometheus, Grafana)
docker-compose --profile monitoring up -d

# Start with Redis caching
docker-compose --profile scaling up -d

# Start documentation server
docker-compose -f docker-compose.dev.yml --profile docs up -d
```

## 📊 Monitoring and Logging

### Built-in Monitoring

Access monitoring endpoints:

- **Metrics**: http://localhost:8000/metrics
- **System Metrics**: http://localhost:8000/metrics/system
- **Application Metrics**: http://localhost:8000/metrics/application
- **Detailed Health**: http://localhost:8000/health/detailed
- **Service Status**: http://localhost:8000/status

### Log Management

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f nginx

# Export logs
docker-compose logs backend > backend.log

# Log rotation is automatic via Docker's logging driver
```

### External Monitoring (Optional)

Start monitoring stack:

```bash
# Start Prometheus and Grafana
docker-compose --profile monitoring up -d

# Access Grafana: http://localhost:3000
# Default login: admin/admin123

# Access Prometheus: http://localhost:9090
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Permission Denied Errors
```bash
# Fix volume permissions
sudo chown -R $USER:$USER data/ logs/
chmod -R 755 data/ logs/
```

#### 2. Port Already in Use
```bash
# Find process using port
sudo lsof -i :8000

# Kill process or change port in .env
PORT=8001
```

#### 3. Database Connection Issues
```bash
# Check database file permissions
ls -la data/backend/

# Recreate database volume
docker-compose down -v
docker-compose up -d
```

#### 4. API Token Issues
```bash
# Verify token is set
docker-compose exec backend env | grep ARK_API_TOKEN

# Update token
echo "ARK_API_TOKEN=new-token" > .env
docker-compose up -d --force-recreate
```

### Debug Commands

```bash
# Enter running container
docker-compose exec backend bash

# Check container health
docker-compose ps
docker inspect <container-id>

# View container logs with timestamps
docker-compose logs -f -t backend

# Check resource usage
docker stats

# Validate Docker Compose file
docker-compose config
```

### Performance Issues

```bash
# Monitor resource usage
docker stats

# Check system metrics endpoint
curl http://localhost:8000/metrics/system

# Increase memory limit
docker-compose down
# Edit docker-compose.yml to add memory limits
docker-compose up -d
```

## 🚀 Advanced Usage

### Custom Docker Images

Build custom images:

```bash
# Build specific target
docker build --target production -t newtab:prod ./backend

# Build with build args
docker build --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') ./backend

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 ./backend
```

### Docker Swarm Deployment

Deploy to Docker Swarm:

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml newtab

# Scale services
docker service scale newtab_backend=3

# View services
docker stack services newtab
```

### Kubernetes Deployment

Generate Kubernetes manifests:

```bash
# Install kompose
curl -L https://github.com/kubernetes/kompose/releases/latest/download/kompose-linux-amd64 -o kompose
chmod +x kompose
sudo mv kompose /usr/local/bin

# Convert docker-compose to k8s
kompose convert

# Apply to cluster
kubectl apply -f .
```

### Backup and Restore

```bash
# Backup data volumes
docker run --rm -v newtab_backend_data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .

# Restore data volumes
docker run --rm -v newtab_backend_data:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /data
```

### CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to server
        run: |
          docker-compose pull
          docker-compose up -d --no-deps backend
```

## 📚 Additional Resources

- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Nginx Configuration](https://nginx.org/en/docs/)

## 🆘 Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `docker-compose logs -f`
3. Validate configuration: `docker-compose config`
4. Check health endpoints: `curl http://localhost:8000/health`
5. Create an issue with logs and configuration details

---

**Note**: This guide assumes you have basic familiarity with Docker and Docker Compose. For detailed Docker tutorials, visit the official Docker documentation.