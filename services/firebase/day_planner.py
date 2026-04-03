import uuid

from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger

OPTION_LABEL_MAX_LEN = 120
MAX_OPTIONS = 200


def _normalize_options(raw):
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        oid = item.get("id")
        label = item.get("label")
        if not isinstance(oid, str) or not db_state.TODO_ID_RE.match(oid):
            continue
        if not isinstance(label, str):
            continue
        label = label.strip()[:OPTION_LABEL_MAX_LEN]
        if not label:
            continue
        out.append({"id": oid, "label": label})
    return out


def _option_ids_set(options):
    return {o["id"] for o in options}


def _normalize_slots(raw, valid_ids):
    out = {str(h): "" for h in range(24)}
    if not isinstance(raw, dict):
        return out
    for h in range(24):
        k = str(h)
        v = raw.get(k)
        if v is None and k not in raw:
            v = raw.get(h)
        if not isinstance(v, str) or not v:
            continue
        if v in valid_ids:
            out[k] = v
    return out


def _read_options_from_store(email_key):
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return _normalize_options(data.get("day_planner_options_v1"))
        except Exception as e:
            logger.error("Firestore day planner options read failed", extra={
                "operation": "get_day_planner_options",
                "error": str(e),
            })
    return _normalize_options(db_state.day_planner_options_memory.get(email_key))


def _write_options(email_key, options_list):
    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False
            doc_ref.set({"day_planner_options_v1": options_list}, merge=True)
            return True
        except Exception as e:
            logger.error("Firestore day planner options write failed", extra={
                "operation": "_write_options",
                "error": str(e),
            })
            return False
    if email_key not in db_state.auth_users_memory:
        return False
    db_state.day_planner_options_memory[email_key] = list(options_list)
    return True


def get_day_planner_options(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return []
    return _read_options_from_store(email_key)


def add_day_planner_option(email, label):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(label, str):
        return False, "invalid_label", None
    label = label.strip()[:OPTION_LABEL_MAX_LEN]
    if not label:
        return False, "invalid_label", None
    options = get_day_planner_options(email)
    if len(options) >= MAX_OPTIONS:
        return False, "too_many_options", None
    options.append({"id": uuid.uuid4().hex, "label": label})
    if _write_options(email_key, options):
        return True, None, options
    return False, "write_failed", None


def update_day_planner_option(email, option_id, label):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(option_id, str) or not db_state.TODO_ID_RE.match(option_id):
        return False, "invalid_id", None
    if not isinstance(label, str):
        return False, "invalid_label", None
    label = label.strip()[:OPTION_LABEL_MAX_LEN]
    if not label:
        return False, "invalid_label", None
    options = get_day_planner_options(email)
    found = False
    new_options = []
    for o in options:
        if o["id"] == option_id:
            new_options.append({"id": option_id, "label": label})
            found = True
        else:
            new_options.append(o)
    if not found:
        return False, "not_found", None
    if _write_options(email_key, new_options):
        return True, None, new_options
    return False, "write_failed", None


def delete_day_planner_option(email, option_id):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(option_id, str) or not db_state.TODO_ID_RE.match(option_id):
        return False, "invalid_id", None
    options = get_day_planner_options(email)
    new_options = [o for o in options if o["id"] != option_id]
    if len(new_options) == len(options):
        return False, "not_found", None
    if not _write_options(email_key, new_options):
        return False, "write_failed", None
    daily_before = _read_day_planner_daily_unvalidated(email_key)
    date_key = daily_before.get("date") or ""
    slots_before = daily_before.get("slots") if isinstance(daily_before.get("slots"), dict) else {}
    cleaned = {}
    changed = False
    for h in range(24):
        k = str(h)
        v = slots_before.get(k, "")
        if not isinstance(v, str):
            v = ""
        if v == option_id:
            cleaned[k] = ""
            changed = True
        else:
            cleaned[k] = v
    if changed and date_key and db_state.DATE_RE.match(date_key):
        ok_daily, err_daily, _ = update_day_planner_daily(email, date_key, cleaned)
        if not ok_daily:
            return False, err_daily or "write_failed", None
    return True, None, new_options


def _read_day_planner_daily_unvalidated(email_key):
    """Stored daily payload; slot values kept as strings (may reference unknown option ids)."""
    payload = None
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                payload = (doc.to_dict() or {}).get("day_planner_daily_v1")
        except Exception as e:
            logger.error("Firestore day planner daily read failed", extra={
                "operation": "_read_day_planner_daily_unvalidated",
                "error": str(e),
            })
    if payload is None:
        payload = db_state.day_planner_daily_memory.get(email_key)
    if not isinstance(payload, dict):
        return {"date": "", "slots": {str(h): "" for h in range(24)}}
    date_key = payload.get("date")
    if not isinstance(date_key, str) or not db_state.DATE_RE.match(date_key):
        date_key = ""
    raw = payload.get("slots")
    slots = {str(h): "" for h in range(24)}
    if isinstance(raw, dict):
        for h in range(24):
            k = str(h)
            v = raw.get(k)
            if v is None:
                v = raw.get(h)
            if isinstance(v, str) and (not v or db_state.TODO_ID_RE.match(v)):
                slots[k] = v
    return {"date": date_key, "slots": slots}


def get_day_planner_daily(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return {"date": "", "slots": _normalize_slots({}, set())}

    payload = None
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                payload = data.get("day_planner_daily_v1")
        except Exception as e:
            logger.error("Firestore day planner daily read failed", extra={
                "operation": "get_day_planner_daily",
                "error": str(e),
            })
    if payload is None:
        payload = db_state.day_planner_daily_memory.get(email_key)

    if not isinstance(payload, dict):
        return {"date": "", "slots": _normalize_slots({}, set())}
    date_key = payload.get("date")
    if not isinstance(date_key, str) or not db_state.DATE_RE.match(date_key):
        date_key = ""
    valid = _option_ids_set(get_day_planner_options(email))
    return {"date": date_key, "slots": _normalize_slots(payload.get("slots"), valid)}


def update_day_planner_daily(email, date_key, slots):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(date_key, str) or not db_state.DATE_RE.match(date_key):
        return False, "invalid_date", None
    valid = _option_ids_set(get_day_planner_options(email))
    norm_slots = _normalize_slots(slots if isinstance(slots, dict) else {}, valid)
    payload = {"date": date_key, "slots": norm_slots}

    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False, "no_user", None
            doc_ref.set({"day_planner_daily_v1": payload}, merge=True)
            return True, None, payload
        except Exception as e:
            logger.error("Firestore day planner daily write failed", extra={
                "operation": "update_day_planner_daily",
                "error": str(e),
            })
            return False, "write_failed", None

    if email_key not in db_state.auth_users_memory:
        return False, "no_user", None
    db_state.day_planner_daily_memory[email_key] = dict(payload)
    return True, None, payload
