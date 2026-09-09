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
- Domain models for doctors, patients, appointments, and prescriptions
- RESTful endpoint planning with request/response validation

## Project goals

- Build a robust backend for healthcare operations
- Support doctor and patient management workflows
- Enable appointment scheduling and tracking
- Manage prescription creation and retrieval
- Provide structured APIs for future frontend integration
- Maintain clean, modular backend architecture

## Task 3: Database setup

This milestone adds the persistence layer for the PulseTrack healthcare API. The backend now uses SQLAlchemy with async database access and Alembic for schema versioning, so the application transitions from in-memory data storage to a real database-backed architecture.

### Database architecture

- PostgreSQL is the production-ready target database for the healthcare platform
- SQLAlchemy ORM models define the core entities and relationships
- Alembic tracks schema changes and supports safe migrations
- Async database sessions enable non-blocking data access in FastAPI
- A local SQLite fallback is included for development and testing consistency

### Models and relationships

The database schema includes the four core entities:

- Doctor: profile and clinic information
- Patient: demographics, contact details, and address
- Appointment: scheduled doctor-patient consultation relationship
- Prescription: medical diagnosis, medications, instructions, and follow-up date

### Alembic workflow

```bash
cd "/Users/srinidhivishalchejarla/Downloads/zyoralabs vscode"
source .venv/bin/activate
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

### Environment configuration

```bash
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/pulsetrack"
```

If no database URL is set, the application falls back to a local SQLite database for quick testing.

## Task 2: API design

This milestone focuses on defining the core healthcare domain and the REST contract before implementation. The system centers on four main entities:

- Doctor: personal profile, specialization, clinic association, and contact details
- Patient: demographic data, DOB, contact information, and address
- Appointment: scheduled meeting between a doctor and patient with status tracking
- Prescription: clinical diagnosis, medicines, instructions, and follow-up plan

### Relationships

- One doctor can have many appointments
- One patient can have many appointments
- Each appointment belongs to exactly one doctor and one patient
- Each prescription belongs to one appointment, one doctor, and one patient

### Pydantic models

The API uses Pydantic models to validate request and response payloads for all core entities. These models define required fields, optional fields, and constraints such as field lengths, date validation, and supported appointment statuses.

### Endpoint plan

#### Doctors

- `GET /api/v1/doctors` — list all doctors
- `POST /api/v1/doctors` — create a doctor profile
- `GET /api/v1/doctors/{doctor_id}` — fetch a specific doctor

#### Patients

- `GET /api/v1/patients` — list all patients
- `POST /api/v1/patients` — create a patient profile
- `GET /api/v1/patients/{patient_id}` — fetch a specific patient

#### Appointments

- `GET /api/v1/appointments` — list all appointments
- `POST /api/v1/appointments` — schedule a consultation
- `GET /api/v1/appointments/{appointment_id}` — fetch one appointment
- `PATCH /api/v1/appointments/{appointment_id}` — update appointment details
- `PATCH /api/v1/appointments/{appointment_id}/status` — update appointment status
- `DELETE /api/v1/appointments/{appointment_id}` — remove an appointment and any related prescriptions

#### Prescriptions

- `GET /api/v1/prescriptions` — list all prescriptions
- `POST /api/v1/prescriptions` — create a prescription after an appointment
- `GET /api/v1/prescriptions/{prescription_id}` — fetch one prescription
- `DELETE /api/v1/prescriptions/{prescription_id}` — delete a prescription

### Success and error handling

- Standard HTTP 200 responses for fetches and updates
- HTTP 201 for successful creation
- HTTP 404 when a doctor, patient, appointment, or prescription is missing
- HTTP 400 validation errors for invalid relation mapping or malformed payloads

## Task 4: Create workflow

This milestone completes the core create workflow for the healthcare backend. It includes validation, persistence for valid records, and structured 4xx responses for invalid requests.

### Completed workflow

- Create doctor profiles via `POST /api/v1/doctors`
- Create patient profiles via `POST /api/v1/patients`
- Create appointment records via `POST /api/v1/appointments`
- Create prescriptions via `POST /api/v1/prescriptions`
- Update appointment status via `PATCH /api/v1/appointments/{appointment_id}/status`

### Completion guide

- Valid data is persisted
- Invalid input returns useful 4xx errors
- Response payloads do not expose internal fields

### Validation rules

- Required doctor and patient fields are enforced
- Email format and length are validated
- Appointment status must match the supported enum values
- Prescription must reference a valid doctor, patient, and appointment pair
- A doctor/patient cannot be created with a duplicate email

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
- Signed bearer-token authentication for protected API routes
  "message": "Doctor-patient appointment and prescription API",
  "status": "ok"
}
```

### Health check


```json
{
  "status": "ok",
  "service": "PulseTrack"
}

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

Use the returned `access_token` for protected requests with `Authorization: Bearer <token>`. Tokens use HMAC-SHA256 signing and are rejected after expiry or tampering.

## Task 8: Authorization

Private doctor, patient, appointment, and prescription queries are scoped to the authenticated user. Cross-user detail, update, and delete requests return `403 Forbidden`, while collection endpoints return only records owned by the current user. New records inherit the authenticated user as their owner, and related records must also belong to that user.
```

### API design examples

```text
GET http://127.0.0.1:8000/api/v1/doctors
POST http://127.0.0.1:8000/api/v1/doctors
GET http://127.0.0.1:8000/api/v1/patients
POST http://127.0.0.1:8000/api/v1/appointments
POST http://127.0.0.1:8000/api/v1/prescriptions
```

## Task 5: Read workflow completion

This milestone completes the read and update workflow for the PulseTrack healthcare API. It ensures the backend supports responsive list queries, reliable detail lookups, and consistent status updates for scheduled appointments.

### Completion guide

- List endpoints are paginated via `skip` and `limit`
- Detail endpoints are scoped to the correct resource ID
- Missing records return a `404` response
- Appointment status updates accept both JSON payloads and query-parameter input
- Read workflow behavior is covered by automated tests

## Task 6: Update and delete workflow

This milestone adds the final lifecycle controls to the PulseTrack healthcare API. It lets teams make partial updates to appointment details, change status with a dedicated endpoint, and safely remove appointments or prescriptions while keeping the data model consistent.

### Completed workflow

- Update appointment details via `PATCH /api/v1/appointments/{appointment_id}`
- Update appointment status via `PATCH /api/v1/appointments/{appointment_id}/status`
- Delete an appointment and remove related prescriptions via `DELETE /api/v1/appointments/{appointment_id}`
- Delete a prescription via `DELETE /api/v1/prescriptions/{prescription_id}`

### Project status

The repository now includes the backend foundation, the Task 2 API design for doctors, patients, appointments, and prescriptions, the Task 3 database setup with SQLAlchemy ORM models, async database access, and Alembic migration support, the Task 4 create workflow for healthcare records with validation and status updates, the Task 5 completion of the read workflow with pagination and 404 validation, and the Task 6 update-and-delete workflow with safe removal and partial appointment updates.
