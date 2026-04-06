from copy import deepcopy

from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger

SECTION_ON_RISING = "onRising"
SECTION_BREAKFAST = "breakfast"
SECTION_LUNCH = "lunch"
SECTION_DINNER = "dinner"

MEAL_PLAN_SECTIONS = [
    {
        "id": SECTION_ON_RISING,
        "label": "On rising",
        "options": [
            {
                "id": "rise_half_grapefruit",
                "label": "Half a grapefruit",
            },
        ],
    },
    {
        "id": SECTION_BREAKFAST,
        "label": "Breakfast",
        "options": [
            {
                "id": "breakfast_smoked_salmon_avocado_or_cream_cheese",
                "label": "60g smoked salmon with a small avocado and or 25g nuts/seeds.",
            }
        ],
    },
    {
        "id": SECTION_LUNCH,
        "label": "Lunch",
        "options": [
            {
                "id": "lunch_green_salad_salmon_or_beef_with_fat_option",
                "label": "Green salad with 100g beef with 100g cream cheese.",
            },
        ],
    },
    {
        "id": SECTION_DINNER,
        "label": "Dinner",
        "options": [
            {
                "id": "dinner_200g_protein_salad_cooked_greens_olive_oil",
                "label": "200g beef with a green salad and a small portion of cooked green vegetables with olive oil.",
            },
        ],
    },
]

_VALID_OPTIONS_BY_SECTION = {
    section["id"]: {opt["id"] for opt in section["options"]}
    for section in MEAL_PLAN_SECTIONS
}

_SECTION_IDS = [section["id"] for section in MEAL_PLAN_SECTIONS]
_DEFAULT_SELECTIONS = {
    SECTION_ON_RISING: "rise_half_grapefruit",
    SECTION_BREAKFAST: "",
    SECTION_LUNCH: "lunch_green_salad_salmon_or_beef_with_fat_option",
    SECTION_DINNER: "dinner_200g_protein_salad_cooked_greens_olive_oil",
}


def _empty_completed():
    return {section_id: False for section_id in _SECTION_IDS}


def _default_payload(date_key=""):
    return {
        "date": date_key,
        "selections": dict(_DEFAULT_SELECTIONS),
        "completed": _empty_completed(),
    }


def _normalize_date(value):
    if isinstance(value, str) and db_state.DATE_RE.match(value):
        return value
    return ""


def _normalize_selections(raw):
    out = dict(_DEFAULT_SELECTIONS)
    if not isinstance(raw, dict):
        return out
    for section_id in _SECTION_IDS:
        value = raw.get(section_id)
        if not isinstance(value, str):
            continue
        if value in _VALID_OPTIONS_BY_SECTION[section_id] or value == "":
            out[section_id] = value
    return out


def _normalize_completed(raw):
    out = _empty_completed()
    if not isinstance(raw, dict):
        return out
    for section_id in _SECTION_IDS:
        value = raw.get(section_id)
        if isinstance(value, bool):
            out[section_id] = value
    return out


def _normalize_entry(payload):
    if not isinstance(payload, dict):
        return _default_payload()
    date_key = _normalize_date(payload.get("date"))
    return {
        "date": date_key,
        "selections": _normalize_selections(payload.get("selections")),
        "completed": _normalize_completed(payload.get("completed")),
    }


def get_meal_plan_sections():
    return deepcopy(MEAL_PLAN_SECTIONS)


def get_meal_plan_daily(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return _default_payload()

    payload = None
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                payload = (doc.to_dict() or {}).get("meal_plan_daily_v1")
        except Exception as e:
            logger.error("Firestore meal plan read failed", extra={
                "operation": "get_meal_plan_daily",
                "error": str(e),
            })
    if payload is None:
        payload = db_state.meal_plan_daily_memory.get(email_key)
    return _normalize_entry(payload)


def update_meal_plan_daily(email, date_key, selections, completed):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(date_key, str) or not db_state.DATE_RE.match(date_key):
        return False, "invalid_date", None
    payload = {
        "date": date_key,
        "selections": _normalize_selections(selections),
        "completed": _normalize_completed(completed),
    }

    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False, "no_user", None
            doc_ref.set({"meal_plan_daily_v1": payload}, merge=True)
            return True, None, payload
        except Exception as e:
            logger.error("Firestore meal plan write failed", extra={
                "operation": "update_meal_plan_daily",
                "error": str(e),
            })
            return False, "write_failed", None

    if email_key not in db_state.auth_users_memory:
        return False, "no_user", None
    db_state.meal_plan_daily_memory[email_key] = dict(payload)
    return True, None, payload
