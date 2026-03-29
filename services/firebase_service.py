import os
import re
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
from .logging_service import logger

HABIT_IDS = frozenset({"spar", "bigshop", "amazon", "workout", "subs", "save"})
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CELL_KEY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")

# Load environment variables
load_dotenv()

# Global variables for database state
db = None
users_collection_ref = None
auth_users_memory = {}
# In-memory habit cells when Firestore is unavailable (mirrors user doc field habits_v1)
habit_memory = {}


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
        if habit_id not in HABIT_IDS:
            continue
        if not _DATE_RE.match(date_str):
            continue
        if v not in ("done", "fail"):
            continue
        out[k] = v
    return out


def get_habits_map(email):
    """Return habit cell map keyed as YYYY-MM-DD_habitId -> done|fail."""
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
    Set one cell: state is done | fail | none (none removes the key).
    Returns (ok, error_code).
    """
    email_key = _normalize_user_email(email)
    if not email_key or not _user_exists(email_key):
        return False, "no_user"
    if habit_id not in HABIT_IDS:
        return False, "invalid_habit"
    if not _DATE_RE.match(date_str or ""):
        return False, "invalid_date"
    if state not in ("done", "fail", "none"):
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
    incoming: dict cell_key -> done|fail|none; none removes key.
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
        if habit_id not in HABIT_IDS:
            continue
        if v == "none":
            habits.pop(k, None)
        elif v in ("done", "fail"):
            habits[k] = v

    habits = _normalize_habits_dict(habits)
    if _write_habits_map(email_key, habits):
        return True, None, habits
    return False, "write_failed", None
