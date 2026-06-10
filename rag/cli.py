from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from phases.phase2_rag_core.retrieval.context_assembler import ContextAssembler
from phases.phase2_rag_core.retrieval.hybrid_retriever import HybridRetriever
from phases.phase2_rag_core.validation.golden_runner import GoldenQueryRunner
from phases.phase2_rag_core.validation.ingest_validator import IngestValidator

logger = logging.getLogger(__name__)


def _project_root(value: Path | None) -> Path:
    return value or Path.cwd()


def _build_retriever(project_root: Path) -> HybridRetriever:
    return HybridRetriever.from_config_files(
        embedding_config_path=project_root / "config" / "embedding.yaml",
        retrieval_config_path=project_root / "config" / "retrieval.yaml",
        sources_path=project_root / "config" / "sources.yaml",
        project_root=project_root,
    )


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def cmd_validate(args: argparse.Namespace) -> int:
    root = _project_root(args.project_root)
    retriever = _build_retriever(root)
    validator = IngestValidator(
        retriever.embedder.vector_store,
        sources_path=root / "config" / "sources.yaml",
    )
    report = validator.validate(expected_min_chunks=args.min_chunks)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.passed else 1


def cmd_golden(args: argparse.Namespace) -> int:
    root = _project_root(args.project_root)
    retriever = _build_retriever(root)
    runner = GoldenQueryRunner(retriever)
    report = runner.run()
    if args.output:
        report.write_json(args.output)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.passed else 1


def cmd_retrieve(args: argparse.Namespace) -> int:
    root = _project_root(args.project_root)
    retriever = _build_retriever(root)
    hits = retriever.retrieve(args.query)
    assembler = ContextAssembler()

    output = {
        "query": args.query,
        "hits": [
            {
                "chunk_id": hit.chunk_id,
                "section_key": hit.section_key,
                "scheme_name": hit.scheme_name,
                "source_url": hit.source_url,
                "final_score": round(hit.final_score, 4),
                "dense_score": round(hit.dense_score, 4),
                "sparse_score": round(hit.sparse_score, 4),
            }
            for hit in hits
        ],
        "context": assembler.assemble(hits),
        "citation": assembler.primary_source_url(hits),
    }
    print(json.dumps(output, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rag",
        description="RAG retrieval and validation CLI (Phase 5.2)",
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("-v", "--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate-index",
        help="Run post-ingest index validation (chunking doc §8.2)",
    )
    validate_parser.add_argument("--min-chunks", type=int, default=1)
    validate_parser.set_defaults(func=cmd_validate)

    golden_parser = subparsers.add_parser(
        "golden",
        help="Run golden query smoke tests (chunking doc §8.3)",
    )
    golden_parser.add_argument("--output", type=Path, help="Write JSON report to path")
    golden_parser.set_defaults(func=cmd_golden)

    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="Hybrid retrieve for a query",
    )
    retrieve_parser.add_argument("query", type=str)
    retrieve_parser.set_defaults(func=cmd_retrieve)

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
