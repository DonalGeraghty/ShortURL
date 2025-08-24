from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from url_shortener import shorten_url, get_long_url

app = Flask(__name__)
CORS(app)

@app.route('/api/data', methods=['POST'])
def handle_post():
    """
    Handle POST requests to /api/data endpoint
    Accepts string input and returns string output
    """
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
                return "Error: Please send a string or {'text': 'your string'}", 400
        else:
            # If raw text is sent
            input_string = request.get_data(as_text=True)
        
        # Validate that we have a string
        if not input_string or not isinstance(input_string, str):
            return "Error: Please provide a valid string input", 400
        
        # Process the string using the shorten_url method
        shortened_result = shorten_url(input_string)
        
        return shortened_result, 200
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/url/<short_code>', methods=['GET'])
def get_url(short_code):
    """
    Handle GET requests to retrieve the long URL from a short code
    """
    try:
        # Get the long URL using the short code
        long_url = get_long_url(short_code)
        
        if long_url:
            return jsonify({
                'short_code': short_code,
                'long_url': long_url,
                'status': 'success'
            }), 200
        else:
            return jsonify({
                'short_code': short_code,
                'error': 'Short code not found',
                'status': 'error'
            }), 404
            
    except Exception as e:
        return jsonify({
            'short_code': short_code,
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information"""
    return jsonify({
        'message': 'Python REST API',
        'endpoints': {
            'POST /api/data': 'Submit data via POST request',
            'GET /api/url/<short_code>': 'Get long URL from short code',
            'GET /health': 'Health check endpoint',
            'GET /': 'This information endpoint'
        },
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Starting Flask server on port {port}")
    print(f"Debug mode: {debug}")
    print(f"API endpoint: http://localhost:{port}/api/data")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
