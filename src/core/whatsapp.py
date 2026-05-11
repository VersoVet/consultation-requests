"""WhatsApp alerting for consultation notifications."""

import httpx

from src.config import logger

WHATSAPP_SERVICE_URL = "http://10.0.0.44:8710"


async def get_whatsapp_config() -> dict:
    """Get WhatsApp alert configuration.

    Returns:
        Dict with enabled (bool) and phone (str) keys
    """
    from src.core.database import get_config

    enabled = await get_config("whatsapp_enabled", "false")
    phone = await get_config("whatsapp_phone", "33744938228")

    return {
        "enabled": enabled.lower() == "true",
        "phone": phone,
    }


async def send_whatsapp_alert(
    animal_name: str,
    owner_name: str,
    owner_phone: str | None = None,
) -> bool:
    """Send WhatsApp alert notification for new consultation.

    Sends alert to configured phone number with consultation details.
    Non-blocking: fails gracefully if disabled or service unavailable.

    Args:
        animal_name: Name of the animal
        owner_name: Name of the owner
        owner_phone: Owner phone (for reference in message, not alert recipient)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Get WhatsApp configuration
        config = await get_whatsapp_config()
        if not config["enabled"]:
            logger.debug("WhatsApp alerts disabled in configuration")
            return False

        phone = config["phone"]

        # Build message with owner details
        message = f"🔔 *Nouvelle consultation*\n\nAnimal: {animal_name}\nPropriétaire: {owner_name}"
        if owner_phone:
            message += f"\nTél: {owner_phone}"
        message += "\n\nDashboard: http://10.0.0.44:8092"

        # Send via WhatsApp service
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/send",
                json={"to": phone, "message": message},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"WhatsApp alert sent (MessageID: {data.get('messageId')})")
                    return True

            logger.warning(f"Failed to send WhatsApp alert: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error sending WhatsApp alert: {e}")
        return False
