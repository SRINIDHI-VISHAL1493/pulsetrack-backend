import httpx

from app import services
from app.main import app


client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(app)


def test_service_integration_route_uses_mockable_layer(monkeypatch):
    def fake_status():
        return {"status": "ok", "provider": "mocked", "service": "pulsecare"}

    monkeypatch.setattr("app.main.fetch_external_status", fake_status)

    response = client.get("/api/v1/service-status")
    assert response.status_code == 200
    assert response.json()["external_service"]["provider"] == "mocked"


def test_service_client_handles_timeouts_and_http_failures():
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, timeout=None):
            raise httpx.TimeoutException("timed out")

    original = services.ExternalServiceClient._build_client
    try:
        services.ExternalServiceClient._build_client = staticmethod(lambda *args, **kwargs: FakeAsyncClient())
        try:
            services.fetch_external_status()
        except services.ExternalServiceTimeoutError:
            pass
        else:
            raise AssertionError("Expected timeout error to be raised")
    finally:
        services.ExternalServiceClient._build_client = original

    class FakeResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError("bad response", request=None, response=None)

        def json(self):
            return {"status": "error"}

    class FakeHTTPClient:
        async def get(self, url, timeout=None):
            return FakeResponse()

    original_client = services.ExternalServiceClient._build_client
    try:
        services.ExternalServiceClient._build_client = staticmethod(lambda *args, **kwargs: FakeHTTPClient())
        try:
            services.fetch_external_status()
        except services.ExternalServiceError:
            pass
        else:
            raise AssertionError("Expected external service error to be raised")
    finally:
        services.ExternalServiceClient._build_client = original_client
