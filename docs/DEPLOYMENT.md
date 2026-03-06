# landRAG Deployment Guide

Step-by-step guide to deploy landRAG to GCP Cloud Run.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated
- GCP project `landrag` created with billing enabled
- Docker installed (for local testing)
- DNS: CNAME `landrag.softmaxco.io` -> `ghs.googlehosted.com` (already done)

## Configuration

| Setting | Value |
|---------|-------|
| GCP Project | `landrag` |
| Region | `europe-west2` (London) |
| Cloud SQL instance | `landrag-db` (Postgres 16, db-f1-micro) |
| Artifact Registry | `landrag` (Docker) |
| Pinecone index (prod) | `landrag-prod` |
| Domain | `landrag.softmaxco.io` |

---

## Step 1: Authenticate gcloud

```bash
gcloud auth login
gcloud config set project landrag
```

Verify:
```bash
gcloud config get-value project
# Expected: landrag
```

## Step 2: Provision infrastructure

Run the one-time provisioning script. This enables APIs, creates Artifact Registry, Cloud SQL instance, and database.

```bash
export GCP_PROJECT=landrag
bash scripts/provision.sh
```

This takes 5-10 minutes (Cloud SQL creation is slow). When it finishes, it prints next steps.

## Step 3: Set database password

Generate a secure password and set it on the Cloud SQL postgres user:

```bash
gcloud sql users set-password postgres \
  --instance=landrag-db \
  --password=YOUR_SECURE_PASSWORD \
  --project=landrag
```

Save this password — you'll need it for `DB_PASSWORD` in Step 5.

## Step 4: Store API keys in Secret Manager

Store each API key. Replace the placeholder values with your actual keys from `.env`:

```bash
echo -n 'sk-...' | gcloud secrets create openai-api-key --data-file=- --project=landrag
echo -n 'pcsk_...' | gcloud secrets create pinecone-api-key --data-file=- --project=landrag
echo -n '...' | gcloud secrets create cohere-api-key --data-file=- --project=landrag
echo -n 'sk-ant-...' | gcloud secrets create anthropic-api-key --data-file=- --project=landrag
```

Grant the default Cloud Run service account access:

```bash
PROJECT_NUMBER=$(gcloud projects describe landrag --format='value(projectNumber)')
gcloud projects add-iam-policy-binding landrag \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Step 5: Get Cloud SQL connection name

```bash
gcloud sql instances describe landrag-db \
  --format='value(connectionName)' \
  --project=landrag
```

This returns something like `landrag:europe-west2:landrag-db`. Save it for the next step.

## Step 6: Deploy to Cloud Run

Set the required environment variables and run the deploy script:

```bash
export GCP_PROJECT=landrag
export CLOUD_SQL_CONNECTION=landrag:europe-west2:landrag-db
export DB_PASSWORD=YOUR_SECURE_PASSWORD
bash scripts/deploy.sh
```

This will:
1. Build the Docker image via Cloud Build
2. Push to Artifact Registry
3. Deploy to Cloud Run with Cloud SQL connectivity and secrets
4. Map `landrag.softmaxco.io` domain

## Step 7: Verify deployment

```bash
# Get the Cloud Run URL
SERVICE_URL=$(gcloud run services describe landrag \
  --region=europe-west2 --project=landrag \
  --format='value(status.url)')

# Health check (should show database: ok)
curl $SERVICE_URL/health

# Test search API
curl -X POST $SERVICE_URL/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "environmental impact of offshore wind", "limit": 5}'
```

Visit `https://landrag.softmaxco.io` in the browser to confirm the UI loads.

## Step 8: Run data ingestion

Ingestion runs from your local machine against the production database. You need the Cloud SQL Auth Proxy to connect locally:

```bash
# Install Cloud SQL Auth Proxy (one-time)
# https://cloud.google.com/sql/docs/postgres/sql-proxy

# Start the proxy (in a separate terminal)
cloud-sql-proxy landrag:europe-west2:landrag-db --port=5433

# Update .env to point at the proxy
# DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5433/landrag
# DATABASE_URL_SYNC=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5433/landrag
# PINECONE_INDEX_NAME=landrag-prod

# Run ingestion (10 docs per project for MVP)
.venv/Scripts/python -m landrag.cli --max-docs 10 --log-level INFO
```

## Redeployment

For subsequent deploys after code changes:

```bash
export GCP_PROJECT=landrag
export CLOUD_SQL_CONNECTION=landrag:europe-west2:landrag-db
export DB_PASSWORD=YOUR_SECURE_PASSWORD
bash scripts/deploy.sh
```

## Local testing with Docker Compose

To test the full stack locally before deploying:

```bash
docker compose up --build
# Visit http://localhost:8080/health
```

## Troubleshooting

**Cloud Run logs:**
```bash
gcloud run services logs read landrag --region=europe-west2 --project=landrag --limit=50
```

**Cloud SQL connectivity issues:**
- Verify the Cloud SQL instance is running: `gcloud sql instances list --project=landrag`
- Check the connection name matches what's in the deploy script
- Ensure the service account has `cloudsql.client` role

**Migration failures:**
- Check logs for Alembic errors — the entrypoint runs `alembic upgrade head` before starting the app
- Connect via Cloud SQL Auth Proxy and run migrations manually if needed

**Secret access denied:**
- Verify the service account has `secretmanager.secretAccessor` role (Step 4)
