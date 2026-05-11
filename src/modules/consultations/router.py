"""Consultation request routes - SIMPLIFIED (IMAP-based)."""

import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from src.config import logger
from src.core.database import (
    delete_consultation,
    get_consultation,
    list_consultations,
)
from src.core.imap_monitor import delete_imap_email
from src.modules.consultations.integration import (
    add_animal_to_existing_client,
    create_new_client_and_animal,
    integrate_with_erp,
)
from src.modules.consultations.search import search_animals_in_erp
from src.modules.consultations.security import generate_file_token

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.get("")
async def list_consultations_endpoint(
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """List all consultations with optional filtering.

    Args:
        status: Filter by status (unmatched, matched, integrated, rejected)
        limit: Number of results to return
        offset: Number of results to skip

    Returns:
        List of consultations
    """
    try:
        consultations = await list_consultations(status=status, limit=limit, offset=offset)

        # Parse data_json for each consultation
        for consultation in consultations:
            if "data_json" in consultation:
                try:
                    consultation["data"] = json.loads(consultation["data_json"])
                except (json.JSONDecodeError, ValueError):
                    pass

        return {
            "count": len(consultations),
            "limit": limit,
            "offset": offset,
            "status_filter": status,
            "consultations": consultations,
        }
    except Exception as e:
        logger.error(f"Error listing consultations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_animals(
    q: Annotated[str, Query(description="Search query (animal/owner name)")] = "",
) -> dict:
    """Direct search in ERP.

    Args:
        q: Search query

    Returns:
        List of matching animals
    """
    try:
        if not q:
            return {"matches": []}

        matches = await search_animals_in_erp(q)

        return {
            "query": q,
            "count": len(matches),
            "matches": [
                {
                    "erp_animal_id": m.erp_animal_id,
                    "animal_name": m.animal_name,
                    "race": m.race,
                    "owner": m.owner_name,
                    "species": m.species,
                }
                for m in matches
            ],
        }

    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{uuid}/file-token")
async def get_file_token(
    uuid: str,
    filename: Annotated[str, Query(description="Filename to generate token for")] = "",
) -> dict:
    """Generate HMAC token for secure file download.

    Args:
        uuid: Consultation UUID
        filename: Filename to tokenize

    Returns:
        Dict with token for use in download URL
    """
    try:
        if not filename:
            raise HTTPException(status_code=400, detail="filename parameter required")

        # Generate token for the file
        token = await generate_file_token(f"{uuid}/{filename}")

        return {
            "uuid": uuid,
            "filename": filename,
            "token": token,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating file token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{consultation_id}/create-patient-check")
async def get_create_patient_check(consultation_id: int) -> dict:
    """Check for similar clients/animals before creating a new patient.

    Returns pre-filled form data from consultation and lists of similar
    clients/animals found in ERP as homonyme warnings.

    Args:
        consultation_id: Consultation ID

    Returns:
        prefill dict + similar_clients list + similar_animals list
    """
    try:
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        data = json.loads(consultation.get("data_json", "{}"))

        # Build pre-fill from consultation data
        prefill = {
            "owner_nom": data.get("owner_nom", ""),
            "owner_prenom": data.get("owner_prenom", ""),
            "owner_email": data.get("owner_email", ""),
            "owner_telephone": data.get("owner_telephone", ""),
            "owner_address": data.get("owner_address", ""),
            "animal_nom": data.get("animal_nom", ""),
            "animal_espece": data.get("animal_espece", ""),
            "animal_race": data.get("animal_race", ""),
            "animal_sexe": data.get("animal_sexe", ""),
        }

        # Search ERP for similar clients by owner name
        similar_clients: list[dict] = []
        owner_nom = prefill["owner_nom"]
        if owner_nom:
            matches = await search_animals_in_erp(owner_nom)
            # Filter to keep only matches where owner_name contains the search term
            # and deduplicate by owner_id
            seen_owner_ids: set[int] = set()
            search_lower = owner_nom.lower()
            for m in matches:
                # Check if owner name contains search term (case-insensitive)
                if m.owner_name and search_lower in m.owner_name.lower():
                    if m.owner_id and m.owner_id not in seen_owner_ids:
                        seen_owner_ids.add(m.owner_id)
                        similar_clients.append(
                            {
                                "erp_id": m.owner_id,
                                "nom": m.owner_name,
                            }
                        )

        # Search ERP for similar animals by animal name
        similar_animals: list[dict] = []
        animal_nom = prefill["animal_nom"]
        if animal_nom:
            animal_matches = await search_animals_in_erp(animal_nom)
            # Filter to keep only matches where animal_name contains the search term
            search_lower = animal_nom.lower()
            for m in animal_matches:
                # Check if animal name contains search term (case-insensitive)
                if m.animal_name and search_lower in m.animal_name.lower():
                    similar_animals.append(
                        {
                            "erp_animal_id": m.erp_animal_id,
                            "animal_name": m.animal_name,
                            "species": m.species,
                            "owner": m.owner_name,
                            "owner_id": m.owner_id,
                        }
                    )

        return {
            "consultation_id": consultation_id,
            "prefill": prefill,
            "similar_clients": similar_clients,
            "similar_animals": similar_animals,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create-patient-check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{consultation_id}")
async def get_consultation_detail(consultation_id: int) -> dict:
    """Get consultation request details.

    Args:
        consultation_id: ID of consultation to retrieve

    Returns:
        Consultation details
    """
    try:
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Parse data_json
        if "data_json" in consultation:
            try:
                consultation["data"] = json.loads(consultation["data_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return consultation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving consultation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{consultation_id}")
async def delete_consultation_endpoint(consultation_id: int) -> dict:
    """Delete a consultation (mark as deleted and remove from IMAP).

    Args:
        consultation_id: ID of consultation to delete

    Returns:
        Status confirmation
    """
    try:
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        if consultation.get("status") == "deleted":
            raise HTTPException(status_code=400, detail="Consultation already deleted")

        # Mark as deleted in database
        await delete_consultation(consultation_id)

        # Delete from IMAP if UID is available
        imap_uid = consultation.get("imap_uid")
        if imap_uid:
            success = await delete_imap_email(imap_uid)
            if not success:
                logger.warning(f"Failed to delete IMAP email {imap_uid}, but consultation marked deleted")

        logger.info(f"Consultation {consultation_id} deleted successfully")
        return {
            "status": "deleted",
            "id": consultation_id,
            "message": "Consultation deleted and IMAP email removed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting consultation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{consultation_id}/search")
async def search_animal_matches(
    consultation_id: int,
    search_query: Annotated[str, Query()] = "",
) -> dict:
    """Propose animal matches from ERP for a consultation.

    Searches ERP for matching animals based on consultation data.

    Args:
        consultation_id: Consultation ID
        search_query: Override search query (optional)

    Returns:
        List of suggested matches with erp_animal_id
    """
    try:
        # Get consultation
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Parse consultation data
        data = json.loads(consultation.get("data_json", "{}"))

        # Build search query
        if not search_query:
            animal_name = data.get("animal_name", "")
            owner_name = data.get("owner_name", "")
            search_query = f"{animal_name} {owner_name}".strip()

        if not search_query:
            return {"consultation_id": consultation_id, "suggestions": []}

        logger.info(f"Searching ERP for: {search_query}")

        # Search in ERP
        matches = await search_animals_in_erp(search_query)

        return {
            "consultation_id": consultation_id,
            "search_query": search_query,
            "email_data": {
                "animal_name": data.get("animal_name"),
                "owner_name": data.get("owner_name"),
                "motif": data.get("motif"),
            },
            "suggestions": [
                {
                    "erp_animal_id": m.erp_animal_id,
                    "animal_name": m.animal_name,
                    "race": m.race,
                    "owner": m.owner_name,
                    "species": m.species,
                    "last_visit": m.last_visit,
                    "weight": m.weight,
                }
                for m in matches
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{consultation_id}/integrate")
async def integrate_consultation(
    consultation_id: int,
    erp_animal_id: int | None = Query(None),
    erp_client_id: int | None = Query(None),
    create_new_client: bool = Query(False),
    owner_nom: str | None = Query(None),
    owner_prenom: str | None = Query(None),
    owner_email: str | None = Query(None),
    owner_telephone: str | None = Query(None),
    animal_nom: str | None = Query(None),
    animal_espece: str | None = Query(None),
    animal_race: str | None = Query(None),
) -> dict:
    """Integrate consultation into VetoPartner ERP.

    Three modes:
    - erp_animal_id: link to existing animal
    - erp_client_id: add new animal to existing client
    - create_new_client=true: create new client + animal

    Args:
        consultation_id: Consultation ID to integrate
        erp_animal_id: Existing animal ID in ERP
        erp_client_id: Existing client ID to add new animal to
        create_new_client: Create new client + animal
        owner_nom/prenom/email/telephone: Override form values for client creation
        animal_nom/espece/race: Override form values for animal creation

    Returns:
        Integration result with erp_consult_id
    """
    try:
        # Get consultation
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Parse consultation data (use form overrides if provided)
        data = json.loads(consultation.get("data_json", "{}"))
        effective_animal_nom = animal_nom or data.get("animal_nom", "Unknown")
        effective_animal_espece = animal_espece or data.get("animal_espece", "")
        effective_animal_race = animal_race or data.get("animal_race", "")

        logger.info(f"Integrating consultation {consultation_id}...")

        if create_new_client:
            # Create new client and animal using form values or consultation data
            logger.info("Creating new client and animal...")
            effective_owner_nom = owner_nom or data.get("owner_nom", "Unknown")
            effective_owner_prenom = owner_prenom or data.get("owner_prenom", "")
            effective_owner_email = owner_email or data.get("owner_email", "")
            effective_owner_tel = owner_telephone or data.get("owner_telephone", "")

            create_result = await create_new_client_and_animal(
                owner_name=f"{effective_owner_nom} {effective_owner_prenom}".strip(),
                owner_email=effective_owner_email,
                owner_phone=effective_owner_tel,
                animal_name=effective_animal_nom,
                species=effective_animal_espece,
                race=effective_animal_race,
            )

            if not create_result.get("success"):
                raise HTTPException(status_code=400, detail="Failed to create client/animal")

            erp_animal_id = create_result["idanimal"]

        elif erp_client_id:
            # Add new animal to existing client
            logger.info(f"Adding new animal to existing client {erp_client_id}...")
            add_result = await add_animal_to_existing_client(
                erp_client_id=erp_client_id,
                animal_name=effective_animal_nom,
                species=effective_animal_espece,
                race=effective_animal_race,
            )

            if not add_result.get("success"):
                raise HTTPException(status_code=400, detail="Failed to create animal for existing client")

            erp_animal_id = add_result["idanimal"]

        elif not erp_animal_id:
            raise HTTPException(status_code=400, detail="erp_animal_id, erp_client_id or create_new_client required")

        # Now integrate with animal
        result = await integrate_with_erp(
            consultation_id=consultation_id,
            erp_animal_id=erp_animal_id,
            motif=data.get("motif", ""),
            specialite=data.get("specialite", "general"),
            urgence=data.get("urgence", False),
        )

        if result.get("success"):
            logger.info(f"Consultation {consultation_id} integrated successfully")
            return {
                "success": True,
                "id": consultation_id,
                "erp_consult_id": result.get("erp_consult_id"),
                "message": "Integrated into VetoPartner",
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Integration failed"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error integrating consultation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
