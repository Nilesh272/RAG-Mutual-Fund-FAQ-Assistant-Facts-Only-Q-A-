from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from phases.phase4_api.api.routes import router
from phases.phase4_api.orchestrator import ChatOrchestrator
from phases.phase4_api.session.store import SessionStore


def create_app(project_root: Path | None = None) -> FastAPI:
    root = project_root or Path.cwd()
    app = FastAPI(
        title="Mutual Fund FAQ Assistant",
        description="Facts-only RAG assistant for HDFC mutual fund schemes.",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.project_root = root
    app.state.sessions = SessionStore()
    app.state.orchestrator = ChatOrchestrator.from_config_files(root)

    app.include_router(router, prefix="/api")

    return app
