from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
MICRO_SUMMARIES_DIR = OUTPUT_DIR / "micro_summaries"
DATA_DIR = Path(__file__).resolve().parent / "data"

CONVERSATION_INDEX_PATH = OUTPUT_DIR / "conversation_index.json"
STABLE_PROFILE_PATH = OUTPUT_DIR / "stable_profile.json"
PIPELINE_STATE_PATH = OUTPUT_DIR / "pipeline_state.json"
PIPELINE_LOG_PATH = OUTPUT_DIR / "pipeline.log"
KEYWORDS_PATH = DATA_DIR / "keywords.json"
SURVEY_PATH = PROJECT_ROOT / "docs" / "father-profile-raw.json"

PARSED_CONVERSATIONS_PATH = OUTPUT_DIR / "parsed_conversations.json"
PREPROCESSED_CHUNKS_PATH = OUTPUT_DIR / "preprocessed_chunks.json"

COLLECTED_DIR = OUTPUT_DIR / "collected"
BRIEFINGS_DIR = OUTPUT_DIR / "briefings"
WEB_DIR = PROJECT_ROOT / "web"
RSS_FEEDS_PATH = DATA_DIR / "rss_feeds.json"

ROLES_TO_EXTRACT = {"user", "assistant"}
CONTENT_TYPES_TO_EXTRACT = {"text"}

MAX_CHUNK_CHARS = 24_000


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MICRO_SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    COLLECTED_DIR.mkdir(parents=True, exist_ok=True)
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
