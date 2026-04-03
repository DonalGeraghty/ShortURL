import uuid

from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger

CATEGORY_LABEL_MAX_LEN = 80
MAX_CATEGORIES = 100


def _pretty_label_from_id(cat_id):
    return cat_id.replace("_", " ").strip().title() if cat_id else ""


def _normalize_category_item(raw):
    if not isinstance(raw, dict):
        return None
    cid = raw.get("id")
    if not isinstance(cid, str) or not db_state.TODO_ID_RE.match(cid):
        return None
    label = raw.get("label")
    if not isinstance(label, str) or not label.strip():
        return None
    label = label.strip()[:CATEGORY_LABEL_MAX_LEN]
    return {"id": cid, "label": label}


def _normalize_categories_list(items):
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        n = _normalize_category_item(item)
        if n:
            out.append(n)
    return out


def _read_raw_categories_list(email_key):
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                h = data.get("habit_categories_v1")
                return h if isinstance(h, list) else []
        except Exception as e:
            logger.error("Firestore habit categories read failed", extra={
                "operation": "_read_raw_categories_list",
                "error": str(e),
            })
            return []
    return list(db_state.habit_categories_memory.get(email_key, []))


def _write_categories_list(email_key, categories_list):
    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False
            doc_ref.set({"habit_categories_v1": categories_list}, merge=True)
            return True
        except Exception as e:
            logger.error("Firestore habit categories write failed", extra={
                "operation": "_write_categories_list",
                "error": str(e),
            })
            return False
    if email_key not in db_state.auth_users_memory:
        return False
    db_state.habit_categories_memory[email_key] = list(categories_list)
    return True


def _migrate_categories_from_habits(email_key):
    """If categories are empty but habits reference category ids, seed categories once."""
    raw_cats = _read_raw_categories_list(email_key)
    if _normalize_categories_list(raw_cats):
        return
    from .habits import read_raw_custom_habits_list

    raw_habits = read_raw_custom_habits_list(email_key)
    seen = []
    for h in raw_habits:
        if not isinstance(h, dict):
            continue
        c = h.get("category")
        if not isinstance(c, str):
            continue
        c = c.strip()[:64]
        if not c or not db_state.TODO_ID_RE.match(c):
            continue
        if c not in seen:
            seen.append(c)
    if not seen:
        return
    cats = [{"id": x, "label": _pretty_label_from_id(x)} for x in seen]
    _write_categories_list(email_key, cats)


def get_habit_categories(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return []
    _migrate_categories_from_habits(email_key)
    return _normalize_categories_list(_read_raw_categories_list(email_key))


def get_category_id_set(email):
    return {c["id"] for c in get_habit_categories(email)}


def add_habit_category(email, label):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(label, str):
        return False, "invalid_label", None
    label = label.strip()[:CATEGORY_LABEL_MAX_LEN]
    if not label:
        return False, "invalid_label", None

    cats = get_habit_categories(email)
    if len(cats) >= MAX_CATEGORIES:
        return False, "too_many_categories", None
    new_item = {"id": uuid.uuid4().hex, "label": label}
    next_list = cats + [new_item]
    if not _write_categories_list(email_key, next_list):
        return False, "write_failed", None
    return True, None, next_list


def update_habit_category(email, category_id, label):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(category_id, str) or not db_state.TODO_ID_RE.match(category_id):
        return False, "invalid_id", None
    if not isinstance(label, str):
        return False, "invalid_label", None
    label = label.strip()[:CATEGORY_LABEL_MAX_LEN]
    if not label:
        return False, "invalid_label", None

    cats = get_habit_categories(email)
    found = False
    next_list = []
    for c in cats:
        if c["id"] == category_id:
            next_list.append({"id": category_id, "label": label})
            found = True
        else:
            next_list.append(c)
    if not found:
        return False, "not_found", None
    if not _write_categories_list(email_key, next_list):
        return False, "write_failed", None
    return True, None, next_list


def delete_habit_category(email, category_id, reassign_to_id=None):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(category_id, str) or not db_state.TODO_ID_RE.match(category_id):
        return False, "invalid_id", None

    from .habits import get_custom_habits, update_custom_habits

    habits = get_custom_habits(email)
    if any(h["category"] == category_id for h in habits):
        if not isinstance(reassign_to_id, str) or not db_state.TODO_ID_RE.match(reassign_to_id):
            return False, "category_in_use", None
        if reassign_to_id == category_id:
            return False, "invalid_reassign", None
        cur_ids = get_category_id_set(email)
        if reassign_to_id not in cur_ids:
            return False, "invalid_reassign", None
        new_habits = [
            {**h, "category": reassign_to_id if h["category"] == category_id else h["category"]}
            for h in habits
        ]
        ok, err, _ = update_custom_habits(email, new_habits)
        if not ok:
            return False, err or "update_failed", None

    cats = get_habit_categories(email)
    next_cats = [c for c in cats if c["id"] != category_id]
    if len(next_cats) == len(cats):
        return False, "not_found", None
    if not _write_categories_list(email_key, next_cats):
        return False, "write_failed", None
    return True, None, next_cats
