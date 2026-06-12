"""Load variables from a .env file in the project root (if present)."""

from __future__ import annotations

from pathlib import Path


def load_env(project_root: Path | None = None) -> None:
    """Load .env from project root without overriding existing environment variables."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    root = project_root or Path.cwd()
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
