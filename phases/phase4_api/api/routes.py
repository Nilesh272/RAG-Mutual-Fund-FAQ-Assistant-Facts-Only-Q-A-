from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from phases.phase4_api.api.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ThreadResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    status = request.app.state.orchestrator.health_status()
    return HealthResponse(**status)


@router.post("/threads", response_model=ThreadResponse)
def create_thread(request: Request) -> ThreadResponse:
    thread = request.app.state.sessions.create_thread()
    return ThreadResponse(
        thread_id=thread.thread_id,
        messages=[],
        scheme_name=thread.scheme_name,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
def get_thread(thread_id: str, request: Request) -> ThreadResponse:
    thread = request.app.state.sessions.get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadResponse(
        thread_id=thread.thread_id,
        messages=[m.to_dict() for m in thread.messages],
        scheme_name=thread.scheme_name,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


@router.delete("/threads/{thread_id}")
def delete_thread(thread_id: str, request: Request) -> dict:
    if not request.app.state.sessions.delete_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"deleted": True, "thread_id": thread_id}


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    sessions = request.app.state.sessions
    orchestrator = request.app.state.orchestrator

    if body.thread_id:
        thread = sessions.get_thread(body.thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")
    else:
        thread = sessions.create_thread()

    try:
        result = orchestrator.handle_message(thread, body.message.strip())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Chat pipeline error: {exc}") from exc

    return ChatResponse(
        thread_id=result.thread_id,
        answer=result.answer,
        citation=result.citation,
        last_updated=result.last_updated,
        intent=result.intent,
        formatted_answer=result.formatted_answer,
    )
