"""PII(개인식별정보) 마스킹 — 정규식 기반."""

from __future__ import annotations

import re
from dataclasses import replace

from src.models.conversation import Message

_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 주민등록번호: 6자리-7자리 (가장 먼저)
    (re.compile(r"\d{6}\s*-\s*[1-4]\d{6}"), "[SSN]"),
    # 휴대폰: 010-1234-5678 등 (계좌보다 먼저 — 전화번호를 선점해야 함)
    (re.compile(r"(?<!\d)01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}"), "[PHONE]"),
    # 일반 전화: 02-123-4567, 031-1234-5678 ((?<!\d)로 숫자열 중간 오탐 방지)
    (re.compile(r"(?<!\d)0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}"), "[PHONE]"),
    # 계좌번호: 하이픈 구분, 마지막 그룹 4+ 자리 (전화 치환 후 잔여 매칭)
    (re.compile(r"\d{2,6}[-]\d{2,6}[-]\d{4,6}(?:[-]\d{1,4})?"), "[ACCOUNT]"),
    # 이메일
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL]"),
    # 한국 주소 패턴: ~시/도 ~구/군 ~로/길 숫자
    (
        re.compile(
            r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남"
            r"|전북|전남|경북|경남|제주)"
            r"(?:특별시|광역시|특별자치시|특별자치도|도|시)?"
            r"\s*\S+(?:시|군|구)"
            r"(?:\s*\S+(?:구|동|읍|면))?"
            r"\s*\S+(?:로|길)"
            r"(?:\s*\d+(?:-\d+)?)?"
        ),
        "[ADDRESS]",
    ),
]


def mask_text(text: str) -> str:
    """텍스트에서 PII 패턴을 플레이스홀더로 치환."""
    result = text
    for pattern, placeholder in _PATTERNS:
        result = pattern.sub(placeholder, result)
    return result


def mask_messages(messages: list[Message]) -> list[Message]:
    """메시지 리스트의 PII를 마스킹. 원본 불변, 새 리스트 반환."""
    return [replace(m, text=mask_text(m.text)) for m in messages]
