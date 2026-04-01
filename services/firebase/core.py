import os
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv

from . import db_state
from ..logging_service import logger

load_dotenv()


def initialize_firebase():
    """Initialize Firebase Admin SDK with Google Cloud automatic authentication."""
    try:
        initialize_app()
        logger.info("Firebase initialization successful", extra={
            "auth_method": "google_cloud_automatic",
            "status": "success"
        })
    except ValueError:
        service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
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
                db_state.auth_users_memory = {}
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
            db_state.auth_users_memory = {}
            return

    try:
        db_state.db = firestore.client()
        db_state.users_collection_ref = db_state.db.collection("users")
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
        db_state.db = None
        db_state.users_collection_ref = None
        db_state.auth_users_memory = {}
        status = get_database_status()
        logger.info("Database status after fallback", extra={
            "operation": "firebase_initialization",
            "database_status": status,
            "fallback": "in_memory_storage",
            "status": "fallback"
        })


def get_database_status():
    return {
        "firestore_available": db_state.users_collection_ref is not None,
        "users_firestore": db_state.users_collection_ref is not None,
        "users_in_memory_count": len(db_state.auth_users_memory),
    }


def normalize_user_email(email):
    return (email or "").strip().lower()


def user_exists(email_key):
    if db_state.users_collection_ref:
        try:
            if db_state.users_collection_ref.document(email_key).get().exists:
                return True
        except Exception as e:
            logger.error("Firestore user exists check failed", extra={
                "operation": "user_exists",
                "error": str(e),
            })
    return email_key in db_state.auth_users_memory
