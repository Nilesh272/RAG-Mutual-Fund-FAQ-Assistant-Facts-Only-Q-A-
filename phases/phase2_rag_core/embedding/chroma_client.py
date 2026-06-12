from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chromadb.api import ClientAPI

    from phases.phase2_rag_core.embedding.models import VectorStoreConfig

logger = logging.getLogger(__name__)

VALID_MODES = frozenset({"cloud", "ephemeral"})


def resolve_chroma_mode(config: VectorStoreConfig) -> str:
    """Resolve Chroma client mode from env vars and config."""
    explicit = os.getenv("VECTOR_STORE_MODE", "").strip().lower()
    if explicit:
        if explicit not in VALID_MODES:
            raise ValueError(
                f"VECTOR_STORE_MODE must be one of {sorted(VALID_MODES)}, got {explicit!r}"
            )
        return explicit
    return config.mode or "cloud"


def create_chroma_client(
    config: VectorStoreConfig,
    project_root: Path,
    *,
    mode: str | None = None,
) -> ClientAPI:
    """Create a Chroma Cloud client, or EphemeralClient for unit tests."""
    import chromadb

    _ = project_root  # Cloud-only; no local persist path
    resolved_mode = mode or resolve_chroma_mode(config)
    if resolved_mode not in VALID_MODES:
        raise ValueError(f"Unsupported Chroma mode: {resolved_mode!r}")

    if resolved_mode == "ephemeral":
        logger.debug("Using Chroma EphemeralClient (unit tests only)")
        return chromadb.EphemeralClient()

    api_key = os.getenv("CHROMA_API_KEY")
    if not api_key:
        raise ValueError(
            "CHROMA_API_KEY is required. Set CHROMA_API_KEY, CHROMA_TENANT, and "
            "CHROMA_DATABASE for Chroma Cloud, or VECTOR_STORE_MODE=ephemeral for tests."
        )

    tenant = os.getenv("CHROMA_TENANT") or config.tenant or None
    database = os.getenv("CHROMA_DATABASE") or config.database or None
    cloud_host = os.getenv("CHROMA_HOST") or config.host or "api.trychroma.com"

    if not tenant:
        raise ValueError("CHROMA_TENANT is required for Chroma Cloud")
    if not database:
        raise ValueError("CHROMA_DATABASE is required for Chroma Cloud")

    logger.info(
        "Connecting to Chroma Cloud (tenant=%s, database=%s, host=%s)",
        tenant,
        database,
        cloud_host,
    )
    return chromadb.CloudClient(
        tenant=tenant,
        database=database,
        api_key=api_key,
        cloud_host=cloud_host,
    )
