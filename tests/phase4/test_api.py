from pathlib import Path

from fastapi.testclient import TestClient

from phases.phase4_api.api.app import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_health_endpoint() -> None:
    client = TestClient(create_app(PROJECT_ROOT))
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "indexed_chunks" in data


def test_chat_refusal_advisory() -> None:
    client = TestClient(create_app(PROJECT_ROOT))
    thread = client.post("/api/threads").json()
    response = client.post(
        "/api/chat",
        json={"thread_id": thread["thread_id"], "message": "Should I invest in HDFC Large Cap?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "ADVISORY"
    assert "amfi" in data["citation"].lower() or "sebi" in data["citation"].lower()


def test_create_and_get_thread() -> None:
    client = TestClient(create_app(PROJECT_ROOT))
    created = client.post("/api/threads").json()
    fetched = client.get(f"/api/threads/{created['thread_id']}").json()
    assert fetched["thread_id"] == created["thread_id"]
