from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from config.load_env import load_env
from phases.phase4_api.api.app import create_app


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(prog="api", description="Run Mutual Fund FAQ API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    app = create_app(args.project_root)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
