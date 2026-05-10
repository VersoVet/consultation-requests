"""ERP integration for consultations."""

import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx

from src.config import logger
from src.core.database import (
    get_consultation,
    update_consultation_status,
)
from src.core.vault import get_secret
from src.modules.consultations.files import delete_local_files


def _format_consultation_text(data: dict) -> str:
    """Format consultation data into concise text for ERP synthese field.

    Only includes motif description, date, origin, and referring vet.
    Patient/owner info already in dossier animal.

    Args:
        data: Consultation data dictionary

    Returns:
        Formatted text for ERP consultation
    """
    from datetime import datetime

    lines = []

    # Motif/Description
    motif = data.get("motif", "Consultation")
    lines.append(f"Demande: {motif}")
    lines.append("")

    # Date of request
    submitted_at = data.get("submitted_at")
    if submitted_at:
        try:
            dt = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
            lines.append(f"Date demande: {dt.strftime('%d/%m/%Y à %H:%M')}")
        except (ValueError, AttributeError):
            lines.append(f"Date demande: {submitted_at}")
    lines.append("")

    # Origin
    lines.append("Origine: verso-vet.com (formulaire en ligne)")
    lines.append("")

    # Referring vet
    if data.get("vet_nom"):
        vet_name = f"{data.get('vet_prenom', '')} {data.get('vet_nom')}".strip()
        lines.append("Vétérinaire référent:")
        lines.append(f"  {vet_name}")
        if data.get("vet_clinique"):
            lines.append(f"  Clinique: {data.get('vet_clinique')}")

    return "\n".join(lines)


async def integrate_with_erp(
    consultation_id: int,
    erp_animal_id: int,
    motif: str | None = None,
    specialite: str | None = None,
    urgence: bool = False,
    attachments: list[str] | None = None,
    erp_url: str = "http://10.0.0.44:8101",
) -> dict:
    """Integrate consultation into ERP.

    Creates consultation in ERP with formatted text summary.

    Args:
        consultation_id: Consultation ID in local DB
        erp_animal_id: Animal ID in ERP
        motif: Consultation motif (optional, from data)
        specialite: Speciality (unused, kept for compatibility)
        urgence: Is urgent (unused, kept for compatibility)
        attachments: List of local file paths
        erp_url: ERP connector URL

    Returns:
        Integration result with erp_consult_id
    """
    try:
        logger.info(f"Integrating consultation {consultation_id} into ERP...")

        # Get full consultation data
        consultation = await get_consultation(consultation_id)
        if not consultation:
            return {"success": False, "error": "Consultation not found"}

        # Parse consultation data
        try:
            data = json.loads(consultation.get("data_json", "{}"))
        except (json.JSONDecodeError, ValueError):
            data = {}

        # Format comprehensive summary text
        synthese = _format_consultation_text(data)
        logger.info(f"Formatted synthese text ({len(synthese)} chars)")

        # Create consultation in ERP with correct field names
        async with httpx.AsyncClient() as client:
            consult_response = await client.post(
                f"{erp_url}/consultations",
                json={
                    "animal_id": erp_animal_id,
                    "synthese": synthese,
                    "motif": "Demande de consultation",
                },
                timeout=30.0,
            )

            if consult_response.status_code != 201:
                logger.error(
                    f"Failed to create consultation in ERP: {consult_response.status_code} - {consult_response.text}"
                )
                return {"success": False, "error": "ERP creation failed"}

            consult_data = consult_response.json()
            erp_consult_id = consult_data.get("id")  # ERP returns "id", not "idconsult"

            logger.info(f"Created consultation {erp_consult_id} in ERP")

            # Upload documents from files_local
            files_local_json = consultation.get("files_local", "[]") or "[]"
            try:
                files_local = json.loads(files_local_json)
            except (json.JSONDecodeError, ValueError):
                files_local = []

            if files_local:
                logger.info(f"Uploading {len(files_local)} document(s) from consultation...")

                # Get ERP upload secret for HMAC signing
                try:
                    erp_upload_secret = await get_secret("erp_upload_secret")
                except Exception as e:
                    logger.warning(f"Could not get erp_upload_secret: {e}, skipping file uploads")
                    erp_upload_secret = None

                if erp_upload_secret:
                    from src.config import FILES_DIR

                    for local_path in files_local:
                        try:
                            file_full_path = str(FILES_DIR / local_path)
                            success = await _upload_document_to_erp(
                                client,
                                erp_url,
                                erp_animal_id,
                                file_full_path,
                                erp_upload_secret,
                            )

                            # Delete local file after successful upload
                            if success:
                                try:
                                    Path(file_full_path).unlink()
                                    logger.info(f"Deleted local copy: {local_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete local file {local_path}: {e}")

                        except Exception as e:
                            logger.error(f"Error processing file {local_path}: {e}")

                    # Delete from WordPress after all uploads
                    uuid = consultation.get("uuid", "")
                    if uuid:
                        await _delete_wordpress_files(uuid)

                    # Clean up local directory
                    uuid = consultation.get("uuid", "")
                    if uuid:
                        delete_local_files(uuid)

        # Update local DB
        await update_consultation_status(consultation_id, "integrated")

        doc_count = len(attachments) if attachments else 0
        return {
            "success": True,
            "erp_consult_id": erp_consult_id,
            "documents_uploaded": doc_count,
        }

    except Exception as e:
        logger.error(f"Error integrating consultation: {e}")
        await update_consultation_status(consultation_id, "rejected")
        return {"success": False, "error": str(e)}


async def _upload_document_to_erp(
    client: httpx.AsyncClient,
    erp_url: str,
    erp_animal_id: int,
    file_path: str,
    erp_upload_secret: str,
) -> bool:
    """Upload a single document to ERP with HMAC signature.

    Args:
        client: HTTP client
        erp_url: ERP base URL
        erp_animal_id: ERP animal ID
        file_path: Local file path to upload
        erp_upload_secret: HMAC secret for signing

    Returns:
        True if successful, False otherwise
    """
    try:
        file_obj = Path(file_path)
        filename = file_obj.name

        # Prepare HMAC signature
        # Message format: {animal_id}:{filename}:{doc_type}:{timestamp}
        timestamp = int(time.time())
        doc_type = "document"

        message = f"{erp_animal_id}:{filename}:{doc_type}:{timestamp}"
        signature = hmac.new(
            erp_upload_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Upload file
        with open(file_path, "rb") as f:
            response = await client.post(
                f"{erp_url}/animals/{erp_animal_id}/documents/upload",
                data={
                    "doc_type": doc_type,
                    "timestamp": str(timestamp),
                    "signature": signature,
                },
                files={"file": (filename, f)},
                timeout=60.0,
            )

        if response.status_code == 201:
            logger.info(f"Uploaded document to ERP: {filename}")
            return True
        else:
            logger.error(
                f"Failed to upload {filename} to ERP: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"Error uploading document {file_path}: {e}")
        return False


async def _delete_wordpress_files(uuid: str) -> bool:
    """Delete consultation files from WordPress after ERP integration.

    Calls DELETE /wp-json/verso/v1/consultations/{uuid}/files endpoint.
    This endpoint is implemented in the verso-consultation-plugin.

    Args:
        uuid: Consultation UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        # Note: Plugin endpoint for file deletion will be implemented separately
        # For now, this is a stub that logs a warning
        logger.warning(
            f"WordPress file deletion not yet implemented - files should be manually "
            f"deleted from verso-vet.com/wp-content/uploads/consultations/{uuid}/"
        )
        return False

    except Exception as e:
        logger.error(f"Error deleting WordPress files for {uuid}: {e}")
        return False


async def create_new_client_and_animal(
    owner_name: str,
    owner_email: str,
    owner_phone: str,
    animal_name: str,
    species: str,
    race: str,
    erp_url: str = "http://10.0.0.44:8101",
) -> dict:
    """Create new client and animal in ERP.

    Args:
        owner_name: Client name (nom)
        owner_email: Client email
        owner_phone: Client phone
        animal_name: Animal name
        species: Animal species
        race: Animal race/breed
        erp_url: ERP connector URL

    Returns:
        Created IDs: {"idclient": ..., "idanimal": ...}
    """
    try:
        async with httpx.AsyncClient() as client:
            # Create client
            client_response = await client.post(
                f"{erp_url}/clients",
                json={
                    "nom": owner_name,
                    "email": owner_email,
                    "telephone": owner_phone,
                },
                timeout=30.0,
            )

            if client_response.status_code != 201:
                logger.error(f"Failed to create client: {client_response.status_code}")
                return {"success": False}

            client_data = client_response.json()
            idclient = client_data.get("id") or client_data.get("idclient")

            logger.info(f"Created client {idclient}")

            # Create animal
            animal_response = await client.post(
                f"{erp_url}/animals",
                json={
                    "idclient": idclient,
                    "nom": animal_name,
                    "espece": species,
                    "race": race,
                },
                timeout=30.0,
            )

            if animal_response.status_code != 201:
                logger.error(f"Failed to create animal: {animal_response.status_code}")
                return {"success": False, "idclient": idclient}

            animal_data = animal_response.json()
            idanimal = animal_data.get("id") or animal_data.get("idanimal")

            logger.info(f"Created animal {idanimal}")

            return {
                "success": True,
                "idclient": idclient,
                "idanimal": idanimal,
            }

    except Exception as e:
        logger.error(f"Error creating client/animal: {e}")
        return {"success": False, "error": str(e)}


async def add_animal_to_existing_client(
    erp_client_id: int,
    animal_name: str,
    species: str,
    race: str,
    erp_url: str = "http://10.0.0.44:8101",
) -> dict:
    """Add a new animal to an existing client in ERP.

    Args:
        erp_client_id: Existing client ID in ERP
        animal_name: Animal name
        species: Animal species (espece)
        race: Animal breed
        erp_url: ERP connector URL

    Returns:
        Dict with success and idanimal
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{erp_url}/animals",
                json={
                    "idclient": erp_client_id,
                    "nom": animal_name,
                    "espece": species,
                    "race": race,
                },
                timeout=30.0,
            )

            if response.status_code != 201:
                logger.error(f"Failed to create animal for client {erp_client_id}: {response.status_code} {response.text}")
                return {"success": False}

            data = response.json()
            idanimal = data.get("id") or data.get("idanimal")
            logger.info(f"Created animal {idanimal} for existing client {erp_client_id}")

            return {"success": True, "idanimal": idanimal}

    except Exception as e:
        logger.error(f"Error adding animal to client {erp_client_id}: {e}")
        return {"success": False, "error": str(e)}
