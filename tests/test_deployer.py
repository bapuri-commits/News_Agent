"""Phase 7 deployer module tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.deployer.nav_injector import inject_nav
from src.deployer.index_generator import generate_index, _load_briefing_meta
from src.deployer.site_builder import build_site, _scan_dates


# ─── nav_injector ───


class TestInjectNav:
    SIMPLE_HTML = "<html><body><header>test</header><section>content</section></body></html>"

    def test_nav_injected_after_header(self):
        result = inject_nav(self.SIMPLE_HTML, "2026-02-21", "2026-02-23", "2026-02-22")
        header_end = result.find("</header>")
        nav_start = result.find('<nav class="briefing-nav">')
        assert header_end < nav_start

    def test_prev_next_links_present(self):
        result = inject_nav(self.SIMPLE_HTML, "2026-02-21", "2026-02-23", "2026-02-22")
        assert "2026-02-21.html" in result
        assert "2026-02-23.html" in result
        assert "index.html" in result

    def test_no_prev_shows_disabled(self):
        result = inject_nav(self.SIMPLE_HTML, None, "2026-02-23", "2026-02-22")
        nav_section = result[result.find("<nav"):result.find("</nav>")]
        assert 'nav-disabled' in nav_section
        assert "2026-02-23.html" in nav_section

    def test_no_next_shows_disabled(self):
        result = inject_nav(self.SIMPLE_HTML, "2026-02-21", None, "2026-02-22")
        nav_section = result[result.find("<nav"):result.find("</nav>")]
        assert 'nav-disabled' in nav_section
        assert "2026-02-21.html" in nav_section

    def test_both_disabled(self):
        result = inject_nav(self.SIMPLE_HTML, None, None, "2026-02-22")
        nav_section = result[result.find("<nav"):result.find("</nav>")]
        assert nav_section.count("nav-disabled") == 2

    def test_fallback_when_no_header(self):
        no_header = "<html><body><div>no header</div></body></html>"
        result = inject_nav(no_header, None, None, "2026-02-22")
        assert "briefing-nav" in result

    def test_xss_prevention(self):
        result = inject_nav(self.SIMPLE_HTML, '<script>alert(1)</script>', None, "2026-02-22")
        nav_section = result[result.find("<nav"):result.find("</nav>")]
        assert "<script>" not in nav_section
        assert "&lt;script&gt;" in nav_section

    def test_original_content_preserved(self):
        result = inject_nav(self.SIMPLE_HTML, "2026-02-21", "2026-02-23", "2026-02-22")
        assert "<section>content</section>" in result

    def test_sticky_css_present(self):
        result = inject_nav(self.SIMPLE_HTML, None, None, "2026-02-22")
        assert "position: sticky" in result
        assert "z-index: 100" in result

    def test_real_briefing_html(self):
        """output/briefings/ HTML on disk (if present)."""
        real_path = Path("output/briefings/2026-02-22.html")
        if not real_path.exists():
            pytest.skip("No real briefing HTML available")
        html = real_path.read_text(encoding="utf-8")
        result = inject_nav(html, None, None, "2026-02-22")
        assert result.count('<nav class="briefing-nav">') == 1
        header_end = result.find("</header>")
        nav_start = result.find('<nav class="briefing-nav">')
        assert header_end < nav_start


# ─── index_generator ───


class TestLoadBriefingMeta:
    def test_valid_json(self, tmp_path: Path):
        data = {
            "date": "2026-02-22",
            "top5": [{"headline": "Test headline"}],
            "sk_ecoplant": {"headline": "SK test"},
            "by_category": {"fab_capex": {"items": [{}]}},
            "metadata": {"total_articles": 10},
        }
        json_path = tmp_path / "2026-02-22.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        meta = _load_briefing_meta(json_path)
        assert meta is not None
        assert meta["date"] == "2026-02-22"
        assert meta["top_headline"] == "Test headline"
        assert meta["sk_headline"] == "SK test"
        assert meta["theme_label"] != ""

    def test_missing_json(self, tmp_path: Path):
        meta = _load_briefing_meta(tmp_path / "nonexistent.json")
        assert meta is None

    def test_invalid_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid", encoding="utf-8")
        meta = _load_briefing_meta(bad)
        assert meta is None

    def test_empty_top5(self, tmp_path: Path):
        data = {"date": "2026-02-22", "top5": [], "by_category": {}}
        json_path = tmp_path / "2026-02-22.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")
        meta = _load_briefing_meta(json_path)
        assert meta["top_headline"] == ""

    def test_no_sk_ecoplant(self, tmp_path: Path):
        data = {"date": "2026-02-22", "top5": [{"headline": "H"}], "by_category": {}}
        json_path = tmp_path / "2026-02-22.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")
        meta = _load_briefing_meta(json_path)
        assert meta["sk_headline"] == ""


class TestGenerateIndex:
    def test_generates_valid_html(self, tmp_path: Path):
        briefings = tmp_path / "briefings"
        briefings.mkdir()
        data = {
            "date": "2026-02-22",
            "top5": [{"headline": "Test"}],
            "by_category": {},
        }
        (briefings / "2026-02-22.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        out = tmp_path / "web" / "index.html"
        generate_index(briefings, ["2026-02-22"], out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "2026-02-22.html" in content
        assert "Executive Briefing" in content

    def test_empty_dates(self, tmp_path: Path):
        out = tmp_path / "web" / "index.html"
        generate_index(tmp_path, [], out)
        content = out.read_text(encoding="utf-8")
        assert "idx-empty" in content

    def test_multiple_dates_newest_first(self, tmp_path: Path):
        briefings = tmp_path / "briefings"
        briefings.mkdir()
        for d in ["2026-02-20", "2026-02-21", "2026-02-22"]:
            data = {"date": d, "top5": [{"headline": f"H-{d}"}], "by_category": {}}
            (briefings / f"{d}.json").write_text(
                json.dumps(data), encoding="utf-8"
            )
        out = tmp_path / "index.html"
        generate_index(briefings, ["2026-02-20", "2026-02-21", "2026-02-22"], out)
        content = out.read_text(encoding="utf-8")
        pos_22 = content.find("2026-02-22")
        pos_20 = content.find("2026-02-20")
        assert pos_22 < pos_20


# ─── site_builder ───


class TestScanDates:
    def test_valid_dates_only(self, tmp_path: Path):
        (tmp_path / "2026-02-22.html").touch()
        (tmp_path / "2026-02-23.html").touch()
        (tmp_path / "index.html").touch()
        (tmp_path / "style.css").touch()
        dates = _scan_dates(tmp_path)
        assert dates == ["2026-02-22", "2026-02-23"]

    def test_sorted_output(self, tmp_path: Path):
        (tmp_path / "2026-02-25.html").touch()
        (tmp_path / "2026-02-22.html").touch()
        (tmp_path / "2026-02-23.html").touch()
        dates = _scan_dates(tmp_path)
        assert dates == ["2026-02-22", "2026-02-23", "2026-02-25"]


class TestBuildSite:
    def test_end_to_end(self, tmp_path: Path):
        briefings = tmp_path / "briefings"
        briefings.mkdir()
        web = tmp_path / "web"

        for d in ["2026-02-21", "2026-02-22", "2026-02-23"]:
            html = f"<html><head></head><body><header>H-{d}</header><p>{d}</p></body></html>"
            (briefings / f"{d}.html").write_text(html, encoding="utf-8")
            data = {"date": d, "top5": [{"headline": f"News-{d}"}], "by_category": {}}
            (briefings / f"{d}.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

        build_site(briefings, web)

        assert (web / "index.html").exists()
        for d in ["2026-02-21", "2026-02-22", "2026-02-23"]:
            deployed = web / f"{d}.html"
            assert deployed.exists()
            content = deployed.read_text(encoding="utf-8")
            assert "briefing-nav" in content

        mid = (web / "2026-02-22.html").read_text(encoding="utf-8")
        assert "2026-02-21.html" in mid
        assert "2026-02-23.html" in mid

        first = (web / "2026-02-21.html").read_text(encoding="utf-8")
        assert "nav-disabled" in first
        assert "2026-02-22.html" in first

        last = (web / "2026-02-23.html").read_text(encoding="utf-8")
        assert "nav-disabled" in last
        assert "2026-02-22.html" in last

    def test_empty_briefings(self, tmp_path: Path):
        briefings = tmp_path / "empty"
        briefings.mkdir()
        web = tmp_path / "web"
        build_site(briefings, web)
        assert not web.exists()
