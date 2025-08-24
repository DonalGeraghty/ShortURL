@echo off
REM Google Cloud Run Deployment Script for Windows
REM This script deploys your URL shortener API to Google Cloud Run

setlocal enabledelayedexpansion

REM Configuration
set PROJECT_ID=your-google-cloud-project-id
set SERVICE_NAME=url-shortener-api
set REGION=us-central1
set SERVICE_ACCOUNT=url-shortener@%PROJECT_ID%.iam.gserviceaccount.com

echo 🚀 Starting deployment to Google Cloud Run...

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Google Cloud CLI (gcloud) is not installed.
    echo Please install it from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Check if user is authenticated
gcloud auth list --filter=status:ACTIVE --format="value(account)" | findstr . >nul
if %errorlevel% neq 0 (
    echo 🔐 Please authenticate with Google Cloud first:
    echo gcloud auth login
    pause
    exit /b 1
)

REM Set the project
echo 📋 Setting project to: %PROJECT_ID%
gcloud config set project %PROJECT_ID%

REM Enable required APIs
echo 🔧 Enabling required APIs...
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable cloudbuild.googleapis.com

REM Create service account if it doesn't exist
echo 👤 Setting up service account...
gcloud iam service-accounts describe %SERVICE_ACCOUNT% >nul 2>nul
if %errorlevel% neq 0 (
    echo Creating service account: %SERVICE_ACCOUNT%
    gcloud iam service-accounts create url-shortener --display-name="URL Shortener API Service Account"
) else (
    echo Service account already exists: %SERVICE_ACCOUNT%
)

REM Grant necessary permissions
echo 🔐 Granting Firestore permissions...
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT%" --role="roles/datastore.user"
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT%" --role="roles/datastore.viewer"

REM Build and deploy to Cloud Run
echo 🏗️  Building and deploying to Cloud Run...
gcloud run deploy %SERVICE_NAME% --source . --region %REGION% --service-account %SERVICE_ACCOUNT% --allow-unauthenticated --port 8080 --memory 512Mi --cpu 1 --max-instances 10 --timeout 300 --set-env-vars FLASK_ENV=production

REM Get the service URL
for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --region %REGION% --format="value(status.url)"') do set SERVICE_URL=%%i

echo.
echo 🎉 Deployment successful!
echo 🌐 Your API is now available at: %SERVICE_URL%
echo.
echo 📋 API Endpoints:
echo   POST %SERVICE_URL%/api/data     - Create short URL
echo   GET  %SERVICE_URL%/api/url/{id} - Get long URL
echo   GET  %SERVICE_URL%/health       - Health check
echo   GET  %SERVICE_URL%/             - API info
echo.
echo 🧪 Test your API:
echo curl -X POST -H "Content-Type: application/json" -d "{\"text\": \"https://www.example.com/test\"}" %SERVICE_URL%/api/data
echo.
echo 🔍 Monitor your service:
echo gcloud run services describe %SERVICE_NAME% --region %REGION%
echo.
echo 📊 View logs:
echo gcloud logs read --service=%SERVICE_NAME% --limit=50

pause
