import os
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
from logging_config import logger

# Load environment variables
load_dotenv()

# Global variables for database state
db = None
collection_ref = None
url_database = {}

def initialize_firebase():
    """Initialize Firebase Admin SDK with Google Cloud automatic authentication"""
    global db, collection_ref, url_database
    
    # Initialize Firebase Admin SDK with Google Cloud automatic authentication
    # This will work automatically when deployed on Google Cloud
    try:
        # Try to initialize with default credentials (Google Cloud automatic auth)
        # This works when running on Google Cloud (Cloud Run, App Engine, Compute Engine, etc.)
        initialize_app()
        logger.info("Firebase initialization successful", extra={
            "auth_method": "google_cloud_automatic",
            "status": "success"
        })
    except ValueError as e:
        # If no default credentials, try to initialize with service account key file (for local development)
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
                print("⚠️  Falling back to in-memory storage")
                url_database = {}
                return
        else:
            # Fallback to in-memory storage if no credentials available
            logger.warning("No Google Cloud credentials found", extra={
                "auth_method": "none",
                "fallback": "in_memory_storage",
                "status": "warning"
            })
            print("💡 For local development: Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
            print("💡 For production: Deploy on Google Cloud with proper IAM service account")
            print("📝 Using in-memory storage as fallback")
            url_database = {}
            return

    # Initialize Firestore client
    try:
        db = firestore.client()
        collection_ref = db.collection('shortened_urls')
        logger.info("Firestore client initialized successfully", extra={
            "database": "firestore",
            "collection": "shortened_urls",
            "status": "success"
        })
    except Exception as e:
        logger.error("Firestore initialization failed", extra={
            "error": str(e),
            "database": "firestore",
            "status": "failed"
        })
        print("📝 Falling back to in-memory storage")
        db = None
        collection_ref = None
        url_database = {}

def store_url_mapping(short_code, long_url):
    """Store URL mapping in Firestore or fallback to in-memory storage"""
    global url_database
    
    if collection_ref:
        try:
            doc_ref = collection_ref.document(short_code)
            doc_ref.set({
                'long_url': long_url,
                'short_code': short_code,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            logger.info("URL mapping stored in Firestore", extra={
                "operation": "store_url_mapping",
                "short_code": short_code,
                "database": "firestore",
                "status": "success"
            })
            return True
        except Exception as e:
            logger.error("Firestore storage failed, falling back to in-memory", extra={
                "operation": "store_url_mapping",
                "error": str(e),
                "database": "firestore",
                "fallback": "in_memory",
                "status": "error"
            })
            # Fallback to in-memory storage
            url_database[short_code] = long_url
            return False
    else:
        # Fallback to in-memory storage
        url_database[short_code] = long_url
        logger.info("URL mapping stored in memory", extra={
            "operation": "store_url_mapping",
            "short_code": short_code,
            "database": "in_memory",
            "status": "success"
        })
        return False

def check_url_exists(long_url):
    """Check if URL already exists in Firestore"""
    if collection_ref:
        try:
            existing_docs = collection_ref.where('long_url', '==', long_url).limit(1).stream()
            existing_doc = next(existing_docs, None)
            if existing_doc:
                logger.info("URL already exists in Firestore", extra={
                    "operation": "check_url_exists",
                    "existing_short_code": existing_doc.id,
                    "database": "firestore",
                    "status": "found"
                })
                return existing_doc.id
        except Exception as e:
            logger.error("Firestore check failed", extra={
                "operation": "check_url_exists",
                "error": str(e),
                "database": "firestore",
                "status": "error"
            })
    
    # Check in-memory storage as fallback
    for short_code, stored_url in url_database.items():
        if stored_url == long_url:
            logger.info("URL already exists in memory", extra={
                "operation": "check_url_exists",
                "existing_short_code": short_code,
                "database": "in_memory",
                "status": "found"
            })
            return short_code
    
    return None

def retrieve_url_mapping(short_code):
    """Retrieve URL mapping from Firestore or in-memory storage"""
    if collection_ref:
        try:
            doc = collection_ref.document(short_code).get()
            if doc.exists:
                long_url = doc.to_dict()['long_url']
                logger.info("URL mapping retrieved from Firestore", extra={
                    "operation": "retrieve_url_mapping",
                    "short_code": short_code,
                    "database": "firestore",
                    "status": "success"
                })
                return long_url
        except Exception as e:
            logger.error("Firestore retrieval failed", extra={
                "operation": "retrieve_url_mapping",
                "short_code": short_code,
                "error": str(e),
                "database": "firestore",
                "status": "error"
            })
    
    # Fallback to in-memory storage
    long_url = url_database.get(short_code)
    if long_url:
        logger.info("URL mapping retrieved from memory", extra={
            "operation": "retrieve_url_mapping",
            "short_code": short_code,
            "database": "in_memory",
            "status": "success"
        })
        return long_url
    
    return None

def get_database_status():
    """Get current database status and configuration"""
    return {
        "firestore_available": collection_ref is not None,
        "in_memory_available": True,
        "url_count": len(url_database),
        "collection_name": "shortened_urls" if collection_ref else None
    }
