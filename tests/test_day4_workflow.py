from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
