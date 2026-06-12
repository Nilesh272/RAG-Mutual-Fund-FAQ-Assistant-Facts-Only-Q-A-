# Phase 5 — UI (Next.js)

**Status:** Implemented

## Stack

- **Next.js 16** (App Router, TypeScript)
- **Tailwind CSS v4** — dark theme (zinc + emerald accent)
- **Component-based** chat UI in `web/src/components/`

## Components

| Component | Purpose |
|-----------|---------|
| `Header` | Title, API health / index status |
| `DisclaimerBanner` | "Facts-only. No investment advice." |
| `Sidebar` | Scheme list, new conversation (desktop) |
| `MobileThreadBar` | New chat on mobile |
| `WelcomePanel` | Intro copy |
| `ExampleQuestions` | Three starter prompts |
| `ChatMessageList` | Scrollable message thread |
| `ChatMessage` | User / assistant bubbles with linkified citations |
| `ChatInput` | Message form |
| `LoadingIndicator` | Retrieval + generation state |
| `ErrorAlert` | API / network errors |
| `ChatApp` | Root client layout |

## Run locally

**Terminal 1 — FastAPI backend (port 8000):**

```bash
source .venv/bin/activate
python -m api --host 127.0.0.1 --port 8000
```

**Terminal 2 — Next.js frontend (port 3000):**

```bash
cd phases/phase5_ui/web
cp .env.local.example .env.local   # optional; defaults to localhost:8000
npm install
npm run dev
```

Open **http://localhost:3000**. API calls are proxied to the backend via `next.config.ts` rewrites.

## Build for production

```bash
cd phases/phase5_ui/web
npm run build
npm start
```

Set `API_URL` to your deployed FastAPI host when not using localhost.
