"""Keycloak JWT authentication middleware.

Validates Bearer tokens against Keycloak's JWKS endpoint. Bypasses auth
on the ADK Dev UI, health endpoints, and static assets so the browser
chat interface works without tokens while API calls are secured.

Set AUTH_DISABLED=true to bypass validation entirely (local dev / tests).
"""

from __future__ import annotations

import logging
import os
import time

import httpx
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.model_config import load_config

logger = logging.getLogger(__name__)

_BYPASS_PREFIXES = (
    "/dev-ui",
    "/healthz",
    "/readyz",
    "/list-apps",
    "/.well-known",
    "/static",
    "/apps/",
    "/debug/",
    "/openapi.json",
    "/docs",
    "/favicon",
    "/builder",
    "/run_sse",
    "/run",
)

_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0
_JWKS_TTL = 300


def _get_auth_config() -> dict:
    cfg = load_config().get("auth", {})
    return {
        "keycloak_url": cfg.get("keycloak_url", ""),
        "realm": cfg.get("realm", "kagenti"),
        "client_id": cfg.get("client_id", "kagenti"),
        "disabled": cfg.get("disabled", os.environ.get("AUTH_DISABLED", "false").lower() == "true"),
    }


def _fetch_jwks(keycloak_url: str, realm: str) -> dict:
    url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"
    resp = httpx.get(url, timeout=5, verify=False)
    resp.raise_for_status()
    return resp.json()


def _get_jwks(keycloak_url: str, realm: str, force: bool = False) -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.time()
    if _jwks_cache is not None and not force and (now - _jwks_fetched_at) <= _JWKS_TTL:
        return _jwks_cache
    _jwks_cache = _fetch_jwks(keycloak_url, realm)
    _jwks_fetched_at = now
    return _jwks_cache


def _validate_token(token: str, auth_cfg: dict) -> dict:
    """Validate JWT and return decoded payload."""
    keycloak_url = auth_cfg["keycloak_url"]
    realm = auth_cfg["realm"]

    jwks = _get_jwks(keycloak_url, realm)
    jwk_set = jwt.PyJWKSet.from_dict(jwks)
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    signing_key = None
    for key in jwk_set.keys:
        if key.key_id == kid:
            signing_key = key
            break

    if signing_key is None:
        jwks = _get_jwks(keycloak_url, realm, force=True)
        jwk_set = jwt.PyJWKSet.from_dict(jwks)
        for key in jwk_set.keys:
            if key.key_id == kid:
                signing_key = key
                break

    if signing_key is None:
        raise jwt.InvalidTokenError(f"No matching key for kid={kid}")

    issuer = f"{keycloak_url}/realms/{realm}"
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=issuer,
        options={"verify_aud": False},
    )
    return payload


class KeycloakJWTMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that validates Keycloak JWTs on protected routes."""

    async def dispatch(self, request: Request, call_next):
        auth_cfg = _get_auth_config()

        if auth_cfg["disabled"]:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in _BYPASS_PREFIXES):
            return await call_next(request)

        if request.method == "GET" and path == "/":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header. Use: Bearer <token>"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[7:]
        try:
            payload = _validate_token(token, auth_cfg)
            request.state.user_id = payload.get("sub", "unknown")
            request.state.username = payload.get("preferred_username", "unknown")
            request.state.roles = payload.get("realm_access", {}).get("roles", [])
            logger.info("Authenticated: user=%s roles=%s", request.state.username, request.state.roles)
        except jwt.ExpiredSignatureError:
            return JSONResponse({"error": "Token expired"}, status_code=401)
        except jwt.InvalidTokenError as exc:
            return JSONResponse({"error": f"Invalid token: {exc}"}, status_code=401)
        except Exception as exc:
            logger.error("Auth error: %s", exc)
            return JSONResponse({"error": "Authentication service error"}, status_code=503)

        return await call_next(request)
