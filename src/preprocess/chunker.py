"""대화 → ConversationChunk 변환. 기본 1:1, 초과 시 메시지 경계 분할."""

from __future__ import annotations

from src import config
from src.models.conversation import Conversation, ConversationChunk, Message


def chunk_conversation(conv: Conversation) -> list[ConversationChunk]:
    """Conversation을 ConversationChunk 리스트로 변환.

    대부분의 대화는 MAX_CHUNK_CHARS 이내이므로 1:1 매핑.
    초과하는 경우에만 메시지 경계에서 분할.
    """
    if conv.char_count <= config.MAX_CHUNK_CHARS:
        return [
            ConversationChunk(
                conversation_id=conv.id,
                chunk_index=0,
                total_chunks=1,
                messages=list(conv.messages),
            )
        ]

    return _split_at_message_boundary(conv)


def _split_at_message_boundary(conv: Conversation) -> list[ConversationChunk]:
    """MAX_CHUNK_CHARS 초과 대화를 메시지 경계에서 분할."""
    chunks: list[list[Message]] = []
    current: list[Message] = []
    current_chars = 0

    for msg in conv.messages:
        msg_len = len(msg.text)

        if current and current_chars + msg_len > config.MAX_CHUNK_CHARS:
            chunks.append(current)
            current = []
            current_chars = 0

        current.append(msg)
        current_chars += msg_len

    if current:
        chunks.append(current)

    total = len(chunks)
    return [
        ConversationChunk(
            conversation_id=conv.id,
            chunk_index=i,
            total_chunks=total,
            messages=msgs,
        )
        for i, msgs in enumerate(chunks)
    ]


def chunk_all(conversations: list[Conversation]) -> list[ConversationChunk]:
    """여러 Conversation을 일괄 청킹."""
    result: list[ConversationChunk] = []
    for conv in conversations:
        result.extend(chunk_conversation(conv))
    return result
