import os
import random
import re
import uuid
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
from .logging_service import logger


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CELL_KEY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")
_TODO_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")

# Load environment variables
load_dotenv()

# Global variables for database state
db = None
users_collection_ref = None
auth_users_memory = {}
# In-memory habit cells when Firestore is unavailable (mirrors user doc field habits_v1)
habit_memory = {}
custom_habits_memory = {}
todo_memory = {}
flashcards_memory = {}


def initialize_firebase():
    """Initialize Firebase Admin SDK with Google Cloud automatic authentication"""
    global db, users_collection_ref, auth_users_memory

    try:
        initialize_app()
        logger.info("Firebase initialization successful", extra={
            "auth_method": "google_cloud_automatic",
            "status": "success"
        })
    except ValueError:
        service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if service_account_path and os.path.exists(service_account_path):
            try:
                cred = credentials.Certificate(service_account_path)
                initialize_app(cred)
                logger.info("Firebase initialization successful", extra={
                    "auth_method": "service_account_key",
                    "status": "success"
                })
            except Exception as key_error:
                logger.error("Firebase service account key error", extra={
                    "error": str(key_error),
                    "auth_method": "service_account_key",
                    "status": "failed"
                })
                print("Warning: Falling back to in-memory storage")
                auth_users_memory = {}
                return
        else:
            logger.warning("No Google Cloud credentials found", extra={
                "auth_method": "none",
                "fallback": "in_memory_storage",
                "status": "warning"
            })
            print("Tip: For local development, set GOOGLE_APPLICATION_CREDENTIALS")
            print("Tip: For production, deploy on Google Cloud with proper IAM service account")
            print("Using in-memory storage as fallback")
            auth_users_memory = {}
            return

    try:
        db = firestore.client()
        users_collection_ref = db.collection('users')
        logger.info("Firestore client initialized successfully", extra={
            "database": "firestore",
            "collection": "users",
            "status": "success"
        })

        status = get_database_status()
        logger.info("Database status after initialization", extra={
            "operation": "firebase_initialization",
            "database_status": status,
            "status": "success"
        })

    except Exception as e:
        logger.error("Firestore initialization failed", extra={
            "error": str(e),
            "database": "firestore",
            "status": "failed"
        })
        print("Falling back to in-memory storage")
        db = None
        users_collection_ref = None
        auth_users_memory = {}

        status = get_database_status()
        logger.info("Database status after fallback", extra={
            "operation": "firebase_initialization",
            "database_status": status,
            "fallback": "in_memory_storage",
            "status": "fallback"
        })

        final_status = get_database_status()
        logger.info("Final database status after initialization", extra={
            "operation": "firebase_initialization",
            "final_database_status": final_status,
            "status": "initialization_complete"
        })


def get_database_status():
    """Get current database status and configuration"""
    return {
        "firestore_available": users_collection_ref is not None,
        "users_firestore": users_collection_ref is not None,
        "users_in_memory_count": len(auth_users_memory),
    }


def _normalize_user_email(email):
    return (email or "").strip().lower()


def create_user_record(email, password_hash):
    """Create a user with hashed password. Returns (success, error_code)."""
    global auth_users_memory
    email_key = _normalize_user_email(email)
    if not email_key or "@" not in email_key:
        return False, "invalid_email"

    if users_collection_ref:
        try:
            doc_ref = users_collection_ref.document(email_key)
            if doc_ref.get().exists:
                return False, "exists"
            doc_ref.set({
                "email": email_key,
                "password_hash": password_hash,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
            logger.info("User stored in Firestore", extra={
                "operation": "create_user_record",
                "email": email_key,
                "status": "success",
            })
            return True, None
        except Exception as e:
            logger.error("Firestore user create failed, using memory", extra={
                "operation": "create_user_record",
                "error": str(e),
                "status": "fallback",
            })
            if email_key in auth_users_memory:
                return False, "exists"
            auth_users_memory[email_key] = {
                "email": email_key,
                "password_hash": password_hash,
            }
            return True, None

    if email_key in auth_users_memory:
        return False, "exists"
    auth_users_memory[email_key] = {
        "email": email_key,
        "password_hash": password_hash,
    }
    return True, None


def get_user_record(email):
    """Return dict with email and password_hash, or None."""
    global auth_users_memory
    email_key = _normalize_user_email(email)
    if not email_key:
        return None

    if users_collection_ref:
        try:
            doc = users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return {
                    "email": data.get("email", email_key),
                    "password_hash": data.get("password_hash"),
                }
        except Exception as e:
            logger.error("Firestore user read failed", extra={
                "operation": "get_user_record",
                "error": str(e),
            })

    row = auth_users_memory.get(email_key)
    if row:
        return {
            "email": row["email"],
            "password_hash": row["password_hash"],
        }
    return None


def _user_exists(email_key):
    if users_collection_ref:
        try:
            if users_collection_ref.document(email_key).get().exists:
                return True
        except Exception as e:
            logger.error("Firestore user exists check failed", extra={
                "operation": "_user_exists",
                "error": str(e),
            })
    return email_key in auth_users_memory


def _normalize_habits_dict(raw):
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        m = _CELL_KEY_RE.match(k)
        if not m:
            continue
        date_str, habit_id = m.group(1), m.group(2)
        if not re.match(r"^[a-zA-Z0-9_\-]+$", habit_id):
            continue
        if not _DATE_RE.match(date_str):
            continue
        if v != "done":
            continue
        out[k] = v
    return out


def get_habits_map(email):
    """Return habit cell map keyed as YYYY-MM-DD_habitId -> done."""
    email_key = _normalize_user_email(email)
    if not email_key:
        return {}

    if users_collection_ref:
        try:
            doc = users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                h = data.get("habits_v1")
                return _normalize_habits_dict(h) if isinstance(h, dict) else {}
        except Exception as e:
            logger.error("Firestore habits read failed", extra={
                "operation": "get_habits_map",
                "error": str(e),
            })

    return _normalize_habits_dict(dict(habit_memory.get(email_key, {})))


def _write_habits_map(email_key, habits_dict):
    """Persist full habits map for user."""
    if users_collection_ref:
        try:
            doc_ref = users_collection_ref.document(email_key)
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

    if email_key not in auth_users_memory:
        return False
    habit_memory[email_key] = dict(habits_dict)
    return True


def patch_habit_cell(email, date_str, habit_id, state):
    """
    Set one cell: state is done | none (none removes the key).
    Returns (ok, error_code).
    """
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user"
    if not re.match(r"^[a-zA-Z0-9_\-]+$", str(habit_id)):
        return False, "invalid_habit"
    if not _DATE_RE.match(date_str or ""):
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
    """
    Merge validated cells into stored habits (client keys win).
    incoming: dict cell_key -> done|none; none removes key.
    Returns (ok, error_code, merged_dict).
    """
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None
    if not isinstance(incoming, dict):
        return False, "invalid_body", None
    if len(incoming) > 2500:
        return False, "too_many_keys", None

    habits = get_habits_map(email)
    for k, v in incoming.items():
        if not isinstance(k, str):
            continue
        m = _CELL_KEY_RE.match(k)
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
    """Return custom habits list for user."""
    email_key = _normalize_user_email(email)
    if not email_key:
        return []

    if users_collection_ref:
        try:
            doc = users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                h = data.get("custom_habits_v1")
                return h if isinstance(h, list) else []
        except Exception as e:
            logger.error("Firestore custom habits read failed", extra={
                "operation": "get_custom_habits",
                "error": str(e),
            })

    return list(custom_habits_memory.get(email_key, []))

def update_custom_habits(email, habits_list):
    """Persist full custom habits list for user."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user"
    if not isinstance(habits_list, list):
        return False, "invalid_body"
    
    # Simple validation of habit objects
    valid_habits = []
    for h in habits_list:
        if isinstance(h, dict) and "id" in h and re.match(r"^[a-zA-Z0-9_\-]+$", str(h["id"])):
            valid_habits.append(h)

    if users_collection_ref:
        try:
            doc_ref = users_collection_ref.document(email_key)
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

    if email_key not in auth_users_memory:
        return False, "no_user"
    custom_habits_memory[email_key] = list(valid_habits)
    return True, None


_TODO_TEXT_MAX_LEN = 240
_TODO_MAX_ITEMS = 500
_FLASHCARD_GROUP_NAME_MAX_LEN = 80
_FLASHCARD_TEXT_MAX_LEN = 240
_FLASHCARD_MAX_GROUPS = 200
_FLASHCARD_MAX_CARDS_PER_GROUP = 1000
_NUTRITION_MAX_DAYS = 400
_STOIC_TEXT_MAX_LEN = 1200


def _normalize_todos_list(raw):
    """Return validated todo list: [{ id: str, text: str }, ...]."""
    if not isinstance(raw, list):
        return []

    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        todo_id = item.get("id")
        text = item.get("text")
        if not isinstance(todo_id, str) or not _TODO_ID_RE.match(todo_id):
            continue
        if not isinstance(text, str):
            continue
        text = text.strip()
        if not text:
            continue
        if len(text) > _TODO_TEXT_MAX_LEN:
            continue
        out.append({"id": todo_id, "text": text})
    return out


def get_todos(email):
    """Return user's todos list."""
    email_key = _normalize_user_email(email)
    if not email_key:
        return []

    if users_collection_ref:
        try:
            doc = users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                t = data.get("todos_v1")
                return _normalize_todos_list(t)
        except Exception as e:
            logger.error("Firestore todos read failed", extra={
                "operation": "get_todos",
                "error": str(e),
            })

    return list(todo_memory.get(email_key, []))


def _write_todos_list(email_key, todos_list):
    """Persist full todos list for user."""
    if users_collection_ref:
        try:
            doc_ref = users_collection_ref.document(email_key)
            if not doc_ref.get().exists:
                return False
            doc_ref.set({"todos_v1": todos_list}, merge=True)
            return True
        except Exception as e:
            logger.error("Firestore todos write failed", extra={
                "operation": "_write_todos_list",
                "error": str(e),
            })
            return False

    if email_key not in auth_users_memory:
        return False

    todo_memory[email_key] = list(todos_list)
    return True


def add_todo_item(email, text):
    """Add a todo item. Returns (ok, error_code, todos_list)."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None

    if not isinstance(text, str):
        return False, "invalid_text", None
    text = text.strip()
    if not text:
        return False, "invalid_text", None
    if len(text) > _TODO_TEXT_MAX_LEN:
        return False, "invalid_text", None

    todos = get_todos(email)
    if len(todos) >= _TODO_MAX_ITEMS:
        return False, "too_many_todos", None

    todo_id = uuid.uuid4().hex  # safe for _TODO_ID_RE
    todos.append({"id": todo_id, "text": text})

    if _write_todos_list(email_key, todos):
        return True, None, todos
    return False, "write_failed", None


def delete_todo_item(email, todo_id):
    """Delete a todo item. Returns (ok, error_code, todos_list)."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None

    if not isinstance(todo_id, str) or not _TODO_ID_RE.match(todo_id):
        return False, "invalid_todo_id", None

    todos = get_todos(email)
    next_todos = [t for t in todos if t.get("id") != todo_id]
    if len(next_todos) == len(todos):
        return False, "not_found", None

    if _write_todos_list(email_key, next_todos):
        return True, None, next_todos
    return False, "write_failed", None


def _normalize_flashcard_groups(raw):
    """
    Return validated flashcard groups list:
    [{ id: str, name: str, cards: [{ id: str, front: str, back: str }] }, ...]
    """
    if not isinstance(raw, list):
        return []

    groups_out = []
    seen_group_ids = set()
    for group in raw:
        if not isinstance(group, dict):
            continue

        group_id = group.get("id")
        name = group.get("name")
        if not isinstance(group_id, str) or not _TODO_ID_RE.match(group_id):
            continue
        if group_id in seen_group_ids:
            continue
        if not isinstance(name, str):
            continue
        name = name.strip()
        if not name or len(name) > _FLASHCARD_GROUP_NAME_MAX_LEN:
            continue

        cards_raw = group.get("cards")
        cards_out = []
        seen_card_ids = set()
        if isinstance(cards_raw, list):
            for card in cards_raw:
                if not isinstance(card, dict):
                    continue
                card_id = card.get("id")
                front = card.get("front")
                back = card.get("back")
                if not isinstance(card_id, str) or not _TODO_ID_RE.match(card_id):
                    continue
                if card_id in seen_card_ids:
                    continue
                if not isinstance(front, str) or not isinstance(back, str):
                    continue
                front = front.strip()
                back = back.strip()
                if not front or not back:
                    continue
                if len(front) > _FLASHCARD_TEXT_MAX_LEN or len(back) > _FLASHCARD_TEXT_MAX_LEN:
                    continue
                cards_out.append({"id": card_id, "front": front, "back": back})
                seen_card_ids.add(card_id)
                if len(cards_out) >= _FLASHCARD_MAX_CARDS_PER_GROUP:
                    break

        groups_out.append({"id": group_id, "name": name, "cards": cards_out})
        seen_group_ids.add(group_id)
        if len(groups_out) >= _FLASHCARD_MAX_GROUPS:
            break

    return groups_out


def get_flashcard_groups(email):
    """Return user's flashcard groups."""
    email_key = _normalize_user_email(email)
    if not email_key:
        return []

    if users_collection_ref:
        try:
            doc = users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                groups = data.get("flashcards_v1")
                return _normalize_flashcard_groups(groups)
        except Exception as e:
            logger.error("Firestore flashcards read failed", extra={
                "operation": "get_flashcard_groups",
                "error": str(e),
            })

    return _normalize_flashcard_groups(flashcards_memory.get(email_key, []))


def _write_flashcard_groups(email_key, groups):
    """Persist full flashcard groups list for user."""
    if users_collection_ref:
        try:
            doc_ref = users_collection_ref.document(email_key)
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

    if email_key not in auth_users_memory:
        return False
    flashcards_memory[email_key] = list(groups)
    return True


def update_flashcard_groups(email, groups):
    """Replace user's flashcard groups. Returns (ok, error_code, groups)."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None
    if not isinstance(groups, list):
        return False, "invalid_body", None

    normalized = _normalize_flashcard_groups(groups)
    if _write_flashcard_groups(email_key, normalized):
        return True, None, normalized
    return False, "write_failed", None


def add_flashcard_group(email, name):
    """Add a new flashcard group. Returns (ok, error_code, groups)."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None
    if not isinstance(name, str):
        return False, "invalid_name", None
    name = name.strip()
    if not name or len(name) > _FLASHCARD_GROUP_NAME_MAX_LEN:
        return False, "invalid_name", None

    groups = get_flashcard_groups(email)
    if len(groups) >= _FLASHCARD_MAX_GROUPS:
        return False, "too_many_groups", None

    groups.append({"id": uuid.uuid4().hex, "name": name, "cards": []})
    if _write_flashcard_groups(email_key, groups):
        return True, None, groups
    return False, "write_failed", None


def add_flashcard_to_group(email, group_id, front, back):
    """Add a card to a group. Returns (ok, error_code, groups)."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None
    if not isinstance(group_id, str) or not _TODO_ID_RE.match(group_id):
        return False, "invalid_group_id", None
    if not isinstance(front, str) or not isinstance(back, str):
        return False, "invalid_card_text", None

    front = front.strip()
    back = back.strip()
    if not front or not back:
        return False, "invalid_card_text", None
    if len(front) > _FLASHCARD_TEXT_MAX_LEN or len(back) > _FLASHCARD_TEXT_MAX_LEN:
        return False, "invalid_card_text", None

    groups = get_flashcard_groups(email)
    target_group = None
    for group in groups:
        if group.get("id") == group_id:
            target_group = group
            break

    if target_group is None:
        return False, "group_not_found", None
    if len(target_group.get("cards", [])) >= _FLASHCARD_MAX_CARDS_PER_GROUP:
        return False, "too_many_cards", None

    target_group["cards"].append({
        "id": uuid.uuid4().hex,
        "front": front,
        "back": back,
    })

    normalized = _normalize_flashcard_groups(groups)
    if _write_flashcard_groups(email_key, normalized):
        return True, None, normalized
    return False, "write_failed", None


def get_random_flashcards(email, group_id=None):
    """
    Return a randomized flashcard list, optionally scoped to one group.
    Each card also includes group metadata for UI rendering.
    """
    groups = get_flashcard_groups(email)
    if isinstance(group_id, str) and group_id.strip():
        group_id = group_id.strip()
        groups = [g for g in groups if g.get("id") == group_id]
        if not groups:
            return False, "group_not_found", None

    cards = []
    for group in groups:
        g_id = group.get("id")
        g_name = group.get("name")
        for card in group.get("cards", []):
            cards.append({
                "id": card.get("id"),
                "front": card.get("front"),
                "back": card.get("back"),
                "groupId": g_id,
                "groupName": g_name,
            })

    random.shuffle(cards)
    return True, None, cards


def _normalize_nutrition_history(raw):
    """
    Validate daily nutrition history map:
    {
      "YYYY-MM-DD": { "calories"?: int, "weight"?: float, "waterMl"?: int },
      ...
    }
    """
    if not isinstance(raw, dict):
        return {}

    out = {}
    for date_key, row in raw.items():
        if not isinstance(date_key, str) or not _DATE_RE.match(date_key):
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
        if len(out) >= _NUTRITION_MAX_DAYS:
            break

    return out


def get_nutrition_history(email):
    """Return nutrition history map for user."""
    email_key = _normalize_user_email(email)
    if not email_key:
        return {}

    if users_collection_ref:
        try:
            doc = users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return _normalize_nutrition_history(data.get("nutrition_v1"))
        except Exception as e:
            logger.error("Firestore nutrition read failed", extra={
                "operation": "get_nutrition_history",
                "error": str(e),
            })

    row = auth_users_memory.get(email_key, {})
    return _normalize_nutrition_history(row.get("nutrition_v1"))


def update_nutrition_history(email, history):
    """Replace nutrition history map. Returns (ok, error_code, history)."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None
    if not isinstance(history, dict):
        return False, "invalid_body", None

    normalized = _normalize_nutrition_history(history)
    if users_collection_ref:
        try:
            doc_ref = users_collection_ref.document(email_key)
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

    if email_key not in auth_users_memory:
        return False, "no_user", None
    auth_users_memory[email_key]["nutrition_v1"] = dict(normalized)
    return True, None, normalized


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
        if isinstance(v, str):
            out[k] = v.strip()[:_STOIC_TEXT_MAX_LEN]
        else:
            out[k] = ""
    return out


def get_stoic_journal(email):
    """Return stoic journal payload { date, form }."""
    email_key = _normalize_user_email(email)
    if not email_key:
        return {"date": "", "form": _normalize_stoic_form({})}

    payload = None
    if users_collection_ref:
        try:
            doc = users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                payload = data.get("stoic_v1")
        except Exception as e:
            logger.error("Firestore stoic read failed", extra={
                "operation": "get_stoic_journal",
                "error": str(e),
            })
    if payload is None:
        payload = auth_users_memory.get(email_key, {}).get("stoic_v1")

    if not isinstance(payload, dict):
        return {"date": "", "form": _normalize_stoic_form({})}

    date_key = payload.get("date")
    if not isinstance(date_key, str) or not _DATE_RE.match(date_key):
        date_key = ""
    form = _normalize_stoic_form(payload.get("form"))
    return {"date": date_key, "form": form}


def update_stoic_journal(email, date_key, form):
    """Replace today's stoic journal payload. Returns (ok, error, payload)."""
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user", None
    if not isinstance(date_key, str) or not _DATE_RE.match(date_key):
        return False, "invalid_date", None

    payload = {"date": date_key, "form": _normalize_stoic_form(form)}
    if users_collection_ref:
        try:
            doc_ref = users_collection_ref.document(email_key)
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

    if email_key not in auth_users_memory:
        return False, "no_user", None
    auth_users_memory[email_key]["stoic_v1"] = dict(payload)
    return True, None, payload
