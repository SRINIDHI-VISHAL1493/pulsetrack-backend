# PulseTrack

PulseTrack is a minimal FastAPI backend for the internship project focused on doctor-patient appointments and prescriptions.

## Features

- FastAPI application scaffold
- Health check endpoint
- App metadata and cleaner startup info
- Favicon route for browser-friendly requests

## Run locally

```bash
cd "/Users/srinidhivishalchejarla/Downloads/zyoralabs vscode"
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Endpoints

### Root

```text
http://127.0.0.1:8000/
```

Expected response:

```json
{
  "app": "PulseTrack",
  "message": "Doctor-patient appointment and prescription API",
  "status": "ok"
}
```

### Health check

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "PulseTrack"
}
```
