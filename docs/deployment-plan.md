# Deployment Plan — Mutual Fund FAQ Assistant

## 1. Document Purpose

This document describes how to deploy the Mutual Fund FAQ Assistant to production using:

| Component | Platform | Role |
|-----------|----------|------|
| **Scheduler / ingest** | GitHub Actions | Daily scrape → chunk → embed → Chroma Cloud upsert |
| **Backend (API)** | Render | FastAPI chat orchestrator + RAG retrieval |
| **Frontend (UI)** | Vercel | Next.js chat interface |
| **Vector store** | Chroma Cloud | Shared index used by ingest and API |

The split keeps heavy offline work (scraping, embedding) off the API server, while the API only loads the BGE model for query embedding at request time.

---

## 2. Target Architecture

```mermaid
flowchart LR
    subgraph Vercel["Vercel"]
        UI[Next.js UI<br/>phase5_ui/web]
    end

    subgraph Render["Render"]
        API[FastAPI<br/>python -m api]
    end

    subgraph GHA["GitHub Actions"]
        INGEST[Daily Ingest<br/>daily-ingest.yml]
    end

    subgraph Chroma["Chroma Cloud"]
        VDB[(mf_faq_hdfc_groww)]
    end

    subgraph External["External"]
        GROWW[Groww scheme pages]
    end

    UI -->|"/api/* rewrite"| API
    API -->|query embed + retrieve| VDB
    INGEST -->|scrape| GROWW
    INGEST -->|upsert chunks| VDB
```

**Request path (chat):** Browser → Vercel → Render API → BGE query embed → Chroma retrieve → extractive generation → JSON response.

**Offline path (ingest):** GitHub Actions cron → scrape 5 Groww URLs → parse/chunk → BGE document embed → Chroma upsert.

---

## 3. Prerequisites

Before deploying, ensure you have:

1. **GitHub repository** with this codebase pushed to `main` (or your production branch).
2. **Chroma Cloud** account and a database (e.g. `testDB`) with API credentials from [trychroma.com](https://www.trychroma.com/).
3. **Render** account — [render.com](https://render.com).
4. **Vercel** account — [vercel.com](https://vercel.com).
5. **Initial index populated** — either run `python -m ingest run` locally once, or trigger the GitHub Actions workflow manually after secrets are configured.

---

## 4. Shared Configuration (Chroma Cloud)

Both GitHub Actions (ingest) and Render (API) must point at the **same** Chroma Cloud database and collection.

| Variable | Example | Used by |
|----------|---------|---------|
| `CHROMA_API_KEY` | `ck-...` | Ingest + API |
| `CHROMA_TENANT` | tenant UUID | Ingest + API |
| `CHROMA_DATABASE` | `testDB` | Ingest + API |
| `CHROMA_HOST` | `api.trychroma.com` | Ingest + API (default) |
| `VECTOR_STORE_MODE` | `cloud` | Ingest + API |

Store these as secrets in GitHub and environment variables on Render. **Never commit real values to the repo.**

---

## 5. Scheduler — GitHub Actions

### 5.1 What already exists

The workflow [`.github/workflows/daily-ingest.yml`](../.github/workflows/daily-ingest.yml) is production-ready:

- **Schedule:** daily at **9:15 AM IST** (`cron: '45 3 * * *'` UTC)
- **Manual trigger:** `workflow_dispatch` with optional `force_reindex`
- **Pipeline:** scrape → parse → chunk → BGE embed → Chroma upsert → `validate-index`
- **Artifacts:** run summary (30 days), raw HTML snapshots (7 days)
- **Caching:** BGE model (`.cache/huggingface`) and scrape metadata (`data/metadata`)

### 5.2 Repository secrets

In **GitHub → Settings → Secrets and variables → Actions**, add:

| Secret | Required |
|--------|----------|
| `CHROMA_API_KEY` | Yes |
| `CHROMA_TENANT` | Yes |
| `CHROMA_DATABASE` | Yes |

No Render or Vercel secrets are needed for the scheduler.

### 5.3 First run & verification

1. Push the repo to GitHub.
2. Go to **Actions → Daily Ingest Pipeline → Run workflow**.
3. Confirm the job completes and `validate-index` passes.
4. Check artifacts for `/tmp/run-summary.json` if you need run-level diagnostics.

### 5.4 Operational notes

| Topic | Detail |
|-------|--------|
| **Concurrency** | `concurrency.group: ingest-pipeline` — only one ingest at a time |
| **Timeout** | 45 minutes (sufficient for 5 URLs + BGE on `ubuntu-latest`) |
| **Python version** | 3.11 on CI (local dev may use 3.9+) |
| **Force reindex** | Use `workflow_dispatch` + `force_reindex: true` after embedding model or chunking changes |
| **Collection reset** | Set `CHROMA_RESET_COLLECTION=true` as a workflow `env` override only when changing embedding dimensions |

---

## 6. Backend — Render

### 6.1 Service type

Create a **Web Service** (not a cron job — ingestion stays on GitHub Actions).

| Setting | Value |
|---------|-------|
| **Repository** | This GitHub repo |
| **Root directory** | *(repo root — leave blank)* |
| **Runtime** | Python 3 |
| **Build command** | `pip install -r requirements-api.txt` |
| **Start command** | `python -m api --host 0.0.0.0 --port $PORT` |

Render injects `$PORT`; the API must bind to `0.0.0.0`, not `127.0.0.1`.

### 6.2 Instance sizing

The API loads **BAAI/bge-small-en-v1.5** locally for query embedding (`EMBEDDING_PROVIDER=bge`). Recommended:

| Plan | RAM | Notes |
|------|-----|-------|
| **Minimum** | 512 MB | May OOM on cold start; test carefully |
| **Recommended** | 1 GB+ | Stable BGE + FastAPI + Chroma client |

Free-tier services **spin down after inactivity** (~15 s cold start + ~10 s first BGE load). Use a paid instance or an external uptime ping if you need consistent latency.

### 6.3 Environment variables (Render)

| Variable | Value | Required |
|----------|-------|----------|
| `CHROMA_API_KEY` | Chroma Cloud key | Yes |
| `CHROMA_TENANT` | Tenant ID | Yes |
| `CHROMA_DATABASE` | e.g. `testDB` | Yes |
| `CHROMA_HOST` | `api.trychroma.com` | Yes |
| `VECTOR_STORE_MODE` | `cloud` | Yes |
| `EMBEDDING_PROVIDER` | `bge` | Yes (default) |
| `GENERATION_PROVIDER` | `extractive` | Yes (default; no OpenAI key needed) |
| `HF_HOME` | `/opt/render/project/src/.cache/huggingface` | Recommended |
| `OPENAI_API_KEY` | — | Only if `GENERATION_PROVIDER=openai` |

`HF_HOME` keeps the embedding model cache inside the Render filesystem across restarts on the same instance (still re-downloads after redeploys unless you add a persistent disk).

### 6.4 Health check

Configure Render health check path:

```
/api/health
```

Expected response:

```json
{"status":"ok","indexed_chunks":30,"collection":"mf_faq_hdfc_groww"}
```

`indexed_chunks` should be ≥ 1 after a successful ingest.

### 6.5 API surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness + index status |
| `POST` | `/api/chat` | Send a message (creates thread if omitted) |
| `POST` | `/api/threads` | Create empty thread |
| `GET` | `/api/threads/{id}` | Fetch thread history |
| `DELETE` | `/api/threads/{id}` | Delete thread |
| `GET` | `/docs` | OpenAPI (Swagger) UI |

CORS is already open (`allow_origins=["*"]`) in `phases/phase4_api/api/app.py`, so direct browser calls to Render work if needed. In production, traffic should go through Vercel rewrites.

### 6.6 Known limitations on Render

| Limitation | Impact | Mitigation (future) |
|------------|--------|---------------------|
| **In-memory sessions** | Threads lost on restart or scale-out | Redis / DB-backed `SessionStore` |
| **Cold starts** | First chat after idle is slow | Paid plan, keep-warm ping, or `EMBEDDING_PROVIDER=openai` |
| **Single instance** | No horizontal scaling without shared sessions | External session store |
| **No ingest on Render** | Index only updates via GitHub Actions | By design |

---

## 7. Frontend — Vercel

### 7.1 Project setup

| Setting | Value |
|---------|-------|
| **Framework preset** | Next.js |
| **Root directory** | `phases/phase5_ui/web` |
| **Build command** | `npm run build` (default) |
| **Output** | Next.js default |
| **Install command** | `npm install` (default) |

Import the GitHub repo in Vercel and set the root directory to `phases/phase5_ui/web` — do not deploy from the monorepo root.

### 7.2 Environment variables (Vercel)

| Variable | Value | Environment |
|----------|-------|-------------|
| `API_URL` | `https://<your-render-service>.onrender.com` | Production (and Preview if previews should hit a staging API) |

`API_URL` is read at **build time** by [`next.config.ts`](../phases/phase5_ui/web/next.config.ts) for rewrite rules:

```ts
// Browser calls /api/chat → proxied to ${API_URL}/api/chat
destination: `${apiUrl}/api/:path*`
```

After changing `API_URL`, **redeploy** the Vercel project so rewrites pick up the new backend URL.

### 7.3 Domains

| Environment | Typical URL |
|-------------|-------------|
| Production | `https://<project>.vercel.app` or custom domain |
| Preview | Per-PR preview URLs (optional separate `API_URL` for staging API) |

### 7.4 Local vs production

| | Local | Production |
|---|-------|------------|
| UI | `http://localhost:3000` | Vercel URL |
| API | `http://127.0.0.1:8000` | Render URL |
| Proxy | `API_URL` defaults to localhost | `API_URL` = Render HTTPS URL |

---

## 8. Deployment Sequence

Execute in this order to avoid a UI pointing at an empty or missing index:

```mermaid
flowchart TD
    A[1. Create Chroma Cloud DB] --> B[2. Add GitHub Actions secrets]
    B --> C[3. Run ingest workflow manually]
    C --> D{validate-index OK?}
    D -->|No| C
    D -->|Yes| E[4. Deploy Render API]
    E --> F[5. Verify /api/health]
    F --> G[6. Deploy Vercel UI with API_URL]
    G --> H[7. Smoke-test chat on Vercel URL]
    H --> I[8. Enable daily schedule / monitor Actions]
```

### Smoke-test checklist

- [ ] `GET https://<render>/api/health` → `status: ok`, `indexed_chunks > 0`
- [ ] `POST https://<render>/api/chat` with `{"message":"What is the expense ratio of HDFC Mid Cap Fund?"}` → answer + citation
- [ ] Open Vercel URL → disclaimer banner, health indicator green
- [ ] Send a message in the UI → response with Groww citation link
- [ ] GitHub Actions ingest run succeeds on schedule (or manual trigger)

---

## 9. Secrets & Environment Matrix

| Variable | GitHub Actions | Render | Vercel |
|----------|:--------------:|:------:|:------:|
| `CHROMA_API_KEY` | Secret | Env | — |
| `CHROMA_TENANT` | Secret | Env | — |
| `CHROMA_DATABASE` | Secret | Env | — |
| `CHROMA_HOST` | Default in workflow | Env | — |
| `EMBEDDING_PROVIDER` | `bge` in workflow | Env | — |
| `GENERATION_PROVIDER` | — | Env | — |
| `OPENAI_API_KEY` | — | Optional | — |
| `HF_HOME` | Workflow env | Env | — |
| `API_URL` | — | — | Env |
| `FORCE_REINDEX` | Workflow input | — | — |

---

## 10. Monitoring & Operations

### 10.1 GitHub Actions (ingest)

- **Success signal:** green workflow run + `validate-index` step
- **Failure alerts:** enable GitHub email notifications or a Slack webhook on workflow failure
- **Artifacts:** `ingest-run-summary-<run_id>` for chunk counts and per-URL status

### 10.2 Render (API)

- Use Render dashboard metrics (CPU, memory, restarts)
- Alert on health check failures
- Watch for OOM kills when using BGE on small instances

### 10.3 Vercel (UI)

- Deployment logs for build failures (often missing `API_URL` or wrong root directory)
- Vercel Analytics (optional) for traffic

### 10.4 Data freshness

Answers reflect the last successful ingest. The UI shows **last updated from sources** per response. If Groww pages change mid-day, users see stale data until the next **9:15 AM IST** run (or a manual `workflow_dispatch`).

---

## 11. Optional Enhancements (Post-v1)

| Enhancement | Platform | Benefit |
|-------------|----------|---------|
| Staging Render service + Vercel preview `API_URL` | Render + Vercel | Safe pre-prod testing |
| Render persistent disk for `HF_HOME` | Render | Faster cold starts after deploy |
| `GENERATION_PROVIDER=openai` | Render | Richer answers (adds cost + key management) |
| Redis for `SessionStore` | Render + Upstash | Durable threads across restarts |
| Custom domain + HTTPS | Vercel + Render | Branded URLs |
| Branch protection + required Actions check | GitHub | Block merges if ingest tests fail |

---

## 12. Rollback

| Layer | Rollback |
|-------|----------|
| **UI** | Redeploy previous Vercel deployment from dashboard |
| **API** | Roll back to previous Render deploy |
| **Index** | Re-run ingest with `force_reindex: false`; for bad upserts, use `CHROMA_RESET_COLLECTION=true` once then re-ingest |
| **Scheduler** | Revert workflow file on `main`; disable schedule in workflow YAML if needed |

---

## 13. Related Documentation

- [RAG Architecture](./rag-architecture.md) — system design, scheduler spec (§5.1), Chroma model (§6)
- [Chunking & Embedding Architecture](./chunking-embedding-architecture.md) — index shape and embedding config
- [README](../README.md) — local setup and CLI commands
- [Phase 5 UI README](../phases/phase5_ui/README.md) — frontend build notes
