"""Consultation request routes."""

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from src.config import logger
from src.core.database import (
    create_consultation,
    get_consultation,
    list_consultations,
    update_consultation_status,
)
from src.core.models import ConsultationRequest, ConsultationStatus
from src.modules.consultations.service import (
    integrate_consultation_with_erp,
    process_consultation_submission,
    validate_hmac_signature,
)

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.post("/submit", status_code=201)
async def submit_consultation(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """Receive consultation request from WordPress (webhook).

    Validates HMAC signature, stores in DB, processes files/email asynchronously.

    Args:
        request: FastAPI Request object (for raw body)
        background_tasks: FastAPI background tasks

    Returns:
        Response with created consultation ID
    """
    try:
        # Get raw body for HMAC validation
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")

        # Validate HMAC signature
        signature_header = request.headers.get("X-Verso-Signature", "")
        if not signature_header:
            logger.warning("Missing X-Verso-Signature header")
            raise HTTPException(status_code=401, detail="Missing signature")

        is_valid = await validate_hmac_signature(body_str, signature_header)
        if not is_valid:
            client_host = request.client.host if request.client else "unknown"
            logger.warning(f"Invalid HMAC signature from {client_host}")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse JSON
        consultation_data = json.loads(body_str)
        consultation_request = ConsultationRequest(**consultation_data)

        # Store in database
        timestamp = datetime.now(UTC).isoformat()
        data_json = consultation_request.model_dump_json()
        consultation_id = await create_consultation(
            uuid=consultation_request.uuid,
            submitted_at=timestamp,
            submitter_type=consultation_request.submitter_type,
            data_json=data_json,
        )

        logger.info(
            f"Consultation received: id={consultation_id}, uuid={consultation_request.uuid}, "
            f"animal={consultation_request.animal.nom}, submitter={consultation_request.submitter_type}"
        )

        # Schedule async processing (files + email)
        background_tasks.add_task(
            process_consultation_submission,
            consultation_request,
            consultation_id,
        )

        return {
            "success": True,
            "id": consultation_id,
            "uuid": consultation_request.uuid,
            "status": "pending",
        }

    except HTTPException:
        raise
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
        consultations = await list_consultations(status=status, limit=limit, offset=offset)
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
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

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
    background_tasks: BackgroundTasks,
) -> dict:
    """Integrate consultation into VetoPartner ERP.

    Orchestrates:
    1. Search for or create client in VetoPartner
    2. Search for or create animal in VetoPartner
    3. Create consultation in VetoPartner
    4. Upload documents

    Processed asynchronously.

    Args:
        consultation_id: ID of consultation to integrate
        background_tasks: FastAPI background tasks

    Returns:
        Integration scheduled response
    """
    try:
        consultation = await get_consultation(consultation_id)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Parse consultation data
        import json

        if "data_json" in consultation:
            try:
                consultation_data = json.loads(consultation["data_json"])
            except (json.JSONDecodeError, ValueError):
                consultation_data = {}
        else:
            consultation_data = {}

        # Schedule async integration
        background_tasks.add_task(
            integrate_consultation_with_erp,
            consultation_id,
            consultation_data,
        )

        logger.info(f"ERP integration scheduled for consultation {consultation_id}")

        return {
            "success": True,
            "id": consultation_id,
            "message": "Integration scheduled",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
