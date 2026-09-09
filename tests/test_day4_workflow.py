from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.main import app


client = TestClient(app, headers={"Authorization": f"Bearer {create_access_token()}"})


def test_create_doctor_persists_and_is_fetchable():
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "specialization": "Neurology",
        "email": "ada.lovelace@example.com",
        "phone": "+1-555-1234",
        "clinic_name": "Analytical Health",
    }

    response = client.post("/api/v1/doctors", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == payload["email"]
    assert body["id"] > 0

    fetch_response = client.get(f"/api/v1/doctors/{body['id']}")
    assert fetch_response.status_code == 200
    assert fetch_response.json()["email"] == payload["email"]


def test_update_appointment_status_accepts_status_payload():
    doctor_response = client.post(
        "/api/v1/doctors",
        json={
            "first_name": "Grace",
            "last_name": "Hopper",
            "specialization": "Cardiology",
            "email": "grace.hopper@example.com",
            "phone": "+1-555-9999",
            "clinic_name": "Command Clinic",
        },
    )
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Alan",
            "last_name": "Turing",
            "date_of_birth": "1912-06-23",
            "gender": "male",
            "email": "alan.turing@example.com",
            "phone": "+1-555-7777",
            "address": "42 Bletchley Park",
        },
    )

    appointment_response = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_response.json()["id"],
            "patient_id": patient_response.json()["id"],
            "appointment_date": "2026-09-20",
            "appointment_time": "14:15",
            "reason": "Routine review",
            "status": "scheduled",
        },
    )
    appointment_id = appointment_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        json={"status": "completed"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["status"] == "completed"


def test_update_appointment_status_accepts_query_parameter():
    doctor_response = client.post(
        "/api/v1/doctors",
        json={
            "first_name": "Margaret",
            "last_name": "Hamilton",
            "specialization": "Emergency Medicine",
            "email": "margaret.hamilton@example.com",
            "phone": "+1-555-1122",
            "clinic_name": "Northstar Clinic",
        },
    )
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "von Neumann",
            "date_of_birth": "1903-12-28",
            "gender": "male",
            "email": "john.vonneumann@example.com",
            "phone": "+1-555-3344",
            "address": "1 Institute Road",
        },
    )

    appointment_response = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_response.json()["id"],
            "patient_id": patient_response.json()["id"],
            "appointment_date": "2026-09-25",
            "appointment_time": "09:00",
            "reason": "Follow-up evaluation",
            "status": "scheduled",
        },
    )
    appointment_id = appointment_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/appointments/{appointment_id}/status?status=confirmed"
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["status"] == "confirmed"


def test_partial_update_and_delete_appointment_flow():
    doctor_response = client.post(
        "/api/v1/doctors",
        json={
            "first_name": "Rosalind",
            "last_name": "Franklin",
            "specialization": "Oncology",
            "email": "rosalind.franklin@example.com",
            "phone": "+1-555-8821",
            "clinic_name": "Lattice Care",
        },
    )
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Katherine",
            "last_name": "Johnson",
            "date_of_birth": "1956-08-26",
            "gender": "female",
            "email": "katherine.johnson@example.com",
            "phone": "+1-555-1133",
            "address": "22 Celestial Avenue",
        },
    )

    appointment_response = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_response.json()["id"],
            "patient_id": patient_response.json()["id"],
            "appointment_date": "2026-09-28",
            "appointment_time": "11:30",
            "reason": "Initial screening",
            "status": "scheduled",
        },
    )
    appointment_id = appointment_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/appointments/{appointment_id}",
        json={"reason": "Follow-up screening", "status": "confirmed"},
    )
    assert update_response.status_code == 200, update_response.text
    payload = update_response.json()
    assert payload["reason"] == "Follow-up screening"
    assert payload["status"] == "confirmed"

    delete_response = client.delete(f"/api/v1/appointments/{appointment_id}")
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["detail"] == "Appointment deleted successfully"

    fetch_response = client.get(f"/api/v1/appointments/{appointment_id}")
    assert fetch_response.status_code == 404


def test_delete_prescription_removes_related_record():
    doctor_response = client.post(
        "/api/v1/doctors",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "specialization": "Pediatrics",
            "email": "jane.doe@example.com",
            "phone": "+1-555-2000",
            "clinic_name": "Little Sprouts",
        },
    )
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Ethan",
            "last_name": "Smith",
            "date_of_birth": "2015-04-12",
            "gender": "male",
            "email": "ethan.smith@example.com",
            "phone": "+1-555-9090",
            "address": "7 Maple Street",
        },
    )
    appointment_response = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_response.json()["id"],
            "patient_id": patient_response.json()["id"],
            "appointment_date": "2026-10-02",
            "appointment_time": "15:45",
            "reason": "Child wellness visit",
            "status": "scheduled",
        },
    )
    appointment_id = appointment_response.json()["id"]

    prescription_response = client.post(
        "/api/v1/prescriptions",
        json={
            "appointment_id": appointment_id,
            "doctor_id": doctor_response.json()["id"],
            "patient_id": patient_response.json()["id"],
            "diagnosis": "Seasonal allergy",
            "medications": [
                {
                    "name": "Cetirizine",
                    "dosage": "10mg",
                    "frequency": "Once daily",
                    "duration_days": 14,
                }
            ],
            "instructions": "Use as directed and review symptoms after one week.",
            "follow_up_date": "2026-10-16",
        },
    )
    prescription_id = prescription_response.json()["id"]

    delete_response = client.delete(f"/api/v1/prescriptions/{prescription_id}")
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["detail"] == "Prescription deleted successfully"

    fetch_response = client.get(f"/api/v1/prescriptions/{prescription_id}")
    assert fetch_response.status_code == 404


def test_list_endpoints_are_paginated_and_ordered():
    doctor_response = client.get("/api/v1/doctors?limit=1&skip=0")
    assert doctor_response.status_code == 200
    assert len(doctor_response.json()) == 1

    patient_response = client.get("/api/v1/patients?limit=1&skip=0")
    assert patient_response.status_code == 200
    assert len(patient_response.json()) == 1

    appointment_response = client.get("/api/v1/appointments?limit=1&skip=0")
    assert appointment_response.status_code == 200
    assert len(appointment_response.json()) == 1

    prescription_response = client.get("/api/v1/prescriptions?limit=1&skip=0")
    assert prescription_response.status_code == 200
    assert len(prescription_response.json()) == 1
