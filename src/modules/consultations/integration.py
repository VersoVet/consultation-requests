"""ERP integration for consultations."""

from datetime import UTC, datetime

import httpx

from src.config import logger
from src.core.database import update_consultation_status


async def integrate_with_erp(
    consultation_id: int,
    erp_animal_id: int,
    motif: str,
    specialite: str,
    urgence: bool,
    attachments: list[str],
    erp_url: str = "http://10.0.0.44:8101",
) -> dict:
    """Integrate consultation into ERP.

    Creates consultation in ERP and uploads documents.

    Args:
        consultation_id: Consultation ID in local DB
        erp_animal_id: Animal ID in ERP
        motif: Consultation motif
        specialite: Speciality
        urgence: Is urgent
        attachments: List of local file paths
        erp_url: ERP connector URL

    Returns:
        Integration result with erp_consult_id
    """
    try:
        logger.info(f"Integrating consultation {consultation_id} into ERP...")

        # Create consultation in ERP
        async with httpx.AsyncClient() as client:
            consult_response = await client.post(
                f"{erp_url}/consultations",
                json={
                    "idanimal": erp_animal_id,
                    "synthese": motif,
                    "specialite": specialite,
                    "urgent": urgence,
                    "date_consult": datetime.now(UTC).isoformat(),
                },
                timeout=30.0,
            )

        if consult_response.status_code != 201:
            logger.error(f"Failed to create consultation in ERP: {consult_response.status_code}")
            return {"success": False, "error": "ERP creation failed"}

        consult_data = consult_response.json()
        erp_consult_id = consult_data.get("idconsult")

        logger.info(f"Created consultation {erp_consult_id} in ERP")

        # Upload documents
        if attachments:
            logger.info(f"Uploading {len(attachments)} documents...")
            for attachment in attachments:
                try:
                    # Upload document to ERP
                    with open(attachment, "rb") as f:
                        files = {"file": f}
                        doc_response = await client.post(
                            f"{erp_url}/animals/{erp_animal_id}/documents/upload",
                            files=files,
                            timeout=30.0,
                        )

                    if doc_response.status_code == 201:
                        logger.info(f"Uploaded: {attachment.split('/')[-1]}")
                    else:
                        logger.warning(f"Failed to upload {attachment}: {doc_response.status_code}")

                except Exception as e:
                    logger.error(f"Error uploading {attachment}: {e}")

        # Update local DB
        await update_consultation_status(consultation_id, "integrated")

        return {
            "success": True,
            "erp_consult_id": erp_consult_id,
            "documents_uploaded": len(attachments),
        }

    except Exception as e:
        logger.error(f"Error integrating consultation: {e}")
        await update_consultation_status(consultation_id, "rejected")
        return {"success": False, "error": str(e)}


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
            idclient = client_data.get("idclient")

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
            idanimal = animal_data.get("idanimal")

            logger.info(f"Created animal {idanimal}")

            return {
                "success": True,
                "idclient": idclient,
                "idanimal": idanimal,
            }

    except Exception as e:
        logger.error(f"Error creating client/animal: {e}")
        return {"success": False, "error": str(e)}
