from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field


AUTH_SECRET_KEY = os.getenv("PULSETRACK_AUTH_SECRET_KEY", "local-development-secret-change-me")
AUTH_USERNAME = os.getenv("PULSETRACK_AUTH_USERNAME", "demo")
AUTH_PASSWORD = os.getenv("PULSETRACK_AUTH_PASSWORD", "pulsetrack-dev-password")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("PULSETRACK_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthenticatedUser(BaseModel):
    username: str
    role: str


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(username: str = AUTH_USERNAME, role: str = "user") -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        AUTH_SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def authenticate_user(username: str, password: str) -> bool:
    return hmac.compare_digest(username, AUTH_USERNAME) and hmac.compare_digest(
        password, AUTH_PASSWORD
    )


def decode_access_token(token: str) -> AuthenticatedUser:
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        expected_signature = hmac.new(
            AUTH_SECRET_KEY.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_decode(encoded_signature), expected_signature):
            raise ValueError("invalid signature")

        payload: dict[str, Any] = json.loads(_decode(encoded_payload))
        if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("role"), str):
            raise ValueError("invalid claims")
        if int(payload["exp"]) <= int(time.time()):
            raise ValueError("expired token")
        return AuthenticatedUser(username=payload["sub"], role=payload["role"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def authenticate_request(authorization: str | None) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(authorization[7:].strip())