"""ZIP 파일을 열고 conversations.json을 탐지/추출한다."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


CONVERSATIONS_FILENAME = "conversations.json"


def discover_conversations_file(zip_path: Path) -> str | None:
    """ZIP 내부에서 conversations.json 경로를 찾는다."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(CONVERSATIONS_FILENAME):
                return name
    return None


def extract_conversations_json(zip_path: Path) -> list[dict]:
    """ZIP에서 conversations.json을 읽어 파이썬 리스트로 반환한다."""
    target = discover_conversations_file(zip_path)
    if target is None:
        raise FileNotFoundError(
            f"'{CONVERSATIONS_FILENAME}' not found in {zip_path}"
        )

    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(target) as f:
            raw = f.read().decode("utf-8")
            return json.loads(raw)


def list_zip_contents(zip_path: Path) -> list[dict]:
    """ZIP 내부 파일 목록과 크기를 반환한다 (디버깅/로깅용)."""
    contents = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            contents.append({
                "filename": info.filename,
                "file_size": info.file_size,
                "compress_size": info.compress_size,
            })
    return contents
