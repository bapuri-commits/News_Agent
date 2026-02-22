from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Message:
    role: str
    text: str
    timestamp: float

    @property
    def timestamp_iso(self) -> str:
        if self.timestamp:
            return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()
        return ""

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "text": self.text,
            "timestamp": self.timestamp,
            "timestamp_iso": self.timestamp_iso,
        }


@dataclass
class Conversation:
    id: str
    title: str
    created_at: float
    updated_at: float
    messages: list[Message] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def char_count(self) -> int:
        return sum(len(m.text) for m in self.messages)

    @property
    def created_at_iso(self) -> str:
        if self.created_at:
            return datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()
        return ""

    @property
    def updated_at_iso(self) -> str:
        if self.updated_at:
            return datetime.fromtimestamp(self.updated_at, tz=timezone.utc).isoformat()
        return ""

    def to_meta(self) -> ConversationMeta:
        return ConversationMeta(
            id=self.id,
            title=self.title,
            created_at=self.created_at_iso,
            updated_at=self.updated_at_iso,
            message_count=self.message_count,
            char_count=self.char_count,
            tags=[],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at_iso,
            "updated_at": self.updated_at_iso,
            "message_count": self.message_count,
            "char_count": self.char_count,
            "messages": [m.to_dict() for m in self.messages],
        }


@dataclass
class ConversationChunk:
    conversation_id: str
    chunk_index: int
    total_chunks: int
    messages: list[Message] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        return sum(len(m.text) for m in self.messages)

    def full_text(self) -> str:
        parts = []
        for m in self.messages:
            parts.append(f"[{m.role}]: {m.text}")
        return "\n\n".join(parts)


@dataclass
class ConversationMeta:
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    char_count: int
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
            "char_count": self.char_count,
            "tags": self.tags,
        }
