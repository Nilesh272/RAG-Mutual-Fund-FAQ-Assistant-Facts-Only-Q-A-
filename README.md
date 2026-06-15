# Mutual Fund FAQ Assistant (Facts-Only Q&A)

A RAG-based facts-only FAQ assistant for HDFC mutual fund schemes, using Groww scheme pages as the data source.

**Disclaimer:** Facts-only. No investment advice.

## Project structure

```
├── .github/workflows/daily-ingest.yml   # Scheduler (9:15 AM IST daily)
├── api/                                 # FastAPI server (`python -m api`)
├── config/                              # Sources, embedding, generation, compliance
├── phases/
│   ├── phase1_corpus/                   # ✅ Scheduler + Scraping
│   ├── phase2_rag_core/                 # ✅ Parse + Chunk + Embed + Retrieval
│   ├── phase3_generation/               # ✅ Intent + Generation + Validator
│   ├── phase4_api/                      # ✅ Chat API + Sessions
│   ├── phase5_ui/web/                   # ✅ Next.js dark-theme chat UI
│   └── phase6_eval/                     # ✅ Eval dataset + runner
├── ingest/                              # Ingest CLI
├── rag/                                 # Retrieval / validation / eval CLI
└── docs/                                # Architecture documents
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt

cp .env.example .env   # add Chroma Cloud credentials
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `CHROMA_API_KEY` | Yes | Chroma Cloud API key |
| `CHROMA_TENANT` | Yes | Chroma Cloud tenant ID |
| `CHROMA_DATABASE` | Yes | e.g. `testDB` |
| `OPENAI_API_KEY` | Optional | Only if `GENERATION_PROVIDER=openai` |

## Run the chat app (Phases 4 + 5)

```bash
# Ensure index is populated first
python -m ingest run

# Terminal 1 — FastAPI backend
source .venv/bin/activate
python -m api --host 127.0.0.1 --port 8000

# Terminal 2 — Next.js dark-theme UI
cd phases/phase5_ui/web
npm install
npm run dev
```

Open **http://localhost:3000** (frontend). API runs on **http://127.0.0.1:8000**.

## Ingestion pipeline

```bash
python -m ingest run
python -m rag validate-index
python -m rag golden
python -m rag eval
```

## Scheduler (GitHub Actions)

Daily at **9:15 AM IST** — scrape → chunk → embed → Chroma Cloud upsert.

**Secrets:** `CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE`

## Tests

```bash
pytest tests/ -v
```

## AMC & schemes in scope

- HDFC Mid Cap Fund Direct Growth
- HDFC Equity Fund Direct Growth
- HDFC Focused Fund Direct Growth
- HDFC ELSS Tax Saver Fund Direct Plan Growth
- HDFC Large Cap Fund Direct Growth

## Known limitations

- HTML-only Groww pages (no PDF KIM/SID in v1)
- Five HDFC schemes only; other AMCs refused
- Answers may lag page updates between daily 9:15 AM IST ingest runs
- Extractive generation by default; set `GENERATION_PROVIDER=openai` for LLM answers

## Documentation

- [Deployment Plan](docs/deployment-plan.md)
- [RAG Architecture](docs/rag-architecture.md)
- [Chunking & Embedding Architecture](docs/chunking-embedding-architecture.md)
