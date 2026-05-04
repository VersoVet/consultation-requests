"""Vault client for consultation-requests skill."""

import json
import time

import httpx

from src.config import VAULT_TOKEN, VAULT_URL, logger

# Cache pour les secrets (TTL 5 minutes)
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300


async def get_secret(key: str, ttl: float = _CACHE_TTL) -> str:
    """Get a secret from the Vault.

    Args:
        key: Secret key name
        ttl: Cache TTL in seconds

    Returns:
        Secret value as string

    Raises:
        Exception: If secret not found or Vault error
    """
    now = time.time()
    if key in _cache:
        value, ts = _cache[key]
        if now - ts < ttl:
            return value

    headers = {"X-Vault-Token": VAULT_TOKEN} if VAULT_TOKEN else {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{VAULT_URL}/{key}", headers=headers)
            resp.raise_for_status()
            value = resp.json()["value"]
            _cache[key] = (value, now)
            return value
        except httpx.HTTPError as e:
            logger.error(f"Vault error for key {key}: {e}")
            raise Exception(f"Failed to retrieve secret {key}") from e


async def get_secret_json(key: str) -> dict:
    """Get a secret from Vault and parse as JSON.

    Args:
        key: Secret key name

    Returns:
        Parsed JSON as dict
    """
    raw = await get_secret(key)
    try:
        return json.loads(raw) if raw.startswith("{") else {"value": raw}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse secret {key} as JSON: {e}")
        raise Exception(f"Secret {key} is not valid JSON") from e
