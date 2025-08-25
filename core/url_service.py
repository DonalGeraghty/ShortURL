import hashlib
import time
from datetime import datetime
from services.logging_service import logger
from services.firebase_service import (
    initialize_firebase,
    store_url_mapping,
    check_url_exists,
    retrieve_url_mapping
)

# Initialize Firebase service
initialize_firebase()

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
        
        # Check if URL already exists
        existing_short_code = check_url_exists(long_url)
        if existing_short_code:
            duration = (time.time() - start_time) * 1000
            logger.info("URL already shortened, returning existing code", extra={
                "operation": "shorten_url",
                "action": "return_existing",
                "short_code": existing_short_code,
                "duration_ms": round(duration, 2),
                "status": "success"
            })
            return f"{existing_short_code}"
        
        # Store new URL mapping
        store_url_mapping(short_code, long_url)
        
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
        long_url = retrieve_url_mapping(short_code)
        
        if long_url:
            duration = (time.time() - start_time) * 1000
            logger.info("URL retrieved successfully", extra={
                "operation": "get_long_url",
                "short_code": short_code,
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