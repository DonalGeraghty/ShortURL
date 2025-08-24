# 🚨 GitHub Actions Troubleshooting Guide

## 🔐 **Google Cloud Authentication Error**

### **Error Message:**
```
the GitHub Action workflow must specify exactly one of "workload_identity_provider" or "credentials_json"! 
If you are specifying input values via GitHub secrets, ensure the secret is being injected into the environment. 
By default, secrets are not passed to workflows triggered from forks, including Dependabot.
```

## ✅ **Solution Steps:**

### **Step 1: Verify GitHub Secret**

1. **Go to your repository**: `https://github.com/YOUR_USERNAME/shortUrl`
2. **Click Settings** → **Secrets and variables** → **Actions**
3. **Check if `GCP_SA_KEY` exists**
4. **If it doesn't exist, create it:**
   - Click **New repository secret**
   - **Name**: `GCP_SA_KEY`
   - **Value**: Copy the entire JSON content of your service account key file

### **Step 2: Verify Secret Content**

The `GCP_SA_KEY` secret should contain the **entire JSON file content**, not just a path or partial content.

**✅ Correct format:**
```json
{
  "type": "service_account",
  "project_id": "donal-geraghty-home",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "github-actions@donal-geraghty-home.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/github-actions%40donal-geraghty-home.iam.gserviceaccount.com"
}
```

**❌ Incorrect formats:**
- Just the file path
- Partial JSON content
- Empty value
- Wrong secret name

### **Step 3: Check Repository Permissions**

1. **Ensure you're not working from a fork**
2. **Verify you have admin access** to the repository
3. **Check if the repository is public or private**

### **Step 4: Test the Secret**

You can test if the secret is being read correctly by adding a debug step:

```yaml
- name: Debug Secret
  run: |
    if [ -n "${{ secrets.GCP_SA_KEY }}" ]; then
      echo "✅ Secret is set and has content"
      echo "Length: ${#GCP_SA_KEY}"
    else
      echo "❌ Secret is empty or not set"
    fi
```

## 🔧 **Alternative Solutions:**

### **Option 1: Use Workload Identity (Recommended for Production)**

Instead of service account keys, use Google Cloud's Workload Identity:

```yaml
- name: Google Auth
  id: auth
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: projects/${{ env.PROJECT_ID }}/locations/global/workloadIdentityPools/github-actions/providers/github-actions
    service_account: github-actions@${{ env.PROJECT_ID }}.iam.gserviceaccount.com
```

### **Option 2: Check Secret Injection**

Add this step before the Google Auth step:

```yaml
- name: Check Secret
  run: |
    echo "Secret length: ${#GCP_SA_KEY}"
    if [ -z "${{ secrets.GCP_SA_KEY }}" ]; then
      echo "❌ GCP_SA_KEY secret is empty!"
      exit 1
    fi
    echo "✅ GCP_SA_KEY secret is set"
```

## 🚨 **Common Issues and Fixes:**

### **Issue 1: Secret Not Found**
- **Cause**: Secret name is misspelled
- **Fix**: Double-check the secret name is exactly `GCP_SA_KEY`

### **Issue 2: Secret is Empty**
- **Cause**: Secret was created but has no value
- **Fix**: Delete and recreate the secret with the full JSON content

### **Issue 3: Repository Access**
- **Cause**: Working from a fork or don't have admin access
- **Fix**: Ensure you're working in the original repository with proper permissions

### **Issue 4: JSON Format Issues**
- **Cause**: Malformed JSON in the secret
- **Fix**: Validate the JSON content before adding it to GitHub

## 🧪 **Testing Your Setup:**

1. **Create a test workflow** to verify the secret is working
2. **Use the debug step** above to check secret content
3. **Test locally** with the service account key first

## 📞 **Still Having Issues?**

1. **Check GitHub Actions logs** for more detailed error messages
2. **Verify your Google Cloud service account** has the correct permissions
3. **Ensure Firestore is enabled** in your Google Cloud project
4. **Check if billing is enabled** for your Google Cloud project

## 🔒 **Security Notes:**

- **Never commit** service account keys to your repository
- **Use repository secrets** for sensitive information
- **Consider Workload Identity** for production environments
- **Rotate service account keys** regularly

---

🎯 **The most common fix is ensuring the `GCP_SA_KEY` secret contains the complete JSON content of your service account key file.**
