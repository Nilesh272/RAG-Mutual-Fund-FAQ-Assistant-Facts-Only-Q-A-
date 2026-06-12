# Phase 3 — Generation

**Status:** Implemented

## Deliverables

- Intent classifier (`intent/classifier.py`) — rule-based, architecture §6.2
- Constrained generation (`generation/`) — extractive (default) or OpenAI optional
- Response validator (`validation/response_validator.py`) — architecture §9
- Refusal handler (`refusal/handler.py`) — architecture §8
- Compliance link registry (`compliance/link_registry.py`)

## Configuration

`config/generation.yaml` and env `GENERATION_PROVIDER=extractive|openai`.
