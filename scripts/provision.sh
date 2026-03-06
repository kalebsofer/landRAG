#!/bin/bash
# One-time GCP infrastructure provisioning for landRAG
# Run this once to set up Cloud SQL, Artifact Registry, and Secret Manager
set -e

GCP_PROJECT=${GCP_PROJECT:?Set GCP_PROJECT environment variable}
GCP_REGION=${GCP_REGION:-europe-west2}

echo "=== Provisioning landRAG infrastructure ==="
echo "Project: $GCP_PROJECT"
echo "Region: $GCP_REGION"

# Enable required APIs
echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$GCP_PROJECT"

# Create Artifact Registry repository
echo "Creating Artifact Registry..."
gcloud artifacts repositories create landrag \
  --repository-format=docker \
  --location="$GCP_REGION" \
  --project="$GCP_PROJECT" \
  2>/dev/null || echo "Artifact Registry already exists"

# Create Cloud SQL instance
echo "Creating Cloud SQL instance (this takes a few minutes)..."
gcloud sql instances create landrag-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region="$GCP_REGION" \
  --project="$GCP_PROJECT" \
  --database-flags=max_connections=50 \
  2>/dev/null || echo "Cloud SQL instance already exists"

# Create database
echo "Creating database..."
gcloud sql databases create landrag \
  --instance=landrag-db \
  --project="$GCP_PROJECT" \
  2>/dev/null || echo "Database already exists"

echo ""
echo "=== Next steps ==="
echo "1. Set the database password:"
echo "   gcloud sql users set-password postgres --instance=landrag-db --password=YOUR_SECURE_PASSWORD --project=$GCP_PROJECT"
echo ""
echo "2. Store secrets in Secret Manager:"
echo "   echo -n 'key' | gcloud secrets create openai-api-key --data-file=- --project=$GCP_PROJECT"
echo "   echo -n 'key' | gcloud secrets create pinecone-api-key --data-file=- --project=$GCP_PROJECT"
echo "   echo -n 'key' | gcloud secrets create cohere-api-key --data-file=- --project=$GCP_PROJECT"
echo "   echo -n 'key' | gcloud secrets create anthropic-api-key --data-file=- --project=$GCP_PROJECT"
echo ""
echo "3. Get the Cloud SQL connection name:"
echo "   gcloud sql instances describe landrag-db --format='value(connectionName)' --project=$GCP_PROJECT"
echo ""
echo "4. Run scripts/deploy.sh to deploy the app"
