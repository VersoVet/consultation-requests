"""Email alerting via onyx-mailbox."""

import httpx

from src.config import MAILBOX_URL, logger


async def send_email(
    to: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
) -> bool:
    """Send email via onyx-mailbox.

    Args:
        to: List of recipient emails
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body

    Returns:
        True if sent successfully
    """
    try:
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
        }
        if html_body:
            payload["html_body"] = html_body

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{MAILBOX_URL}/api/send",
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"Email sent to {', '.join(to)}: {subject}")
            return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


async def send_notification(
    subject: str,
    message: str,
    level: str = "info",
) -> bool:
    """Send internal notification via onyx-mailbox.

    Args:
        subject: Notification subject
        message: Notification message
        level: Level (info, warning, error)

    Returns:
        True if sent successfully
    """
    try:
        payload = {
            "subject": f"[Consultation] {subject}",
            "message": message,
            "level": level,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{MAILBOX_URL}/api/notify",
                json=payload,
            )
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False
