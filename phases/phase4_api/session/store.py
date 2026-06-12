from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock

from phases.phase4_api.session.models import Thread


class SessionStore:
    """In-memory thread store with TTL (architecture §10.3)."""

    def __init__(self, ttl_hours: int = 24) -> None:
        self._threads: dict[str, Thread] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = Lock()

    def create_thread(self) -> Thread:
        thread = Thread.create()
        with self._lock:
            self._threads[thread.thread_id] = thread
        return thread

    def get_thread(self, thread_id: str) -> Thread | None:
        self._purge_expired()
        with self._lock:
            return self._threads.get(thread_id)

    def delete_thread(self, thread_id: str) -> bool:
        with self._lock:
            return self._threads.pop(thread_id, None) is not None

    def _purge_expired(self) -> None:
        cutoff = datetime.utcnow() - self._ttl
        with self._lock:
            expired = [
                tid
                for tid, thread in self._threads.items()
                if datetime.fromisoformat(thread.updated_at.replace("Z", "")) < cutoff
            ]
            for tid in expired:
                del self._threads[tid]
