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

    logger.warning(f"Auth failed for client IP {client_ip} with token '{token}'")
    return False
