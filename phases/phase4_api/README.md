# Phase 4 — API & Threads

**Status:** Implemented

## Deliverables

- FastAPI app (`api/app.py`, `api/routes.py`)
- Chat orchestrator (`orchestrator.py`)
- In-memory session store with 24h TTL (`session/store.py`)
- PII scanner on input (`pii_scanner.py`)

## Run

```bash
pip install -r requirements-api.txt
python -m api --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Index status |
| `POST` | `/api/threads` | Create thread |
| `GET` | `/api/threads/{id}` | Thread history |
| `DELETE` | `/api/threads/{id}` | Delete thread |
| `POST` | `/api/chat` | Send message |
