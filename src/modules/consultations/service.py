"""Business logic for consultation processing and ERP integration."""

import json
from datetime import UTC, datetime

import httpx

from src.config import FILES_DIR, logger
from src.core.alerting import send_email
from src.core.database import (
    create_consultation,
    update_consultation_erp_ids,
    update_consultation_status,
    update_files_local,
)
from src.core.models import ConsultationRequest
from src.modules.consultations.files import (
    download_and_store_files,
    scan_file_with_clamd,
)
from src.modules.consultations.notifications import build_notification_email


async def integrate_consultation_with_erp(
    consultation_id: int,
    consultation_data: dict,
) -> dict:
    """Integrate consultation into VetoPartner ERP.

    Orchestrates: search/create client, search/create animal,
    create consultation, upload files.

    Args:
        consultation_id: Database consultation ID
        consultation_data: Parsed consultation request data

    Returns:
        Dict with erp_client_id, erp_animal_id, erp_consult_id, success
    """
    from src.modules.consultations.erp import (
        create_animal,
        create_client,
        create_consultation,
        search_animals,
        search_clients,
        upload_document,
    )

    try:
        logger.info(f"Starting ERP integration for consultation {consultation_id}")

        # Parse consultation data
        owner = consultation_data.get("owner", {})
        animal = consultation_data.get("animal", {})

        # Step 1: Search for existing client
        client_search = f"{owner.get('nom', '')} {owner.get('prenom', '')}".strip()
        logger.info(f"Searching for client: {client_search}")

        existing_clients = await search_clients(client_search)
        erp_client_id: int | None = None

        if existing_clients:
            erp_client_id = existing_clients[0].id
            logger.info(f"Found existing client: {erp_client_id}")
        else:
            # Step 2: Create new client
            logger.info(f"Creating new client: {client_search}")
            erp_client_id = await create_client(
                nom=owner.get("nom", "Unknown"),
                prenom=owner.get("prenom"),
                email=owner.get("email"),
                telephone=owner.get("telephone"),
            )
            logger.info(f"Created client: {erp_client_id}")

        # Step 3: Search for existing animal
        animal_name = animal.get("nom", "Unknown")
        logger.info(f"Searching for animal: {animal_name} (client {erp_client_id})")

        existing_animals = await search_animals(erp_client_id, animal_name)
        erp_animal_id: int | None = None

        if existing_animals:
            erp_animal_id = existing_animals[0].id
            logger.info(f"Found existing animal: {erp_animal_id}")
        else:
            # Step 4: Create new animal
            logger.info(f"Creating new animal: {animal_name}")
            erp_animal_id = await create_animal(
                client_id=erp_client_id,
                nom=animal_name,
                espece=animal.get("espece", "Unknown"),
                race=animal.get("race"),
                sexe=animal.get("sexe"),
                date_naissance=animal.get("date_naissance"),
                puce=animal.get("puce"),
                poids=animal.get("poids"),
            )
            logger.info(f"Created animal: {erp_animal_id}")

        # Step 5: Create consultation in ERP
        logger.info(f"Creating consultation in ERP (animal {erp_animal_id})")
        erp_consult_id = await create_consultation(
            animal_id=erp_animal_id,
            motif=consultation_data.get("motif", ""),
            specialite=consultation_data.get("specialite"),
            urgence=consultation_data.get("urgence", False),
            traitements_en_cours=consultation_data.get("traitements_en_cours"),
        )
        logger.info(f"Created consultation: {erp_consult_id}")

        # Step 6: Upload documents (best-effort)
        files_local = consultation_data.get("files_local", [])
        if files_local:
            logger.info(f"Uploading {len(files_local)} documents")
            for local_path in files_local:
                try:
                    file_full_path = FILES_DIR / local_path
                    filename = local_path.split("/")[-1]
                    await upload_document(erp_animal_id, str(file_full_path), filename)
                    logger.info(f"Uploaded: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to upload {local_path}: {e}")

        # Step 7: Update database
        timestamp = datetime.now(UTC).isoformat()
        await update_consultation_erp_ids(
            consultation_id,
            erp_client_id,
            erp_animal_id,
            erp_consult_id,
            timestamp,
        )
        logger.info(f"Consultation {consultation_id} integrated successfully")

        return {
            "success": True,
            "erp_client_id": erp_client_id,
            "erp_animal_id": erp_animal_id,
            "erp_consult_id": erp_consult_id,
        }

    except Exception as e:
        logger.error(f"Error integrating consultation {consultation_id}: {e}")
        await update_consultation_status(consultation_id, "rejected")
        raise


async def process_consultation_submission(
    request: ConsultationRequest,
    consultation_id: int,
) -> None:
    """Process consultation after initial storage.

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


async def pull_consultations_from_wordpress(uuid: str | None = None) -> list[str]:
    """Pull consultations from WordPress.

    Called either:
    - Periodically to get all unprocessed consultations
    - From IMAP monitor when webhook email received

    Args:
        uuid: Optional UUID to fetch single consultation

    Returns:
        List of processed consultation UUIDs
    """
    try:
        wp_url = "https://verso-vet.com"

        if uuid:
            logger.info(f"Fetching consultation {uuid} from WordPress webhook...")
        else:
            logger.info("Pulling unprocessed consultations from WordPress...")

        endpoint = f"{wp_url}/wp-json/verso/v1/consultations/unprocessed"

        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, timeout=30.0)

        if response.status_code != 200:
            logger.warning(f"WordPress returned {response.status_code}")
            return []

        consultations = response.json()

        # If UUID specified, filter to just that consultation
        if uuid:
            consultations = [c for c in consultations if c.get("uuid") == uuid]
            if not consultations:
                logger.warning(f"Consultation {uuid} not found in WordPress")
                return []

        if not consultations:
            logger.debug("No unprocessed consultations found")
            return []

        logger.info(f"Found {len(consultations)} consultation(s) to process")

        processed_uuids = []

        for consultation in consultations:
            try:
                cons_uuid = consultation.get("uuid")
                data = consultation.get("data", {})

                if not cons_uuid or not data:
                    logger.warning(f"Invalid consultation data: {consultation}")
                    continue

                # Create ConsultationRequest object
                request_data = ConsultationRequest(**data)

                # Store in database
                timestamp = datetime.now(UTC).isoformat()
                data_json = request_data.model_dump_json()

                consultation_id = await create_consultation(
                    uuid=cons_uuid,
                    submitted_at=timestamp,
                    submitter_type=request_data.submitter_type,
                    data_json=data_json,
                )

                logger.info(f"Stored consultation {cons_uuid} (ID: {consultation_id})")

                # Process asynchronously
                await process_consultation_submission(
                    request_data,
                    consultation_id,
                )

                # Mark as processed in WordPress
                mark_url = f"{wp_url}/wp-json/verso/v1/consultations/{cons_uuid}/processed"
                async with httpx.AsyncClient() as client:
                    await client.post(mark_url, timeout=30.0)

                processed_uuids.append(cons_uuid)
                logger.info(f"Marked {cons_uuid} as processed in WordPress")

            except Exception as e:
                logger.error(f"Error processing consultation from WP: {e}")
                continue

        logger.info(f"Successfully processed {len(processed_uuids)} consultation(s)")
        return processed_uuids

    except Exception as e:
        logger.error(f"Error pulling consultations from WordPress: {e}")
        return []


async def download_and_scan_files(
    uuid: str,
    file_urls: list[str],
) -> list[str]:
    """Download files from WordPress and scan with ClamAV.

    Infected files are deleted and not included in the result.

    Args:
        uuid: Consultation UUID
        file_urls: List of file URLs from WordPress

    Returns:
        List of local file paths for clean files
    """
    # Download files first
    local_paths = await download_and_store_files(uuid, file_urls)

    if not local_paths:
        return []

    # Scan each file with ClamAV
    clean_paths = []

    for local_path in local_paths:
        try:
            file_full_path = FILES_DIR / local_path
            is_clean, threat = await scan_file_with_clamd(file_full_path)

            if is_clean:
                clean_paths.append(local_path)
            else:
                # Delete infected file
                try:
                    file_full_path.unlink()
                    logger.warning(f"Deleted infected file: {local_path} (threat: {threat})")
                except Exception as e:
                    logger.error(f"Failed to delete infected file {local_path}: {e}")

        except Exception as e:
            logger.error(f"Error scanning file {local_path}: {e}")

    return clean_paths


async def store_consultation_from_json(data: dict) -> bool:
    """Store a consultation received via email JSON attachment.

    Downloads and scans files from fichiers URLs.

    Args:
        data: Parsed consultation dict from email attachment

    Returns:
        True if stored successfully
    """
    try:
        uuid = data.get("uuid", "")
        if not uuid:
            logger.error("No UUID in consultation JSON")
            return False

        submitted_at = data.get("submitted_at", datetime.now(UTC).isoformat())
        data_json = json.dumps(data, ensure_ascii=False)

        consultation_id = await create_consultation(
            uuid=uuid,
            submitted_at=submitted_at,
            submitter_type="owner",
            data_json=data_json,
        )
        await update_consultation_status(consultation_id, "received")
        logger.info(f"Stored consultation {uuid} (ID: {consultation_id}) from email")

        # Download and scan files from fichiers URLs
        fichiers = data.get("fichiers", [])
        if fichiers:
            logger.info(f"Downloading and scanning {len(fichiers)} file(s)...")
            clean_files = await download_and_scan_files(uuid, fichiers)

            if clean_files:
                await update_files_local(consultation_id, clean_files)
                logger.info(f"Stored {len(clean_files)} clean file(s) locally")
            elif fichiers:
                logger.warning(f"No clean files stored for {uuid}")

        return True

    except Exception as e:
        logger.error(f"Error storing consultation from JSON: {e}")
        return False
