from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger

STOIC_TEXT_MAX_LEN = 1200


def _normalize_stoic_form(raw):
    if not isinstance(raw, dict):
        raw = {}
    out = {}
    for k in (
        "morningFocus",
        "likelyChallenge",
        "virtueToPractice",
        "eveningWin",
        "eveningImprove",
        "nextAction",
    ):
        v = raw.get(k)
        out[k] = v.strip()[:STOIC_TEXT_MAX_LEN] if isinstance(v, str) else ""
    return out


def get_stoic_journal(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return {"date": "", "form": _normalize_stoic_form({})}

    payload = None
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                payload = data.get("stoic_v1")
        except Exception as e:
            logger.error("Firestore stoic read failed", extra={
                "operation": "get_stoic_journal",
                "error": str(e),
            })
    if payload is None:
        payload = db_state.auth_users_memory.get(email_key, {}).get("stoic_v1")

    if not isinstance(payload, dict):
        return {"date": "", "form": _normalize_stoic_form({})}
    date_key = payload.get("date")
    if not isinstance(date_key, str) or not db_state.DATE_RE.match(date_key):
        date_key = ""
    return {"date": date_key, "form": _normalize_stoic_form(payload.get("form"))}


def update_stoic_journal(email, date_key, form):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(date_key, str) or not db_state.DATE_RE.match(date_key):
        return False, "invalid_date", None
    payload = {"date": date_key, "form": _normalize_stoic_form(form)}

    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False, "no_user", None
            doc_ref.set({"stoic_v1": payload}, merge=True)
            return True, None, payload
        except Exception as e:
            logger.error("Firestore stoic write failed", extra={
                "operation": "update_stoic_journal",
                "error": str(e),
            })
            return False, "write_failed", None

    if email_key not in db_state.auth_users_memory:
        return False, "no_user", None
    db_state.auth_users_memory[email_key]["stoic_v1"] = dict(payload)
    return True, None, payload
