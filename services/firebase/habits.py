import re

from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger


def _normalize_habits_dict(raw):
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        m = db_state.CELL_KEY_RE.match(k)
        if not m:
            continue
        date_str, habit_id = m.group(1), m.group(2)
        if not re.match(r"^[a-zA-Z0-9_\-]+$", habit_id):
            continue
        if not db_state.DATE_RE.match(date_str):
            continue
        if v != "done":
            continue
        out[k] = v
    return out


def get_habits_map(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return {}

    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                h = data.get("habits_v1")
                return _normalize_habits_dict(h) if isinstance(h, dict) else {}
        except Exception as e:
            logger.error("Firestore habits read failed", extra={
                "operation": "get_habits_map",
                "error": str(e),
            })

    return _normalize_habits_dict(dict(db_state.habit_memory.get(email_key, {})))


def _write_habits_map(email_key, habits_dict):
    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False
            doc_ref.set({"habits_v1": habits_dict}, merge=True)
            return True
        except Exception as e:
            logger.error("Firestore habits write failed", extra={
                "operation": "_write_habits_map",
                "error": str(e),
            })
            return False

    if email_key not in db_state.auth_users_memory:
        return False
    db_state.habit_memory[email_key] = dict(habits_dict)
    return True


def patch_habit_cell(email, date_str, habit_id, state):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user"
    if not re.match(r"^[a-zA-Z0-9_\-]+$", str(habit_id)):
        return False, "invalid_habit"
    if not db_state.DATE_RE.match(date_str or ""):
        return False, "invalid_date"
    if state not in ("done", "none"):
        return False, "invalid_state"

    cell_key = f"{date_str}_{habit_id}"
    habits = get_habits_map(email)
    if state == "none":
        habits.pop(cell_key, None)
    else:
        habits[cell_key] = state

    if _write_habits_map(email_key, habits):
        return True, None
    return False, "write_failed"


def merge_habits_map(email, incoming):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(incoming, dict):
        return False, "invalid_body", None
    if len(incoming) > 2500:
        return False, "too_many_keys", None

    habits = get_habits_map(email)
    for k, v in incoming.items():
        if not isinstance(k, str):
            continue
        m = db_state.CELL_KEY_RE.match(k)
        if not m:
            continue
        date_str, habit_id = m.group(1), m.group(2)
        if not re.match(r"^[a-zA-Z0-9_\-]+$", str(habit_id)):
            continue
        if v == "none":
            habits.pop(k, None)
        elif v == "done":
            habits[k] = v

    habits = _normalize_habits_dict(habits)
    if _write_habits_map(email_key, habits):
        return True, None, habits
    return False, "write_failed", None


def get_custom_habits(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return []
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                h = data.get("custom_habits_v1")
                return h if isinstance(h, list) else []
        except Exception as e:
            logger.error("Firestore custom habits read failed", extra={
                "operation": "get_custom_habits",
                "error": str(e),
            })
    return list(db_state.custom_habits_memory.get(email_key, []))


def update_custom_habits(email, habits_list):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user"
    if not isinstance(habits_list, list):
        return False, "invalid_body"

    valid_habits = []
    for h in habits_list:
        if isinstance(h, dict) and "id" in h and re.match(r"^[a-zA-Z0-9_\-]+$", str(h["id"])):
            valid_habits.append(h)

    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False, "no_user"
            doc_ref.set({"custom_habits_v1": valid_habits}, merge=True)
            return True, None
        except Exception as e:
            logger.error("Firestore custom habits write failed", extra={
                "operation": "update_custom_habits",
                "error": str(e),
            })
            return False, "write_failed"

    if email_key not in db_state.auth_users_memory:
        return False, "no_user"
    db_state.custom_habits_memory[email_key] = list(valid_habits)
    return True, None
