# 🚀 GitHub Actions + Google Cloud Deployment Guide

## 🎯 **Overview**
This guide will help you set up automatic deployment of your URL shortener API to Google Cloud Run using GitHub Actions. Every time you push to the main branch, your API will automatically deploy!

## 📋 **Prerequisites**

1. ✅ **GitHub repository** with your code
2. ✅ **Google Cloud project** (`donal-geraghty-home`)
3. ✅ **Firestore database** enabled in your project

## 🔐 **Step 1: Create Google Cloud Service Account**

### **Option A: Using Google Cloud Console (Recommended)**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `donal-geraghty-home`
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
5. **Name**: `github-actions-deployer`
6. **Description**: `Service account for GitHub Actions deployment`
7. Click **Create and Continue**

### **Step 2: Grant Permissions**

Add these roles to your service account:
- **Cloud Run Admin** (`roles/run.admin`)
- **Service Account User** (`roles/iam.serviceAccountUser`)
- **Firestore User** (`roles/datastore.user`)
- **Cloud Build Service Account** (`roles/cloudbuild.builds.builder`)

### **Step 3: Create and Download Key**

1. Click on your service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Choose **JSON** format
5. Download the key file
6. **Keep this file secure!** Never commit it to your repository

## 🔑 **Step 2: Add GitHub Secret**

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. **Name**: `GCP_SA_KEY`
5. **Value**: Copy the entire contents of your downloaded JSON key file
6. Click **Add secret**

## 📁 **Step 3: Repository Structure**

Your repository should now look like this:
```
shortUrl/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── app.py                      # Flask application
├── url_shortener.py           # URL shortening logic
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── .dockerignore              # Docker ignore file
├── README.md                   # Project documentation
└── GITHUB_ACTIONS_SETUP.md    # This file
```

## 🚀 **Step 4: Push and Deploy**

1. **Commit and push** your changes:
   ```bash
   git add .
   git commit -m "Add GitHub Actions deployment workflow"
   git push origin main
   ```

2. **Check the deployment**:
   - Go to your GitHub repository
   - Click **Actions** tab
   - You'll see the deployment workflow running

## 🔍 **Step 5: Monitor Deployment**

### **GitHub Actions**
- **Actions tab**: View workflow runs and logs
- **Green checkmark**: Deployment successful
- **Red X**: Deployment failed (check logs)

### **Google Cloud Console**
- **Cloud Run**: View your deployed service
- **Logs**: Monitor application logs
- **Metrics**: Track performance and costs

## 🌐 **Your Deployed API**

After successful deployment, your API will be available at:
```
https://url-shortener-api-xxxxx-uc.a.run.app
```

### **API Endpoints:**
- **POST** `/api/data` - Create short URL
- **GET** `/api/url/{id}` - Get long URL  
- **GET** `/health` - Health check
- **GET** `/` - API information

## 🧪 **Test Your Deployed API**

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

## 🔄 **Automatic Updates**

Now every time you:
1. **Push to main branch** → Automatic deployment
2. **Create a pull request** → Tests run automatically
3. **Merge to main** → Automatic deployment

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **"Permission denied"**
   - Check service account has proper roles
   - Verify `GCP_SA_KEY` secret is correct

2. **"Service account not found"**
   - Ensure service account exists in Google Cloud
   - Check project ID in workflow file

3. **"Build failed"**
   - Check Dockerfile syntax
   - Verify all files are committed

### **Useful Commands:**

```bash
# View workflow logs in GitHub
# Go to Actions tab → Click on failed workflow → View logs

# Check Google Cloud service
gcloud run services describe url-shortener-api --region us-central1

# View logs
gcloud logs read --service=url-shortener-api --limit=50
```

## 💰 **Cost Management**

- **Cloud Run**: Pay per request (~$0.40 per million)
- **Firestore**: Pay per operation (~$0.18 per 100K operations)
- **GitHub Actions**: Free for public repos, 2000 minutes/month for private repos

## 🎯 **Next Steps**

1. **Custom domain**: Point your domain to the Cloud Run service
2. **Monitoring**: Set up alerts and dashboards
3. **CI/CD**: Add more automated tests
4. **Scaling**: Configure auto-scaling policies

## 📞 **Need Help?**

- **GitHub Actions**: https://docs.github.com/en/actions
- **Google Cloud Run**: https://cloud.google.com/run/docs
- **Firestore**: https://firebase.google.com/docs/firestore

---

🎉 **Congratulations!** Your API now deploys automatically with every push to main!
