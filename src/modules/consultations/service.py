"""Business logic for consultation requests."""

import hashlib
import hmac
from datetime import UTC, datetime
from pathlib import Path

import httpx

from src.config import DATABASE_PATH, logger
from src.core.alerting import send_email
from src.core.database import (
    update_consultation_status,
    update_files_local,
)
from src.core.models import ConsultationRequest
from src.core.vault import get_secret

# Local file storage
FILES_DIR = DATABASE_PATH.parent / "consultation-requests" / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)


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


async def download_and_store_files(
    uuid: str,
    file_urls: list[str],
) -> list[str]:
    """Download files from WordPress and store locally.

    Args:
        uuid: Consultation UUID
        file_urls: List of file URLs from WordPress

    Returns:
        List of local file paths

    Raises:
        Exception: If download fails
    """
    local_paths: list[str] = []
    uuid_dir = FILES_DIR / uuid
    uuid_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for url in file_urls:
            try:
                # Download file
                response = await client.get(url)
                response.raise_for_status()

                # Extract filename from URL
                filename = url.split("/")[-1]
                if not filename or "." not in filename:
                    filename = f"file_{len(local_paths)}.bin"

                # Save locally
                local_path = uuid_dir / filename
                local_path.write_bytes(response.content)

                local_paths.append(f"{uuid}/{filename}")
                logger.info(f"Downloaded file: {filename} ({len(response.content)} bytes)")

            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")
                # Continue with other files

    if not local_paths:
        logger.warning(f"No files downloaded for consultation {uuid}")

    return local_paths


def build_notification_email(
    request: ConsultationRequest,
    file_urls: list[str],
    consultation_id: int,
) -> tuple[str, str]:
    """Build HTML email notification.

    Args:
        request: ConsultationRequest data
        file_urls: List of local file paths
        consultation_id: Database ID for dashboard link

    Returns:
        Tuple of (plain_text_body, html_body)
    """
    # Plain text
    text_body = f"""
Nouvelle demande de consultation reçue

ID: {consultation_id}
UUID: {request.uuid}
Type: {request.submitter_type.upper()}

--- Animal ---
Nom: {request.animal.nom}
Espèce: {request.animal.espece}
Race: {request.animal.race or "N/A"}

--- Propriétaire ---
Nom: {request.owner.nom} {request.owner.prenom}
Email: {request.owner.email or "N/A"}
Tél: {request.owner.telephone or "N/A"}

--- Motif ---
Spécialité: {request.specialite}
Urgence: {"Oui" if request.urgence else "Non"}
Motif: {request.motif}

Accédez au dashboard: http://10.0.0.44:8092/dashboard
"""

    # HTML body
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2196F3; color: white; padding: 15px; border-radius: 5px; }}
        .section {{ margin: 15px 0; padding: 10px; border-left: 3px solid #2196F3; }}
        .field {{ margin: 8px 0; }}
        .label {{ font-weight: bold; color: #555; }}
        .urgent {{ color: #d32f2f; font-weight: bold; }}
        .button {{ display: inline-block; padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 3px; }}
        .files {{ background: #f5f5f5; padding: 10px; border-radius: 3px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🏥 Nouvelle Demande de Consultation</h2>
        </div>

        <div class="section">
            <div class="field"><span class="label">ID:</span> {consultation_id}</div>
            <div class="field"><span class="label">UUID:</span> {request.uuid}</div>
            <div class="field"><span class="label">Type:</span> {request.submitter_type.upper()}</div>
        </div>

        <div class="section">
            <h3>🐾 Patient</h3>
            <div class="field"><span class="label">Nom:</span> {request.animal.nom}</div>
            <div class="field"><span class="label">Espèce:</span> {request.animal.espece}</div>
            <div class="field"><span class="label">Race:</span> {request.animal.race or "Non spécifiée"}</div>
        </div>

        <div class="section">
            <h3>👤 Propriétaire</h3>
            <div class="field"><span class="label">Nom:</span> {request.owner.nom} {request.owner.prenom}</div>
            <div class="field"><span class="label">Email:</span> {request.owner.email or "N/A"}</div>
            <div class="field"><span class="label">Tél:</span> {request.owner.telephone or "N/A"}</div>
        </div>

        <div class="section">
            <h3>📋 Motif</h3>
            <div class="field"><span class="label">Spécialité:</span> {request.specialite}</div>
            <div class="field"><span class="label">Urgence:</span> <span class="{"urgent" if request.urgence else ""}">{
        "🔴 OUI" if request.urgence else "⚪ Non"
    }</span></div>
            <div class="field"><span class="label">Motif:</span><br>{request.motif}</div>
        </div>

        {
        f'''<div class="files">
            <h3>📎 Fichiers ({len(file_urls)})</h3>
            <ul>{"".join(f"<li>{f.split('/')[-1]}</li>" for f in file_urls)}</ul>
        </div>'''
        if file_urls
        else ""
    }

        <div class="section" style="text-align: center; margin-top: 30px;">
            <a href="http://10.0.0.44:8092/dashboard" class="button">Accéder au Dashboard</a>
        </div>

        <hr>
        <p style="font-size: 12px; color: #999;">
            Consultation #{consultation_id} • {datetime.now(UTC).isoformat()}
        </p>
    </div>
</body>
</html>
"""

    return text_body, html_body


def get_file_path(uuid: str, filename: str) -> Path | None:
    """Get local file path for a consultation file.

    Args:
        uuid: Consultation UUID
        filename: File name

    Returns:
        Path to file if it exists, None otherwise
    """
    file_path = FILES_DIR / uuid / filename

    # Security: ensure the path is within FILES_DIR (prevent directory traversal)
    try:
        file_path.resolve().relative_to(FILES_DIR.resolve())
    except ValueError:
        logger.error(f"Attempted directory traversal: {file_path}")
        return None

    if file_path.exists() and file_path.is_file():
        return file_path

    return None


async def process_consultation_submission(
    request: ConsultationRequest,
    consultation_id: int,
) -> None:
    """Process consultation after initial storage.

    This is called asynchronously after the webhook response.
    Downloads files, sends email, updates status.

    Args:
        request: ConsultationRequest data
        consultation_id: Database ID
    """
    try:
        logger.info(f"Processing consultation {consultation_id}...")

        # Download files
        local_files = await download_and_store_files(
            request.uuid,
            request.fichiers,
        )

        # Store file paths in DB
        if local_files:
            await update_files_local(consultation_id, local_files)

        # Build email
        text_body, html_body = build_notification_email(
            request,
            local_files,
            consultation_id,
        )

        # Send email
        email_sent = await send_email(
            to=["consultations@verso-vet.com"],
            subject=f"[Consultation] {request.animal.nom} - {request.specialite}",
            body=text_body,
            html_body=html_body,
        )

        # Update status
        await update_consultation_status(consultation_id, "received")

        if email_sent:
            logger.info(f"Consultation {consultation_id} processed successfully")
        else:
            logger.warning(f"Consultation {consultation_id} stored but email failed")

    except Exception as e:
        logger.error(f"Error processing consultation {consultation_id}: {e}")
        await update_consultation_status(consultation_id, "rejected")
