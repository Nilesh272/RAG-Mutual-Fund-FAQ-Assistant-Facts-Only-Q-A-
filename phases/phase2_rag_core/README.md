# Phase 2 — RAG Core

**Status:** Implemented (including Phase 5.3 Chroma vector store)

## Deliverables

| Component | Path | Description |
|-----------|------|-------------|
| Groww HTML parser | `parsing/` | HTML → `SectionBlock[]` |
| Chunking Service | `chunking/` | Structure-aware 400–600 token chunks |
| Embedding Service | `embedding/` | BGE (`bge-small-en-v1.5`) or hash/openai embedder + vector upsert |
| **Chroma vector store** | `embedding/vector_store.py`, `chroma_client.py` | Local persistent, Cloud, or ephemeral (Phase 5.3) |
| **Hybrid Retriever** | `retrieval/` | Dense + BM25 sparse + reranking (§6.3–6.5) |
| **Index validation** | `validation/ingest_validator.py` | Post-ingest checks (§8.2, §10.5) |
| **Golden query runner** | `validation/golden_runner.py` | Smoke tests (§8.3) |

## CLI (Phase 5.2 / 5.3)

```bash
# Validate indexed corpus (includes Chroma connectivity checks)
python -m rag validate-index

# Run golden query smoke tests
python -m rag golden

# Hybrid retrieve a query
python -m rag retrieve "expense ratio of HDFC Large Cap Fund"
```

## Configuration

- `config/chunking.yaml`
- `config/embedding.yaml` — `vector_store.mode`, `tenant`, `database`
- `config/retrieval.yaml`

## Environment variables

| Variable | Purpose |
|----------|---------|
| `EMBEDDING_PROVIDER` | `bge` (default), `hash` (tests), or `openai` |
| `VECTOR_STORE_MODE` | `local` (default), `cloud`, or `ephemeral` |
| `CHROMA_API_KEY` | Chroma Cloud API key (required for `cloud` mode) |
| `CHROMA_TENANT` | Chroma Cloud tenant ID |
| `CHROMA_DATABASE` | Chroma Cloud database name |
| `CHROMA_HOST` | Optional; defaults to `api.trychroma.com` |
| `OPENAI_API_KEY` | Only when `EMBEDDING_PROVIDER=openai` |
| `FORCE_REINDEX` | Re-index all pages when `true` |
| `RUN_GOLDEN_QUERIES` | Run golden tests after ingest (`true`/`false`) |

See [chunking-embedding-architecture.md](../../docs/chunking-embedding-architecture.md).
