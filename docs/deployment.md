# DocuMind Deployment Guide

This guide covers deploying DocuMind to various cloud platforms and production environments.

## Prerequisites

- Docker and Docker Compose installed
- Cloud provider CLI configured (AWS CLI, gcloud, or Azure CLI)
- Domain name (optional, for HTTPS)

---

## Local Docker Deployment

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-repo/documind.git
cd documind

# Configure environment
cp src/.env.example src/.env
# Edit .env with your API keys

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Start the API server
cd src && uvicorn main:app --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
cd src && celery -A worker.celery_app worker --loglevel=info -Q extraction_queue
```

---

## AWS Deployment

### Option 1: EC2 + Docker

1. **Launch EC2 Instance**
   - AMI: Amazon Linux 2 or Ubuntu 22.04
   - Instance type: t3.medium (minimum)
   - Storage: 50GB SSD

2. **Install Dependencies**
   ```bash
   # Amazon Linux
   sudo yum update -y
   sudo yum install docker -y
   sudo systemctl start docker
   sudo usermod -aG docker ec2-user

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Deploy Application**
   ```bash
   git clone https://github.com/your-repo/documind.git
   cd documind
   docker-compose -f docker/docker-compose.yml up -d
   ```

4. **Configure Security Group**
   - Allow inbound: 8000 (API), 8501 (Streamlit)
   - Restrict MongoDB/Redis ports to internal only

### Option 2: ECS Fargate

```yaml
# task-definition.json
{
  "family": "documind",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "documind-api",
      "image": "your-ecr-repo/documind:latest",
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"}
      ],
      "environment": [
        {"name": "MONGO_URL", "value": "mongodb://..."}
      ]
    }
  ]
}
```

---

## Google Cloud Platform

### Cloud Run Deployment

1. **Build and Push Image**
   ```bash
   # Authenticate
   gcloud auth configure-docker

   # Build
   docker build -t gcr.io/PROJECT_ID/documind:latest .

   # Push
   docker push gcr.io/PROJECT_ID/documind:latest
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy documind \
     --image gcr.io/PROJECT_ID/documind:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --set-env-vars "MONGO_URL=mongodb://..."
   ```

3. **Set up Cloud Tasks** (for Celery replacement)
   Cloud Run doesn't support long-running workers. Use Cloud Tasks or Pub/Sub for async processing.

---

## Azure Deployment

### Azure Container Instances

```bash
# Create resource group
az group create --name documind-rg --location eastus

# Deploy container
az container create \
  --resource-group documind-rg \
  --name documind-api \
  --image ghcr.io/your-repo/documind:latest \
  --dns-name-label documind \
  --ports 8000 \
  --cpu 2 \
  --memory 4 \
  --environment-variables \
    MONGO_URL="mongodb://..." \
    REDIS_HOST="..."
```

---

## Production Considerations

### 1. Database Setup

**MongoDB Atlas (Recommended)**
```bash
# Connection string format
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/documind?retryWrites=true
```

**Self-hosted MongoDB**
- Enable authentication
- Configure replica set for HA
- Set up backups

### 2. Redis

**AWS ElastiCache / GCP Memorystore**
- Use managed Redis for production
- Enable encryption in transit
- Configure proper VPC networking

### 3. HTTPS/TLS

**Using Nginx Reverse Proxy:**
```nginx
server {
    listen 443 ssl;
    server_name documind.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/documind.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/documind.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }
}
```

### 4. Environment Variables

Never commit secrets. Use:
- AWS Secrets Manager
- GCP Secret Manager
- Azure Key Vault
- HashiCorp Vault

### 5. Monitoring

**Recommended Stack:**
- Prometheus + Grafana for metrics
- ELK Stack or CloudWatch for logs
- Sentry for error tracking

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
services:
  api:
    deploy:
      replicas: 3

  celery-worker:
    deploy:
      replicas: 5
```

### Load Balancing

Use AWS ALB, GCP Load Balancer, or Nginx for distributing traffic across API instances.

---

## Health Checks

Add to your deployment configuration:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/"]
  interval: 30s
  timeout: 10s
  retries: 3
```
