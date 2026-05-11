"""Configuration management routes."""

from fastapi import APIRouter, HTTPException

from src.config import logger
from src.core.database import set_config
from src.core.whatsapp import get_whatsapp_config

router = APIRouter(prefix="/consultations/config", tags=["config"])


@router.get("/whatsapp")
async def get_whatsapp_alert_config() -> dict:
    """Get WhatsApp alert configuration.

    Returns:
        Configuration with enabled status and phone number
    """
    try:
        config = await get_whatsapp_config()
        return {"success": True, "config": config}
    except Exception as e:
        logger.error(f"Error getting WhatsApp config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whatsapp")
async def update_whatsapp_alert_config(enabled: bool = False, phone: str = "") -> dict:
    """Update WhatsApp alert configuration.

    Args:
        enabled: Whether to enable WhatsApp alerts
        phone: Phone number for alerts (international or French format)

    Returns:
        Updated configuration
    """
    try:
        if phone:
            # Convert French format (07xxx) to international (33xxx)
            phone = phone.lstrip("0")
            if not phone.startswith("33"):
                phone = f"33{phone}"

        await set_config("whatsapp_enabled", "true" if enabled else "false")
        if phone:
            await set_config("whatsapp_phone", phone)

        config = await get_whatsapp_config()
        logger.info(f"WhatsApp config updated: enabled={enabled}, phone={phone}")
        return {"success": True, "config": config}

    except Exception as e:
        logger.error(f"Error updating WhatsApp config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
