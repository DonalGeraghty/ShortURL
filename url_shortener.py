import hashlib
import os
import logging
import time
from datetime import datetime
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for Google Cloud Run
def setup_logging():
    """Configure structured logging for Google Cloud Run"""
    # Create logger
    logger = logging.getLogger('url_shortener')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with structured format
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    # Create formatter for structured logging
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

# Initialize logger
logger = setup_logging()

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

def generate_md5_code(url, length=6):
    """Generate MD5 hash code for URL shortening"""
    start_time = time.time()
    hash_object = hashlib.md5(url.encode())
    short_code = hash_object.hexdigest()[:length]
    
    # Log performance metrics
    duration = (time.time() - start_time) * 1000  # Convert to milliseconds
    logger.info("MD5 code generated", extra={
        "operation": "generate_md5_code",
        "url_length": len(url),
        "short_code_length": len(short_code),
        "duration_ms": round(duration, 2),
        "status": "success"
    })
    
    return short_code

def shorten_url(long_url):
    """Shorten a long URL and store in database"""
    start_time = time.time()
    
    # Input validation logging
    logger.info("URL shortening request received", extra={
        "operation": "shorten_url",
        "url_length": len(long_url),
        "url_domain": long_url.split('/')[2] if len(long_url.split('/')) > 2 else "unknown"
    })
    
    try:
        short_code = generate_md5_code(long_url)
        
        # Store mapping in Firestore
        if collection_ref:
            try:
                # Check if URL already exists
                existing_docs = collection_ref.where('long_url', '==', long_url).limit(1).stream()
                existing_doc = next(existing_docs, None)
                
                if existing_doc:
                    # Return existing short code if URL was already shortened
                    duration = (time.time() - start_time) * 1000
                    logger.info("URL already shortened, returning existing code", extra={
                        "operation": "shorten_url",
                        "action": "return_existing",
                        "short_code": existing_doc.id,
                        "duration_ms": round(duration, 2),
                        "status": "success"
                    })
                    return f"{existing_doc.id}"
                
                # Store new URL mapping
                doc_ref = collection_ref.document(short_code)
                doc_ref.set({
                    'long_url': long_url,
                    'short_code': short_code,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                
                duration = (time.time() - start_time) * 1000
                logger.info("URL shortened and stored in Firestore", extra={
                    "operation": "shorten_url",
                    "action": "store_new",
                    "short_code": short_code,
                    "database": "firestore",
                    "duration_ms": round(duration, 2),
                    "status": "success"
                })
                
            except Exception as e:
                logger.error("Firestore storage failed, falling back to in-memory", extra={
                    "operation": "shorten_url",
                    "error": str(e),
                    "database": "firestore",
                    "fallback": "in_memory",
                    "status": "error"
                })
                # Fallback to in-memory storage
                if 'url_database' not in globals():
                    globals()['url_database'] = {}
                url_database[short_code] = long_url
        else:
            # Fallback to in-memory storage
            if 'url_database' not in globals():
                globals()['url_database'] = {}
            url_database[short_code] = long_url
            
            logger.info("URL shortened and stored in memory", extra={
                "operation": "shorten_url",
                "action": "store_new",
                "short_code": short_code,
                "database": "in_memory",
                "status": "success"
            })
        
        duration = (time.time() - start_time) * 1000
        logger.info("URL shortening completed", extra={
            "operation": "shorten_url",
            "short_code": short_code,
            "total_duration_ms": round(duration, 2),
            "status": "success"
        })
        
        return f"{short_code}"
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("URL shortening failed", extra={
            "operation": "shorten_url",
            "error": str(e),
            "duration_ms": round(duration, 2),
            "status": "error"
        })
        raise

def get_long_url(short_code):
    """Retrieve the long URL from Firestore or in-memory storage"""
    start_time = time.time()
    
    logger.info("URL retrieval request received", extra={
        "operation": "get_long_url",
        "short_code": short_code,
        "short_code_length": len(short_code)
    })
    
    try:
        if collection_ref:
            try:
                doc = collection_ref.document(short_code).get()
                if doc.exists:
                    long_url = doc.to_dict()['long_url']
                    duration = (time.time() - start_time) * 1000
                    logger.info("URL retrieved from Firestore", extra={
                        "operation": "get_long_url",
                        "short_code": short_code,
                        "database": "firestore",
                        "duration_ms": round(duration, 2),
                        "status": "success"
                    })
                    return long_url
                else:
                    logger.warning("Short code not found in Firestore", extra={
                        "operation": "get_long_url",
                        "short_code": short_code,
                        "database": "firestore",
                        "status": "not_found"
                    })
            except Exception as e:
                logger.error("Firestore retrieval failed", extra={
                    "operation": "get_long_url",
                    "short_code": short_code,
                    "error": str(e),
                    "database": "firestore",
                    "status": "error"
                })
        
        # Fallback to in-memory storage
        if 'url_database' in globals():
            long_url = url_database.get(short_code)
            if long_url:
                duration = (time.time() - start_time) * 1000
                logger.info("URL retrieved from memory", extra={
                    "operation": "get_long_url",
                    "short_code": short_code,
                    "database": "in_memory",
                    "duration_ms": round(duration, 2),
                    "status": "success"
                })
                return long_url
        
        duration = (time.time() - start_time) * 1000
        logger.warning("URL not found in any storage", extra={
            "operation": "get_long_url",
            "short_code": short_code,
            "duration_ms": round(duration, 2),
            "status": "not_found"
        })
        
        return None
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("URL retrieval failed", extra={
            "operation": "get_long_url",
            "short_code": short_code,
            "error": str(e),
            "duration_ms": round(duration, 2),
            "status": "error"
        })
        return None