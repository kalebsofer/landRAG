#!/bin/bash
# Deploy landRAG to Cloud Run
set -e

GCP_PROJECT=${GCP_PROJECT:?Set GCP_PROJECT environment variable}
GCP_REGION=${GCP_REGION:-europe-west2}
CLOUD_SQL_CONNECTION=${CLOUD_SQL_CONNECTION:?Set CLOUD_SQL_CONNECTION (e.g. project:region:instance)}
DB_PASSWORD=${DB_PASSWORD:?Set DB_PASSWORD environment variable}

IMAGE="$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/landrag/app:latest"

echo "=== Deploying landRAG ==="
echo "Project: $GCP_PROJECT"
echo "Region: $GCP_REGION"
echo "Image: $IMAGE"

# Build and push
echo "Building and pushing image..."
gcloud builds submit \
  --tag "$IMAGE" \
  --project="$GCP_PROJECT"

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy landrag \
  --image="$IMAGE" \
  --region="$GCP_REGION" \
  --project="$GCP_PROJECT" \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances="$CLOUD_SQL_CONNECTION" \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@/landrag?host=/cloudsql/${CLOUD_SQL_CONNECTION}" \
  --set-env-vars="DATABASE_URL_SYNC=postgresql+psycopg2://postgres:${DB_PASSWORD}@/landrag?host=/cloudsql/${CLOUD_SQL_CONNECTION}" \
  --set-env-vars="APP_ENV=production" \
  --set-env-vars="PINECONE_INDEX_NAME=landrag-dev" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest" \
  --set-secrets="PINECONE_API_KEY=pinecone-api-key:latest" \
  --set-secrets="COHERE_API_KEY=cohere-api-key:latest" \
  --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --port=8080

# Map custom domain (idempotent)
echo "Mapping domain..."
gcloud beta run domain-mappings create \
  --service=landrag \
  --domain=landrag.softmaxco.io \
  --region="$GCP_REGION" \
  --project="$GCP_PROJECT" \
  2>/dev/null || echo "Domain mapping already exists"

# Show URL
echo ""
echo "=== Deployment complete ==="
SERVICE_URL=$(gcloud run services describe landrag --region="$GCP_REGION" --project="$GCP_PROJECT" --format='value(status.url)')
echo "Service URL: $SERVICE_URL"
echo "Custom domain: https://landrag.softmaxco.io"
echo "Health check: curl $SERVICE_URL/health"
