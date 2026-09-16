import asyncio
import pytest
from fastapi.testclient import TestClient

from app import services
from app.auth import create_access_token
from app.database import session_scope
from app.main import app


client = TestClient(app)
authenticated_client = TestClient(
    app, headers={"Authorization": f"Bearer {create_access_token()}"}
)


def test_request_id_is_preserved_on_success_and_auth_failure():
    request_id = "reliability-check-123"

    health_response = client.get("/api/v1/health", headers={"X-Request-ID": request_id})
    assert health_response.status_code == 200
    assert health_response.headers["X-Request-ID"] == request_id

    auth_response = client.get("/api/v1/doctors", headers={"X-Request-ID": request_id})
    assert auth_response.status_code == 401
    assert auth_response.headers["X-Request-ID"] == request_id


def test_validation_error_contains_request_id_and_field_details():
    response = authenticated_client.post(
        "/api/v1/doctors",
        headers={"X-Request-ID": "validation-check"},
        json={"first_name": "A"},
    )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "validation-check"
    assert response.json()["detail"] == "Request validation failed"
    assert response.json()["errors"]


def test_invalid_appointment_input_is_rejected_without_persistence():
    before = authenticated_client.get("/api/v1/appointments").json()

    response = authenticated_client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "appointment_date": "2026-09-20",
            "appointment_time": "25:00",
            "reason": "Invalid time should fail",
            "status": "scheduled",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Request validation failed"
    assert authenticated_client.get("/api/v1/appointments").json() == before


def test_external_service_rejects_non_object_payload_and_closes_client(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return ["unexpected", "payload"]

    class FakeClient:
        closed = False

        def get(self, url, timeout=None):
            return FakeResponse()

        def close(self):
            self.closed = True

    fake_client = FakeClient()
    monkeypatch.setattr(services.ExternalServiceClient, "_build_client", staticmethod(lambda **_: fake_client))

    with pytest.raises(services.ExternalServiceError, match="invalid payload"):
        services.fetch_external_status()

    assert fake_client.closed is True


def test_service_status_maps_timeout_to_degraded_response(monkeypatch):
    def fail_with_timeout():
        raise services.ExternalServiceTimeoutError("upstream timed out")

    monkeypatch.setattr("app.main.fetch_external_status", fail_with_timeout)

    response = client.get(
        "/api/v1/service-status",
        headers={"X-Request-ID": "service-timeout-check"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "service-timeout-check"
    assert response.json() == {
        "status": "degraded",
        "external_service": {
            "status": "timeout",
            "details": {"error": "Upstream request timed out"},
        },
    }


def test_service_status_maps_upstream_failure_to_degraded_response(monkeypatch):
    def fail_with_error():
        raise services.ExternalServiceError("upstream failed")

    monkeypatch.setattr("app.main.fetch_external_status", fail_with_error)

    response = client.get("/api/v1/service-status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "external_service": {
            "status": "error",
            "details": {"error": "Upstream request failed"},
        },
    }


def test_session_scope_rolls_back_when_operation_fails(monkeypatch):
    class FakeSession:
        committed = False
        rolled_back = False

        async def commit(self):
            self.committed = True

        async def rollback(self):
            self.rolled_back = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    fake_session = FakeSession()

    class FakeSessionFactory:
        def __call__(self):
            return fake_session

    monkeypatch.setattr("app.database.AsyncSessionLocal", FakeSessionFactory())

    async def failing_operation():
        with pytest.raises(RuntimeError, match="write failed"):
            async with session_scope():
                raise RuntimeError("write failed")

    asyncio.run(failing_operation())

    assert fake_session.committed is False
    assert fake_session.rolled_back is True


def test_failed_prescription_write_does_not_leave_partial_record():
    before = authenticated_client.get("/api/v1/prescriptions").json()

    response = authenticated_client.post(
        "/api/v1/prescriptions",
        json={
            "appointment_id": 1,
            "doctor_id": 2,
            "patient_id": 1,
            "diagnosis": "Mismatched relationship",
            "medications": [
                {
                    "name": "Example",
                    "dosage": "10mg",
                    "frequency": "Once daily",
                    "duration_days": 7,
                }
            ],
            "instructions": "This write must be rejected without persistence.",
        },
    )

    assert response.status_code == 400
    assert "must match" in response.json()["detail"]
    assert authenticated_client.get("/api/v1/prescriptions").json() == before