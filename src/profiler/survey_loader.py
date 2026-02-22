"""설문 JSON 로드 모듈."""

from __future__ import annotations

import json
from pathlib import Path


def load_survey(path: Path) -> dict:
    """docs/father-profile-raw.json을 로드하여 반환.

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때.
        json.JSONDecodeError: JSON 파싱 실패 시.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
