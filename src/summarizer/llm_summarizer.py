"""Claude Opus 기반 MicroSummary 추출."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from src.models.conversation import ConversationChunk
from src.models.summary import MicroSummary
from src.summarizer.base import LLMProvider, SummarizerBase
from src import config

logger = logging.getLogger(__name__)

load_dotenv(config.PROJECT_ROOT / ".env")

SYSTEM_PROMPT = """\
너는 뉴스 브리핑 에이전트를 위한 "Stable Profile Extractor"다.

목적: 건설/반도체/데이터센터/인프라 업계 임원이 매일 아침 받아볼 뉴스 브리핑을 개인화하기 위해,
이 사용자의 ChatGPT 대화에서 장기적으로 유지되는 업무 관심사/선호/패턴을 추출한다.

아래 대화를 분석하고, 반드시 아래 JSON 스키마대로만 응답하라. 설명이나 마크다운 없이 순수 JSON만 출력하라.

분석 규칙:
1. business_relevant: 이 대화가 산업/비즈니스/투자/정책/기술 관련인지 판단 (와인, 여행, 일상 등은 false)
2. business_relevant가 false면 signals는 빈 배열/빈 값으로 채우고, confidence를 0.1 이하로 설정
3. topics_top: 이 대화의 핵심 주제 3~5개 (한국어)
4. entities_top: 등장하는 기업/기관/인물명
5. preferred_format: 사용자가 선호하는 정보 형식 (표, 리스트, 상세설명, 비교분석 등 — 대화에서 추론)
6. avoid: 사용자가 싫어하거나 부정적으로 반응한 패턴 (있으면)
7. decision_lens: 사용자가 정보를 판단하는 관점 (투자, 리스크, 경쟁사 비교, 기술 트렌드 등)
8. keyword_matches: 아래 제공된 키워드 사전에서 이 대화에 실제로 등장하는 항목을 매칭
9. evidence_refs: 근거가 되는 메시지의 인덱스와 핵심 인용구 (120자 이내)

출력 JSON 스키마:
{
  "business_relevant": boolean,
  "relevance_category": "industry|finance|policy|technology|personal|other",
  "signals": {
    "topics_top": ["string"],
    "entities_top": ["string"],
    "preferred_format": ["string"],
    "avoid": ["string"],
    "decision_lens": ["string"]
  },
  "keyword_matches": {
    "industries": {"카테고리명": 출현횟수},
    "entities": ["매칭된 엔티티"],
    "themes": ["매칭된 테마"]
  },
  "confidence": 0.0~1.0,
  "evidence_refs": [{"msg_index": int, "quote": "string"}]
}
"""


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, model: str = "claude-opus-4-6"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text


class LLMSummarizer(SummarizerBase):
    """LLM 기반 micro-summary 추출."""

    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or ClaudeProvider()
        self._keywords = self._load_keywords()

    def _load_keywords(self) -> dict:
        if config.KEYWORDS_PATH.exists():
            with open(config.KEYWORDS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _build_user_prompt(self, chunk: ConversationChunk) -> str:
        conversation_text = chunk.full_text()

        keywords_section = json.dumps(self._keywords, ensure_ascii=False, indent=2)

        return (
            f"## 대화 제목 (참고용)\n"
            f"conversation_id: {chunk.conversation_id}\n\n"
            f"## 키워드 사전 (매칭 참고)\n"
            f"```json\n{keywords_section}\n```\n\n"
            f"## 대화 내용\n"
            f"{conversation_text}"
        )

    def summarize(self, chunk: ConversationChunk) -> MicroSummary:
        user_prompt = self._build_user_prompt(chunk)
        raw_response = self.provider.complete(SYSTEM_PROMPT, user_prompt)

        parsed = self._parse_response(raw_response, chunk)
        return parsed

    def _parse_response(self, raw: str, chunk: ConversationChunk) -> MicroSummary:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse LLM response for %s, returning empty summary",
                chunk.conversation_id,
            )
            return MicroSummary(
                conversation_id=chunk.conversation_id,
                title="",
                time_range=("", ""),
                confidence=0.0,
            )

        signals = data.get("signals", {})
        time_range = self._extract_time_range(chunk)

        return MicroSummary(
            conversation_id=chunk.conversation_id,
            title="",
            time_range=time_range,
            topics_top=signals.get("topics_top", []),
            entities_top=signals.get("entities_top", []),
            preferred_format=signals.get("preferred_format", []),
            avoid=signals.get("avoid", []),
            decision_lens=signals.get("decision_lens", []),
            confidence=data.get("confidence", 0.0),
            evidence_refs=data.get("evidence_refs", []),
            business_relevant=data.get("business_relevant", False),
            relevance_category=data.get("relevance_category", "other"),
            keyword_matches=data.get("keyword_matches", {}),
        )

    def _extract_time_range(self, chunk: ConversationChunk) -> tuple[str, str]:
        timestamps = [m.timestamp for m in chunk.messages if m.timestamp]
        if not timestamps:
            return ("", "")
        from datetime import datetime, timezone
        start = datetime.fromtimestamp(min(timestamps), tz=timezone.utc).isoformat()
        end = datetime.fromtimestamp(max(timestamps), tz=timezone.utc).isoformat()
        return (start, end)
