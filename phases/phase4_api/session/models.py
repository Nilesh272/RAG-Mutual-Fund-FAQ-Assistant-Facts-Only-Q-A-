from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

Role = Literal["user", "assistant"]


@dataclass
class ChatMessage:
    role: Role
    content: str
    timestamp: str
    citation: str | None = None
    intent: str | None = None

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "citation": self.citation,
            "intent": self.intent,
        }


@dataclass
class Thread:
    thread_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    scheme_name: str | None = None
    source_id: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(cls) -> Thread:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return cls(thread_id=str(uuid4()), created_at=now, updated_at=now)

    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)
        self.updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def recent_turns(self, limit: int = 3) -> list[ChatMessage]:
        return self.messages[-limit * 2 :] if self.messages else []
