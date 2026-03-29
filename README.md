# Janus (`janus-gate`)

**Codename: Janus** — Roman god of doorways, passages, and transitions. This repository hosts the small Flask API that powers portfolio **authentication** (register, login, JWT, Firestore users).

## Deploy

Cloud Run service name: **`janus-gate`**. After deploy, the public URL is typically:

`https://janus-gate-<PROJECT_NUMBER>.europe-west1.run.app`

Point the portfolio frontend `API_BASE_URL` in `DonalGeraghtyHome/src/config/api.js` at that URL.

## GitHub

Rename the repository on GitHub to **`janus-gate`** (Settings → General → Repository name), then update your local remote:

```bash
git remote set-url origin https://github.com/<you>/janus-gate.git
```

## GCP note

The deploy workflow uses a dedicated service account **`janus-gate@<PROJECT>.iam.gserviceaccount.com`**. If you previously used `url-shortener`, either migrate IAM to the new account (as the workflow does on first run) or adjust the workflow to keep the old service account name.
