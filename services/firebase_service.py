import os
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
from .logging_service import logger

# Load environment variables
load_dotenv()

# Global variables for database state
db = None
users_collection_ref = None
auth_users_memory = {}


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
