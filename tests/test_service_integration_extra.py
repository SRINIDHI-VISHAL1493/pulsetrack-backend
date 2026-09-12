import importlib

import app.services as services


def test_external_service_settings_are_env_configurable_and_validated():
    original_url = services.EXTERNAL_SERVICE_BASE_URL
    original_timeout = services.EXTERNAL_SERVICE_TIMEOUT_SECONDS
    try:
        services.EXTERNAL_SERVICE_BASE_URL = "https://example.test/api"
        services.EXTERNAL_SERVICE_TIMEOUT_SECONDS = 7.5
        services.ExternalServiceClient.refresh_config()
        assert services.ExternalServiceClient.BASE_URL == "https://example.test/api"
        assert services.ExternalServiceClient.TIMEOUT_SECONDS == 7.5

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"status": "ok"}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.timeout = kwargs.get("timeout")

            def get(self, url, timeout=None):
                assert timeout == 7.5
                assert url == "https://example.test/api/status"
                return FakeResponse()

            def close(self):
                return None

        original_build = services.ExternalServiceClient._build_client
        services.ExternalServiceClient._build_client = staticmethod(lambda *args, **kwargs: FakeClient(*args, **kwargs))
        try:
            assert services.fetch_external_status() == {"status": "ok"}
        finally:
            services.ExternalServiceClient._build_client = original_build
    finally:
        services.EXTERNAL_SERVICE_BASE_URL = original_url
        services.EXTERNAL_SERVICE_TIMEOUT_SECONDS = original_timeout
        services.ExternalServiceClient.BASE_URL = original_url
        services.ExternalServiceClient.TIMEOUT_SECONDS = original_timeout
