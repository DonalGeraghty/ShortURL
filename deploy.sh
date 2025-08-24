#!/bin/bash

# Google Cloud Run Deployment Script
# This script deploys your URL shortener API to Google Cloud Run

set -e  # Exit on any error

# Configuration
PROJECT_ID="your-google-cloud-project-id"  # Replace with your actual project ID
SERVICE_NAME="url-shortener-api"
REGION="us-central1"  # Change to your preferred region
SERVICE_ACCOUNT="url-shortener@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Starting deployment to Google Cloud Run..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud CLI (gcloud) is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "🔐 Please authenticate with Google Cloud first:"
    echo "gcloud auth login"
    exit 1
fi

# Set the project
echo "📋 Setting project to: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create service account if it doesn't exist
echo "👤 Setting up service account..."
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT} &> /dev/null; then
    echo "Creating service account: ${SERVICE_ACCOUNT}"
    gcloud iam service-accounts create url-shortener \
        --display-name="URL Shortener API Service Account"
else
    echo "Service account already exists: ${SERVICE_ACCOUNT}"
fi

# Grant necessary permissions
echo "🔐 Granting Firestore permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/datastore.viewer"

# Build and deploy to Cloud Run
echo "🏗️  Building and deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --timeout 300 \
    --set-env-vars FLASK_ENV=production

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format="value(status.url)")

echo ""
echo "🎉 Deployment successful!"
echo "🌐 Your API is now available at: ${SERVICE_URL}"
echo ""
echo "📋 API Endpoints:"
echo "  POST ${SERVICE_URL}/api/data     - Create short URL"
echo "  GET  ${SERVICE_URL}/api/url/{id} - Get long URL"
echo "  GET  ${SERVICE_URL}/health       - Health check"
echo "  GET  ${SERVICE_URL}/             - API info"
echo ""
echo "🧪 Test your API:"
echo "curl -X POST -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"https://www.example.com/test\"}' \\"
echo "  ${SERVICE_URL}/api/data"
echo ""
echo "🔍 Monitor your service:"
echo "gcloud run services describe ${SERVICE_NAME} --region ${REGION}"
echo ""
echo "📊 View logs:"
echo "gcloud logs read --service=${SERVICE_NAME} --limit=50"
