# Portfolio auth API — codename Janus (Roman god of doorways and transitions).

# Standard library imports
import os
import time
from datetime import datetime

# Third-party imports
from flask import Flask, request, jsonify
from flask_cors import CORS

# Local imports
from core.auth_service import (
    decode_access_token,
    login_user,
    register_user,
)
from services.logging_service import get_flask_app_logger
from services.firebase_service import (
    get_habits_map, merge_habits_map, patch_habit_cell,
    get_custom_habits, update_custom_habits
)

# Initialize logger
logger = get_flask_app_logger()

app = Flask(__name__)
CORS(app)


def _bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None

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


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    payload, err, _ = register_user(email, password)
    if err == "invalid_email":
        return jsonify({"status": "error", "error": "Invalid email"}), 400
    if err == "weak_password":
        return jsonify({
            "status": "error",
            "error": "Password must be at least 8 characters",
        }), 400
    if err == "exists":
        return jsonify({"status": "error", "error": "An account with this email already exists"}), 409
    if err:
        return jsonify({"status": "error", "error": "Registration failed"}), 500
    return jsonify({
        "status": "success",
        "token": payload["token"],
        "user": {"email": payload["email"]},
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    payload, err, _ = login_user(email, password)
    if err:
        return jsonify({"status": "error", "error": "Invalid email or password"}), 401
    return jsonify({
        "status": "success",
        "token": payload["token"],
        "user": {"email": payload["email"]},
    }), 200


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    token = _bearer_token()
    email = decode_access_token(token)
    if not email:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    return jsonify({"status": "success", "user": {"email": email}}), 200


@app.route("/api/habits", methods=["GET"])
def habits_get():
    token = _bearer_token()
    email = decode_access_token(token)
    if not email:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    cells = get_habits_map(email)
    return jsonify({"status": "success", "cells": cells}), 200


@app.route("/api/habits", methods=["PUT"])
def habits_put_merge():
    token = _bearer_token()
    email = decode_access_token(token)
    if not email:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    incoming = data.get("cells")
    if not isinstance(incoming, dict):
        return jsonify({"status": "error", "error": "invalid_body"}), 400
    ok, err, merged = merge_habits_map(email, incoming)
    if not ok:
        code = 400
        if err == "no_user":
            code = 404
        return jsonify({"status": "error", "error": err or "merge_failed"}), code
    return jsonify({"status": "success", "cells": merged}), 200


@app.route("/api/habits/cell", methods=["PATCH"])
def habits_patch_cell():
    token = _bearer_token()
    email = decode_access_token(token)
    if not email:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    date_str = data.get("date")
    habit_id = data.get("habitId")
    state = data.get("state")
    ok, err = patch_habit_cell(email, date_str, habit_id, state)
    if not ok:
        code = 400
        if err == "no_user":
            code = 404
        elif err == "write_failed":
            code = 500
        return jsonify({"status": "error", "error": err or "patch_failed"}), code
    cells = get_habits_map(email)
    return jsonify({"status": "success", "cells": cells}), 200


@app.route("/api/user/habits", methods=["GET"])
def user_habits_get():
    token = _bearer_token()
    email = decode_access_token(token)
    if not email:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    habits = get_custom_habits(email)
    return jsonify({"status": "success", "habits": habits}), 200


@app.route("/api/user/habits", methods=["PUT"])
def user_habits_put():
    token = _bearer_token()
    email = decode_access_token(token)
    if not email:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    incoming = data.get("habits")
    if not isinstance(incoming, list):
        return jsonify({"status": "error", "error": "invalid_body"}), 400
    ok, err = update_custom_habits(email, incoming)
    if not ok:
        code = 400
        if err == "no_user":
            code = 404
        return jsonify({"status": "error", "error": err or "update_failed"}), code
    return jsonify({"status": "success", "habits": incoming}), 200


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
            'message': 'Portfolio Auth API',
            'version': '1.0.0',
            'endpoints': {
                'POST /api/auth/register': 'Register with email and password (password stored as hash)',
                'POST /api/auth/login': 'Login; returns JWT bearer token',
                'GET /api/auth/me': 'Current user from Authorization: Bearer <token>',
                'GET /api/habits': 'Habit tracker cells for current user (JSON map)',
                'PUT /api/habits': 'Merge habit cells body { cells: { "YYYY-MM-DD_id": "done"|"fail"|"none" } }',
                'PATCH /api/habits/cell': 'Set one cell { date, habitId, state }',
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
    print(f"Health: http://localhost:{port}/health")

    app.run(host='0.0.0.0', port=port, debug=debug)
