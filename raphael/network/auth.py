"""
Authentication Helper for Raphael AI Assistant.

Provides both the low-level ``verify_token`` check and a FastAPI dependency
(``require_api_auth``) that can be applied per-route or as a router dependency
to gate REST endpoints behind the same auth token used for WebSocket.
"""

from fastapi import Request, HTTPException
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("network.auth")


def verify_token(token: str, client_ip: str) -> bool:
    """Check a token string against the configured api_token.

    When ``auth_required`` is False, loopback connections are admitted without
    a token. This is the legacy localhost-only dev mode.
    """
    config = get_config()
    if not config.websocket.auth_required:
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            return True

    if token and token == config.websocket.api_token:
        return True

    # SECURITY: never log the token itself. Log only metadata.
    token_present = bool(token)
    logger.warning(
        f"Auth failed for client IP {client_ip} "
        f"(token_present={token_present})"
    )
    return False


async def require_api_auth(request: Request) -> None:
    """FastAPI dependency that enforces token auth on REST endpoints.

    The token may be supplied as:
      * ``Authorization: Bearer <token>`` header (preferred)
      * ``?token=<token>`` query parameter (compat with WS)

    Loopback connections (127.0.0.1 / ::1) are still admitted without a token
    when ``auth_required`` is False in config (backward-compatible dev mode).

    Raises HTTPException(401) on auth failure.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Try Authorization header first, then query param
    token = ""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.query_params.get("token", "")

    if not verify_token(token, client_ip):
        raise HTTPException(status_code=401, detail="Unauthorized")
