# 🔗 URL Shortener API

A modern, scalable URL shortening service built with Flask and Google Cloud Firestore. Automatically deploy to Google Cloud Run with GitHub Actions.

## ✨ Features

- **🔗 URL Shortening**: Convert long URLs to short, shareable links
- **🌐 RESTful API**: Clean HTTP endpoints for easy integration
- **☁️ Cloud Native**: Built for Google Cloud with automatic scaling
- **🔒 Secure**: Google Cloud authentication with service accounts
- **📊 Persistent Storage**: Firestore database for reliable data storage
- **🚀 Auto-Deploy**: GitHub Actions workflow for continuous deployment
- **🧪 Health Monitoring**: Built-in health checks and monitoring

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/shortUrl.git
   cd shortUrl
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Test the API**
   ```bash
   # Create a short URL
   curl -X POST -H "Content-Type: application/json" \
     -d '{"text": "https://www.example.com/very/long/url"}' \
     http://localhost:5000/api/data
   
   # Check health
   curl http://localhost:5000/health
   ```

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/data` | Create a short URL from a long URL |
| `GET` | `/api/url/{short_code}` | Retrieve the original long URL |
| `GET` | `/health` | Health check endpoint |
| `GET` | `/` | API information and documentation |

### Example Usage

#### Create Short URL
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text": "https://www.github.com/python/cpython"}' \
  http://localhost:5000/api/data
```

**Response:**
```
9b1254
```

#### Retrieve Long URL
```bash
curl http://localhost:5000/api/url/9b1254
```

**Response:**
```json
{
  "short_code": "9b1254",
  "long_url": "https://www.github.com/python/cpython",
  "status": "success"
}
```

## 🏗️ Architecture

- **Frontend**: Flask web framework
- **Database**: Google Cloud Firestore (NoSQL)
- **Deployment**: Google Cloud Run (serverless)
- **CI/CD**: GitHub Actions
- **Authentication**: Google Cloud IAM service accounts

## ☁️ Deployment

### Prerequisites
- Google Cloud project with billing enabled
- Firestore database enabled
- GitHub repository

### Automatic Deployment (Recommended)

1. **Set up Google Cloud service account** with proper permissions
2. **Add `GCP_SA_KEY` secret** to your GitHub repository
3. **Push to main branch** - deployment happens automatically!

### Manual Deployment

```bash
# Deploy to Cloud Run
gcloud run deploy url-shortener-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔐 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `5000` |
| `FLASK_ENV` | Flask environment | `production` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account key path | `None` |

### Google Cloud Setup

1. **Enable APIs**:
   - Cloud Run API
   - Firestore API
   - Cloud Build API

2. **Service Account Roles**:
   - Firestore User (`roles/datastore.user`)
   - Cloud Run Admin (`roles/run.admin`)

## 📁 Project Structure

```
shortUrl/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions deployment
├── app.py                      # Flask web server
├── url_shortener.py           # Core URL shortening logic
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── .dockerignore              # Docker ignore file
└── README.md                  # This file
```

## 🧪 Testing

### Run Tests
```bash
# Test imports
python -c "from url_shortener import shorten_url, get_long_url; print('✅ All imports successful')"

# Test Flask app
python -c "from app import app; print('✅ Flask app imports successful')"
```

### API Testing
```bash
# Health check
curl http://localhost:5000/health

# Create short URL
curl -X POST -H "Content-Type: application/json" \
  -d '{"text": "https://www.google.com"}' \
  http://localhost:5000/api/data

# Get long URL
curl http://localhost:5000/api/url/SHORT_CODE
```

## 🔍 Monitoring

### Health Checks
- **Endpoint**: `/health`
- **Response**: JSON with status and timestamp
- **Use Case**: Load balancer health checks, monitoring

### Logs
```bash
# View Cloud Run logs
gcloud logs read --service=url-shortener-api --limit=50

# View service details
gcloud run services describe url-shortener-api --region us-central1
```

## 💰 Cost Optimization

- **Cloud Run**: Pay per request (~$0.40 per million)
- **Firestore**: Pay per operation (~$0.18 per 100K operations)
- **Estimated**: $5-20/month for moderate usage

## 🚨 Troubleshooting

### Common Issues

1. **"Permission denied"**
   - Check service account has proper IAM roles
   - Verify Firestore is enabled

2. **"Service not found"**
   - Ensure service name and region are correct
   - Check deployment logs

3. **"Authentication failed"**
   - Verify `GCP_SA_KEY` secret is set correctly
   - Check service account permissions

### Debug Commands

```bash
# Check service status
gcloud run services list

# View logs
gcloud logs read --service=url-shortener-api --limit=100

# Test locally
python app.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/shortUrl/issues)
- **Documentation**: [Google Cloud Docs](https://cloud.google.com/run/docs)
- **Firestore**: [Firestore Docs](https://firebase.google.com/docs/firestore)

---

⭐ **Star this repository if you find it helpful!**
