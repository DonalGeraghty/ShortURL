from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger

NUTRITION_MAX_DAYS = 400


def _normalize_nutrition_history(raw):
    if not isinstance(raw, dict):
        return {}
    out = {}
    for date_key, row in raw.items():
        if not isinstance(date_key, str) or not db_state.DATE_RE.match(date_key):
            continue
        if not isinstance(row, dict):
            continue
        next_row = {}
        calories = row.get("calories")
        if isinstance(calories, int) and calories >= 0:
            next_row["calories"] = calories
        weight = row.get("weight")
        if isinstance(weight, (int, float)) and float(weight) > 0:
            next_row["weight"] = round(float(weight), 1)
        water_ml = row.get("waterMl")
        if isinstance(water_ml, int) and water_ml >= 0:
            next_row["waterMl"] = water_ml
        if next_row:
            out[date_key] = next_row
        if len(out) >= NUTRITION_MAX_DAYS:
            break
    return out


def get_nutrition_history(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return {}
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return _normalize_nutrition_history(data.get("nutrition_v1"))
        except Exception as e:
            logger.error("Firestore nutrition read failed", extra={
                "operation": "get_nutrition_history",
                "error": str(e),
            })
    row = db_state.auth_users_memory.get(email_key, {})
    return _normalize_nutrition_history(row.get("nutrition_v1"))


def update_nutrition_history(email, history):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(history, dict):
        return False, "invalid_body", None
    normalized = _normalize_nutrition_history(history)

    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False, "no_user", None
            doc_ref.set({"nutrition_v1": normalized}, merge=True)
            return True, None, normalized
        except Exception as e:
            logger.error("Firestore nutrition write failed", extra={
                "operation": "update_nutrition_history",
                "error": str(e),
            })
            return False, "write_failed", None

    if email_key not in db_state.auth_users_memory:
        return False, "no_user", None
    db_state.auth_users_memory[email_key]["nutrition_v1"] = dict(normalized)
    return True, None, normalized
