from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

EXTERNAL_SERVICE_BASE_URL = os.getenv("PULSETRACK_EXTERNAL_SERVICE_URL", "https://example.com/api")
EXTERNAL_SERVICE_TIMEOUT_SECONDS = float(
    os.getenv("PULSETRACK_EXTERNAL_SERVICE_TIMEOUT_SECONDS", "5.0")
)


class ExternalServiceTimeoutError(RuntimeError):
    pass


class ExternalServiceError(RuntimeError):
    pass


class ExternalServiceClient:
    BASE_URL = EXTERNAL_SERVICE_BASE_URL
    TIMEOUT_SECONDS = EXTERNAL_SERVICE_TIMEOUT_SECONDS

    @classmethod
    def refresh_config(cls) -> None:
        global EXTERNAL_SERVICE_BASE_URL, EXTERNAL_SERVICE_TIMEOUT_SECONDS
        cls.BASE_URL = EXTERNAL_SERVICE_BASE_URL
        cls.TIMEOUT_SECONDS = EXTERNAL_SERVICE_TIMEOUT_SECONDS

    @staticmethod
    def _build_client(*args, **kwargs):
        return httpx.Client(*args, **kwargs)

    @staticmethod
    def _resolve_response(client: Any, url: str, timeout_seconds: float) -> Any:
        result = client.get(url, timeout=timeout_seconds)
        if asyncio.iscoroutine(result):
            return asyncio.run(result)
        return result

    @classmethod
    def get_status(cls) -> dict:
        cls.refresh_config()
        client = None
        try:
            client = cls._build_client(timeout=cls.TIMEOUT_SECONDS)
            response = cls._resolve_response(client, f"{cls.BASE_URL}/status", cls.TIMEOUT_SECONDS)
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ExternalServiceError("External service returned an invalid payload")
            return payload
        except httpx.TimeoutException as exc:
            raise ExternalServiceTimeoutError("External service timed out") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError("External service request failed") from exc
        except ExternalServiceError:
            raise
        except (TypeError, ValueError) as exc:
            raise ExternalServiceError("External service returned an invalid response") from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()


def fetch_external_status() -> dict:
    return ExternalServiceClient.get_status()
