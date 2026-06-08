"""Scorimmo lead ingestion endpoint."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from src.config import logger
from src.core.database import create_consultation
from src.core.models import ScorimmоLeadInput

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.post("/from-scorimmo")
async def ingest_scorimmo_lead(payload: ScorimmоLeadInput) -> dict:
    """Ingest a Scorimmo lead and store as consultation.

    Maps Scorimmo lead fields to consultation format with source='scorimmo'.

    Args:
        payload: Scorimmo lead data

    Returns:
        Created consultation details
    """
    try:
        lead_id = payload.lead_id

        # Build data_json in the flat format used by existing code
        data_json = {
            "uuid": f"scorimmo-{lead_id}",
            "submitter_type": "scorimmo",
            "animal_nom": payload.animal_nom or "Non renseigné",
            "animal_espece": "Non renseigné",
            "animal_race": payload.animal_race,
            "animal_sexe": None,
            "owner_nom": payload.customer_last_name,
            "owner_prenom": payload.customer_first_name,
            "owner_email": payload.customer_email,
            "owner_telephone": payload.customer_phone,
            "motif": payload.motif or "Consultation call center",
            "specialite": "call-center",
            "urgence": False,
            "scorimmo_lead_id": lead_id,
            "scorimmo_origin": payload.origin,
            "scorimmo_veto_habituel": payload.veto_habituel,
        }

        # Use provided created_at or current time
        submitted_at = payload.created_at or datetime.now(UTC).isoformat()

        # Create consultation with source='scorimmo'
        consultation_id = await create_consultation(
            uuid=f"scorimmo-{lead_id}",
            submitted_at=submitted_at,
            submitter_type="scorimmo",
            data_json=json.dumps(data_json),
            source="scorimmo",
        )

        logger.info(f"Scorimmo lead {lead_id} ingested as consultation {consultation_id}")

        return {
            "success": True,
            "consultation_id": consultation_id,
            "uuid": f"scorimmo-{lead_id}",
            "source": "scorimmo",
            "message": f"Scorimmo lead {lead_id} stored as consultation",
        }

    except Exception as e:
        logger.error(f"Error ingesting Scorimmo lead {payload.lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
