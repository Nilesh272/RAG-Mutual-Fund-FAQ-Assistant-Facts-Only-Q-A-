from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from config.load_env import load_env
from ingest.pipeline import build_pipeline


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    load_env()
    parser = argparse.ArgumentParser(
        prog="ingest",
        description=(
            "Mutual Fund FAQ ingestion pipeline: scrape → parse → chunk → "
            "embed → Chroma Cloud upsert"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run full ingestion pipeline")
    run_parser.add_argument(
        "--summary",
        type=Path,
        help="Write JSON run summary to this path",
    )
    run_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: cwd)",
    )
    run_parser.add_argument("-v", "--verbose", action="store_true")

    scrape_parser = subparsers.add_parser(
        "scrape-only",
        help="Run scraping only (no downstream phases)",
    )
    scrape_parser.add_argument("--summary", type=Path)
    scrape_parser.add_argument("--project-root", type=Path, default=Path.cwd())
    scrape_parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    pipeline = build_pipeline(project_root=args.project_root)
    trigger = __import__("os").getenv("INGEST_TRIGGER", "manual")

    if args.command == "run":
        summary = pipeline.run(trigger=trigger)
    elif args.command == "scrape-only":
        summary = pipeline.run(trigger=trigger, scrape_only=True)
    else:
        parser.print_help()
        return 1

    if args.summary:
        summary.write_json(args.summary)

    print(
        f"Ingest complete: status={summary.status} "
        f"fetched={summary.urls_fetched} changed={summary.urls_changed} "
        f"failed={summary.urls_failed} skipped={summary.urls_skipped}"
    )

    return 0 if summary.status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
