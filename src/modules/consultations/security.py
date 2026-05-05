"""Security utilities: HMAC validation and token generation."""

import hashlib
import hmac

from src.config import logger
from src.core.vault import get_secret


async def validate_hmac_signature(
    request_body: str,
    signature_header: str,
) -> bool:
    """Validate HMAC-SHA256 signature from WordPress.

    Args:
        request_body: Raw request body (JSON string)
        signature_header: X-Verso-Signature header value

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        webhook_secret = await get_secret("consultation_webhook_secret")
        expected_signature = hmac.new(
            webhook_secret.encode(),
            request_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature_header, expected_signature)
    except Exception as e:
        logger.warning(f"HMAC validation error: {e}")
        return False


async def validate_file_token(filename: str, provided_token: str) -> bool:
    """Validate HMAC token for file download.

    Args:
        filename: Filename to validate
        provided_token: Token from user

    Returns:
        True if token is valid
    """
    try:
        expected_token = await generate_file_token(filename)
        return hmac.compare_digest(provided_token, expected_token)
    except Exception as e:
        logger.warning(f"Token validation error: {e}")
        return False


async def generate_file_token(filename: str, ttl_days: int = 7) -> str:
    """Generate HMAC token for file download.

    Args:
        filename: Filename to tokenize
        ttl_days: Token validity in days

    Returns:
        HMAC token (can be used in URL)
    """
    try:
        file_secret = await get_secret("consultation_file_secret")
        token = hmac.new(
            file_secret.encode(),
            f"{filename}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return token
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        return ""
