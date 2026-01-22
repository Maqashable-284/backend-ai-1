# Scoop AI Backend - Deployment Guide

## Prerequisites

- Python 3.11+
- MongoDB Atlas account (or local MongoDB)
- Google Cloud account with Gemini API access
- Docker (optional, for containerized deployment)

---

## Environment Variables

Create a `.env` file in the backend directory:

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/scoop

# Optional (with defaults)
MODEL_NAME=gemini-2.5-flash-preview-05-20
MONGODB_DATABASE=scoop
THINKING_LEVEL=LOW
THINKING_BUDGET=4096
MAX_FUNCTION_CALLS=30
MAX_HISTORY_MESSAGES=20
MAX_HISTORY_TOKENS=8000
MAX_OUTPUT_TOKENS=16384
GEMINI_TIMEOUT_SECONDS=60
SESSION_TTL_SECONDS=3600
CATALOG_CACHE_TTL_SECONDS=3600

# Context Caching (85% token savings)
ENABLE_CONTEXT_CACHING=true
CONTEXT_CACHE_TTL_MINUTES=60
CACHE_REFRESH_BEFORE_EXPIRY_MINUTES=5
CACHE_CHECK_INTERVAL_MINUTES=1

# Security
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
ADMIN_TOKEN=your-secret-admin-token

# Optional Features
ENABLE_SAFETY_SETTINGS=false
DEBUG=false
```

---

## Local Development

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export GEMINI_API_KEY="your-api-key"
export MONGODB_URI="your-mongodb-uri"
```

Or create a `.env` file (recommended).

### 3. Run Development Server

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. Verify Health

```bash
curl http://localhost:8080/health
# Expected: {"status": "healthy", ...}
```

---

## Docker Deployment

### Build Image

```bash
docker build -t scoop-ai-backend:v2.0 .
```

### Run Container

```bash
docker run -d \
  --name scoop-backend \
  -p 8080:8080 \
  -e GEMINI_API_KEY="your-api-key" \
  -e MONGODB_URI="your-mongodb-uri" \
  -e MODEL_NAME="gemini-2.5-flash-preview-05-20" \
  scoop-ai-backend:v2.0
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MONGODB_URI=${MONGODB_URI}
      - MODEL_NAME=gemini-2.5-flash-preview-05-20
      - THINKING_LEVEL=LOW
      - ENABLE_CONTEXT_CACHING=true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Cloud Run Deployment

### 1. Build and Push Image

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/scoop-backend:v2.0
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy scoop-backend \
  --image gcr.io/YOUR_PROJECT_ID/scoop-backend:v2.0 \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 60s \
  --set-env-vars "GEMINI_API_KEY=your-key,MONGODB_URI=your-uri"
```

### 3. Production Settings

```bash
# Set secrets (recommended over env vars)
gcloud secrets create gemini-api-key --data-file=- <<< "your-api-key"
gcloud secrets create mongodb-uri --data-file=- <<< "your-mongodb-uri"

# Deploy with secrets
gcloud run deploy scoop-backend \
  --image gcr.io/YOUR_PROJECT_ID/scoop-backend:v2.0 \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,MONGODB_URI=mongodb-uri:latest"
```

---

## MongoDB Atlas Setup

### 1. Create Cluster

- Go to [MongoDB Atlas](https://cloud.mongodb.com)
- Create a new cluster (M0 Free tier works for development)
- Create database user with read/write access
- Whitelist IP addresses (or 0.0.0.0/0 for Cloud Run)

### 2. Create Indexes

```javascript
// Connect to MongoDB and run:

// Text search index
db.products.createIndex(
  { name: "text", name_ka: "text", brand: "text", category: "text" },
  { default_language: "none" }
);

// Vector search index (Atlas UI)
// Index name: vector_index
// Path: description_embedding
// Dimensions: 768
// Similarity: cosine
```

### 3. Get Connection String

```
mongodb+srv://username:password@cluster.mongodb.net/scoop?retryWrites=true&w=majority
```

---

## Health Checks

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic health check |
| `/health/detailed` | Detailed system status (admin only) |
| `/admin/cache/status` | Context cache status (admin only) |

### Health Response

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "model": "gemini-2.5-flash-preview-05-20",
  "mongodb": "connected",
  "context_cache": "active",
  "uptime_seconds": 3600
}
```

---

## Monitoring

### Logs

```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=scoop-backend" --limit 100

# Docker logs
docker logs -f scoop-backend
```

### Key Metrics to Monitor

- Request latency (target: <3s P95)
- Error rate (target: <1%)
- Token usage (context cache hit rate)
- MongoDB connection pool

---

## Scaling Guidelines

| Traffic Level | Cloud Run Config |
|---------------|-----------------|
| Low (<10 RPS) | min-instances=0, max-instances=3 |
| Medium (10-50 RPS) | min-instances=1, max-instances=10 |
| High (>50 RPS) | min-instances=3, max-instances=20 |

### Cold Start Optimization

```bash
# Set min-instances to avoid cold starts
gcloud run services update scoop-backend --min-instances 1
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "texts=0" errors | Check Gemini API quota, retry logic handles this |
| MongoDB connection timeout | Verify IP whitelist, connection string |
| Context cache miss | Check cache TTL settings, may need warmup |
| High latency | Enable context caching, check THINKING_LEVEL |

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m uvicorn main:app --log-level debug
```

---

## Rollback

### Docker

```bash
docker stop scoop-backend
docker run -d --name scoop-backend-v1 scoop-ai-backend:v1.0
```

### Cloud Run

```bash
# List revisions
gcloud run revisions list --service scoop-backend

# Rollback to previous revision
gcloud run services update-traffic scoop-backend \
  --to-revisions REVISION_NAME=100
```

---

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [README.md](./README.md) - Quick start guide
- [CONTEXT.md](./CONTEXT.md) - Development history
