"""conversations.json의 트리 구조를 순회하여 선형 Conversation 리스트로 변환한다."""

from __future__ import annotations

import logging
from typing import Any

from src.config import ROLES_TO_EXTRACT, CONTENT_TYPES_TO_EXTRACT
from src.models.conversation import Conversation, Message

logger = logging.getLogger(__name__)


def _find_root_node(mapping: dict[str, Any]) -> str | None:
    """parent가 None인 루트 노드 ID를 찾는다."""
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            return node_id
    return None


def _extract_text_from_content(content: dict | None) -> str | None:
    """message.content에서 텍스트를 추출한다."""
    if content is None:
        return None

    content_type = content.get("content_type", "")
    if content_type not in CONTENT_TYPES_TO_EXTRACT:
        return None

    parts = content.get("parts", [])
    text_parts = []
    for part in parts:
        if isinstance(part, str):
            text_parts.append(part)
        else:
            text_parts.append("[NON_TEXT_CONTENT]")

    combined = "\n".join(text_parts).strip()
    return combined if combined else None


def _pick_latest_child(children: list[str], mapping: dict[str, Any]) -> str | None:
    """분기 대화에서 가장 최신 timestamp를 가진 자식 노드를 선택한다."""
    if not children:
        return None
    if len(children) == 1:
        return children[0]

    best_id = children[0]
    best_time = 0.0
    for child_id in children:
        node = mapping.get(child_id, {})
        msg = node.get("message")
        if msg and msg.get("create_time"):
            t = msg["create_time"]
            if t > best_time:
                best_time = t
                best_id = child_id
    return best_id


def _traverse_tree(mapping: dict[str, Any]) -> list[Message]:
    """트리를 순회하여 시간순 Message 리스트를 만든다."""
    root_id = _find_root_node(mapping)
    if root_id is None:
        return []

    messages: list[Message] = []
    current_id: str | None = root_id

    while current_id is not None:
        node = mapping.get(current_id)
        if node is None:
            break

        msg_data = node.get("message")
        if msg_data is not None:
            role = msg_data.get("author", {}).get("role", "")
            if role in ROLES_TO_EXTRACT:
                text = _extract_text_from_content(msg_data.get("content"))
                if text:
                    timestamp = msg_data.get("create_time", 0.0) or 0.0
                    messages.append(Message(role=role, text=text, timestamp=timestamp))

        children = node.get("children", [])
        current_id = _pick_latest_child(children, mapping)

    return messages


def parse_single_conversation(raw: dict) -> Conversation | None:
    """단일 대화 JSON을 Conversation 객체로 변환한다."""
    mapping = raw.get("mapping")
    if not mapping:
        return None

    conv_id = raw.get("id", raw.get("conversation_id", ""))
    title = raw.get("title", "(제목 없음)")
    created_at = raw.get("create_time", 0.0) or 0.0
    updated_at = raw.get("update_time", 0.0) or 0.0

    messages = _traverse_tree(mapping)
    if not messages:
        logger.info("Skipping empty conversation: %s (%s)", title, conv_id)
        return None

    return Conversation(
        id=conv_id,
        title=title,
        created_at=created_at,
        updated_at=updated_at,
        messages=messages,
    )


def parse_all_conversations(raw_list: list[dict]) -> list[Conversation]:
    """전체 대화 리스트를 파싱한다."""
    conversations: list[Conversation] = []
    skipped = 0

    for raw in raw_list:
        conv = parse_single_conversation(raw)
        if conv is not None:
            conversations.append(conv)
        else:
            skipped += 1

    logger.info(
        "Parsed %d conversations (%d skipped)",
        len(conversations),
        skipped,
    )
    return conversations
