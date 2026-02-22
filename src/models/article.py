from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Article:
    title: str
    url: str
    source_name: str
    source_group: str
    published_at: str
    language: str
    snippet: str
    categories: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source_name": self.source_name,
            "source_group": self.source_group,
            "published_at": self.published_at,
            "language": self.language,
            "snippet": self.snippet,
            "categories": self.categories,
            "relevance_score": self.relevance_score,
            "collected_at": self.collected_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Article:
        return cls(
            id=data.get("id", uuid.uuid4().hex[:12]),
            title=data["title"],
            url=data["url"],
            source_name=data["source_name"],
            source_group=data["source_group"],
            published_at=data["published_at"],
            language=data["language"],
            snippet=data.get("snippet", ""),
            categories=data.get("categories", []),
            relevance_score=data.get("relevance_score", 0.0),
            collected_at=data.get(
                "collected_at", datetime.now(timezone.utc).isoformat()
            ),
        )
