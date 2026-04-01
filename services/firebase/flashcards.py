import random
import uuid

from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger

FLASHCARD_GROUP_NAME_MAX_LEN = 80
FLASHCARD_TEXT_MAX_LEN = 240
FLASHCARD_MAX_GROUPS = 200
FLASHCARD_MAX_CARDS_PER_GROUP = 1000


def _normalize_flashcard_groups(raw):
    if not isinstance(raw, list):
        return []
    groups_out = []
    seen_group_ids = set()
    for group in raw:
        if not isinstance(group, dict):
            continue
        group_id = group.get("id")
        name = group.get("name")
        if not isinstance(group_id, str) or not db_state.TODO_ID_RE.match(group_id):
            continue
        if group_id in seen_group_ids:
            continue
        if not isinstance(name, str):
            continue
        name = name.strip()
        if not name or len(name) > FLASHCARD_GROUP_NAME_MAX_LEN:
            continue

        cards_out = []
        seen_card_ids = set()
        cards_raw = group.get("cards")
        if isinstance(cards_raw, list):
            for card in cards_raw:
                if not isinstance(card, dict):
                    continue
                card_id = card.get("id")
                front = card.get("front")
                back = card.get("back")
                if not isinstance(card_id, str) or not db_state.TODO_ID_RE.match(card_id):
                    continue
                if card_id in seen_card_ids:
                    continue
                if not isinstance(front, str) or not isinstance(back, str):
                    continue
                front = front.strip()
                back = back.strip()
                if not front or not back:
                    continue
                if len(front) > FLASHCARD_TEXT_MAX_LEN or len(back) > FLASHCARD_TEXT_MAX_LEN:
                    continue
                cards_out.append({"id": card_id, "front": front, "back": back})
                seen_card_ids.add(card_id)
                if len(cards_out) >= FLASHCARD_MAX_CARDS_PER_GROUP:
                    break

        groups_out.append({"id": group_id, "name": name, "cards": cards_out})
        seen_group_ids.add(group_id)
        if len(groups_out) >= FLASHCARD_MAX_GROUPS:
            break
    return groups_out


def get_flashcard_groups(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return []
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return _normalize_flashcard_groups(data.get("flashcards_v1"))
        except Exception as e:
            logger.error("Firestore flashcards read failed", extra={
                "operation": "get_flashcard_groups",
                "error": str(e),
            })
    return _normalize_flashcard_groups(db_state.flashcards_memory.get(email_key, []))


def _write_flashcard_groups(email_key, groups):
    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False
            doc_ref.set({"flashcards_v1": groups}, merge=True)
            return True
        except Exception as e:
            logger.error("Firestore flashcards write failed", extra={
                "operation": "_write_flashcard_groups",
                "error": str(e),
            })
            return False
    if email_key not in db_state.auth_users_memory:
        return False
    db_state.flashcards_memory[email_key] = list(groups)
    return True


def update_flashcard_groups(email, groups):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(groups, list):
        return False, "invalid_body", None
    normalized = _normalize_flashcard_groups(groups)
    if _write_flashcard_groups(email_key, normalized):
        return True, None, normalized
    return False, "write_failed", None


def add_flashcard_group(email, name):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(name, str):
        return False, "invalid_name", None
    name = name.strip()
    if not name or len(name) > FLASHCARD_GROUP_NAME_MAX_LEN:
        return False, "invalid_name", None
    groups = get_flashcard_groups(email)
    if len(groups) >= FLASHCARD_MAX_GROUPS:
        return False, "too_many_groups", None
    groups.append({"id": uuid.uuid4().hex, "name": name, "cards": []})
    if _write_flashcard_groups(email_key, groups):
        return True, None, groups
    return False, "write_failed", None


def add_flashcard_to_group(email, group_id, front, back):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(group_id, str) or not db_state.TODO_ID_RE.match(group_id):
        return False, "invalid_group_id", None
    if not isinstance(front, str) or not isinstance(back, str):
        return False, "invalid_card_text", None
    front = front.strip()
    back = back.strip()
    if not front or not back:
        return False, "invalid_card_text", None
    if len(front) > FLASHCARD_TEXT_MAX_LEN or len(back) > FLASHCARD_TEXT_MAX_LEN:
        return False, "invalid_card_text", None

    groups = get_flashcard_groups(email)
    target_group = next((g for g in groups if g.get("id") == group_id), None)
    if target_group is None:
        return False, "group_not_found", None
    if len(target_group.get("cards", [])) >= FLASHCARD_MAX_CARDS_PER_GROUP:
        return False, "too_many_cards", None

    target_group["cards"].append({"id": uuid.uuid4().hex, "front": front, "back": back})
    normalized = _normalize_flashcard_groups(groups)
    if _write_flashcard_groups(email_key, normalized):
        return True, None, normalized
    return False, "write_failed", None


def get_random_flashcards(email, group_id=None):
    groups = get_flashcard_groups(email)
    if isinstance(group_id, str) and group_id.strip():
        group_id = group_id.strip()
        groups = [g for g in groups if g.get("id") == group_id]
        if not groups:
            return False, "group_not_found", None
    cards = []
    for group in groups:
        for card in group.get("cards", []):
            cards.append({
                "id": card.get("id"),
                "front": card.get("front"),
                "back": card.get("back"),
                "groupId": group.get("id"),
                "groupName": group.get("name"),
            })
    random.shuffle(cards)
    return True, None, cards
