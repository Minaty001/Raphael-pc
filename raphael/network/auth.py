"""
Authentication Helper for Raphael AI Assistant.
"""

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("network.auth")

def verify_token(token: str, client_ip: str) -> bool:
    config = get_config()
    if not config.websocket.auth_required:
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            return True

    if token == config.websocket.api_token:
        return True

    # SECURITY: never log the token itself. Log only metadata.
    token_present = bool(token)
    logger.warning(
        f"Auth failed for client IP {client_ip} "
        f"(token_present={token_present})"
    )
    return False
