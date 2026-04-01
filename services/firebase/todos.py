import uuid

from . import db_state
from .core import normalize_user_email, user_exists
from ..logging_service import logger

TODO_TEXT_MAX_LEN = 240
TODO_MAX_ITEMS = 500


def _normalize_todos_list(raw):
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        todo_id = item.get("id")
        text = item.get("text")
        if not isinstance(todo_id, str) or not db_state.TODO_ID_RE.match(todo_id):
            continue
        if not isinstance(text, str):
            continue
        text = text.strip()
        if not text or len(text) > TODO_TEXT_MAX_LEN:
            continue
        out.append({"id": todo_id, "text": text})
    return out


def get_todos(email):
    email_key = normalize_user_email(email)
    if not email_key:
        return []
    if db_state.users_collection_ref:
        try:
            doc = db_state.users_collection_ref.document(email_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return _normalize_todos_list(data.get("todos_v1"))
        except Exception as e:
            logger.error("Firestore todos read failed", extra={
                "operation": "get_todos",
                "error": str(e),
            })
    return list(db_state.todo_memory.get(email_key, []))


def _write_todos_list(email_key, todos_list):
    if db_state.users_collection_ref:
        try:
            doc_ref = db_state.users_collection_ref.document(email_key)
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

    if email_key not in db_state.auth_users_memory:
        return False
    db_state.todo_memory[email_key] = list(todos_list)
    return True


def add_todo_item(email, text):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(text, str):
        return False, "invalid_text", None
    text = text.strip()
    if not text or len(text) > TODO_TEXT_MAX_LEN:
        return False, "invalid_text", None

    todos = get_todos(email)
    if len(todos) >= TODO_MAX_ITEMS:
        return False, "too_many_todos", None
    todos.append({"id": uuid.uuid4().hex, "text": text})
    if _write_todos_list(email_key, todos):
        return True, None, todos
    return False, "write_failed", None


def delete_todo_item(email, todo_id):
    email_key = normalize_user_email(email)
    if not email_key or not user_exists(email_key):
        return False, "no_user", None
    if not isinstance(todo_id, str) or not db_state.TODO_ID_RE.match(todo_id):
        return False, "invalid_todo_id", None

    todos = get_todos(email)
    next_todos = [t for t in todos if t.get("id") != todo_id]
    if len(next_todos) == len(todos):
        return False, "not_found", None
    if _write_todos_list(email_key, next_todos):
        return True, None, next_todos
    return False, "write_failed", None
