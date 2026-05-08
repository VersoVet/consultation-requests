"""IMAP monitoring for consultation emails from verso-vet.com."""

import email
import json

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

        # verso_webhook_email is optional, use fallback if not found
        try:
            webhook_email = await get_secret("verso_webhook_email")
        except Exception:
            webhook_email = "consultations@verso-vet.com"

        return {
            "host": imap_host,
            "username": imap_user,
            "password": imap_pass,
            "webhook_email": webhook_email,
        }
    except Exception as e:
        logger.error(f"Error getting IMAP credentials from Vault: {e}")
        return {}


def extract_json_attachment(msg: email.message.Message) -> dict | None:
    """Extract consultation data from JSON email attachment.

    Args:
        msg: Parsed email message

    Returns:
        Parsed consultation dict, or None if not found
    """
    for part in msg.walk():
        filename = part.get_filename() or ""
        disposition = part.get("Content-Disposition", "")
        if filename.endswith(".json") and "attachment" in disposition:
            payload = part.get_payload(decode=True)
            if payload:
                try:
                    return json.loads(payload.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return None
    return None


async def monitor_imap() -> list[str]:
    """Monitor IMAP mailbox for consultation emails.

    Connects to IMAP server, retrieves unread emails with "[Verso Vet] Demande"
    subject, extracts JSON attachment, and stores consultation data.

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

        # Search for unread consultation emails
        search_criteria = [
            b"UNSEEN",
            b"SUBJECT",
            b"[Verso Vet] Demande",
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

                # Extract JSON attachment
                subject = msg.get("Subject", "")
                data = extract_json_attachment(msg)

                if not data:
                    logger.warning(f"No JSON attachment in: {subject}")
                    imap.flag([uid], [r"\Seen"])
                    continue

                uuid = data.get("uuid", "unknown")
                logger.info(f"Processing consultation {uuid} from email")

                # Import here to avoid circular imports
                from src.modules.consultations.service import (
                    store_consultation_from_json,
                )

                # Store consultation from JSON data
                result = await store_consultation_from_json(data)

                if result:
                    processed_uuids.append(uuid)
                    logger.info(f"Stored consultation {uuid} from email")
                else:
                    logger.warning(f"Failed to store consultation {uuid}")

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
