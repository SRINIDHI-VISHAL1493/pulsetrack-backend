from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.main import app


client = TestClient(app, headers={"Authorization": f"Bearer {create_access_token()}"})


def test_search_and_filter_endpoints_are_applied_in_collection_queries():
    doctor_response = client.post(
        "/api/v1/doctors",
        json={
            "first_name": "Marie",
            "last_name": "Curie",
            "specialization": "Radiology",
            "email": "marie.curie@example.com",
            "phone": "+1-555-2200",
            "clinic_name": "Beacon Care",
        },
    )
    doctor_id = doctor_response.json()["id"]

    patient_response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Nikola",
            "last_name": "Tesla",
            "date_of_birth": "1856-07-10",
            "gender": "male",
            "email": "nikola.tesla@example.com",
            "phone": "+1-555-3311",
            "address": "15 Wardenclyffe Lane",
        },
    )
    patient_id = patient_response.json()["id"]

    appointment_response = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "appointment_date": "2026-10-20",
            "appointment_time": "16:00",
            "reason": "Imaging consult",
            "status": "scheduled",
        },
    )
    appointment_id = appointment_response.json()["id"]

    search_doctors = client.get("/api/v1/doctors?search=Marie")
    assert search_doctors.status_code == 200
    assert any(doc["email"] == "marie.curie@example.com" for doc in search_doctors.json())

    filtered = client.get(f"/api/v1/appointments?status=scheduled&doctor_id={doctor_id}&patient_id={patient_id}")
    assert filtered.status_code == 200
    assert len(filtered.json()) >= 1
    assert all(item["id"] == appointment_id or item["status"] == "scheduled" for item in filtered.json())

    paginated = client.get(f"/api/v1/appointments?status=scheduled&skip=0&limit=1")
    assert paginated.status_code == 200
    assert len(paginated.json()) == 1
