"""conversation_parser 단위 테스트."""

import json
from pathlib import Path

from src.parser.conversation_parser import parse_all_conversations, parse_single_conversation

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture() -> list[dict]:
    with open(FIXTURES / "sample_conversations.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestParseSingleConversation:
    def test_normal_conversation(self):
        raw_list = _load_fixture()
        conv = parse_single_conversation(raw_list[0])

        assert conv is not None
        assert conv.id == "conv-001"
        assert conv.title == "반도체 공장 수주 동향"
        assert conv.message_count == 4
        assert conv.messages[0].role == "user"
        assert "반도체" in conv.messages[0].text
        assert conv.messages[1].role == "assistant"
        assert "TSMC" in conv.messages[1].text

    def test_short_conversation(self):
        raw_list = _load_fixture()
        conv = parse_single_conversation(raw_list[1])

        assert conv is not None
        assert conv.id == "conv-002"
        assert conv.message_count == 2

    def test_empty_conversation_returns_none(self):
        raw_list = _load_fixture()
        conv = parse_single_conversation(raw_list[2])

        assert conv is None

    def test_branching_picks_latest(self):
        raw_list = _load_fixture()
        conv = parse_single_conversation(raw_list[3])

        assert conv is not None
        assert conv.message_count == 2
        assert "국내 EPC" in conv.messages[1].text
        assert "이전 응답" not in conv.messages[1].text


class TestParseAllConversations:
    def test_parses_and_skips(self):
        raw_list = _load_fixture()
        conversations = parse_all_conversations(raw_list)

        assert len(conversations) == 3  # conv-003 (empty) is skipped

    def test_meta_generation(self):
        raw_list = _load_fixture()
        conversations = parse_all_conversations(raw_list)

        meta = conversations[0].to_meta()
        assert meta.id == "conv-001"
        assert meta.message_count == 4
        assert meta.char_count > 0
        assert meta.created_at != ""

    def test_char_count(self):
        raw_list = _load_fixture()
        conversations = parse_all_conversations(raw_list)

        for conv in conversations:
            assert conv.char_count == sum(len(m.text) for m in conv.messages)
