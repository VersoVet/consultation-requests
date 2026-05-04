"""Consultation request routes."""

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from src.config import logger
from src.core.database import (
    create_consultation,
    get_consultation,
    list_consultations,
    update_consultation_status,
)
from src.core.models import ConsultationRequest, ConsultationResponse, ConsultationStatus

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.post("/submit", status_code=201)
async def submit_consultation(request: ConsultationRequest) -> dict:
    """Receive consultation request from WordPress (webhook).

    Args:
        request: ConsultationRequest with all data

    Returns:
        Response with created consultation ID
    """
    try:
        # Validate HMAC in production (simplified for now)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Store in database
        data_json = request.model_dump_json()
        consultation_id = await create_consultation(
            uuid=request.uuid,
            submitted_at=timestamp,
            submitter_type=request.submitter_type,
            data_json=data_json,
        )

        logger.info(
            f"Consultation received: id={consultation_id}, uuid={request.uuid}, "
            f"animal={request.animal.nom}, submitter={request.submitter_type}"
        )

        return {
            "success": True,
            "id": consultation_id,
            "uuid": request.uuid,
            "status": "pending",
        }

    except Exception as e:
        logger.error(f"Error submitting consultation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_consultations_endpoint(
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """List all consultations with optional filtering.

    Args:
        status: Filter by status (pending, received, integrated, rejected)
        limit: Number of results to return
        offset: Number of results to skip

    Returns:
        List of consultations
    """
    try:
        consultations = await list_consultations(
            status=status, limit=limit, offset=offset
        )
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
            except:
                pass

        return consultation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving consultation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{consultation_id}/status")
async def update_status(
    consultation_id: int,
    status: str,
) -> dict:
    """Update consultation status.

    Args:
        consultation_id: ID of consultation
        status: New status (pending, received, integrated, rejected)

    Returns:
        Updated consultation
    """
    try:
        # Validate status
        valid_statuses = [s.value for s in ConsultationStatus]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )

        await update_consultation_status(consultation_id, status)
        consultation = await get_consultation(consultation_id)

        logger.info(f"Consultation {consultation_id} status updated to {status}")
        return consultation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating consultation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{consultation_id}/integrate")
async def integrate_consultation(
    consultation_id: int,
    erp_client_id: int | None = None,
    erp_animal_id: int | None = None,
) -> dict:
    """Integrate consultation into VetoPartner ERP.

    This is a placeholder endpoint. In production, it will:
    1. Search for or create client in VetoPartner
    2. Search for or create animal in VetoPartner
    3. Create consultation in VetoPartner
    4. Upload documents

    Args:
        consultation_id: ID of consultation to integrate
        erp_client_id: Optional existing client ID in VetoPartner
        erp_animal_id: Optional existing animal ID in VetoPartner

    Returns:
        Integration result
    """
    try:
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Placeholder - full implementation in service.py
        logger.info(
            f"Integration initiated for consultation {consultation_id}, "
            f"erp_client_id={erp_client_id}, erp_animal_id={erp_animal_id}"
        )

        return {
            "success": True,
            "id": consultation_id,
            "message": "Integration scheduled",
            "erp_client_id": erp_client_id,
            "erp_animal_id": erp_animal_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error integrating consultation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
