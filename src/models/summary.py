from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MicroSummary:
    conversation_id: str
    title: str
    time_range: tuple[str, str]
    topics_top: list[str] = field(default_factory=list)
    entities_top: list[str] = field(default_factory=list)
    preferred_format: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    decision_lens: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence_refs: list[dict] = field(default_factory=list)
    business_relevant: bool = False
    relevance_category: str = "other"
    keyword_matches: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "time_range": {"start": self.time_range[0], "end": self.time_range[1]},
            "business_relevant": self.business_relevant,
            "relevance_category": self.relevance_category,
            "signals": {
                "topics_top": self.topics_top,
                "entities_top": self.entities_top,
                "preferred_format": self.preferred_format,
                "avoid": self.avoid,
                "decision_lens": self.decision_lens,
                "confidence": self.confidence,
            },
            "keyword_matches": self.keyword_matches,
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class StableProfile:
    user_intent: str = ""
    top_priorities: list[dict] = field(default_factory=list)
    must_include_triggers: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    preferred_format: dict = field(default_factory=dict)
    source_preferences: dict = field(default_factory=dict)
    schedule: dict = field(default_factory=dict)
    industries: dict = field(default_factory=dict)
    themes: dict = field(default_factory=dict)
    companies: dict = field(default_factory=dict)
    regions: list[str] = field(default_factory=list)
    sk_ecoplant_lens: list[str] = field(default_factory=list)
    conversation_hint_policy: dict = field(default_factory=lambda: {
        "lookback_days": 7,
        "max_weight_percent": 10,
    })
    risk_guardrails: dict = field(default_factory=lambda: {
        "diversity_enforced": True,
        "require_links": True,
        "separate_fact_inference": True,
    })
    open_questions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "user_intent": self.user_intent,
            "top_priorities": self.top_priorities,
            "must_include_triggers": self.must_include_triggers,
            "avoid": self.avoid,
            "preferred_format": self.preferred_format,
            "source_preferences": self.source_preferences,
            "schedule": self.schedule,
            "industries": self.industries,
            "themes": self.themes,
            "companies": self.companies,
            "regions": self.regions,
            "sk_ecoplant_lens": self.sk_ecoplant_lens,
            "conversation_hint_policy": self.conversation_hint_policy,
            "risk_guardrails": self.risk_guardrails,
            "open_questions": self.open_questions,
            "metadata": {
                **self.metadata,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
