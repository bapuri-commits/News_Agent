"""News Agent — CLI (Program #1: Profile 추출 + Program #2: 뉴스 수집)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src import config
from src.models.conversation import Conversation, Message
from src.parser.zip_explorer import extract_conversations_json, list_zip_contents
from src.parser.conversation_parser import parse_all_conversations
from src.preprocess.pii_masker import mask_messages
from src.preprocess.chunker import chunk_all
from src.models.conversation import ConversationChunk


def setup_logging() -> None:
    from dotenv import load_dotenv
    load_dotenv(config.PROJECT_ROOT / ".env")

    config.ensure_output_dirs()

    import io
    stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(stream),
            logging.FileHandler(config.PIPELINE_LOG_PATH, encoding="utf-8"),
        ],
    )


def cmd_parse(args: argparse.Namespace) -> None:
    """Phase 1: ZIP 파싱 -> conversation_index.json + parsed_conversations.json"""
    logger = logging.getLogger("parse")
    zip_path = Path(args.zip)

    if not zip_path.exists():
        logger.error("ZIP file not found: %s", zip_path)
        sys.exit(1)

    logger.info("=== Phase 1: Parse ===")
    logger.info("ZIP: %s", zip_path)

    contents = list_zip_contents(zip_path)
    logger.info("ZIP contains %d files:", len(contents))
    for c in contents:
        logger.info("  %s (%d bytes)", c["filename"], c["file_size"])

    raw_conversations = extract_conversations_json(zip_path)
    logger.info("Raw conversations found: %d", len(raw_conversations))

    conversations = parse_all_conversations(raw_conversations)
    logger.info("Parsed conversations: %d", len(conversations))

    total_messages = sum(c.message_count for c in conversations)
    total_chars = sum(c.char_count for c in conversations)
    logger.info("Total messages: %d, Total chars: %d", total_messages, total_chars)

    index = [c.to_meta().to_dict() for c in conversations]
    with open(config.CONVERSATION_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s", config.CONVERSATION_INDEX_PATH)

    parsed = [c.to_dict() for c in conversations]
    with open(config.PARSED_CONVERSATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s", config.PARSED_CONVERSATIONS_PATH)

    _save_pipeline_state("parse", {
        "zip_path": str(zip_path),
        "raw_count": len(raw_conversations),
        "parsed_count": len(conversations),
        "total_messages": total_messages,
        "total_chars": total_chars,
    })
    logger.info("=== Phase 1 complete ===")


def cmd_preprocess(args: argparse.Namespace) -> None:
    """Phase 2: PII 마스킹 + Chunking -> preprocessed_chunks.json"""
    logger = logging.getLogger("preprocess")
    logger.info("=== Phase 2: Preprocess ===")

    parsed_path = config.PARSED_CONVERSATIONS_PATH
    if not parsed_path.exists():
        logger.error("parsed_conversations.json not found. Run 'parse' first.")
        sys.exit(1)

    with open(parsed_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    conversations = _rebuild_conversations(raw_data)
    logger.info("Loaded %d conversations", len(conversations))

    for conv in conversations:
        conv.messages = mask_messages(conv.messages)
    logger.info("PII masking complete")

    chunks = chunk_all(conversations)
    logger.info("Chunking complete: %d chunks from %d conversations",
                len(chunks), len(conversations))

    output_path = config.PREPROCESSED_CHUNKS_PATH
    chunks_data = [
        {
            "conversation_id": ch.conversation_id,
            "chunk_index": ch.chunk_index,
            "total_chunks": ch.total_chunks,
            "char_count": ch.char_count,
            "messages": [m.to_dict() for m in ch.messages],
        }
        for ch in chunks
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s", output_path)

    _save_pipeline_state("preprocess", {
        "input_conversations": len(conversations),
        "output_chunks": len(chunks),
        "total_chars": sum(ch.char_count for ch in chunks),
    })
    logger.info("=== Phase 2 complete ===")


def _rebuild_conversations(raw_data: list[dict]) -> list[Conversation]:
    """parsed_conversations.json → Conversation 객체 리스트 복원."""
    conversations = []
    for item in raw_data:
        messages = [
            Message(
                role=m["role"],
                text=m["text"],
                timestamp=m["timestamp"],
            )
            for m in item["messages"]
        ]
        conversations.append(Conversation(
            id=item["id"],
            title=item["title"],
            created_at=_iso_to_timestamp(item.get("created_at", "")),
            updated_at=_iso_to_timestamp(item.get("updated_at", "")),
            messages=messages,
        ))
    return conversations


def _iso_to_timestamp(iso_str: str) -> float:
    """ISO 8601 문자열 → Unix timestamp. 파싱 실패 시 0.0."""
    if not iso_str:
        return 0.0
    try:
        from datetime import datetime
        return datetime.fromisoformat(iso_str).timestamp()
    except (ValueError, TypeError):
        return 0.0


def cmd_build_profile(args: argparse.Namespace) -> None:
    """Phase 4: micro-summary + 설문 → stable_profile.json 생성."""
    logger = logging.getLogger("build-profile")
    logger.info("=== Phase 4: Build Profile ===")

    biz_path = config.MICRO_SUMMARIES_DIR / "business_summaries.json"
    if not biz_path.exists():
        logger.error("business_summaries.json not found. Run 'summarize' first.")
        sys.exit(1)

    survey_path = config.SURVEY_PATH
    if not survey_path.exists():
        logger.error("father-profile-raw.json not found at %s", survey_path)
        sys.exit(1)

    with open(biz_path, "r", encoding="utf-8") as f:
        summaries = json.load(f)
    logger.info("Loaded %d business summaries", len(summaries))

    from src.profiler.survey_loader import load_survey
    survey = load_survey(survey_path)
    logger.info("Loaded survey from %s", survey_path)

    from src.profiler.profile_builder import build_profile
    profile = build_profile(summaries, survey)

    profile_dict = profile.to_dict()
    output_path = config.STABLE_PROFILE_PATH
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile_dict, f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s", output_path)

    logger.info("Top priorities: %d items", len(profile.top_priorities))
    logger.info("Open questions: %d items", len(profile.open_questions))
    for q in profile.open_questions:
        logger.info("  - %s", q)

    _save_pipeline_state("build_profile", {
        "input_summaries": len(summaries),
        "top_priorities": len(profile.top_priorities),
        "open_questions": len(profile.open_questions),
        "output_path": str(output_path),
    })
    logger.info("=== Phase 4 complete ===")


def cmd_summarize(args: argparse.Namespace) -> None:
    """Phase 3: micro-summary 생성 (LLM)."""
    logger = logging.getLogger("summarize")
    logger.info("=== Phase 3: Summarize ===")

    chunks_path = config.PREPROCESSED_CHUNKS_PATH
    if not chunks_path.exists():
        logger.error("preprocessed_chunks.json not found. Run 'preprocess' first.")
        sys.exit(1)

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)

    with open(config.CONVERSATION_INDEX_PATH, "r", encoding="utf-8") as f:
        index = {c["id"]: c["title"] for c in json.load(f)}

    chunks = [
        ConversationChunk(
            conversation_id=ch["conversation_id"],
            chunk_index=ch["chunk_index"],
            total_chunks=ch["total_chunks"],
            messages=[
                Message(role=m["role"], text=m["text"], timestamp=m["timestamp"])
                for m in ch["messages"]
            ],
        )
        for ch in chunks_data
    ]
    logger.info("Loaded %d chunks", len(chunks))

    from src.summarizer.llm_summarizer import LLMSummarizer
    summarizer = LLMSummarizer()

    summaries = []
    business_count = 0
    for i, chunk in enumerate(chunks):
        title = index.get(chunk.conversation_id, "(unknown)")
        logger.info(
            "[%d/%d] Summarizing: %s (chunk %d/%d, %d chars)",
            i + 1, len(chunks), title,
            chunk.chunk_index + 1, chunk.total_chunks, chunk.char_count,
        )

        try:
            summary = summarizer.summarize(chunk)
            summary.title = title
            summaries.append(summary)

            if summary.business_relevant:
                business_count += 1
                logger.info("  -> Business relevant (%.2f): %s",
                            summary.confidence, summary.topics_top[:3])
            else:
                logger.info("  -> Not business relevant (%.2f)", summary.confidence)

        except Exception as e:
            logger.error("  -> FAILED: %s", e)

    output_path = config.MICRO_SUMMARIES_DIR / "all_summaries.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([s.to_dict() for s in summaries], f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s", output_path)

    biz_only = [s for s in summaries if s.business_relevant]
    biz_path = config.MICRO_SUMMARIES_DIR / "business_summaries.json"
    with open(biz_path, "w", encoding="utf-8") as f:
        json.dump([s.to_dict() for s in biz_only], f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s (%d business-relevant)", biz_path, len(biz_only))

    _save_pipeline_state("summarize", {
        "total_chunks": len(chunks),
        "total_summaries": len(summaries),
        "business_relevant": business_count,
        "non_business": len(summaries) - business_count,
    })
    logger.info("=== Phase 3 complete ===")


def _save_pipeline_state(phase: str, data: dict) -> None:
    state_path = config.PIPELINE_STATE_PATH
    state = {}
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

    from datetime import datetime, timezone
    state[phase] = {
        **data,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def cmd_collect(args: argparse.Namespace) -> None:
    """Phase 5: 뉴스 수집 (Google News RSS 검색 + 전문매체 RSS)."""
    logger = logging.getLogger("collect")
    logger.info("=== Phase 5: Collect ===")

    profile_path = config.STABLE_PROFILE_PATH
    if not profile_path.exists():
        logger.error("stable_profile.json not found. Run 'build-profile' first.")
        sys.exit(1)

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)
    logger.info("Loaded profile from %s", profile_path)

    target_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info("Target date: %s", target_date)

    from src.collector.query_builder import build_queries
    queries = build_queries(profile)
    logger.info("Generated %d search queries", len(queries))

    from src.collector.gnews_client import GNewsClient
    gnews_client = GNewsClient()
    gnews_articles = gnews_client.search_queries(queries)
    logger.info("Google News: %d raw articles", len(gnews_articles))

    feeds_path = config.RSS_FEEDS_PATH
    rss_articles: list = []
    if feeds_path.exists():
        with open(feeds_path, "r", encoding="utf-8") as f:
            feeds_data = json.load(f)

        from src.collector.rss_client import RSSClient
        rss_state_path = config.OUTPUT_DIR / "rss_state.json"
        rss_client = RSSClient(state_path=rss_state_path)
        rss_articles = rss_client.fetch_all(feeds_data["feeds"])
        logger.info("RSS feeds: %d raw articles", len(rss_articles))
    else:
        logger.warning("rss_feeds.json not found - skipping RSS feeds")

    all_articles = gnews_articles + rss_articles
    logger.info("Total raw: %d articles", len(all_articles))

    from src.collector.dedup import deduplicate
    deduped = deduplicate(all_articles)
    logger.info("After dedup: %d articles", len(deduped))

    from src.collector.article_filter import filter_articles
    filtered = filter_articles(deduped, profile, max_count=50)
    logger.info("After filter: %d articles", len(filtered))

    from collections import Counter
    source_dist = Counter(a.source_group for a in filtered)
    source_names = Counter(a.source_name for a in filtered)
    logger.info("Source distribution: %s", dict(source_dist))
    for src_name, cnt in source_names.most_common(10):
        logger.info("  %s: %d", src_name, cnt)

    output = {
        "date": target_date,
        "collection_stats": {
            "gnews_raw": len(gnews_articles),
            "rss_raw": len(rss_articles),
            "after_dedup": len(deduped),
            "after_filter": len(filtered),
            "source_distribution": dict(source_dist),
        },
        "articles": [a.to_dict() for a in filtered],
    }

    config.ensure_output_dirs()
    output_path = config.COLLECTED_DIR / f"{target_date}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s", output_path)

    _save_pipeline_state("collect", {
        "date": target_date,
        "gnews_raw": len(gnews_articles),
        "rss_raw": len(rss_articles),
        "after_dedup": len(deduped),
        "after_filter": len(filtered),
        "source_distribution": dict(source_dist),
        "output_path": str(output_path),
    })
    logger.info("=== Phase 5 complete ===")


def cmd_brief(args: argparse.Namespace) -> None:
    """Phase 6: 수집된 기사 → 브리핑 생성 (LLM 4단계 파이프라인)."""
    logger = logging.getLogger("brief")
    logger.info("=== Phase 6: Brief ===")

    target_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    collected_path = config.COLLECTED_DIR / f"{target_date}.json"

    if not collected_path.exists():
        logger.error("collected/%s.json not found. Run 'collect --date %s' first.",
                      target_date, target_date)
        sys.exit(1)

    with open(collected_path, "r", encoding="utf-8") as f:
        collected = json.load(f)

    profile_path = config.STABLE_PROFILE_PATH
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    from src.models.article import Article
    articles = [Article.from_dict(a) for a in collected["articles"]]
    logger.info("Loaded %d articles for %s", len(articles), target_date)

    from src.briefer.briefing_generator import BriefingGenerator
    generator = BriefingGenerator()
    briefing = generator.generate(articles, profile, target_date)

    config.ensure_output_dirs()

    json_path = config.BRIEFINGS_DIR / f"{target_date}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)
    logger.info("Saved: %s", json_path)

    from src.briefer.markdown_renderer import render_markdown
    md_text = render_markdown(briefing)
    md_path = config.BRIEFINGS_DIR / f"{target_date}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    logger.info("Saved: %s", md_path)

    from src.briefer.html_renderer import render_html
    html_text = render_html(briefing)
    html_path = config.BRIEFINGS_DIR / f"{target_date}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)
    logger.info("Saved: %s", html_path)

    _save_pipeline_state("brief", {
        "date": target_date,
        "articles_input": len(articles),
        "top5_count": len(briefing.get("top5", [])),
        "categories_count": len(briefing.get("by_category", {})),
        "has_sk_ecoplant": briefing.get("sk_ecoplant") is not None,
        "output_json": str(json_path),
        "output_md": str(md_path),
        "output_html": str(html_path),
    })
    logger.info("=== Phase 6 complete ===")


def cmd_deploy(args: argparse.Namespace) -> None:
    """Phase 7: briefings/ HTML → web/ 정적 사이트 빌드."""
    logger = logging.getLogger("deploy")
    logger.info("=== Phase 7: Deploy ===")

    briefings_dir = config.BRIEFINGS_DIR
    output_dir = Path(args.output_dir) if args.output_dir else config.WEB_DIR

    if not briefings_dir.exists() or not list(briefings_dir.glob("*.html")):
        logger.error("빌드할 HTML 브리핑이 없습니다. 'brief' 명령을 먼저 실행하세요.")
        sys.exit(1)

    from src.deployer.site_builder import build_site
    build_site(briefings_dir, output_dir)

    _save_pipeline_state("deploy", {
        "output_dir": str(output_dir),
    })

    if args.push:
        import subprocess
        logger.info("git push 시작...")
        try:
            subprocess.run(["git", "add", str(output_dir)], check=True,
                           cwd=config.PROJECT_ROOT)
            subprocess.run(
                ["git", "commit", "-m", f"deploy: update web briefings"],
                check=True, cwd=config.PROJECT_ROOT,
            )
            subprocess.run(["git", "push"], check=True, cwd=config.PROJECT_ROOT)
            logger.info("git push 완료")
        except subprocess.CalledProcessError as e:
            logger.error("git push 실패: %s", e)
            sys.exit(1)

    logger.info("=== Phase 7 complete ===")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="news-agent",
        description="News Agent — Profile 추출 + 뉴스 수집 + 브리핑 파이프라인",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="Phase 1: ZIP 파싱")
    p_parse.add_argument("--zip", required=True, help="ChatGPT export ZIP 경로")

    sub.add_parser("preprocess", help="Phase 2: PII 마스킹 + Chunking")
    sub.add_parser("summarize", help="Phase 3: micro-summary 생성 (LLM)")
    sub.add_parser("build-profile", help="Phase 4: Stable Profile 생성")

    p_collect = sub.add_parser("collect", help="Phase 5: 뉴스 수집 (GNews + RSS)")
    p_collect.add_argument("--date", default=None, help="수집 대상 날짜 (YYYY-MM-DD)")

    p_brief = sub.add_parser("brief", help="Phase 6: 브리핑 생성 (LLM)")
    p_brief.add_argument("--date", default=None, help="브리핑 대상 날짜 (YYYY-MM-DD)")

    p_deploy = sub.add_parser("deploy", help="Phase 7: 정적 사이트 빌드 (web/)")
    p_deploy.add_argument("--output-dir", default=None, help="출력 디렉토리 (기본: web/)")
    p_deploy.add_argument("--push", action="store_true", help="빌드 후 git add/commit/push 자동 실행")

    return parser


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "parse":
        cmd_parse(args)
    elif args.command == "preprocess":
        cmd_preprocess(args)
    elif args.command == "summarize":
        cmd_summarize(args)
    elif args.command == "build-profile":
        cmd_build_profile(args)
    elif args.command == "collect":
        cmd_collect(args)
    elif args.command == "brief":
        cmd_brief(args)
    elif args.command == "deploy":
        cmd_deploy(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
