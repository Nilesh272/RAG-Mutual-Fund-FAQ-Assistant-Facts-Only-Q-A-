# Phase 1 — Corpus (Scheduler + Scraping)

**Status:** Implemented

## Deliverables

- Source Registry (`config/sources.yaml`)
- Scraping Service (`phases/phase1_corpus/scraping/`)
- GitHub Actions scheduler (`.github/workflows/daily-ingest.yml`)
- Ingest CLI entry point (`ingest/`)

## Run locally

```bash
pip install -r requirements-ingest.txt
python -m ingest run
python -m ingest scrape-only   # scrape without downstream phases
```

## Scheduled run

Daily at **9:15 AM IST** via GitHub Actions `daily-ingest.yml`.
