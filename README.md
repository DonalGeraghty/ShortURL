# Janus Gate (`janus-gate`)

**Codename: Janus** — Roman god of doorways, passages, and transitions. This repository is a small **Flask** API for portfolio **authentication**: register, login, JWT issuance, and a “current user” endpoint. User records live in **Firestore** (via the Firebase Admin SDK); local dev can fall back to in-memory storage when Firestore is not configured.

## Requirements

- **Python 3.11+** (matches the `Dockerfile` base image)
- A **Firebase / GCP** project with Firestore enabled for production
- **`JWT_SECRET_KEY`** set in production (see below)

Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Pinned packages are listed in **`requirements.txt`** (Flask, Flask-CORS, `firebase-admin`, Firestore client, PyJWT, `python-dotenv`).

## Run locally

```bash
set FLASK_ENV=development       # Windows CMD
set JWT_SECRET_KEY=dev-secret   # dev only; use a strong secret in prod
python app.py
```

PowerShell:

```powershell
$env:FLASK_ENV = "development"
$env:JWT_SECRET_KEY = "dev-secret"
python app.py
```

Defaults: host `0.0.0.0`, port from **`PORT`** or **5000**. Health check: [http://localhost:5000/health](http://localhost:5000/health).

For Firestore outside Google Cloud, set **`GOOGLE_APPLICATION_CREDENTIALS`** to a service account JSON path (see `services/firebase_service.py`).

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service info and endpoint list |
| `GET` | `/health` | Liveness / health JSON |
| `POST` | `/api/auth/register` | JSON `{ "email", "password" }` — min 8 characters |
| `POST` | `/api/auth/login` | Same body; returns JWT |
| `GET` | `/api/auth/me` | `Authorization: Bearer <token>` |

CORS is enabled for browser clients (configure appropriately for production origins if needed).

## Layout

```
app.py                 # Flask app, routes, request/response logging
core/
  auth_service.py      # Password hashing, JWT, register/login helpers
services/
  firebase_service.py  # Firestore / in-memory user store
  logging_service.py # Structured logging for the app
```

## Docker

```bash
docker build -t janus-gate .
docker run -p 8080:8080 -e PORT=8080 -e JWT_SECRET_KEY=your-secret janus-gate
```

The image sets **`PORT=8080`** and runs `python app.py`. Ensure **`JWT_SECRET_KEY`** and Firebase / GCP credentials are supplied at runtime for real deployments.

## Deploy (Google Cloud Run)

The GitHub Action in **`.github/workflows/deploy.yml`** builds and deploys the **janus-gate** service. After deploy, the URL usually looks like:

`https://janus-gate-<PROJECT_NUMBER>.europe-west1.run.app`

Point the **Minerva** frontend `API_BASE_URL` in `minerva/src/config/api.js` at that host.

### Service account

The workflow expects a dedicated service account (e.g. **`janus-gate@<PROJECT>.iam.gserviceaccount.com`**). If you previously used another service name (for example `url-shortener`), migrate IAM or adjust the workflow to match your GCP setup.

## Security notes

- Set a strong **`JWT_SECRET_KEY`** in every non-local environment. Without it, the app falls back to an insecure default (logged as a warning).
- Passwords are stored using **Werkzeug** password hashes, not plain text.

## GitHub

Rename the repository on GitHub to **`janus-gate`** if needed (**Settings → General → Repository name**), then:

```bash
git remote set-url origin https://github.com/<you>/janus-gate.git
```

## Related repo

- **Minerva** (`minerva`) — React / Vite frontend that consumes this API; configure its `src/config/api.js` with this service URL.
