# PulseTrack

PulseTrack is a FastAPI-based backend project designed for a doctor-patient appointment and prescription management system. It serves as the foundation for a healthcare platform where doctors can manage patient records, schedule appointments, and issue prescriptions through a clean and scalable API.

This project is being developed as part of a Python backend internship and is structured to evolve from a basic backend foundation into a fully functional healthcare service API.

## Features

- FastAPI application scaffold
- Health check endpoint for service validation
- Clean project structure for scalable backend development
- Local environment setup with Python virtual environment
- Browser-friendly favicon support
- API-ready foundation for future modules and authentication

## Project goals

- Build a robust backend for healthcare operations
- Support doctor and patient management workflows
- Enable appointment scheduling and tracking
- Manage prescription creation and retrieval
- Provide structured APIs for future frontend integration
- Maintain clean, modular backend architecture

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

Example response:

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

Example response:

```json
{
  "status": "ok",
  "service": "PulseTrack"
}
```

## Project status

The repository currently includes the initial backend foundation and is ready for the next phases of feature development, including doctor and patient APIs, appointment logic, and prescription management.
