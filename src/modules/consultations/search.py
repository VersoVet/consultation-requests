"""Search animals/clients in ERP."""

from dataclasses import dataclass
from typing import Optional

import httpx

from src.config import logger


@dataclass
class AnimalMatch:
    """Animal match from ERP search."""

    erp_animal_id: int
    animal_name: str
    species: str
    race: Optional[str]
    owner_name: str
    owner_id: int
    last_visit: Optional[str]
    age: Optional[int]
    weight: Optional[float]


async def search_animals_in_erp(
    search_query: str,
    erp_url: str = "http://10.0.0.44:8101",
) -> list[AnimalMatch]:
    """Search animals in ERP by name or owner.

    Args:
        search_query: Animal name or owner name
        erp_url: ERP connector URL

    Returns:
        List of matching animals from ERP
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{erp_url}/search",
                params={"q": search_query},
                timeout=10.0,
            )

        if response.status_code != 200:
            logger.warning(f"ERP search failed: {response.status_code}")
            return []

        results = response.json()
        matches = []

        for item in results.get("results", []):
            match = AnimalMatch(
                erp_animal_id=item.get("idanimal"),
                animal_name=item.get("nom_animal"),
                species=item.get("espece"),
                race=item.get("race"),
                owner_name=item.get("nom_client"),
                owner_id=item.get("idclient"),
                last_visit=item.get("last_visit"),
                age=item.get("age"),
                weight=item.get("poids"),
            )
            matches.append(match)

        logger.info(f"ERP search for '{search_query}': {len(matches)} matches")
        return matches[:5]  # Limit to top 5

    except Exception as e:
        logger.error(f"Error searching ERP: {e}")
        return []


async def get_animal_details(
    erp_animal_id: int,
    erp_url: str = "http://10.0.0.44:8101",
) -> Optional[dict]:
    """Get detailed info for an animal from ERP.

    Args:
        erp_animal_id: Animal ID in ERP
        erp_url: ERP connector URL

    Returns:
        Animal details or None if not found
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{erp_url}/animals/{erp_animal_id}",
                timeout=10.0,
            )

        if response.status_code == 200:
            return response.json()

        return None

    except Exception as e:
        logger.error(f"Error getting animal details: {e}")
        return None
