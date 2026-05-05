"""Parse consultation emails from consultations@verso-vet.com"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedConsultation:
    """Parsed consultation from email."""

    animal_name: str
    animal_species: str
    owner_name: str
    owner_email: Optional[str]
    owner_phone: Optional[str]
    motif: str
    specialite: str
    urgence: bool
    email_subject: str
    email_from: str
    raw_text: str


def parse_consultation_email(subject: str, body: str, from_addr: str) -> Optional[ParsedConsultation]:
    """Parse consultation email to extract structured data.

    Args:
        subject: Email subject
        body: Email body (plaintext)
        from_addr: Sender email address

    Returns:
        ParsedConsultation if valid, None otherwise
    """
    try:
        # Extract patterns from email body
        animal_match = re.search(r"Animal[:\s]+([^\n]+)", body, re.IGNORECASE)
        species_match = re.search(r"Espèce[:\s]+([^\n]+)", body, re.IGNORECASE)
        owner_match = re.search(r"Propriétaire[:\s]+([^\n]+)", body, re.IGNORECASE)
        motif_match = re.search(r"Motif[:\s]+([^\n]+)", body, re.IGNORECASE)
        specialite_match = re.search(r"Spécialité[:\s]+([^\n]+)", body, re.IGNORECASE)
        urgence_match = re.search(r"Urgent[:\s]+(oui|yes|true)", body, re.IGNORECASE)

        # Required fields
        if not animal_match or not owner_match or not motif_match:
            return None

        animal_name = animal_match.group(1).strip()
        species = species_match.group(1).strip() if species_match else "Inconnu"
        owner_name = owner_match.group(1).strip()
        motif = motif_match.group(1).strip()
        specialite = specialite_match.group(1).strip() if specialite_match else "general"
        urgence = bool(urgence_match)

        # Extract email contact if in body
        email_match = re.search(r"Email[:\s]+([a-zA-Z0-9._%+-]+@[^\n]+)", body)
        phone_match = re.search(r"Téléphone[:\s]+([^\n]+)", body)

        return ParsedConsultation(
            animal_name=animal_name,
            animal_species=species,
            owner_name=owner_name,
            owner_email=email_match.group(1).strip() if email_match else from_addr,
            owner_phone=phone_match.group(1).strip() if phone_match else None,
            motif=motif,
            specialite=specialite,
            urgence=urgence,
            email_subject=subject,
            email_from=from_addr,
            raw_text=body,
        )

    except Exception as e:
        return None
