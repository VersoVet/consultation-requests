"""IMAP monitoring for webhook emails from verso-vet.com."""

import email
import re

import imapclient

from src.config import logger
from src.core.vault import get_secret


async def get_imap_credentials() -> dict:
    """Get IMAP credentials from Vault.

    Returns:
        Dict with host, username, password, webhook_email
    """
    try:
        imap_host = await get_secret("imap_host")
        imap_user = await get_secret("imap_username")
        imap_pass = await get_secret("imap_password")
        webhook_email = await get_secret("verso_webhook_email")

        return {
            "host": imap_host,
            "username": imap_user,
            "password": imap_pass,
            "webhook_email": webhook_email or "consultations+webhook@verso-vet.com",
        }
    except Exception as e:
        logger.error(f"Error getting IMAP credentials from Vault: {e}")
        return {}


async def extract_uuid_from_email(email_subject: str) -> str:
    """Extract UUID from email subject.

    Expected format: "VERSO_WEBHOOK UUID:xxxxx TYPE:xxx ANIMAL:xxx"

    Args:
        email_subject: Email subject line

    Returns:
        UUID if found, empty string otherwise
    """
    match = re.search(r"UUID:([a-zA-Z0-9\-]+)", email_subject)
    if match:
        return match.group(1)
    return ""


async def monitor_imap() -> list[str]:
    """Monitor IMAP mailbox for webhook emails.

    Connects to IMAP server, retrieves unread emails with VERSO_WEBHOOK
    subject, extracts UUIDs, and triggers consultation processing.

    Returns:
        List of processed UUIDs
    """
    try:
        credentials = await get_imap_credentials()
        if not credentials:
            logger.error("No IMAP credentials configured")
            return []

        logger.info("Connecting to IMAP server...")

        # Connect to IMAP server (OVH uses port 993 with SSL/TLS)
        imap = imapclient.IMAPClient(
            credentials["host"],
            port=993,
            use_uid=True,
            ssl=True,
        )
        imap.login(credentials["username"], credentials["password"])
        imap.select_folder("INBOX")

        logger.info("Connected to IMAP")

        # Search for unread VERSO_WEBHOOK emails
        search_criteria = [
            b"UNSEEN",
            b"SUBJECT",
            b"VERSO_WEBHOOK",
        ]

        uids = imap.search(search_criteria)
        logger.info(f"Found {len(uids)} unread webhook emails")

        if not uids:
            imap.logout()
            return []

        processed_uuids = []

        # Fetch and process each email
        for uid in uids:
            try:
                email_data = imap.fetch([uid], ["RFC822"])
                if uid not in email_data:
                    continue

                msg_bytes = email_data[uid][b"RFC822"]
                msg = email.message_from_bytes(msg_bytes)

                # Extract UUID from subject
                subject = msg.get("Subject", "")
                uuid = await extract_uuid_from_email(subject)

                if not uuid:
                    logger.warning(f"Could not extract UUID from subject: {subject}")
                    imap.flag([uid], [r"\Seen"])
                    continue

                logger.info(f"Processing webhook for UUID: {uuid}")

                # Import here to avoid circular imports
                from src.modules.consultations.service import (
                    pull_consultations_from_wordpress,
                )

                # Fetch and process consultation from WordPress
                result = await pull_consultations_from_wordpress(uuid)

                if result:
                    processed_uuids.append(uuid)
                    logger.info(f"Successfully processed consultation {uuid}")
                else:
                    logger.warning(f"Failed to process consultation {uuid}")

                # Mark email as read
                imap.flag([uid], [r"\Seen"])

            except Exception as e:
                logger.error(f"Error processing email: {e}")
                continue

        imap.logout()
        logger.info(f"IMAP monitoring complete. Processed {len(processed_uuids)} consultations")
        return processed_uuids

    except Exception as e:
        logger.error(f"IMAP monitoring error: {e}")
        return []
