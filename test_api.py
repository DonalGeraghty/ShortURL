import requests
import json

def test_post_request():
    """Test the POST endpoint of the REST API"""
    
    # API endpoint
    url = "http://localhost:5000/api/data"
    
    # Sample data to send
    sample_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "message": "Hello from the test client!",
        "timestamp": "2024-01-01T12:00:00Z"
    }
    
    # Headers for JSON content
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print("Sending POST request to:", url)
        print("Data:", json.dumps(sample_data, indent=2))
        print("-" * 50)
        
        # Make POST request
        response = requests.post(url, json=sample_data, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print("Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print("\nResponse Body:")
        if response.headers.get('content-type', '').startswith('application/json'):
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
        else:
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server.")
        print("Make sure the Flask app is running on http://localhost:5000")
    except Exception as e:
        print(f"Error: {e}")

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get("http://localhost:5000/health")
        print(f"\nHealth Check - Status: {response.status_code}")
        if response.status_code == 200:
            print("API is healthy!")
    except:
        print("Health check failed - server may not be running")

if __name__ == "__main__":
    print("Testing Python REST API")
    print("=" * 50)
    
    # Test health check first
    test_health_check()
    
    # Test POST request
    test_post_request()
