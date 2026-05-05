"""Consultation request routes - SIMPLIFIED (IMAP-based)."""

import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from src.config import logger
from src.core.database import (
    get_consultation,
    list_consultations,
    update_consultation_status,
)
from src.core.models import ConsultationStatus
from src.modules.consultations.integration import (
    create_new_client_and_animal,
    integrate_with_erp,
)
from src.modules.consultations.search import search_animals_in_erp

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
    create_new_client: bool = Query(False),
) -> dict:
    """Integrate consultation into VetoPartner ERP.

    Either match with existing animal or create new client+animal.

    Args:
        consultation_id: Consultation ID to integrate
        erp_animal_id: Animal ID in ERP (if matching existing)
        create_new_client: If True, create new client+animal

    Returns:
        Integration result with erp_consult_id
    """
    try:
        # Get consultation
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Parse consultation data
        data = json.loads(consultation.get("data_json", "{}"))

        logger.info(f"Integrating consultation {consultation_id}...")

        if create_new_client:
            # Create new client and animal
            logger.info("Creating new client and animal...")

            create_result = await create_new_client_and_animal(
                owner_name=data.get("owner_name", "Unknown"),
                owner_email=data.get("owner_email", ""),
                owner_phone=data.get("owner_phone", ""),
                animal_name=data.get("animal_name", "Unknown"),
                species=data.get("animal_species", "Unknown"),
                race=data.get("animal_race", ""),
            )

            if not create_result.get("success"):
                raise HTTPException(status_code=400, detail="Failed to create client/animal")

            erp_animal_id = create_result["idanimal"]

        elif not erp_animal_id:
            raise HTTPException(status_code=400, detail="Either erp_animal_id or create_new_client required")

        # Now integrate with animal
        result = await integrate_with_erp(
            consultation_id=consultation_id,
            erp_animal_id=erp_animal_id,
            motif=data.get("motif", ""),
            specialite=data.get("specialite", "general"),
            urgence=data.get("urgence", False),
            attachments=[],  # TODO: Get from consultation files
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
