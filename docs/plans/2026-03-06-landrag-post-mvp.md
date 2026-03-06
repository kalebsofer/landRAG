# landRAG Post-MVP (Alpha) Features

> Living document. Features added as needs emerge.

---

## 1. Nightly Ingestion Pipeline

**Goal:** Automatically ingest new PINS documents daily without manual intervention.

**Trigger:** GCP Cloud Scheduler fires a HTTP request to the API at ~02:00 UTC nightly, which enqueues a Celery ingestion job.

**Incremental scraping:**
- Query existing `Document.source_url` values before scraping
- Only download and process documents not already in Postgres
- Track high-water marks (e.g. last-seen page, most recent publish date) per source portal in an `IngestionCursor` table

**Deduplication:**
- Hash raw file content (SHA-256) on download
- Skip parsing/chunking/embedding if hash matches an existing document
- Handle re-published documents (same content, new URL) via hash lookup

**Monitoring:**
- Log document counts per run (found, new, skipped, failed) to the `IngestionJob` record
- Cloud Monitoring alert if a nightly run finds zero new documents for 7+ consecutive days (possible scraper breakage)
- Alert on failure rate > 10% within a single run

**Backfill:** Support a manual full-crawl mode for initial population or recovery, triggered via API endpoint or CLI command.

---

## Future Features (Unprioritised)

_Add items below as they become relevant._

-
