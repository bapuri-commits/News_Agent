"""top5-history.json 저장/로드/정리 단위 테스트."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.briefer.top5_history import load_history, save_history, get_recent_top5


@pytest.fixture
def history_path(tmp_path: Path) -> Path:
    return tmp_path / "top5-history.json"


class TestLoadHistory:

    def test_file_not_exists(self, history_path: Path):
        assert load_history(history_path) == {}

    def test_valid_json(self, history_path: Path):
        data = {"2026-02-27": ["h1", "h2"]}
        history_path.write_text(json.dumps(data), encoding="utf-8")
        assert load_history(history_path) == data

    def test_invalid_json(self, history_path: Path):
        history_path.write_text("not json", encoding="utf-8")
        assert load_history(history_path) == {}

    def test_non_dict_json(self, history_path: Path):
        history_path.write_text("[]", encoding="utf-8")
        assert load_history(history_path) == {}


class TestSaveHistory:

    def test_save_creates_file(self, history_path: Path):
        save_history("2026-02-27", ["h1", "h2", "h3"], path=history_path)
        data = json.loads(history_path.read_text(encoding="utf-8"))
        assert data == {"2026-02-27": ["h1", "h2", "h3"]}

    def test_save_appends(self, history_path: Path):
        save_history("2026-02-26", ["a1"], path=history_path)
        save_history("2026-02-27", ["b1"], path=history_path)
        data = json.loads(history_path.read_text(encoding="utf-8"))
        assert "2026-02-26" in data
        assert "2026-02-27" in data

    def test_save_overwrites_same_date(self, history_path: Path):
        save_history("2026-02-27", ["old"], path=history_path)
        save_history("2026-02-27", ["new"], path=history_path)
        data = json.loads(history_path.read_text(encoding="utf-8"))
        assert data["2026-02-27"] == ["new"]

    def test_max_days_trimming(self, history_path: Path):
        for day in range(1, 12):
            save_history(
                f"2026-02-{day:02d}", [f"h{day}"],
                path=history_path, max_days=7,
            )
        data = json.loads(history_path.read_text(encoding="utf-8"))
        assert len(data) == 7
        assert "2026-02-05" in data
        assert "2026-02-04" not in data


class TestGetRecentTop5:

    def test_returns_recent_days(self, history_path: Path):
        for day in [25, 26, 27]:
            save_history(
                f"2026-02-{day}", [f"headline_{day}"],
                path=history_path,
            )
        result = get_recent_top5(
            exclude_date="2026-02-27", max_days=3, path=history_path,
        )
        assert "2026-02-27" not in result
        assert "2026-02-26" in result
        assert "2026-02-25" in result

    def test_excludes_today(self, history_path: Path):
        save_history("2026-02-27", ["today"], path=history_path)
        result = get_recent_top5(
            exclude_date="2026-02-27", path=history_path,
        )
        assert result == {}

    def test_empty_history(self, history_path: Path):
        result = get_recent_top5(path=history_path)
        assert result == {}

    def test_max_days_limit(self, history_path: Path):
        for day in range(20, 28):
            save_history(
                f"2026-02-{day}", [f"h{day}"], path=history_path,
            )
        result = get_recent_top5(
            exclude_date="2026-02-27", max_days=2, path=history_path,
        )
        assert len(result) == 2
        assert "2026-02-26" in result
        assert "2026-02-25" in result
