from firebase_admin import firestore

from . import db_state
from .core import normalize_user_email
from ..logging_service import logger


def create_user_record(email, password_hash):
    email_key = normalize_user_email(email)
    if not email_key or "@" not in email_key:
        return False, "invalid_email"

    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
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
            if email_key in db_state.auth_users_memory:
                return False, "exists"
            db_state.auth_users_memory[email_key] = {
                "email": email_key,
                "password_hash": password_hash,
            }
            return True, None

    if email_key in db_state.auth_users_memory:
        return False, "exists"
    db_state.auth_users_memory[email_key] = {
        "email": email_key,
        "password_hash": password_hash,
    }
    return True, None


def get_user_record(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return None

    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
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

    row = db_state.auth_users_memory.get(email_key)
    if row:
        return {
            "email": row["email"],
            "password_hash": row["password_hash"],
        }
    return None


def _clear_user_memory(email_key):
    """Remove all in-memory rows for a user (used when deleting account or syncing with Firestore delete)."""
    db_state.auth_users_memory.pop(email_key, None)
    db_state.habit_memory.pop(email_key, None)
    db_state.custom_habits_memory.pop(email_key, None)
    db_state.habit_categories_memory.pop(email_key, None)
    db_state.todo_memory.pop(email_key, None)
    db_state.flashcards_memory.pop(email_key, None)
    db_state.day_planner_options_memory.pop(email_key, None)
    db_state.day_planner_daily_memory.pop(email_key, None)
    db_state.meal_plan_daily_memory.pop(email_key, None)


def delete_user_account(email):
    """
    Delete the Firestore user document (all fields) and clear in-memory stores for that user.
    Returns (success, error_code).
    """
    email_key = normalize_user_email(email)
    if not email_key:
        return False, "invalid_email"

    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
            if doc_ref.get().exists:
                doc_ref.delete()
            logger.info("User account deleted from Firestore", extra={
                "operation": "delete_user_account",
                "email": email_key,
                "status": "success",
            })
        except Exception as e:
            logger.error("Firestore user delete failed", extra={
                "operation": "delete_user_account",
                "email": email_key,
                "error": str(e),
            })
            return False, "delete_failed"

    _clear_user_memory(email_key)
    return True, None
