"""ERP Connector API client for VetoPartner integration."""

from typing import Any

import httpx
from pydantic import BaseModel, Field

from src.config import logger

# ERP Connector API base URL
ERP_BASE_URL = "http://10.0.0.44:8101"
ERP_TIMEOUT = 30.0


class ErpConnectorError(Exception):
    """ERP Connector error."""

    pass


class ClientModel(BaseModel):
    """Client in VetoPartner."""

    id: int = Field(..., description="Client ID")
    nom: str = Field(..., description="Last name")
    prenom: str | None = Field(None, description="First name")
    email: str | None = Field(None, description="Email")
    telephone: str | None = Field(None, description="Phone")


class AnimalModel(BaseModel):
    """Animal in VetoPartner."""

    id: int = Field(..., description="Animal ID")
    client_id: int = Field(..., description="Owner (client) ID")
    nom: str = Field(..., description="Animal name")
    espece: str = Field(..., description="Species")
    race: str | None = Field(None, description="Breed")
    sexe: str | None = Field(None, description="Sex")


class ConsultationModel(BaseModel):
    """Consultation in VetoPartner."""

    id: int = Field(..., description="Consultation ID")
    animal_id: int = Field(..., description="Animal ID")
    motif: str = Field(..., description="Reason")
    specialite: str | None = Field(None, description="Specialty")


async def search_clients(search: str) -> list[ClientModel]:
    """Search clients in VetoPartner.

    Args:
        search: Search string (name, email, etc)

    Returns:
        List of matching clients

    Raises:
        ErpConnectorError: If API error
    """
    try:
        async with httpx.AsyncClient(timeout=ERP_TIMEOUT) as client:
            response = await client.get(
                f"{ERP_BASE_URL}/clients",
                params={"search": search},
            )
            response.raise_for_status()
            data = response.json()
            return [ClientModel(**c) for c in data.get("clients", [])]
    except httpx.HTTPError as e:
        logger.error(f"ERP search_clients error: {e}")
        raise ErpConnectorError(f"Failed to search clients: {e}") from e


async def create_client(
    nom: str,
    prenom: str | None = None,
    email: str | None = None,
    telephone: str | None = None,
) -> int:
    """Create a new client in VetoPartner.

    Args:
        nom: Last name
        prenom: First name
        email: Email
        telephone: Phone number

    Returns:
        Client ID

    Raises:
        ErpConnectorError: If API error
    """
    try:
        payload = {"nom": nom}
        if prenom:
            payload["prenom"] = prenom
        if email:
            payload["email"] = email
        if telephone:
            payload["telephone"] = telephone

        async with httpx.AsyncClient(timeout=ERP_TIMEOUT) as client:
            response = await client.post(
                f"{ERP_BASE_URL}/clients",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            client_id = data.get("id")
            if not client_id:
                raise ErpConnectorError("No ID returned from create_client")
            return int(client_id)
    except httpx.HTTPError as e:
        logger.error(f"ERP create_client error: {e}")
        raise ErpConnectorError(f"Failed to create client: {e}") from e


async def search_animals(client_id: int, search: str | None = None) -> list[AnimalModel]:
    """Search animals for a client.

    Args:
        client_id: Client ID
        search: Optional search string (name, etc)

    Returns:
        List of matching animals

    Raises:
        ErpConnectorError: If API error
    """
    try:
        params: dict[str, Any] = {"client_id": client_id}
        if search:
            params["search"] = search

        async with httpx.AsyncClient(timeout=ERP_TIMEOUT) as client:
            response = await client.get(
                f"{ERP_BASE_URL}/animals",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return [AnimalModel(**a) for a in data.get("animals", [])]
    except httpx.HTTPError as e:
        logger.error(f"ERP search_animals error: {e}")
        raise ErpConnectorError(f"Failed to search animals: {e}") from e


async def create_animal(
    client_id: int,
    nom: str,
    espece: str,
    race: str | None = None,
    sexe: str | None = None,
    date_naissance: str | None = None,
    puce: str | None = None,
    poids: float | None = None,
) -> int:
    """Create a new animal in VetoPartner.

    Args:
        client_id: Client (owner) ID
        nom: Animal name
        espece: Species
        race: Breed
        sexe: Sex
        date_naissance: Birth date (ISO format)
        puce: Microchip number
        poids: Weight in kg

    Returns:
        Animal ID

    Raises:
        ErpConnectorError: If API error
    """
    try:
        payload = {
            "idclient": client_id,
            "nom": nom,
            "espece": espece,
        }
        if race:
            payload["race"] = race
        if sexe:
            payload["sexe"] = sexe
        if date_naissance:
            payload["date_naissance"] = date_naissance
        if puce:
            payload["puce_num"] = puce
        if poids:
            payload["poids"] = poids

        async with httpx.AsyncClient(timeout=ERP_TIMEOUT) as client:
            response = await client.post(
                f"{ERP_BASE_URL}/animals",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            animal_id = data.get("id")
            if not animal_id:
                raise ErpConnectorError("No ID returned from create_animal")
            return int(animal_id)
    except httpx.HTTPError as e:
        logger.error(f"ERP create_animal error: {e}")
        raise ErpConnectorError(f"Failed to create animal: {e}") from e


async def create_consultation(
    animal_id: int,
    motif: str,
    specialite: str | None = None,
    urgence: bool = False,
    traitements_en_cours: str | None = None,
) -> int:
    """Create a consultation in VetoPartner.

    Args:
        animal_id: Animal ID
        motif: Reason for consultation
        specialite: Specialty
        urgence: Is it urgent?
        traitements_en_cours: Current treatments

    Returns:
        Consultation ID

    Raises:
        ErpConnectorError: If API error
    """
    try:
        payload = {
            "animal_id": animal_id,
            "synthese": motif,
        }
        if specialite:
            payload["specialite"] = specialite
        if urgence:
            payload["urgence"] = urgence
        if traitements_en_cours:
            payload["traitements_en_cours"] = traitements_en_cours

        async with httpx.AsyncClient(timeout=ERP_TIMEOUT) as client:
            response = await client.post(
                f"{ERP_BASE_URL}/consultations",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            consult_id = data.get("id")
            if not consult_id:
                raise ErpConnectorError("No ID returned from create_consultation")
            return int(consult_id)
    except httpx.HTTPError as e:
        logger.error(f"ERP create_consultation error: {e}")
        raise ErpConnectorError(f"Failed to create consultation: {e}") from e


async def upload_document(animal_id: int, file_path: str, file_name: str) -> dict:
    """Upload a document to VetoPartner.

    Args:
        animal_id: Animal ID
        file_path: Local file path
        file_name: File name to use in VetoPartner

    Returns:
        Upload result (dict with upload details)

    Raises:
        ErpConnectorError: If API error
    """
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, "application/octet-stream")}
            async with httpx.AsyncClient(timeout=ERP_TIMEOUT) as client:
                response = await client.post(
                    f"{ERP_BASE_URL}/animals/{animal_id}/documents/upload",
                    files=files,
                )
                response.raise_for_status()
                return response.json()
    except (OSError, httpx.HTTPError, FileNotFoundError) as e:
        logger.error(f"ERP upload_document error: {e}")
        raise ErpConnectorError(f"Failed to upload document: {e}") from e
