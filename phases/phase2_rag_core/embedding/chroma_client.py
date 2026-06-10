from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb
    from chromadb.api import ClientAPI

    from phases.phase2_rag_core.embedding.models import VectorStoreConfig

logger = logging.getLogger(__name__)

VALID_MODES = frozenset({"local", "cloud", "ephemeral"})


def resolve_chroma_mode(config: VectorStoreConfig) -> str:
    """Resolve Chroma client mode from env vars and config."""
    explicit = os.getenv("VECTOR_STORE_MODE", "").strip().lower()
    if explicit:
        if explicit not in VALID_MODES:
            raise ValueError(
                f"VECTOR_STORE_MODE must be one of {sorted(VALID_MODES)}, got {explicit!r}"
            )
        return explicit
    if os.getenv("CHROMA_API_KEY"):
        return "cloud"
    return config.mode or "local"


def create_chroma_client(
    config: VectorStoreConfig,
    project_root: Path,
    *,
    mode: str | None = None,
) -> ClientAPI:
    """Create a Chroma client for local persistence, Cloud, or ephemeral (tests)."""
    import chromadb

    resolved_mode = mode or resolve_chroma_mode(config)
    if resolved_mode not in VALID_MODES:
        raise ValueError(f"Unsupported Chroma mode: {resolved_mode!r}")

    if resolved_mode == "cloud":
        api_key = os.getenv("CHROMA_API_KEY")
        if not api_key:
            raise ValueError("CHROMA_API_KEY is required when VECTOR_STORE_MODE=cloud")

        tenant = os.getenv("CHROMA_TENANT") or config.tenant or None
        database = os.getenv("CHROMA_DATABASE") or config.database or None
        cloud_host = os.getenv("CHROMA_HOST") or config.host or "api.trychroma.com"

        logger.info(
            "Connecting to Chroma Cloud (tenant=%s, database=%s, host=%s)",
            tenant or "<default>",
            database or "<default>",
            cloud_host,
        )
        return chromadb.CloudClient(
            tenant=tenant,
            database=database,
            api_key=api_key,
            cloud_host=cloud_host,
        )

    if resolved_mode == "ephemeral":
        logger.debug("Using Chroma EphemeralClient (in-memory)")
        return chromadb.EphemeralClient()

    persist_dir = project_root / config.persist_dir
    persist_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Using Chroma PersistentClient at %s", persist_dir)
    return chromadb.PersistentClient(path=str(persist_dir))
