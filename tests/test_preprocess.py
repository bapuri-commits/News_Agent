"""PII 마스킹 + Chunking 단위 테스트."""

from src.models.conversation import Conversation, Message
from src.preprocess.pii_masker import mask_text, mask_messages
from src.preprocess.chunker import chunk_conversation, chunk_all
from src import config


def _make_message(role: str, text: str, ts: float = 1.0) -> Message:
    return Message(role=role, text=text, timestamp=ts)


def _make_conversation(
    conv_id: str, messages: list[Message], title: str = "test"
) -> Conversation:
    return Conversation(
        id=conv_id,
        title=title,
        created_at=1000.0,
        updated_at=2000.0,
        messages=messages,
    )


# ── PII Masker ──


class TestMaskText:
    # ── 전화번호 ──

    def test_phone_mobile(self):
        assert mask_text("연락처: 010-1234-5678") == "연락처: [PHONE]"

    def test_phone_mobile_no_dash(self):
        assert mask_text("전화 01012345678 입니다") == "전화 [PHONE] 입니다"

    def test_phone_mobile_dot_separator(self):
        assert mask_text("010.1234.5678") == "[PHONE]"

    def test_phone_landline(self):
        assert mask_text("사무실 02-123-4567") == "사무실 [PHONE]"

    def test_phone_regional(self):
        assert mask_text("031-1234-5678로 연락") == "[PHONE]로 연락"

    # ── 이메일 ──

    def test_email(self):
        assert mask_text("메일: user@example.com") == "메일: [EMAIL]"

    def test_email_complex(self):
        assert mask_text("my.name+tag@sub.domain.co.kr") == "[EMAIL]"

    # ── 주민번호 ──

    def test_ssn(self):
        assert mask_text("주민번호 850101-1234567") == "주민번호 [SSN]"

    def test_ssn_with_spaces(self):
        assert mask_text("850101 - 1234567") == "[SSN]"

    def test_ssn_invalid_prefix_preserved(self):
        result = mask_text("850101-5234567")
        assert result == "850101-5234567"

    # ── 계좌번호 ──

    def test_account(self):
        assert mask_text("계좌 110-123-456789") == "계좌 [ACCOUNT]"

    def test_account_4segment(self):
        assert mask_text("1002-123-456789-01") == "[ACCOUNT]"

    def test_account_not_match_date(self):
        """날짜(YYYY-MM-DD)가 계좌번호로 오탐되면 안 됨"""
        assert mask_text("2026-02-18") == "2026-02-18"
        assert mask_text("날짜: 2025-12-31 입니다") == "날짜: 2025-12-31 입니다"

    def test_account_not_match_short_numbers(self):
        assert mask_text("12-34-56") == "12-34-56"

    # ── 주소 ──

    def test_address(self):
        result = mask_text("서울시 강남구 테헤란로 123")
        assert "[ADDRESS]" in result

    def test_address_full_qualifier(self):
        result = mask_text("서울특별시 강남구 테헤란로 123")
        assert "[ADDRESS]" in result

    def test_address_gyeonggi(self):
        result = mask_text("경기도 화성시 동탄대로 456-7")
        assert "[ADDRESS]" in result

    # ── 복합/일반 ──

    def test_no_pii_unchanged(self):
        original = "반도체 팹 증설 뉴스입니다."
        assert mask_text(original) == original

    def test_industry_text_no_false_positive(self):
        """업무 용어가 PII로 오탐되면 안 됨"""
        text = "TSMC 3nm 팹 CapEx 200억 달러 투자 발표"
        assert mask_text(text) == text

    def test_multiple_pii(self):
        text = "연락: 010-1234-5678, 메일: a@b.com"
        result = mask_text(text)
        assert "[PHONE]" in result
        assert "[EMAIL]" in result
        assert "010" not in result

    def test_all_pii_types_in_one_text(self):
        text = (
            "이름: 홍길동, 주민번호: 900101-1234567, "
            "전화: 010-9999-8888, 메일: hong@test.com, "
            "계좌: 110-123-456789"
        )
        result = mask_text(text)
        assert "[SSN]" in result
        assert "[PHONE]" in result
        assert "[EMAIL]" in result
        assert "[ACCOUNT]" in result
        assert "900101" not in result
        assert "010-9999" not in result

    def test_empty_string(self):
        assert mask_text("") == ""


class TestMaskMessages:
    def test_returns_new_list(self):
        original = [_make_message("user", "010-1234-5678")]
        masked = mask_messages(original)

        assert masked is not original
        assert masked[0] is not original[0]
        assert original[0].text == "010-1234-5678"
        assert masked[0].text == "[PHONE]"

    def test_preserves_role_and_timestamp(self):
        original = [_make_message("user", "메일 a@b.com", ts=42.0)]
        masked = mask_messages(original)

        assert masked[0].role == "user"
        assert masked[0].timestamp == 42.0
        assert masked[0].text == "메일 [EMAIL]"

    def test_empty_list(self):
        assert mask_messages([]) == []


# ── Chunker ──


class TestChunkConversation:
    def test_single_chunk_under_limit(self):
        msgs = [_make_message("user", "짧은 텍스트")]
        conv = _make_conversation("c1", msgs)
        chunks = chunk_conversation(conv)

        assert len(chunks) == 1
        assert chunks[0].conversation_id == "c1"
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1
        assert len(chunks[0].messages) == 1

    def test_splits_over_limit(self):
        big_text = "가" * (config.MAX_CHUNK_CHARS - 100)
        msgs = [
            _make_message("user", big_text, ts=1.0),
            _make_message("assistant", big_text, ts=2.0),
        ]
        conv = _make_conversation("c2", msgs)
        chunks = chunk_conversation(conv)

        assert len(chunks) == 2
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[0].total_chunks == 2
        assert chunks[1].total_chunks == 2
        assert chunks[0].conversation_id == "c2"

    def test_exact_limit_no_split(self):
        text = "나" * config.MAX_CHUNK_CHARS
        msgs = [_make_message("user", text)]
        conv = _make_conversation("c3", msgs)
        chunks = chunk_conversation(conv)

        assert len(chunks) == 1

    def test_chunk_preserves_messages(self):
        msgs = [
            _make_message("user", "질문", ts=1.0),
            _make_message("assistant", "답변", ts=2.0),
        ]
        conv = _make_conversation("c4", msgs)
        chunks = chunk_conversation(conv)

        assert chunks[0].messages[0].text == "질문"
        assert chunks[0].messages[1].text == "답변"

    def test_empty_conversation_single_chunk(self):
        """메시지 0개 대화 → 빈 메시지의 청크 1개"""
        conv = _make_conversation("empty", [])
        chunks = chunk_conversation(conv)

        assert len(chunks) == 1
        assert chunks[0].messages == []
        assert chunks[0].char_count == 0

    def test_single_giant_message_not_split(self):
        """단일 메시지가 MAX_CHUNK_CHARS 초과 → 메시지 내부 분할 불가, 1청크"""
        giant = "X" * (config.MAX_CHUNK_CHARS + 5000)
        conv = _make_conversation("giant", [_make_message("user", giant)])
        chunks = chunk_conversation(conv)

        assert len(chunks) == 1
        assert chunks[0].char_count == len(giant)

    def test_many_small_messages_split(self):
        """작은 메시지 100개가 합산 초과 시 분할"""
        unit = "가" * 500
        msgs = [_make_message("user", unit, ts=float(i)) for i in range(100)]
        conv = _make_conversation("many", msgs)

        total_chars = 500 * 100  # 50,000 > 24,000
        assert conv.char_count == total_chars

        chunks = chunk_conversation(conv)
        assert len(chunks) >= 2

        recovered_msgs = []
        for ch in chunks:
            recovered_msgs.extend(ch.messages)
        assert len(recovered_msgs) == 100

    def test_chunk_char_count_matches(self):
        """청크의 char_count 프로퍼티가 실제 텍스트 합과 일치"""
        msgs = [
            _make_message("user", "ABC" * 100),
            _make_message("assistant", "DEF" * 200),
        ]
        conv = _make_conversation("cc", msgs)
        for chunk in chunk_conversation(conv):
            expected = sum(len(m.text) for m in chunk.messages)
            assert chunk.char_count == expected

    def test_three_way_split(self):
        """3분할 시 chunk_index 0,1,2 / total_chunks 3"""
        size = config.MAX_CHUNK_CHARS - 100
        msgs = [_make_message("user", "가" * size, ts=float(i)) for i in range(3)]
        conv = _make_conversation("tri", msgs)
        chunks = chunk_conversation(conv)

        assert len(chunks) == 3
        for i, ch in enumerate(chunks):
            assert ch.chunk_index == i
            assert ch.total_chunks == 3


class TestChunkAll:
    def test_multiple_conversations(self):
        convs = [
            _make_conversation("a", [_make_message("user", "안녕")]),
            _make_conversation("b", [_make_message("user", "하이")]),
        ]
        chunks = chunk_all(convs)

        assert len(chunks) == 2
        ids = [ch.conversation_id for ch in chunks]
        assert "a" in ids
        assert "b" in ids

    def test_empty_list(self):
        assert chunk_all([]) == []

    def test_mixed_sizes(self):
        small = _make_conversation("s", [_make_message("user", "짧음")])
        big_text = "다" * (config.MAX_CHUNK_CHARS - 100)
        big = _make_conversation("b", [
            _make_message("user", big_text, ts=1.0),
            _make_message("assistant", big_text, ts=2.0),
        ])
        chunks = chunk_all([small, big])

        assert len(chunks) == 3
        assert chunks[0].conversation_id == "s"
        assert chunks[1].conversation_id == "b"
        assert chunks[2].conversation_id == "b"

    def test_preserves_conversation_order(self):
        """chunk_all 출력이 입력 Conversation 순서를 보존"""
        convs = [
            _make_conversation("x", [_make_message("user", "first")]),
            _make_conversation("y", [_make_message("user", "second")]),
            _make_conversation("z", [_make_message("user", "third")]),
        ]
        chunks = chunk_all(convs)
        ids = [ch.conversation_id for ch in chunks]
        assert ids == ["x", "y", "z"]
