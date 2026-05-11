"""WhatsApp alerting for consultation notifications."""

import httpx

from src.config import logger

WHATSAPP_SERVICE_URL = "http://10.0.0.44:8710"


async def send_whatsapp_alert(
    phone_number: str,
    animal_name: str,
    owner_name: str,
) -> bool:
    """Send WhatsApp alert notification for new consultation.

    Formats the phone number (0xxx -> 33xxx) and sends concise alert.

    Args:
        phone_number: Phone number (French format: 0607695021)
        animal_name: Name of the animal
        owner_name: Name of the owner

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Convert French format 0xxxxxxxxx to international 33xxxxxxxxx
        formatted_phone = phone_number.lstrip("0")
        if not formatted_phone.startswith("33"):
            formatted_phone = f"33{formatted_phone}"

        # Build message
        message = (
            f"🔔 *Nouvelle consultation*\n\n"
            f"Animal: {animal_name}\n"
            f"Propriétaire: {owner_name}\n\n"
            f"Dashboard: http://10.0.0.44:8092"
        )

        # Send via WhatsApp service
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/send",
                json={"to": formatted_phone, "message": message},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"WhatsApp alert sent to {formatted_phone} (MessageID: {data.get('messageId')})")
                    return True

            logger.warning(
                f"Failed to send WhatsApp alert to {formatted_phone}: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"Error sending WhatsApp alert: {e}")
        return False
