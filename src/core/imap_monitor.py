"""IMAP monitoring for consultation emails from verso-vet.com."""

import email
import json

import imapclient

from src.config import logger
from src.core.database import update_imap_uid
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
            if payload and isinstance(payload, bytes):
                try:
                    return json.loads(payload.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return None
    return None


def extract_file_attachments(msg: email.message.Message) -> list[tuple[str, bytes]]:
    """Extract all non-JSON file attachments from email message.

    These are document files sent directly by the consultation plugin,
    not JSON metadata.

    Args:
        msg: Parsed email message

    Returns:
        List of (filename, file_bytes) tuples for all document attachments
    """
    attachments = []
    for part in msg.walk():
        filename = part.get_filename() or ""
        disposition = part.get("Content-Disposition", "")

        # Skip JSON metadata and non-attachments
        if not filename or filename.endswith(".json") or "attachment" not in disposition:
            continue

        payload = part.get_payload(decode=True)
        if payload and isinstance(payload, bytes):
            attachments.append((filename, payload))
            logger.debug(f"Extracted attachment: {filename} ({len(payload)} bytes)")

    return attachments


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

        # Search for consultation emails (both read and unread)
        # Note: Check UNSEEN first, then ALL if needed for recovery
        search_criteria = [
            b"UNSEEN",
            b"SUBJECT",
            b"[Verso Vet] Demande",
        ]

        uids = imap.search(search_criteria)
        logger.info(f"Found {len(uids)} unread consultation emails")

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

                # Extract JSON metadata and file attachments
                subject = msg.get("Subject", "")
                data = extract_json_attachment(msg)

                if not data:
                    logger.warning(f"No JSON attachment in: {subject}")
                    imap.add_flags([uid], [r"\Seen"])
                    continue

                uuid = data.get("uuid", "unknown")
                logger.info(f"Processing consultation {uuid} from email")

                # Extract document attachments (sent directly by plugin)
                attachments = extract_file_attachments(msg)
                if attachments:
                    logger.info(f"Found {len(attachments)} document attachment(s)")

                # Import here to avoid circular imports
                from src.modules.consultations.service import (
                    store_consultation_from_json,
                )

                # Store consultation from JSON data + attachments
                result = await store_consultation_from_json(data, attachments)

                if result:
                    processed_uuids.append(uuid)
                    logger.info(f"Stored consultation {uuid} from email")
                    # Store IMAP UID for later deletion
                    try:
                        await update_imap_uid(uuid, uid)
                    except Exception as e:
                        logger.warning(f"Failed to store IMAP UID for {uuid}: {e}")
                else:
                    logger.warning(f"Failed to store consultation {uuid}")

                # Mark email as read
                imap.add_flags([uid], [r"\Seen"])

            except Exception as e:
                logger.error(f"Error processing email: {e}")
                continue

        imap.logout()
        logger.info(f"IMAP monitoring complete. Processed {len(processed_uuids)} consultations")
        return processed_uuids

    except Exception as e:
        logger.error(f"IMAP monitoring error: {e}")
        return []


async def delete_imap_email(imap_uid: int) -> bool:
    """Delete an email from IMAP by UID.

    Args:
        imap_uid: IMAP message UID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        credentials = await get_imap_credentials()
        if not credentials:
            logger.error("No IMAP credentials available for email deletion")
            return False

        imap = imapclient.IMAPClient(
            credentials["host"],
            port=993,
            use_uid=True,
            ssl=True,
        )
        imap.login(credentials["username"], credentials["password"])
        imap.select_folder("INBOX")
        imap.delete_messages([imap_uid])
        imap.expunge()
        imap.logout()

        logger.info(f"IMAP email {imap_uid} deleted successfully")
        return True

    except Exception as e:
        logger.error(f"Error deleting IMAP email {imap_uid}: {e}")
        return False
