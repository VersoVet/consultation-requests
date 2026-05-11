"""WhatsApp alerting for consultation notifications."""

import httpx

from src.config import logger

WHATSAPP_SERVICE_URL = "http://10.0.0.44:8710"
# Verso alert phone number (07 44 93 82 28 → 33744938228)
VERSO_ALERT_PHONE = "33744938228"


async def send_whatsapp_alert(
    animal_name: str,
    owner_name: str,
    owner_phone: str | None = None,
) -> bool:
    """Send WhatsApp alert notification for new consultation to Verso.

    Sends alert to Verso's dedicated phone number with consultation details.

    Args:
        animal_name: Name of the animal
        owner_name: Name of the owner
        owner_phone: Owner phone (for reference in message, not alert recipient)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Build message with owner details
        message = f"🔔 *Nouvelle consultation*\n\nAnimal: {animal_name}\nPropriétaire: {owner_name}"
        if owner_phone:
            message += f"\nTél: {owner_phone}"
        message += "\n\nDashboard: http://10.0.0.44:8092"

        # Send via WhatsApp service to Verso
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/send",
                json={"to": VERSO_ALERT_PHONE, "message": message},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"WhatsApp alert sent to Verso (MessageID: {data.get('messageId')})")
                    return True

            logger.warning(f"Failed to send WhatsApp alert to Verso: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error sending WhatsApp alert: {e}")
        return False
