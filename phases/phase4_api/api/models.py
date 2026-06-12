from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    citation: str
    last_updated: Optional[str] = None
    intent: str
    formatted_answer: Optional[str] = None


class ThreadResponse(BaseModel):
    thread_id: str
    messages: list[dict[str, Any]]
    scheme_name: Optional[str] = None
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    status: str
    indexed_chunks: int
    collection: str
