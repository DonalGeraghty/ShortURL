# 🚀 Google Cloud Deployment Guide

## 📋 **Prerequisites**

1. **Google Cloud Account** with billing enabled
2. **Google Cloud CLI** installed and authenticated
3. **Firestore Database** enabled in your project

## 🔧 **Step 1: Install Google Cloud CLI**

### Windows:
```bash
# Download from: https://cloud.google.com/sdk/docs/install
# Or use winget:
winget install Google.CloudSDK
```

### macOS:
```bash
# Using Homebrew:
brew install --cask google-cloud-sdk
```

### Linux:
```bash
# Download and install from:
# https://cloud.google.com/sdk/docs/install
```

## 🔐 **Step 2: Authenticate with Google Cloud**

```bash
# Login to your Google account
gcloud auth login

# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Verify authentication
gcloud auth list
```

## 🏗️ **Step 3: Deploy to Cloud Run**

### **Option A: Use the Deployment Script (Recommended)**

1. **Edit the deployment script**:
   - Open `deploy.bat` (Windows) or `deploy.sh` (Linux/Mac)
   - Replace `your-google-cloud-project-id` with your actual project ID
   - Optionally change the region (default: `us-central1`)

2. **Run the deployment**:
   ```bash
   # Windows:
   deploy.bat
   
   # Linux/Mac:
   chmod +x deploy.sh
   ./deploy.sh
   ```

### **Option B: Manual Deployment**

```bash
# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create service account
gcloud iam service-accounts create url-shortener \
    --display-name="URL Shortener API Service Account"

# Grant Firestore permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:url-shortener@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

# Deploy to Cloud Run
gcloud run deploy url-shortener-api \
    --source . \
    --region us-central1 \
    --service-account url-shortener@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10
```

## 🌐 **Step 4: Test Your Deployed API**

After deployment, you'll get a URL like:
`https://url-shortener-api-xxxxx-uc.a.run.app`

### **Test the endpoints:**

```bash
# Health check
curl https://your-service-url/health

# Create short URL
curl -X POST -H "Content-Type: application/json" \
  -d '{"text": "https://www.example.com/test"}' \
  https://your-service-url/api/data

# Get long URL
curl https://your-service-url/api/url/SHORT_CODE
```

## 📊 **Step 5: Monitor Your Service**

```bash
# View service details
gcloud run services describe url-shortener-api --region us-central1

# View logs
gcloud logs read --service=url-shortener-api --limit=50

# View metrics in Google Cloud Console
# Go to: Cloud Run > url-shortener-api > Metrics
```

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **"Permission denied"**
   - Ensure service account has proper IAM roles
   - Check that Firestore is enabled

2. **"Service not found"**
   - Verify the service name and region
   - Check deployment logs

3. **"Authentication failed"**
   - Re-authenticate: `gcloud auth login`
   - Check project ID: `gcloud config get-value project`

### **Useful Commands:**

```bash
# List all Cloud Run services
gcloud run services list

# Delete a service
gcloud run services delete url-shortener-api --region us-central1

# Update environment variables
gcloud run services update url-shortener-api \
    --region us-central1 \
    --set-env-vars NEW_VAR=value

# View service logs
gcloud logs read --service=url-shortener-api --limit=100
```

## 💰 **Cost Optimization**

- **Cloud Run**: Pay only when requests are processed
- **Firestore**: Pay per read/write operation
- **Estimated cost**: ~$5-20/month for moderate usage

## 🔄 **Updating Your Service**

To deploy updates:

```bash
# Simply run the deployment script again
./deploy.sh

# Or manually:
gcloud run deploy url-shortener-api --source . --region us-central1
```

## 🎯 **Next Steps**

1. **Set up custom domain** (optional)
2. **Configure monitoring and alerts**
3. **Set up CI/CD pipeline**
4. **Add authentication** (if needed)

## 📞 **Need Help?**

- **Google Cloud Documentation**: https://cloud.google.com/run/docs
- **Cloud Run Pricing**: https://cloud.google.com/run/pricing
- **Firestore Documentation**: https://firebase.google.com/docs/firestore
