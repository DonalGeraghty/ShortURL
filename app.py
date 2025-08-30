from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
from datetime import datetime
from core.url_service import shorten_url, get_long_url
from services.logging_service import get_flask_app_logger

import firebase_admin
import google.cloud
from firebase_admin import credentials, firestore

# Initialize logger
logger = get_flask_app_logger()

app = Flask(__name__)
CORS(app)

# Request logging middleware
@app.before_request
def log_request_info():
    """Log request information before processing"""
    request.start_time = time.time()
    
    # Extract client information
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    logger.info("Request received", extra={
        "operation": "request_received",
        "method": request.method,
        "path": request.path,
        "client_ip": client_ip,
        "user_agent": user_agent[:100],  # Truncate long user agents
        "content_length": request.content_length or 0,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.after_request
def log_response_info(response):
    """Log response information after processing"""
    if hasattr(request, 'start_time'):
        duration = (time.time() - request.start_time) * 1000  # Convert to milliseconds
        
        logger.info("Request completed", extra={
            "operation": "request_completed",
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration, 2),
            "response_size": len(response.get_data()),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return response

@app.route('/api/data', methods=['POST'])
def handle_post():
    """
    Handle POST requests to /api/data endpoint
    Accepts string input and returns string output
    """
    start_time = time.time()
    
    logger.info("URL shortening request started", extra={
        "operation": "handle_post",
        "endpoint": "/api/data",
        "method": "POST"
    })
    
    try:
        # Get the raw text data from request
        if request.is_json:
            # If JSON is sent, extract the string value
            data = request.get_json()
            if isinstance(data, dict) and 'text' in data:
                input_string = data['text']
            elif isinstance(data, str):
                input_string = data
            else:
                logger.warning("Invalid JSON format received", extra={
                    "operation": "handle_post",
                    "error": "invalid_json_format",
                    "received_data": str(data)[:200]  # Truncate long data
                })
                return "Error: Please send a string or {'text': 'your string'}", 400
        else:
            # If raw text is sent
            input_string = request.get_data(as_text=True)
        
        # Validate that we have a string
        if not input_string or not isinstance(input_string, str):
            logger.warning("Invalid input received", extra={
                "operation": "handle_post",
                "error": "invalid_input",
                "input_type": type(input_string).__name__,
                "input_length": len(str(input_string)) if input_string else 0
            })
            return "Error: Please provide a valid string input", 400
        
        logger.info("Input validation successful", extra={
            "operation": "handle_post",
            "input_length": len(input_string),
            "input_domain": input_string.split('/')[2] if len(input_string.split('/')) > 2 else "unknown"
        })
        
        # Process the string using the shorten_url method
        shortened_result = shorten_url(input_string)
        
        duration = (time.time() - start_time) * 1000
        logger.info("URL shortening completed successfully", extra={
            "operation": "handle_post",
            "result": shortened_result,
            "duration_ms": round(duration, 2),
            "status": "success"
        })
        
        return shortened_result, 200
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("URL shortening failed", extra={
            "operation": "handle_post",
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": round(duration, 2),
            "status": "error"
        })
        return f"Error: {str(e)}", 500

@app.route('/api/url/<short_code>', methods=['GET'])
def get_url(short_code):
    """
    Handle GET requests to retrieve the long URL from a short code
    """
    start_time = time.time()
    
    logger.info("URL retrieval request started", extra={
        "operation": "get_url",
        "endpoint": f"/api/url/{short_code}",
        "method": "GET",
        "short_code": short_code
    })
    
    try:
        # Get the long URL using the short code
        long_url = get_long_url(short_code)
        
        if long_url:
            duration = (time.time() - start_time) * 1000
            logger.info("URL retrieval completed successfully", extra={
                "operation": "get_url",
                "short_code": short_code,
                "long_url_domain": long_url.split('/')[2] if len(long_url.split('/')) > 2 else "unknown",
                "duration_ms": round(duration, 2),
                "status": "success"
            })
            
            return jsonify({
                'short_code': short_code,
                'long_url': long_url,
                'status': 'success'
            }), 200
        else:
            duration = (time.time() - start_time) * 1000
            logger.warning("URL not found", extra={
                "operation": "get_url",
                "short_code": short_code,
                "duration_ms": round(duration, 2),
                "status": "not_found"
            })
            
            return jsonify({
                'short_code': short_code,
                'error': 'Short code not found',
                'status': 'error'
            }), 404
            
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("URL retrieval failed", extra={
            "operation": "get_url",
            "short_code": short_code,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": round(duration, 2),
            "status": "error"
        })
        
        return jsonify({
            'short_code': short_code,
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/firestore-test', methods=['GET'])
def firestore_test():
    """
    Test endpoint for Firestore functionality
    """
    start_time = time.time()
    
    logger.info("Firestore test request received", extra={
        "operation": "firestore_test",
        "endpoint": "/api/firestore-test",
        "method": "GET"
    })
    
    try:
        service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        cred = credentials.Certificate(service_account_path)
        app = firebase_admin.initialize_app(cred)

        store = firestore.client()

        doc_ref = store.collection(u'test')
        doc_ref.add({u'name': u'test', u'added': u'just now'})
        
        # This is a blank function as requested
        # You can add Firestore testing logic here later
        
        duration = (time.time() - start_time) * 1000
        logger.info("Firestore test completed", extra={
            "operation": "firestore_test",
            "duration_ms": round(duration, 2),
            "status": "success"
        })
        
        return jsonify({
            'message': 'Firestore test endpoint reached successfully',
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("Firestore test failed", extra={
            "operation": "firestore_test",
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_ms": round(duration, 2),
            "status": "error"
        })
        
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    start_time = time.time()
    
    logger.info("Health check request received", extra={
        "operation": "health_check",
        "endpoint": "/health",
        "method": "GET"
    })
    
    try:
        # Basic health checks
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'app_running': True,
                'timestamp': True
            }
        }
        
        duration = (time.time() - start_time) * 1000
        logger.info("Health check completed", extra={
            "operation": "health_check",
            "status": "healthy",
            "duration_ms": round(duration, 2)
        })
        
        return jsonify(health_status), 200
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("Health check failed", extra={
            "operation": "health_check",
            "error": str(e),
            "duration_ms": round(duration, 2),
            "status": "unhealthy"
        })
        
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information"""
    start_time = time.time()
    
    logger.info("Root endpoint request received", extra={
        "operation": "root",
        "endpoint": "/",
        "method": "GET"
    })
    
    try:
        api_info = {
            'message': 'URL Shortener API',
            'version': '1.0.0',
            'endpoints': {
                'POST /api/data': 'Create short URL from long URL',
                'GET /api/url/<short_code>': 'Get long URL from short code',
                'GET /health': 'Health check endpoint',
                'GET /': 'This information endpoint'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        duration = (time.time() - start_time) * 1000
        logger.info("Root endpoint completed", extra={
            "operation": "root",
            "duration_ms": round(duration, 2),
            "status": "success"
        })
        
        return jsonify(api_info), 200
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error("Root endpoint failed", extra={
            "operation": "root",
            "error": str(e),
            "duration_ms": round(duration, 2),
            "status": "error"
        })
        
        return jsonify({
            'error': 'Failed to retrieve API information',
            'timestamp': datetime.now().isoformat()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning("404 error occurred", extra={
        "operation": "error_handler",
        "error_code": 404,
        "path": request.path,
        "method": request.method
    })
    return jsonify({
        'error': 'Endpoint not found',
        'path': request.path,
        'method': request.method,
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error("500 error occurred", extra={
        "operation": "error_handler",
        "error_code": 500,
        "path": request.path,
        "method": request.method,
        "error": str(error)
    })
    return jsonify({
        'error': 'Internal server error',
        'timestamp': datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info("Starting Flask server", extra={
        "operation": "server_start",
        "port": port,
        "debug_mode": debug,
        "environment": os.environ.get('FLASK_ENV', 'production')
    })
    
    print(f"Starting Flask server on port {port}")
    print(f"Debug mode: {debug}")
    print(f"API endpoint: http://localhost:{port}/api/data")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
