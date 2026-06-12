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

## Scheduled run (GitHub Actions)

Daily at **9:15 AM IST** via `.github/workflows/daily-ingest.yml`.

Pipeline order on each run:

1. **Scrape** — fetch latest HTML from all 5 allowlisted Groww URLs
2. **Parse & chunk** — structure-aware chunks per changed page
3. **Embed** — `BAAI/bge-small-en-v1.5` vectors
4. **Upsert** — update embeddings in Chroma Cloud (`mf_faq_hdfc_groww`)
5. **Validate** — `python -m rag validate-index` after a successful ingest

### Required GitHub secrets

| Secret | Description |
|--------|-------------|
| `CHROMA_API_KEY` | Chroma Cloud API key |
| `CHROMA_TENANT` | Chroma Cloud tenant ID |
| `CHROMA_DATABASE` | Database name (e.g. `testDB`) |

Manual trigger: **Actions → Daily Ingest Pipeline → Run workflow**. Use `force_reindex` to re-chunk and re-embed even when HTML is unchanged.
