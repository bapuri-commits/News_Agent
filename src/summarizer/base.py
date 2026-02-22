"""Summarizer 인터페이스 정의."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.conversation import ConversationChunk
from src.models.summary import MicroSummary


class LLMProvider(ABC):
    """LLM API 호출 추상 인터페이스."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """시스템 프롬프트 + 사용자 프롬프트를 보내고 응답 텍스트를 반환."""
        ...


class SummarizerBase(ABC):
    """대화 chunk에서 MicroSummary를 추출하는 추상 인터페이스."""

    @abstractmethod
    def summarize(self, chunk: ConversationChunk) -> MicroSummary:
        ...
