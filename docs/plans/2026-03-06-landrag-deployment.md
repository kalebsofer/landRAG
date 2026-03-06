# landRAG Deployment Plan

## Config

| Setting | Value |
|---------|-------|
| GCP Project ID | `landrag` |
| GCP Project Number | `1031825367236` |
| Region | `europe-west2` (London) |
| Domain | `landrag.softmaxco.io` |
| Registrar | Porkbun |
| GitHub repo | `https://github.com/kalebsofer/landRAG` |
| Pinecone index (prod) | `landrag-prod` |
| Pinecone index (dev) | `landrag-dev` |

## Domain

- **DNS record (done):** CNAME `landrag` → `ghs.googlehosted.com` (TTL 600)
- **SSL:** Automatic via Cloud Run domain mapping

## GCP Project Setup

1. Create a GCP project (done — `landrag`)
2. Enable billing
3. Enable APIs: Cloud Run, Cloud SQL, Memorystore, Cloud Storage, Secret Manager, Artifact Registry, Cloud Build

## Infrastructure Provisioning

### Cloud SQL (PostgreSQL 16)

- Create instance, database `landrag`, and a service user
- Configure private networking (VPC connector) for Cloud Run access

### Memorystore (Redis 7)

- Provision instance in same region/VPC as Cloud Run

### Cloud Storage

- Create bucket `landrag-documents` for raw ingested files

### Artifact Registry

- Create a Docker repository for container images

### Pinecone (done)

- Production index: `landrag-prod`
- Dimensions: 3072 (text-embedding-3-large)

## Secrets

Store in **Secret Manager**:
- `DATABASE_URL`
- `REDIS_URL`
- `PINECONE_API_KEY`
- `OPENAI_API_KEY`
- `COHERE_API_KEY`
- `ANTHROPIC_API_KEY`

Grant Cloud Run service accounts `secretmanager.secretAccessor` role.

## Cloud Run Services

### API Service

- Image from Artifact Registry
- Entrypoint: `uvicorn landrag.api.app:create_app --factory --host 0.0.0.0 --port 8000`
- Environment variables referencing Secret Manager
- VPC connector for Cloud SQL + Memorystore access
- Domain mapping: `landrag.softmaxco.io`

### Celery Worker

- Same image, different entrypoint: `celery -A landrag.workers.celery_app worker --loglevel=info`
- Deploy as Cloud Run service or Cloud Run Job (depending on workload pattern)
- Same VPC connector and secrets access

## Networking

- VPC connector shared by API + worker for private access to Cloud SQL and Memorystore
- No public IP on Cloud SQL or Memorystore

## IAM

- Cloud Run service account needs:
  - `secretmanager.secretAccessor`
  - `cloudsql.client`
  - `storage.objectAdmin` (for GCS bucket)

## CI/CD (GitHub Actions)

- **Repo:** `https://github.com/kalebsofer/landRAG`
- **Auth:** Workload Identity Federation (preferred) or service account key
- **On push:** ruff (lint), mypy (type check), pytest (tests)
- **On merge to main:** Build + push image to Artifact Registry, `gcloud run deploy` API + worker
- **Pipeline file:** `.github/workflows/ci.yml` (to be created)

## Database Migrations

- Run `alembic upgrade head` against production Cloud SQL as part of deploy pipeline (before new revision goes live)

## Monitoring

- Cloud Run built-in logging (Cloud Logging)
- Set up alerting for error rate spikes and high latency (Cloud Monitoring)
