# Mutual Fund FAQ Assistant (Facts-Only Q&A)

A RAG-based facts-only FAQ assistant for HDFC mutual fund schemes, using Groww scheme pages as the data source.

**Disclaimer:** Facts-only. No investment advice.

## Project structure

```
├── .github/workflows/daily-ingest.yml   # Scheduler (9:15 AM IST daily)
├── config/
│   ├── sources.yaml                     # Source Registry (5 Groww URLs)
│   └── scraping.yaml                    # Scraping Service config
├── phases/
│   ├── phase1_corpus/                   # ✅ Scheduler + Scraping
│   ├── phase2_rag_core/                 # ✅ Parse + Chunk + Embed + Index
│   ├── phase3_generation/               # Intent + Generation (planned)
│   ├── phase4_api/                      # Chat API (planned)
│   ├── phase5_ui/                       # UI (planned)
│   └── phase6_eval/                     # Eval + Hardening (planned)
├── ingest/                              # CLI orchestrator
├── data/raw/                            # HTML snapshots (gitignored)
├── data/metadata/                       # Content hashes (gitignored)
├── docs/                                # Architecture documents
└── tests/phase1/                        # Phase 1 tests
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-ingest.txt
```

## Run ingestion (Phase 1)

```bash
# Full pipeline (scrape → parse → chunk → embed → index)
# Default: BAAI/bge-small-en-v1.5 local embeddings
python -m ingest run

# Fast offline / CI tests (deterministic hash vectors)
EMBEDDING_PROVIDER=hash python -m ingest run

# Re-index after switching embedding model
FORCE_REINDEX=true python -m ingest run

# Validate index + golden queries (Phase 5.2 / 5.3)
python -m rag validate-index
python -m rag golden

# Scrape only
python -m ingest scrape-only

# Write run summary JSON
python -m ingest run --summary /tmp/run-summary.json
```

## Scheduler (GitHub Actions)

Workflow: `.github/workflows/daily-ingest.yml`

| Setting | Value |
|---------|-------|
| Schedule | Daily 9:15 AM IST (`45 3 * * *` UTC) |
| Manual run | Actions → Daily Ingest Pipeline → Run workflow |

**Secrets (Chroma Cloud — Phase 5.3):** `CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE`. Local dev uses `data/chroma` (no secrets). `OPENAI_API_KEY` only if `EMBEDDING_PROVIDER=openai`.

### Chroma vector store (Phase 5.3)

| Mode | When | Setup |
|------|------|-------|
| **local** (default) | Development | Vectors persist under `data/chroma` |
| **cloud** | GitHub Actions / staging / prod | Set `VECTOR_STORE_MODE=cloud` + `CHROMA_*` secrets |
| **ephemeral** | Unit tests | `VECTOR_STORE_MODE=ephemeral` (in-memory) |

```bash
# Ingest to Chroma Cloud (after provisioning secrets at https://www.trychroma.com/)
export VECTOR_STORE_MODE=cloud
export CHROMA_API_KEY=...
export CHROMA_TENANT=...
export CHROMA_DATABASE=mf-faq-prod
FORCE_REINDEX=true python -m ingest run
python -m rag validate-index
```

## Tests

```bash
pytest tests/phase1 tests/phase2 -v

# Run Phase 5.2 after ingest (live scrape + index + validate + golden)
EMBEDDING_PROVIDER=hash FORCE_REINDEX=true python -m ingest run --summary /tmp/run-summary.json
EMBEDDING_PROVIDER=hash python -m rag validate-index
EMBEDDING_PROVIDER=hash python -m rag golden --output /tmp/golden-report.json
```

## AMC & schemes in scope

- HDFC Mid Cap Fund Direct Growth
- HDFC Equity Fund Direct Growth
- HDFC Focused Fund Direct Growth
- HDFC ELSS Tax Saver Fund Direct Plan Growth
- HDFC Large Cap Fund Direct Growth

## Documentation

- [RAG Architecture](docs/rag-architecture.md)
- [Chunking & Embedding Architecture](docs/chunking-embedding-architecture.md)
