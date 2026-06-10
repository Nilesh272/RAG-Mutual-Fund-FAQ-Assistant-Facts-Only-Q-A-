from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from phases.phase1_corpus.scraping.models import ScrapeResult
from phases.phase1_corpus.scraping.scraper import ScrapingService
from phases.phase2_rag_core.chunking.chunker import ChunkingService
from phases.phase2_rag_core.embedding.embedder import EmbeddingService
from phases.phase2_rag_core.parsing.groww_parser import GrowwParser
from phases.phase2_rag_core.retrieval.hybrid_retriever import HybridRetriever
from phases.phase2_rag_core.validation.golden_runner import GoldenQueryRunner
from phases.phase2_rag_core.validation.ingest_validator import IngestValidator

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

RunStatus = Literal["success", "partial", "failed"]


@dataclass
class RunSummary:
    run_id: str
    trigger: str
    started_at: str
    completed_at: Optional[str] = None
    urls_fetched: int = 0
    urls_changed: int = 0
    urls_failed: int = 0
    urls_skipped: int = 0
    chunks_created: int = 0
    embeddings_upserted: int = 0
    status: RunStatus = "success"
    workflow_run_id: Optional[str] = None
    scrape_results: list[dict] = field(default_factory=list)
    golden_query_results: list[dict] = field(default_factory=list)
    validation_report: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "trigger": self.trigger,
            "workflow_run_id": self.workflow_run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "urls_fetched": self.urls_fetched,
            "urls_changed": self.urls_changed,
            "urls_failed": self.urls_failed,
            "urls_skipped": self.urls_skipped,
            "chunks_created": self.chunks_created,
            "embeddings_upserted": self.embeddings_upserted,
            "status": self.status,
            "scrape_results": self.scrape_results,
            "golden_query_results": self.golden_query_results,
            "validation_report": self.validation_report,
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


def _now_ist_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _new_run_id() -> str:
    stamp = datetime.now(IST).strftime("%Y-%m-%d-%H%M%S")
    return f"ingest-{stamp}"


class IngestPipeline:
    """Orchestrates Phase 1 scrape and Phase 2 parse/chunk/embed/index."""

    def __init__(
        self,
        scraper: ScrapingService,
        parser: GrowwParser,
        chunker: ChunkingService,
        embedder: EmbeddingService,
        retriever: HybridRetriever,
        project_root: Path,
    ) -> None:
        self.scraper = scraper
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.retriever = retriever
        self.project_root = project_root
        self.force_reindex = os.getenv("FORCE_REINDEX", "false").lower() == "true"
        self.run_golden_queries = os.getenv("RUN_GOLDEN_QUERIES", "true").lower() == "true"

    def run(
        self,
        *,
        trigger: str = "manual",
        workflow_run_id: Optional[str] = None,
        scrape_only: bool = False,
    ) -> RunSummary:
        summary = RunSummary(
            run_id=_new_run_id(),
            trigger=trigger,
            started_at=_now_ist_iso(),
            workflow_run_id=workflow_run_id or os.getenv("GITHUB_RUN_ID"),
        )

        logger.info("Starting ingest run %s (force_reindex=%s)", summary.run_id, self.force_reindex)

        scrape_results = self.scraper.start_scrape()
        summary.scrape_results = [r.to_summary_dict() for r in scrape_results]

        for result in scrape_results:
            self._process_scrape_result(result, summary, scrape_only=scrape_only)

        if not scrape_only and summary.embeddings_upserted > 0:
            summary.validation_report = self._run_index_validation().to_dict()
            if self.run_golden_queries:
                summary.golden_query_results = self._run_golden_queries()

        summary.completed_at = _now_ist_iso()
        summary.status = self._resolve_status(summary)
        logger.info(
            "Ingest run %s finished: status=%s fetched=%s changed=%s failed=%s chunks=%s embeddings=%s",
            summary.run_id,
            summary.status,
            summary.urls_fetched,
            summary.urls_changed,
            summary.urls_failed,
            summary.chunks_created,
            summary.embeddings_upserted,
        )
        return summary

    def _process_scrape_result(
        self,
        result: ScrapeResult,
        summary: RunSummary,
        *,
        scrape_only: bool,
    ) -> None:
        if result.status != "success":
            summary.urls_failed += 1
            return

        summary.urls_fetched += 1
        assert result.content_hash is not None

        if not result.changed and not self.force_reindex:
            summary.urls_skipped += 1
            logger.info("No content change for %s — skipping downstream", result.source_id)
            return

        summary.urls_changed += 1

        if scrape_only:
            return

        chunk_count, embed_count, indexed = self._run_downstream_phases(result)
        summary.chunks_created += chunk_count
        summary.embeddings_upserted += embed_count
        if not indexed:
            summary.urls_failed += 1
            return

        self.scraper.registry.update_source_state(
            result.source_id,
            content_hash=result.content_hash,
            last_fetched=result.fetched_at,
            http_status=result.http_status or 0,
        )

    def _run_downstream_phases(self, result: ScrapeResult) -> tuple[int, int, bool]:
        scheme_meta = self._scheme_meta(result.source_id)
        if scheme_meta is None:
            logger.error("Unknown source_id in registry: %s", result.source_id)
            return 0, 0, False

        sections = self.parser.parse(result, scheme_meta)
        if not sections:
            logger.error("No sections parsed for %s", result.source_id)
            return 0, 0, False

        chunks = self.chunker.chunk_page(sections)
        if not chunks:
            logger.error("No chunks produced for %s", result.source_id)
            return 0, 0, False

        records = self.embedder.embed_chunks(chunks)
        upsert_result = self.embedder.upsert(records, result.source_id)
        if not upsert_result.verified:
            logger.error(
                "Vector upsert failed for %s: %s",
                result.source_id,
                upsert_result.error,
            )
            return len(chunks), 0, False

        logger.info(
            "Indexed %s: sections=%s chunks=%s deleted=%s upserted=%s",
            result.source_id,
            len(sections),
            len(chunks),
            upsert_result.deleted_count,
            upsert_result.upserted_count,
        )
        return len(chunks), upsert_result.upserted_count, True

    def _scheme_meta(self, source_id: str) -> Optional[dict]:
        entry = self.scraper.registry.get_by_id(source_id)
        if entry is None:
            return None
        return {
            "scheme_name": entry.scheme_name,
            "scheme_category": entry.scheme_category,
        }

    def _run_index_validation(self) -> object:
        validator = IngestValidator(
            self.embedder.vector_store,
            sources_path=self.project_root / "config" / "sources.yaml",
        )
        return validator.validate()

    def _run_golden_queries(self) -> list[dict]:
        runner = GoldenQueryRunner(self.retriever)
        report = runner.run()
        return report.to_dict()["results"]

    @staticmethod
    def _resolve_status(summary: RunSummary) -> RunStatus:
        if summary.urls_failed == 0:
            return "success"
        if summary.urls_fetched > 0:
            return "partial"
        return "failed"


def build_pipeline(project_root: Optional[Path] = None) -> IngestPipeline:
    root = project_root or Path.cwd()
    scraper = ScrapingService.from_config_files(
        sources_path=root / "config" / "sources.yaml",
        scraping_config_path=root / "config" / "scraping.yaml",
        project_root=root,
    )
    parser = GrowwParser()
    chunker = ChunkingService.from_config_file(root / "config" / "chunking.yaml")
    embedder = EmbeddingService.from_config_files(
        embedding_config_path=root / "config" / "embedding.yaml",
        project_root=root,
    )
    retriever = HybridRetriever.from_config_files(
        embedding_config_path=root / "config" / "embedding.yaml",
        retrieval_config_path=root / "config" / "retrieval.yaml",
        sources_path=root / "config" / "sources.yaml",
        project_root=root,
    )
    return IngestPipeline(
        scraper=scraper,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        retriever=retriever,
        project_root=root,
    )
