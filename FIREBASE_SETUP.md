# Google Cloud Firestore Setup Guide

## 🎯 **Overview**
This application is designed to work with **Google Cloud Firestore** using automatic authentication. No service account key files are needed when deployed on Google Cloud!

## 🚀 **Production Deployment (Recommended)**

### **Option 1: Google Cloud Automatic Authentication** ⭐ **BEST**
When deployed on Google Cloud (Cloud Run, App Engine, Compute Engine), the application automatically uses the service account credentials:

1. **Deploy your application** to Google Cloud
2. **Assign a service account** with Firestore permissions
3. **That's it!** No key files needed

### **Option 2: Cloud Run Example**
```bash
# Deploy to Cloud Run with service account
gcloud run deploy url-shortener \
  --source . \
  --service-account=your-app@your-project.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 🛠️ **Local Development Setup**

### **Option 1: Service Account Key (Local Only)**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin** → **Service Accounts**
3. Create a new service account or use existing one
4. Grant it **Firestore User** role
5. Create/download a JSON key file
6. Set environment variable:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
   ```

### **Option 2: Google Cloud CLI (Recommended for Local)**
```bash
# Install Google Cloud CLI
# Then authenticate:
gcloud auth application-default login

# This automatically sets up credentials for local development
```

## 🔐 **Required IAM Permissions**

Your service account needs these roles:
- **Firestore User** (`roles/datastore.user`)
- **Firestore Viewer** (`roles/datastore.viewer`)

## 📁 **Project Structure**

```
shortUrl/
├── app.py                 # Flask web server
├── url_shortener.py      # Core URL shortening logic
├── requirements.txt       # Python dependencies
├── .env                  # Local environment variables (optional)
└── FIREBASE_SETUP.md     # This file
```

## 🧪 **Testing**

### **Local Testing**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### **API Testing**
```bash
# Create short URL
curl -X POST -H "Content-Type: application/json" \
  -d '{"text": "https://www.example.com/very/long/url"}' \
  http://localhost:5000/api/data

# Retrieve long URL
curl http://localhost:5000/api/url/abc123
```

## 🌟 **Key Benefits of This Setup**

1. **🔒 Secure**: No key files in production
2. **🚀 Simple**: Automatic authentication on Google Cloud
3. **🔄 Flexible**: Works both locally and in production
4. **📈 Scalable**: Built-in Google Cloud scaling
5. **💰 Cost-effective**: Pay only for what you use

## 🚨 **Important Notes**

- **Never commit service account keys** to version control
- **Use IAM service accounts** for production deployments
- **Local development** can use either approach
- **The app automatically falls back** to in-memory storage if Firestore is unavailable

## 🆘 **Troubleshooting**

### **"No credentials found" Error**
- For local development: Set `GOOGLE_APPLICATION_CREDENTIALS`
- For production: Ensure service account has proper IAM roles

### **"Permission denied" Error**
- Check that your service account has Firestore User role
- Verify the project ID is correct

### **"Connection failed" Error**
- Ensure Firestore is enabled in your Google Cloud project
- Check that your service account has network access
