from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.main import app


client = TestClient(app)


def test_health_is_public_but_domain_routes_require_authentication():
    assert client.get("/api/v1/health").status_code == 200

    response = client.get("/api/v1/doctors")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_bad_credentials_and_returns_expiring_bearer_token():
    invalid_response = client.post(
        "/api/v1/auth/token",
        json={"username": "demo", "password": "incorrect"},
    )
    assert invalid_response.status_code == 401

    response = client.post(
        "/api/v1/auth/token",
        json={"username": "demo", "password": "pulsetrack-dev-password"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert client.get(
        "/api/v1/doctors",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    ).status_code == 200


def test_tampered_token_is_rejected():
    response = client.post(
        "/api/v1/auth/token",
        json={"username": "demo", "password": "pulsetrack-dev-password"},
    )
    token = response.json()["access_token"]

    protected_response = client.get(
        "/api/v1/doctors",
        headers={"Authorization": f"Bearer {token}tampered"},
    )

    assert protected_response.status_code == 401


def test_cross_user_record_access_is_forbidden_and_lists_are_scoped():
    owner_client = TestClient(
        app, headers={"Authorization": f"Bearer {create_access_token('demo')}"}
    )
    other_user_client = TestClient(
        app, headers={"Authorization": f"Bearer {create_access_token('other-user')}"}
    )

    assert other_user_client.get("/api/v1/doctors").json() == []
    response = other_user_client.get("/api/v1/doctors/1")

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not own this doctor"

    update_response = other_user_client.patch(
        "/api/v1/appointments/1/status",
        json={"status": "cancelled"},
    )
    assert update_response.status_code == 403
    assert owner_client.get("/api/v1/appointments/1").json()["status"] == "confirmed"