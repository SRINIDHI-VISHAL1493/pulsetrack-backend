from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, time, timezone
from enum import Enum
import logging
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401  # registers SQLAlchemy models
from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTH_USERNAME,
    LoginRequest,
    TokenResponse,
    authenticate_request,
    authenticate_user,
    create_access_token,
    get_user_role,
)
from app.database import engine, init_db
from app.services import ExternalServiceError, ExternalServiceTimeoutError, fetch_external_status


logger = logging.getLogger("pulsetrack.api")


OPENAPI_TAGS = [
    {"name": "Health", "description": "Service liveness and readiness checks."},
    {"name": "Authentication", "description": "Bearer token issuance and authentication."},
    {"name": "Doctors", "description": "Doctor profile management."},
    {"name": "Patients", "description": "Patient record management."},
    {"name": "Appointments", "description": "Appointment scheduling and status management."},
    {"name": "Prescriptions", "description": "Prescription creation and retrieval."},
    {"name": "Integration", "description": "External service health and dependency status."},
]


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class Medication(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    dosage: str = Field(..., min_length=2, max_length=50)
    frequency: str = Field(..., min_length=2, max_length=60)
    duration_days: int = Field(..., ge=1, le=365)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class AppointmentUpdate(BaseModel):
    doctor_id: int | None = Field(default=None, gt=0)
    patient_id: int | None = Field(default=None, gt=0)
    appointment_date: date | None = None
    appointment_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    reason: str | None = Field(default=None, min_length=3, max_length=255)
    status: AppointmentStatus | None = None

    @field_validator("appointment_time")
    @classmethod
    def normalize_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("appointment_time must be in HH:MM format") from exc
        return value


class DoctorBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    specialization: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    clinic_name: Optional[str] = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("email must be a valid email address")
        return value


class DoctorCreate(DoctorBase):
    pass


class Doctor(DoctorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    date_of_birth: date
    gender: str = Field(..., pattern=r"^(male|female|other)$")
    email: str = Field(..., min_length=5, max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    address: str = Field(..., min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("email must be a valid email address")
        return value


class PatientCreate(PatientBase):
    pass


class Patient(PatientBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AppointmentBase(BaseModel):
    doctor_id: int = Field(..., gt=0)
    patient_id: int = Field(..., gt=0)
    appointment_date: date
    appointment_time: str = Field(..., pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    reason: str = Field(..., min_length=3, max_length=255)
    status: AppointmentStatus = AppointmentStatus.scheduled

    @field_validator("appointment_time")
    @classmethod
    def normalize_time(cls, value: str) -> str:
        try:
            time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("appointment_time must be in HH:MM format") from exc
        return value


class AppointmentCreate(AppointmentBase):
    pass


class Appointment(AppointmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PrescriptionBase(BaseModel):
    appointment_id: int = Field(..., gt=0)
    doctor_id: int = Field(..., gt=0)
    patient_id: int = Field(..., gt=0)
    diagnosis: str = Field(..., min_length=3, max_length=255)
    medications: List[Medication] = Field(..., min_length=1)
    instructions: str = Field(..., min_length=5, max_length=500)
    follow_up_date: Optional[date] = None


class PrescriptionCreate(PrescriptionBase):
    pass


class Prescription(PrescriptionBase):
    id: int
    issued_at: datetime
    model_config = ConfigDict(from_attributes=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="PulseTrack",
    description=(
        "A versioned API for doctor-patient appointments, prescriptions, "
        "authentication, authorization, and external service health."
    ),
    version="0.3.0",
    contact={"name": "PulseTrack API Team"},
    license_info={"name": "Internal project"},
    openapi_tags=OPENAPI_TAGS,
    debug=False,
    lifespan=lifespan,
)


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT-like HMAC token",
        }
    }
    for path, operations in schema["paths"].items():
        if path in PUBLIC_PATHS:
            continue
        for operation in operations.values():
            if isinstance(operation, dict):
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


PUBLIC_PATHS = {
    "/",
    "/health",
    "/readyz",
    "/api/v1/health",
    "/api/v1/readyz",
    "/api/v1/service-status",
    "/api/v1/auth/token",
    "/favicon.ico",
    "/docs",
    "/openapi.json",
    "/redoc",
}


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    if request.url.path not in PUBLIC_PATHS and not request.url.path.startswith(
        ("/docs/", "/redoc/")
    ):
        try:
            request.state.user = authenticate_request(request.headers.get("Authorization"))
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers={**(exc.headers or {}), "X-Request-ID": request_id},
            )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )
        raise
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        },
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    logger.warning(
        "request_validation_failed",
        extra={"request_id": request_id, "path": request.url.path, "errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Request validation failed", "errors": exc.errors(), "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    logger.exception(
        "unhandled_request_error",
        extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


doctors_db: Dict[int, Doctor] = {}
patients_db: Dict[int, Patient] = {}
appointments_db: Dict[int, Appointment] = {}
prescriptions_db: Dict[int, Prescription] = {}
ownership_db: dict[str, dict[int, str]] = {
    "doctors": {},
    "patients": {},
    "appointments": {},
    "prescriptions": {},
}


def current_user(request: Request) -> str:
    return request.state.user.username


def owned_record(
    collection: dict[int, object], ownership: dict[int, str], record_id: int, username: str, label: str
) -> object:
    record = collection.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    if ownership.get(record_id) != username:
        raise HTTPException(status_code=403, detail=f"You do not own this {label.lower()}")
    return record


def normalize_search_term(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def filter_owned_records(
    collection: dict[int, object],
    ownership: dict[int, str],
    username: str,
    *,
    search: str | None = None,
    **filters: object,
) -> list[object]:
    term = normalize_search_term(search)
    results: list[object] = []

    for record_id, record in sorted(collection.items()):
        if ownership.get(record_id) != username:
            continue
        if not all(
            getattr(record, key, None) == value
            for key, value in filters.items()
            if value is not None
        ):
            continue
        if term is not None:
            candidate_values = [
                getattr(record, "first_name", None),
                getattr(record, "last_name", None),
                getattr(record, "email", None),
                getattr(record, "phone", None),
                getattr(record, "specialization", None),
                getattr(record, "clinic_name", None),
                getattr(record, "patient_id", None),
                getattr(record, "doctor_id", None),
                getattr(record, "diagnosis", None),
                getattr(record, "instructions", None),
                getattr(record, "reason", None),
                getattr(record, "address", None),
                getattr(record, "status", None),
            ]
            if not any(term in str(value).lower() for value in candidate_values if value is not None):
                continue
        results.append(record)

    return results


def seed_demo_data() -> None:
    if doctors_db:
        return

    doctor_one = Doctor(
        id=1,
        first_name="Aisha",
        last_name="Rahman",
        specialization="Cardiology",
        email="aisha.rahman@pulsecare.com",
        phone="+1-555-0101",
        clinic_name="Northview Clinic",
    )
    doctor_two = Doctor(
        id=2,
        first_name="Daniel",
        last_name="Kim",
        specialization="General Medicine",
        email="daniel.kim@pulsecare.com",
        phone="+1-555-4402",
        clinic_name="Summit Health",
    )
    doctors_db[doctor_one.id] = doctor_one
    doctors_db[doctor_two.id] = doctor_two
    ownership_db["doctors"].update({doctor_one.id: AUTH_USERNAME, doctor_two.id: AUTH_USERNAME})

    patient_one = Patient(
        id=1,
        first_name="Maya",
        last_name="Patel",
        date_of_birth=date(1992, 4, 15),
        gender="female",
        email="maya.patel@example.com",
        phone="+1-555-2004",
        address="18 River Street, Brooklyn, NY",
    )
    patient_two = Patient(
        id=2,
        first_name="Lucas",
        last_name="Brown",
        date_of_birth=date(1988, 11, 4),
        gender="male",
        email="lucas.brown@example.com",
        phone="+1-555-3991",
        address="44 Pine Avenue, Austin, TX",
    )
    patients_db[patient_one.id] = patient_one
    patients_db[patient_two.id] = patient_two
    ownership_db["patients"].update({patient_one.id: AUTH_USERNAME, patient_two.id: AUTH_USERNAME})

    now = datetime.now(timezone.utc)
    appointment_one = Appointment(
        id=1,
        doctor_id=1,
        patient_id=1,
        appointment_date=date(2026, 9, 10),
        appointment_time="10:30",
        reason="Follow-up consultation for blood pressure review",
        status=AppointmentStatus.confirmed,
        created_at=now,
        updated_at=now,
    )
    appointments_db[appointment_one.id] = appointment_one
    ownership_db["appointments"][appointment_one.id] = AUTH_USERNAME

    prescription_one = Prescription(
        id=1,
        appointment_id=1,
        doctor_id=1,
        patient_id=1,
        diagnosis="Essential hypertension",
        medications=[
            Medication(
                name="Amlodipine",
                dosage="5mg",
                frequency="Once daily",
                duration_days=30,
            )
        ],
        instructions="Continue medication daily and monitor blood pressure twice per day.",
        follow_up_date=date(2026, 10, 10),
        issued_at=now,
    )
    prescriptions_db[prescription_one.id] = prescription_one
    ownership_db["prescriptions"][prescription_one.id] = AUTH_USERNAME


seed_demo_data()


@app.get("/", tags=["Health"], summary="Get API service information")
async def root() -> dict:
    return {
        "app": "PulseTrack",
        "message": "Doctor-patient appointment and prescription API",
        "status": "ok",
    }


@app.get("/health", tags=["Health"], summary="Check service health")
async def health() -> JSONResponse:
    payload, status_code = await readiness_response()
    return JSONResponse(status_code=status_code, content=payload)


async def readiness_response() -> tuple[dict, int]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("readiness_check_failed")
        return (
            {"status": "not_ready", "service": "PulseTrack", "database": "unavailable"},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return {"status": "ready", "service": "PulseTrack", "database": "ok"}, status.HTTP_200_OK


@app.get("/readyz", tags=["Health"], summary="Check service readiness")
async def readiness() -> JSONResponse:
    payload, status_code = await readiness_response()
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/api/v1/health", tags=["Health"], summary="Check versioned API health")
async def api_health() -> JSONResponse:
    payload, status_code = await readiness_response()
    payload["version"] = app.version
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/api/v1/readyz", tags=["Health"], summary="Check versioned service readiness")
async def api_readiness() -> JSONResponse:
    payload, status_code = await readiness_response()
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/api/v1/service-status", tags=["Integration"])
async def service_status() -> dict:
    try:
        external_status = fetch_external_status()
        if isinstance(external_status, dict) and (
            "provider" in external_status or "service" in external_status or "status" in external_status
        ):
            return {"status": "ok", "external_service": external_status}
        return {
            "status": "ok",
            "external_service": {"status": "healthy", "details": external_status},
        }
    except ExternalServiceTimeoutError:
        return {
            "status": "degraded",
            "external_service": {"status": "timeout", "details": {"error": "Upstream request timed out"}},
        }
    except ExternalServiceError:
        return {
            "status": "degraded",
            "external_service": {"status": "error", "details": {"error": "Upstream request failed"}},
        }


@app.post("/api/v1/auth/token", response_model=TokenResponse, tags=["Authentication"])
async def issue_access_token(payload: LoginRequest) -> TokenResponse:
    if not authenticate_user(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_in = max(0, ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    return TokenResponse(
        access_token=create_access_token(payload.username, get_user_role(payload.username)),
        expires_in=expires_in,
    )


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse("static/favicon.svg")


@app.get("/api/v1/doctors", response_model=List[Doctor], tags=["Doctors"])
async def list_doctors(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1),
    search: str | None = Query(default=None, min_length=1),
) -> List[Doctor]:
    username = current_user(request)
    records = filter_owned_records(
        doctors_db,
        ownership_db["doctors"],
        username,
        search=search,
    )
    return records[skip : skip + limit]


@app.post(
    "/api/v1/doctors",
    response_model=Doctor,
    status_code=status.HTTP_201_CREATED,
    tags=["Doctors"],
)
async def create_doctor(request: Request, payload: DoctorCreate) -> Doctor:
    normalized_email = payload.email.lower()
    if any(doctor.email.lower() == normalized_email for doctor in doctors_db.values()):
        raise HTTPException(status_code=400, detail="Doctor with this email already exists")

    doctor_id = max(doctors_db.keys(), default=0) + 1
    doctor = Doctor(id=doctor_id, **payload.model_dump())
    doctors_db[doctor_id] = doctor
    ownership_db["doctors"][doctor_id] = current_user(request)
    return doctor


@app.get("/api/v1/doctors/{doctor_id}", response_model=Doctor, tags=["Doctors"])
async def get_doctor(request: Request, doctor_id: int) -> Doctor:
    return owned_record(
        doctors_db, ownership_db["doctors"], doctor_id, current_user(request), "Doctor"
    )


@app.get("/api/v1/patients", response_model=List[Patient], tags=["Patients"])
async def list_patients(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1),
    search: str | None = Query(default=None, min_length=1),
) -> List[Patient]:
    username = current_user(request)
    records = filter_owned_records(
        patients_db,
        ownership_db["patients"],
        username,
        search=search,
    )
    return records[skip : skip + limit]


@app.post(
    "/api/v1/patients",
    response_model=Patient,
    status_code=status.HTTP_201_CREATED,
    tags=["Patients"],
)
async def create_patient(request: Request, payload: PatientCreate) -> Patient:
    normalized_email = payload.email.lower()
    if any(patient.email.lower() == normalized_email for patient in patients_db.values()):
        raise HTTPException(status_code=400, detail="Patient with this email already exists")

    patient_id = max(patients_db.keys(), default=0) + 1
    patient = Patient(id=patient_id, **payload.model_dump())
    patients_db[patient_id] = patient
    ownership_db["patients"][patient_id] = current_user(request)
    return patient


@app.get("/api/v1/patients/{patient_id}", response_model=Patient, tags=["Patients"])
async def get_patient(request: Request, patient_id: int) -> Patient:
    return owned_record(
        patients_db, ownership_db["patients"], patient_id, current_user(request), "Patient"
    )


@app.get(
    "/api/v1/appointments",
    response_model=List[Appointment],
    tags=["Appointments"],
)
async def list_appointments(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1),
    search: str | None = Query(default=None, min_length=1),
    status: AppointmentStatus | None = Query(default=None),
    doctor_id: int | None = Query(default=None, ge=1),
    patient_id: int | None = Query(default=None, ge=1),
) -> List[Appointment]:
    username = current_user(request)
    records = filter_owned_records(
        appointments_db,
        ownership_db["appointments"],
        username,
        search=search,
        status=status,
        doctor_id=doctor_id,
        patient_id=patient_id,
    )
    return records[skip : skip + limit]


@app.post(
    "/api/v1/appointments",
    response_model=Appointment,
    status_code=status.HTTP_201_CREATED,
    tags=["Appointments"],
)
async def create_appointment(request: Request, payload: AppointmentCreate) -> Appointment:
    username = current_user(request)
    if payload.doctor_id not in doctors_db:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if payload.patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    owned_record(doctors_db, ownership_db["doctors"], payload.doctor_id, username, "Doctor")
    owned_record(patients_db, ownership_db["patients"], payload.patient_id, username, "Patient")

    appointment_id = max(appointments_db.keys(), default=0) + 1
    created_at = datetime.now(timezone.utc)
    appointment = Appointment(
        id=appointment_id,
        created_at=created_at,
        updated_at=created_at,
        **payload.model_dump(),
    )
    appointments_db[appointment_id] = appointment
    ownership_db["appointments"][appointment_id] = username
    return appointment


@app.get(
    "/api/v1/appointments/{appointment_id}",
    response_model=Appointment,
    tags=["Appointments"],
)
async def get_appointment(request: Request, appointment_id: int) -> Appointment:
    return owned_record(
        appointments_db,
        ownership_db["appointments"],
        appointment_id,
        current_user(request),
        "Appointment",
    )


@app.patch(
    "/api/v1/appointments/{appointment_id}",
    response_model=Appointment,
    tags=["Appointments"],
)
async def update_appointment(
    request: Request,
    appointment_id: int,
    payload: AppointmentUpdate,
) -> Appointment:
    username = current_user(request)
    appointment = owned_record(
        appointments_db, ownership_db["appointments"], appointment_id, username, "Appointment"
    )

    update_data = payload.model_dump(exclude_unset=True)
    if "doctor_id" in update_data and update_data["doctor_id"] is not None:
        if update_data["doctor_id"] not in doctors_db:
            raise HTTPException(status_code=404, detail="Doctor not found")
        owned_record(
            doctors_db, ownership_db["doctors"], update_data["doctor_id"], username, "Doctor"
        )
    if "patient_id" in update_data and update_data["patient_id"] is not None:
        if update_data["patient_id"] not in patients_db:
            raise HTTPException(status_code=404, detail="Patient not found")
        owned_record(
            patients_db, ownership_db["patients"], update_data["patient_id"], username, "Patient"
        )

    for field, value in update_data.items():
        setattr(appointment, field, value)
    appointment.updated_at = datetime.now(timezone.utc)
    appointments_db[appointment_id] = appointment
    return appointment


@app.patch(
    "/api/v1/appointments/{appointment_id}/status",
    response_model=Appointment,
    tags=["Appointments"],
)
async def update_appointment_status(
    request: Request,
    appointment_id: int,
    payload: AppointmentStatusUpdate | None = None,
    status: AppointmentStatus | None = None,
) -> Appointment:
    appointment = owned_record(
        appointments_db,
        ownership_db["appointments"],
        appointment_id,
        current_user(request),
        "Appointment",
    )

    resolved_status = payload.status if payload is not None else status
    if resolved_status is None:
        raise HTTPException(status_code=400, detail="Status is required")

    appointment.status = resolved_status
    appointment.updated_at = datetime.now(timezone.utc)
    appointments_db[appointment_id] = appointment
    return appointment


@app.delete(
    "/api/v1/appointments/{appointment_id}",
    tags=["Appointments"],
)
async def delete_appointment(request: Request, appointment_id: int) -> dict:
    appointment = owned_record(
        appointments_db,
        ownership_db["appointments"],
        appointment_id,
        current_user(request),
        "Appointment",
    )

    for prescription_id, prescription in list(prescriptions_db.items()):
        if prescription.appointment_id == appointment_id:
            del prescriptions_db[prescription_id]
            del ownership_db["prescriptions"][prescription_id]

    del appointments_db[appointment_id]
    del ownership_db["appointments"][appointment_id]
    return {"detail": "Appointment deleted successfully"}


@app.get(
    "/api/v1/prescriptions",
    response_model=List[Prescription],
    tags=["Prescriptions"],
)
async def list_prescriptions(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1),
    search: str | None = Query(default=None, min_length=1),
    doctor_id: int | None = Query(default=None, ge=1),
    patient_id: int | None = Query(default=None, ge=1),
    appointment_id: int | None = Query(default=None, ge=1),
) -> List[Prescription]:
    username = current_user(request)
    records = filter_owned_records(
        prescriptions_db,
        ownership_db["prescriptions"],
        username,
        search=search,
        doctor_id=doctor_id,
        patient_id=patient_id,
        appointment_id=appointment_id,
    )
    return records[skip : skip + limit]


@app.post(
    "/api/v1/prescriptions",
    response_model=Prescription,
    status_code=status.HTTP_201_CREATED,
    tags=["Prescriptions"],
)
async def create_prescription(request: Request, payload: PrescriptionCreate) -> Prescription:
    username = current_user(request)
    if payload.appointment_id not in appointments_db:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if payload.doctor_id not in doctors_db:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if payload.patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    owned_record(
        appointments_db, ownership_db["appointments"], payload.appointment_id, username, "Appointment"
    )
    owned_record(doctors_db, ownership_db["doctors"], payload.doctor_id, username, "Doctor")
    owned_record(patients_db, ownership_db["patients"], payload.patient_id, username, "Patient")

    appointment = appointments_db[payload.appointment_id]
    if appointment.doctor_id != payload.doctor_id or appointment.patient_id != payload.patient_id:
        raise HTTPException(
            status_code=400,
            detail="Prescription must match the appointment doctor and patient",
        )

    prescription_id = max(prescriptions_db.keys(), default=0) + 1
    prescription = Prescription(
        id=prescription_id,
        issued_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    prescriptions_db[prescription_id] = prescription
    ownership_db["prescriptions"][prescription_id] = username
    return prescription


@app.get(
    "/api/v1/prescriptions/{prescription_id}",
    response_model=Prescription,
    tags=["Prescriptions"],
)
async def get_prescription(request: Request, prescription_id: int) -> Prescription:
    return owned_record(
        prescriptions_db,
        ownership_db["prescriptions"],
        prescription_id,
        current_user(request),
        "Prescription",
    )


@app.delete(
    "/api/v1/prescriptions/{prescription_id}",
    tags=["Prescriptions"],
)
async def delete_prescription(request: Request, prescription_id: int) -> dict:
    owned_record(
        prescriptions_db,
        ownership_db["prescriptions"],
        prescription_id,
        current_user(request),
        "Prescription",
    )

    del prescriptions_db[prescription_id]
    del ownership_db["prescriptions"][prescription_id]
    return {"detail": "Prescription deleted successfully"}


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("UVICORN_RELOAD", "false").lower() == "true",
    )
