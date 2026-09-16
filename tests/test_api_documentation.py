from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_metadata_and_documented_paths_are_published():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()

    assert document["info"]["title"] == "PulseTrack"
    assert document["info"]["version"] == "0.3.0"
    assert "authentication" in document["info"]["description"].lower()
    assert {tag["name"] for tag in document["tags"]} >= {
        "Health",
        "Authentication",
        "Doctors",
        "Patients",
        "Appointments",
        "Prescriptions",
        "Integration",
    }
    assert "/api/v1/auth/token" in document["paths"]
    assert "/api/v1/doctors" in document["paths"]
    assert "/api/v1/appointments/{appointment_id}" in document["paths"]
    assert "/api/v1/prescriptions" in document["paths"]
    assert document["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert document["paths"]["/api/v1/doctors"]["get"]["security"] == [{"BearerAuth": []}]
    assert "security" not in document["paths"]["/api/v1/health"]["get"]


def test_documentation_endpoints_are_public():
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200