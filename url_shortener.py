import hashlib
import os
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK with Google Cloud automatic authentication
# This will work automatically when deployed on Google Cloud
try:
    # Try to initialize with default credentials (Google Cloud automatic auth)
    # This works when running on Google Cloud (Cloud Run, App Engine, Compute Engine, etc.)
    initialize_app()
    print("✅ Successfully initialized with Google Cloud automatic authentication")
except ValueError as e:
    # If no default credentials, try to initialize with service account key file (for local development)
    service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if service_account_path and os.path.exists(service_account_path):
        try:
            cred = credentials.Certificate(service_account_path)
            initialize_app(cred)
            print("✅ Successfully initialized with service account key file")
        except Exception as key_error:
            print(f"❌ Error with service account key: {key_error}")
            print("⚠️  Falling back to in-memory storage")
            url_database = {}
    else:
        # Fallback to in-memory storage if no credentials available
        print("⚠️  No Google Cloud credentials found")
        print("💡 For local development: Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        print("💡 For production: Deploy on Google Cloud with proper IAM service account")
        print("📝 Using in-memory storage as fallback")
        url_database = {}

# Initialize Firestore client
try:
    db = firestore.client()
    collection_ref = db.collection('shortened_urls')
    print("✅ Firestore client initialized successfully")
except Exception as e:
    print(f"❌ Could not initialize Firestore: {e}")
    print("📝 Falling back to in-memory storage")
    db = None
    collection_ref = None
    url_database = {}

def generate_md5_code(url, length=6):
    hash_object = hashlib.md5(url.encode())
    return hash_object.hexdigest()[:length]

def shorten_url(long_url):
    short_code = generate_md5_code(long_url)
    
    # Store mapping in Firestore
    if collection_ref:
        try:
            # Check if URL already exists
            existing_docs = collection_ref.where('long_url', '==', long_url).limit(1).stream()
            existing_doc = next(existing_docs, None)
            
            if existing_doc:
                # Return existing short code if URL was already shortened
                return f"{existing_doc.id}"
            
            # Store new URL mapping
            doc_ref = collection_ref.document(short_code)
            doc_ref.set({
                'long_url': long_url,
                'short_code': short_code,
                'created_at': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"❌ Error storing in Firestore: {e}")
            # Fallback to in-memory storage
            if 'url_database' not in globals():
                globals()['url_database'] = {}
            url_database[short_code] = long_url
    else:
        # Fallback to in-memory storage
        if 'url_database' not in globals():
            globals()['url_database'] = {}
        url_database[short_code] = long_url
    
    return f"{short_code}"

def get_long_url(short_code):
    """Retrieve the long URL from Firestore or in-memory storage"""
    if collection_ref:
        try:
            doc = collection_ref.document(short_code).get()
            if doc.exists:
                return doc.to_dict()['long_url']
        except Exception as e:
            print(f"❌ Error retrieving from Firestore: {e}")
    
    # Fallback to in-memory storage
    if 'url_database' in globals():
        return url_database.get(short_code)
    
    return None