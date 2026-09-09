# PulseTrack

PulseTrack is a FastAPI backend for doctor-patient appointment and prescription management. It is being developed as part of a Python backend internship and evolves through an ordered set of implementation milestones.

## Features

- FastAPI application scaffold
- Health check endpoints
- SQLAlchemy async database setup with Alembic migrations
- Doctor, patient, appointment, and prescription workflows
- Signed bearer-token authentication
- Owner-scoped authorization for private records
- Request validation and paginated list endpoints

## Project goals

- Build a robust backend for healthcare operations
- Support doctor and patient management workflows
- Enable appointment scheduling and tracking
- Manage prescription creation and retrieval
- Provide structured APIs for frontend integration

## Task 1: Foundation and environment

The project begins with a FastAPI application scaffold, a clean module layout, local virtual-environment support, health checks, and browser-friendly favicon support.

### Run locally

```bash
cd "/Users/srinidhivishalchejarla/Downloads/zyoralabs vscode"
source .venv/bin/activate
uvicorn app.main:app --reload
```

The service is available at `http://127.0.0.1:8000`. The root and health endpoints provide basic service validation.

## Task 2: API design

The API is organized around four healthcare entities:

- Doctor: personal profile, specialization, clinic association, and contact details
- Patient: demographic data, date of birth, contact information, and address
- Appointment: a scheduled doctor-patient consultation with status tracking
- Prescription: diagnosis, medications, instructions, and follow-up plan

### Relationships

- One doctor can have many appointments
- One patient can have many appointments
- Each appointment belongs to one doctor and one patient
- Each prescription belongs to one appointment, doctor, and patient

### Endpoint plan

#### Doctors

- `GET /api/v1/doctors` - list doctors
- `POST /api/v1/doctors` - create a doctor
- `GET /api/v1/doctors/{doctor_id}` - fetch a doctor

#### Patients

- `GET /api/v1/patients` - list patients
- `POST /api/v1/patients` - create a patient
- `GET /api/v1/patients/{patient_id}` - fetch a patient

#### Appointments

- `GET /api/v1/appointments` - list appointments
- `POST /api/v1/appointments` - schedule an appointment
- `GET /api/v1/appointments/{appointment_id}` - fetch an appointment
- `PATCH /api/v1/appointments/{appointment_id}` - update appointment details
- `PATCH /api/v1/appointments/{appointment_id}/status` - update status
- `DELETE /api/v1/appointments/{appointment_id}` - delete an appointment and related prescriptions

#### Prescriptions

- `GET /api/v1/prescriptions` - list prescriptions
- `POST /api/v1/prescriptions` - create a prescription
- `GET /api/v1/prescriptions/{prescription_id}` - fetch a prescription
- `DELETE /api/v1/prescriptions/{prescription_id}` - delete a prescription

## Task 3: Database setup

The persistence layer uses SQLAlchemy with async database access and Alembic for schema versioning. PostgreSQL is the production target, with a local SQLite fallback for development and testing.

### Database architecture

- SQLAlchemy ORM models define the core entities and relationships
- Alembic tracks schema changes
- Async database sessions support non-blocking FastAPI operations
- SQLite provides a quick local fallback when `DATABASE_URL` is not set

### Environment configuration

```bash
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/pulsetrack"
```

### Alembic workflow

```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

## Task 4: Create workflow

The create workflow validates and stores doctor, patient, appointment, and prescription records.

### Completion guide

- Valid data is persisted
- Invalid input returns useful 4xx errors
- Required doctor and patient fields are enforced
- Email format and duplicate-email checks are enforced
- Appointment status values are validated
- Prescriptions must reference a matching doctor, patient, and appointment

## Task 5: Read workflow

The read workflow provides paginated collection queries and reliable detail lookups.

### Completion guide

- List endpoints support `skip` and `limit`
- Detail endpoints are scoped to the requested resource ID
- Missing records return `404 Not Found`
- Appointment status updates accept JSON payloads and query parameters
- Read behavior is covered by automated tests

## Task 6: Update and delete workflow

The update and delete workflow supports partial appointment updates, status changes, and safe record removal.

### Completion guide

- Appointment details can be partially updated
- Appointment status can be updated independently
- Deleting an appointment removes related prescriptions
- Prescriptions can be deleted directly
- Deleted records return `404 Not Found` when fetched again

## Task 7: Authentication

Domain endpoints require a signed bearer token. Health endpoints, API documentation, and the token endpoint remain public.

Set these environment variables before starting the service:

```bash
export PULSETRACK_AUTH_SECRET_KEY="replace-with-a-long-random-secret"
export PULSETRACK_AUTH_USERNAME="demo"
export PULSETRACK_AUTH_PASSWORD="replace-with-a-strong-password"
export PULSETRACK_ACCESS_TOKEN_EXPIRE_MINUTES="60"
```

For multiple users, optionally provide comma-separated `username:password:role` entries:

```bash
export PULSETRACK_AUTH_USERS="demo:replace-with-a-strong-password:user,clinician:another-strong-password:doctor"
```

Request a token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"replace-with-a-strong-password"}'
```

Use the returned `access_token` with `Authorization: Bearer <token>`. Tokens use HMAC-SHA256 signing and are rejected after expiry or tampering.

### Authentication completion guide

- Credentials and tokens are validated
- Anonymous requests to protected routes return `401 Unauthorized`
- Secrets are loaded from environment variables
- Authentication behavior is covered by automated tests

## Task 8: Authorization

Private doctor, patient, appointment, and prescription queries are scoped to the authenticated user.

### Authorization completion guide

- Every private collection query returns only owner records
- Cross-user detail, update, and delete requests return `403 Forbidden`
- New records inherit the authenticated user as their owner
- Related records must also belong to that user
- Ownership behavior is covered by automated tests

## Common endpoints

```text
GET http://127.0.0.1:8000/
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/api/v1/health
POST http://127.0.0.1:8000/api/v1/auth/token
```

## Validation

```bash
python -m compileall -q app tests
python -m pytest -q
```
