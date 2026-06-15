"""Load environment variables from .env and Streamlit secrets."""

from __future__ import annotations

import os
from pathlib import Path

_CHROMA_KEYS = (
    "CHROMA_API_KEY",
    "CHROMA_TENANT",
    "CHROMA_DATABASE",
    "CHROMA_HOST",
    "VECTOR_STORE_MODE",
    "EMBEDDING_PROVIDER",
    "GENERATION_PROVIDER",
    "OPENAI_API_KEY",
)


def bootstrap_env(project_root: Path | None = None) -> None:
    """Load .env, then Streamlit secrets for any keys not already in os.environ."""
    root = project_root or Path.cwd()

    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # type: ignore[assignment]

    env_path = root / ".env"
    if load_dotenv and env_path.is_file():
        load_dotenv(env_path, override=False)

    try:
        import streamlit as st

        for key in _CHROMA_KEYS:
            if os.getenv(key):
                continue
            if key in st.secrets:
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass


def chroma_env_summary() -> dict[str, str | None]:
    """Return non-secret Chroma connection info for UI diagnostics."""
    return {
        "tenant": os.getenv("CHROMA_TENANT"),
        "database": os.getenv("CHROMA_DATABASE"),
        "host": os.getenv("CHROMA_HOST", "api.trychroma.com"),
        "api_key_set": bool(os.getenv("CHROMA_API_KEY")),
    }
