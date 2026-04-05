# Janus Gate (`janus-gate`)

**Codename: Janus** — Roman god of doorways, passages, and transitions. This repository is a **Flask** API that powers Donal Geraghty’s **Minerva** frontend: **authentication** (register, login, JWT, current user) plus **user-scoped data** stored in **Firestore** (habits, todos, flashcards, nutrition history, stoic journal, day planner). Local development can fall back to an in-memory store when Firestore is not configured.

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

For Firestore outside Google Cloud, set **`GOOGLE_APPLICATION_CREDENTIALS`** to a service account JSON path (see `services/firebase_service.py` / `services/firebase/`).

## API overview

Unless noted, user routes require **`Authorization: Bearer <JWT>`**.

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` | JSON `{ "email", "password" }` — min 8 characters |
| `POST` | `/api/auth/login` | Same body; returns JWT |
| `GET` | `/api/auth/me` | Current user from bearer token |

### Habits

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/habits` | Habit grid cells (date × habit map) |
| `PUT` | `/api/habits` | Merge cells: `{ "cells": { "YYYY-MM-DD_habitId": "done"\|"none" } }` |
| `PATCH` | `/api/habits/cell` | One cell: `{ "date", "habitId", "state" }` |
| `GET` / `PUT` | `/api/user/habits` | List / replace habit definitions `{ "habits": [...] }` |
| `GET` / `POST` / `PATCH` / `DELETE` | `/api/user/habit-categories` | Categories (create, rename, delete with optional `reassignTo`) |

### Other user data

| Area | Methods | Path prefix | Notes |
|------|---------|-------------|--------|
| Todos | `GET`, `POST`, `DELETE` | `/api/user/todos` | `POST` `{ "text" }`; `DELETE` `{ "todoId" }` |
| Flashcards | `GET`, `PUT` | `/api/user/flashcards` | Full `groups` replace on `PUT` |
| Flashcards | `POST` | `/api/user/flashcards/groups` | `{ "name" }` |
| Flashcards | `POST` | `/api/user/flashcards/cards` | `{ "groupId", "front", "back" }` |
| Flashcards | `GET` | `/api/user/flashcards/study` | Optional `?groupId=` |
| Nutrition | `GET`, `PUT` | `/api/user/nutrition` | `{ "history": { ... } }` on `PUT` |
| Stoic journal | `GET`, `PUT` | `/api/user/stoic` | `{ "date", "form" }` on `PUT` |
| Day planner | `GET` / `POST` / `PATCH` / `DELETE` | `/api/user/day-planner/options` | Configurable dropdown options |
| Day planner | `GET` / `PUT` | `/api/user/day-planner/daily` | `{ "date", "slots" }` on `PUT` |

### Service

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service metadata and full endpoint list (mirrors this API) |
| `GET` | `/health` | Liveness JSON |

CORS is enabled for browser clients (tighten allowed origins in production if needed).

## Layout

```
app.py                     # Flask app, routes, request/response logging
core/
  auth_service.py          # Password hashing, JWT, register/login
services/
  firebase_service.py      # Facade re-exporting feature modules
  logging_service.py       # Structured logging
  firebase/                # Firestore implementations per feature
    core.py, users.py, db_state.py
    habits.py, habit_categories.py, todos.py, flashcards.py
    nutrition.py, stoic.py, day_planner.py
```

## Docker

```bash
docker build -t janus-gate .
docker run -p 8080:8080 -e PORT=8080 -e JWT_SECRET_KEY=your-secret janus-gate
```

The image sets **`PORT=8080`** and runs `python app.py`. Supply **`JWT_SECRET_KEY`** and Firebase / GCP credentials at runtime for real deployments.

## Deploy (Google Cloud Run)

The GitHub Action in **`.github/workflows/deploy.yml`** builds and deploys **janus-gate**. After deploy, the URL usually looks like:

`https://janus-gate-<PROJECT_NUMBER>.europe-west1.run.app`

Point the **Minerva** frontend **`API_BASE_URL`** in `src/config/api.js` at that host.

### Service account

The workflow uses a dedicated service account (e.g. **`janus-gate@<PROJECT>.iam.gserviceaccount.com`**). If you previously used another service name, migrate IAM or adjust the workflow to match your GCP setup.

## Security notes

- Set a strong **`JWT_SECRET_KEY`** in every non-local environment. Without it, the app falls back to an insecure default (logged as a warning).
- Passwords are stored using **Werkzeug** password hashes, not plain text.

## GitHub

Rename the repository on GitHub to **`janus-gate`** if needed (**Settings → General → Repository name**), then:

```bash
git remote set-url origin https://github.com/<you>/janus-gate.git
```

## Related repo

- **Minerva** — React / Vite SPA that calls this API for auth and persisted user data; see that repo’s README and `src/config/api.js`.
