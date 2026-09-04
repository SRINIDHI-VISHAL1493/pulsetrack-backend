from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import models  # noqa: F401  # registers SQLAlchemy models
from app.database import init_db


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


app = FastAPI(
    title="PulseTrack",
    description="Doctor-patient appointment and prescription API",
    version="0.2.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()


doctors_db: Dict[int, Doctor] = {}
patients_db: Dict[int, Patient] = {}
appointments_db: Dict[int, Appointment] = {}
prescriptions_db: Dict[int, Prescription] = {}


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

    now = datetime.utcnow()
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


seed_demo_data()


@app.get("/")
async def root() -> dict:
    return {
        "app": "PulseTrack",
        "message": "Doctor-patient appointment and prescription API",
        "status": "ok",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "PulseTrack"}


@app.get("/api/v1/health")
async def api_health() -> dict:
    return {"status": "ok", "service": "PulseTrack", "version": app.version}


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse("static/favicon.svg")


@app.get("/api/v1/doctors", response_model=List[Doctor], tags=["Doctors"])
async def list_doctors() -> List[Doctor]:
    return list(doctors_db.values())


@app.post(
    "/api/v1/doctors",
    response_model=Doctor,
    status_code=status.HTTP_201_CREATED,
    tags=["Doctors"],
)
async def create_doctor(payload: DoctorCreate) -> Doctor:
    normalized_email = payload.email.lower()
    if any(doctor.email.lower() == normalized_email for doctor in doctors_db.values()):
        raise HTTPException(status_code=400, detail="Doctor with this email already exists")

    doctor_id = max(doctors_db.keys(), default=0) + 1
    doctor = Doctor(id=doctor_id, **payload.model_dump())
    doctors_db[doctor_id] = doctor
    return doctor


@app.get("/api/v1/doctors/{doctor_id}", response_model=Doctor, tags=["Doctors"])
async def get_doctor(doctor_id: int) -> Doctor:
    doctor = doctors_db.get(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@app.get("/api/v1/patients", response_model=List[Patient], tags=["Patients"])
async def list_patients() -> List[Patient]:
    return list(patients_db.values())


@app.post(
    "/api/v1/patients",
    response_model=Patient,
    status_code=status.HTTP_201_CREATED,
    tags=["Patients"],
)
async def create_patient(payload: PatientCreate) -> Patient:
    normalized_email = payload.email.lower()
    if any(patient.email.lower() == normalized_email for patient in patients_db.values()):
        raise HTTPException(status_code=400, detail="Patient with this email already exists")

    patient_id = max(patients_db.keys(), default=0) + 1
    patient = Patient(id=patient_id, **payload.model_dump())
    patients_db[patient_id] = patient
    return patient


@app.get("/api/v1/patients/{patient_id}", response_model=Patient, tags=["Patients"])
async def get_patient(patient_id: int) -> Patient:
    patient = patients_db.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.get(
    "/api/v1/appointments",
    response_model=List[Appointment],
    tags=["Appointments"],
)
async def list_appointments() -> List[Appointment]:
    return list(appointments_db.values())


@app.post(
    "/api/v1/appointments",
    response_model=Appointment,
    status_code=status.HTTP_201_CREATED,
    tags=["Appointments"],
)
async def create_appointment(payload: AppointmentCreate) -> Appointment:
    if payload.doctor_id not in doctors_db:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if payload.patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")

    appointment_id = max(appointments_db.keys(), default=0) + 1
    created_at = datetime.utcnow()
    appointment = Appointment(
        id=appointment_id,
        created_at=created_at,
        updated_at=created_at,
        **payload.model_dump(),
    )
    appointments_db[appointment_id] = appointment
    return appointment


@app.get(
    "/api/v1/appointments/{appointment_id}",
    response_model=Appointment,
    tags=["Appointments"],
)
async def get_appointment(appointment_id: int) -> Appointment:
    appointment = appointments_db.get(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@app.patch(
    "/api/v1/appointments/{appointment_id}/status",
    response_model=Appointment,
    tags=["Appointments"],
)
async def update_appointment_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate | None = None,
    status_value: AppointmentStatus | None = None,
) -> Appointment:
    appointment = appointments_db.get(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    resolved_status = payload.status if payload is not None else status_value
    if resolved_status is None:
        raise HTTPException(status_code=400, detail="Status is required")

    appointment.status = resolved_status
    appointment.updated_at = datetime.utcnow()
    appointments_db[appointment_id] = appointment
    return appointment


@app.get(
    "/api/v1/prescriptions",
    response_model=List[Prescription],
    tags=["Prescriptions"],
)
async def list_prescriptions() -> List[Prescription]:
    return list(prescriptions_db.values())


@app.post(
    "/api/v1/prescriptions",
    response_model=Prescription,
    status_code=status.HTTP_201_CREATED,
    tags=["Prescriptions"],
)
async def create_prescription(payload: PrescriptionCreate) -> Prescription:
    if payload.appointment_id not in appointments_db:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if payload.doctor_id not in doctors_db:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if payload.patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")

    appointment = appointments_db[payload.appointment_id]
    if appointment.doctor_id != payload.doctor_id or appointment.patient_id != payload.patient_id:
        raise HTTPException(
            status_code=400,
            detail="Prescription must match the appointment doctor and patient",
        )

    prescription_id = max(prescriptions_db.keys(), default=0) + 1
    prescription = Prescription(
        id=prescription_id,
        issued_at=datetime.utcnow(),
        **payload.model_dump(),
    )
    prescriptions_db[prescription_id] = prescription
    return prescription


@app.get(
    "/api/v1/prescriptions/{prescription_id}",
    response_model=Prescription,
    tags=["Prescriptions"],
)
async def get_prescription(prescription_id: int) -> Prescription:
    prescription = prescriptions_db.get(prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
