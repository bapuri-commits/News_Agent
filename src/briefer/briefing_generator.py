"""4단계 브리핑 생성 파이프라인.

Stage 1 (Haiku):  클러스터링 + Top 5 선정
Stage 2 (Opus):   Top 5 심층 요약 (크롤링된 본문 기반)
Stage 3 (Sonnet): 카테고리별 요약 (3건+ 카테고리에 impact 포함)
Stage 4 (Sonnet): SK에코플랜트 렌즈 분석
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

from src import config
from src.briefer.article_crawler import crawl_articles
from src.briefer.prompts import (
    STAGE1_SYSTEM, STAGE2_SYSTEM, STAGE3_SYSTEM, STAGE4_SYSTEM,
    build_stage1_prompt, build_stage2_prompt,
    build_stage3_prompt, build_stage4_prompt,
    build_profile_summary,
)
from src.models.article import Article

logger = logging.getLogger(__name__)

load_dotenv(config.PROJECT_ROOT / ".env")

MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-20250514"
MODEL_OPUS = "claude-opus-4-20250514"


class BriefingGenerator:
    """수집된 기사 → 구조화된 브리핑 JSON을 생성한다."""

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        articles: list[Article],
        profile: dict,
        target_date: str,
    ) -> dict:
        """전체 브리핑 파이프라인을 실행한다."""
        article_dicts = [a.to_dict() for a in articles]

        logger.info("=== Stage 1: Clustering + Top 5 (Haiku) ===")
        stage1 = self._stage1_cluster(article_dicts, profile)

        raw_top5_ids = stage1.get("top5_ids", [])[:5]
        top5_ids = self._dedup_top5(raw_top5_ids, article_dicts)
        sk_ids = stage1.get("sk_ecoplant_ids", [])[:10]
        clusters = stage1.get("clusters", {})
        crawl_target_ids = list(dict.fromkeys(top5_ids + sk_ids))

        logger.info("Top 5: %s", top5_ids)
        logger.info("SK에코플랜트 관련: %d건", len(sk_ids))
        logger.info("크롤링 대상: %d건", len(crawl_target_ids))

        crawl_targets = [a for a in articles if a.id in crawl_target_ids]
        bodies = crawl_articles(crawl_targets) if crawl_targets else {}
        crawl_success = sum(
            1 for a in crawl_targets
            if bodies.get(a.id, "") != a.snippet and len(bodies.get(a.id, "")) > len(a.snippet)
        )
        logger.info("크롤링 결과: %d/%d 성공", crawl_success, len(crawl_targets))

        logger.info("=== Stage 2: Top 5 Deep Summary (Opus) ===")
        top5_articles = self._enrich_with_body(
            [a for a in article_dicts if a["id"] in top5_ids], bodies,
        )
        stage2 = self._stage2_deep_summary(top5_articles)

        logger.info("=== Stage 3: Category Summaries (Sonnet) ===")
        cluster_data = self._build_cluster_data(article_dicts, clusters)
        stage3 = self._stage3_category_summary(cluster_data)

        sk_ecoplant_result = None
        sk_article_dicts = [a for a in article_dicts if a["id"] in sk_ids]
        if sk_article_dicts:
            logger.info("=== Stage 4: SK에코플랜트 Lens (Sonnet) ===")
            sk_with_body = self._enrich_with_body(sk_article_dicts, bodies)
            sk_ecoplant_result = self._stage4_sk_ecoplant(sk_with_body)

        id_to_article = {a["id"]: a for a in article_dicts}
        for item in stage2.get("items", []):
            aid = item.get("id", "")
            if aid in id_to_article:
                orig = id_to_article[aid]
                if "category" not in item:
                    item["category"] = (orig.get("categories") or ["other"])[0]
                if "sources" not in item:
                    item["sources"] = [{"name": orig["source_name"], "url": orig["url"]}]

        for cat_data in stage3.get("categories", {}).values():
            for item in cat_data.get("items", []):
                aid = item.get("id", "")
                if aid in id_to_article:
                    orig = id_to_article[aid]
                    item.setdefault("url", orig.get("url", ""))
                    item.setdefault("source_name", orig.get("source_name", ""))

        risks = self._extract_risks(stage2)
        next_signals = self._extract_next_signals(stage2)

        from collections import Counter
        source_dist = Counter(a["source_group"] for a in article_dicts)

        briefing = {
            "date": target_date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "reading_time_min": 15,
            "top5": stage2.get("items", []),
            "by_category": stage3.get("categories", {}),
            "sk_ecoplant": sk_ecoplant_result,
            "risks": risks,
            "next_signals": next_signals,
            "source_diversity": dict(source_dist),
            "metadata": {
                "total_articles": len(articles),
                "crawl_attempted": len(crawl_targets),
                "crawl_success": crawl_success,
                "models_used": {
                    "clustering": MODEL_HAIKU,
                    "deep_summary": MODEL_OPUS,
                    "category_summary": MODEL_SONNET,
                    "sk_ecoplant": MODEL_SONNET,
                },
                "pipeline_version": "2.0",
            },
        }

        self._validate_briefing(briefing)
        return briefing

    @staticmethod
    def _validate_briefing(briefing: dict) -> None:
        """산출물 품질 자동 검증 — 문제 발견 시 경고 로그."""
        warnings_found = []
        top5 = briefing.get("top5", [])

        if len(top5) < 4:
            warnings_found.append(f"Top 5가 {len(top5)}건뿐 (최소 4건 필요)")

        headlines = [item.get("headline", "") for item in top5]
        for i, h1 in enumerate(headlines):
            for j, h2 in enumerate(headlines):
                if i < j and h1 and h2 and h1 == h2:
                    warnings_found.append(f"Top 5 #{i+1}과 #{j+1} 헤드라인 완전 중복: {h1[:40]}")

        unknown_count = sum(
            1 for item in top5
            if "미확인" in item.get("fact", "") or "확인되지" in item.get("fact", "")
        )
        if unknown_count >= 3:
            warnings_found.append(f"Top 5 중 {unknown_count}건이 '미확인' — 크롤링 실패 가능성")

        categories = briefing.get("by_category", {})
        if not categories:
            warnings_found.append("카테고리 데이터 없음 (Stage 3 실패 가능성)")

        cat_ids = [x["id"] for cat in categories.values() for x in cat.get("items", [])]
        if len(cat_ids) != len(set(cat_ids)):
            warnings_found.append(f"카테고리 내 기사 중복: {len(cat_ids) - len(set(cat_ids))}건")

        risks = briefing.get("risks", [])
        if len(risks) != len(set(risks)):
            warnings_found.append("리스크 항목 중복")

        signals = briefing.get("next_signals", [])
        if len(signals) != len(set(signals)):
            warnings_found.append("Next Signals 중복")

        meta = briefing.get("metadata", {})
        attempted = meta.get("crawl_attempted", 0)
        success = meta.get("crawl_success", 0)
        if attempted > 0 and success == 0:
            warnings_found.append("크롤링 전부 실패 (0/{}건)".format(attempted))

        for item in top5:
            fact = item.get("fact", "")
            if fact and len(fact) > 300:
                warnings_found.append(
                    f"Top5 '{item.get('headline', '')[:20]}' Fact {len(fact)}자 (300자 초과)"
                )
            sources = item.get("sources", [])
            if not sources:
                warnings_found.append(
                    f"Top5 '{item.get('headline', '')[:20]}' 출처 누락"
                )

        for cat_key, cat_data in categories.items():
            items = cat_data.get("items", [])
            if not items:
                warnings_found.append(f"카테고리 '{cat_key}' 기사 0건 (빈 카테고리)")

        source_div = briefing.get("source_diversity", {})
        total = sum(source_div.values()) if source_div else 0
        if total > 0:
            for group, count in source_div.items():
                if count / total > 0.85:
                    warnings_found.append(
                        f"소스 {group} 비중 {count/total:.0%} (85% 초과, 편향 위험)"
                    )

        if warnings_found:
            for w in warnings_found:
                logger.warning("QUALITY CHECK: %s", w)
        else:
            logger.info("QUALITY CHECK: 모든 검증 통과")

    def _stage1_cluster(self, articles: list[dict], profile: dict) -> dict:
        profile_summary = build_profile_summary(profile)
        prompt = build_stage1_prompt(articles, profile_summary)
        raw = self._call_llm(MODEL_HAIKU, STAGE1_SYSTEM, prompt, max_tokens=2048)
        return self._parse_json(raw, "stage1")

    def _stage2_deep_summary(self, articles_with_body: list[dict]) -> dict:
        if not articles_with_body:
            return {"items": []}
        prompt = build_stage2_prompt(articles_with_body)
        raw = self._call_llm(MODEL_OPUS, STAGE2_SYSTEM, prompt, max_tokens=4096)
        return self._parse_json(raw, "stage2")

    def _stage3_category_summary(self, clusters: dict[str, list[dict]]) -> dict:
        non_empty = {k: v for k, v in clusters.items() if v}
        if not non_empty:
            return {"categories": {}}
        prompt = build_stage3_prompt(non_empty)
        raw = self._call_llm(MODEL_SONNET, STAGE3_SYSTEM, prompt, max_tokens=8192)
        return self._parse_json(raw, "stage3")

    def _stage4_sk_ecoplant(self, sk_articles: list[dict]) -> dict | None:
        if not sk_articles:
            return None
        prompt = build_stage4_prompt(sk_articles)
        raw = self._call_llm(MODEL_SONNET, STAGE4_SYSTEM, prompt, max_tokens=2048)
        return self._parse_json(raw, "stage4")

    def _call_llm(
        self,
        model: str,
        system: str,
        user_prompt: str,
        max_tokens: int = 2048,
    ) -> str:
        if "haiku" in model:
            model_label = "Haiku"
        elif "opus" in model:
            model_label = "Opus"
        else:
            model_label = "Sonnet"
        logger.info("LLM call [%s]: %d chars input", model_label, len(user_prompt))
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )
        result = response.content[0].text
        cache_status = getattr(response.usage, "cache_read_input_tokens", 0)
        if cache_status:
            logger.info("LLM response [%s]: %d chars (cache hit: %d tokens)",
                        model_label, len(result), cache_status)
        else:
            logger.info("LLM response [%s]: %d chars", model_label, len(result))
        return result

    @staticmethod
    def _parse_json(raw: str, stage_name: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            first_line, _, rest = text.partition("\n")
            text = rest if rest else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse %s JSON: %s", stage_name, e)
            logger.debug("Raw response: %s", text[:500])
            return {}

    @staticmethod
    def _enrich_with_body(
        articles: list[dict], bodies: dict[str, str],
    ) -> list[dict]:
        result = []
        for a in articles:
            enriched = {**a, "body": bodies.get(a["id"], a.get("snippet", ""))}
            result.append(enriched)
        return result

    @staticmethod
    def _build_cluster_data(
        articles: list[dict], clusters: dict[str, list[str]],
    ) -> dict[str, list[dict]]:
        id_map = {a["id"]: a for a in articles}
        seen: set[str] = set()
        result: dict[str, list[dict]] = {}
        for cat, ids in clusters.items():
            deduped = []
            for aid in ids:
                if aid in id_map and aid not in seen:
                    deduped.append(id_map[aid])
                    seen.add(aid)
            if deduped:
                result[cat] = deduped
        return result

    @staticmethod
    def _dedup_top5(ids: list[str], articles: list[dict]) -> list[str]:
        """같은 기사가 다른 소스 URL로 중복 선정된 경우 제목 유사도 기반으로 제거."""
        id_map = {a["id"]: a for a in articles}
        seen_titles: list[str] = []
        deduped: list[str] = []
        for aid in ids:
            article = id_map.get(aid)
            if not article:
                continue
            title = article.get("title", "").strip().lower()
            title_short = title[:30]
            if any(title_short in seen or seen in title_short
                   for seen in seen_titles):
                logger.info("Top 5 중복 제거: %s (제목 유사)", aid)
                continue
            seen_titles.append(title_short)
            deduped.append(aid)
        return deduped

    @staticmethod
    def _extract_risks(stage2: dict) -> list[str]:
        risks = []
        seen: set[str] = set()
        for item in stage2.get("items", []):
            risk = item.get("risk", "")
            if risk and risk != "특이사항 없음" and risk not in seen:
                risks.append(f"[{item.get('headline', '')}] {risk}")
                seen.add(risk)
        return risks

    @staticmethod
    def _extract_next_signals(stage2: dict) -> list[str]:
        signals = []
        seen: set[str] = set()
        for item in stage2.get("items", []):
            ns = item.get("next_signal", "")
            if ns and ns not in seen:
                signals.append(ns)
                seen.add(ns)
        return signals
