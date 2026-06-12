# Phase 6 — Eval & Hardening

**Status:** Implemented

## Deliverables

- Evaluation dataset (`dataset/eval_queries.yaml`) — 30 labeled prompts
- Eval runner (`runner.py`)
- CLI: `python -m rag eval`
- Tests in `tests/phase3`, `tests/phase4`, `tests/phase6`

## Run evaluation

```bash
python -m rag eval --output /tmp/eval-report.json
```
