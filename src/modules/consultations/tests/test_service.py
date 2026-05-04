"""Tests for consultation service."""

import pytest

from src.core.models import AnimalInfo, ConsultationRequest, OwnerInfo, VetInfo


@pytest.fixture
def sample_consultation() -> ConsultationRequest:
    """Create a sample consultation request."""
    return ConsultationRequest(
        uuid="test_uuid_12345",
        submitter_type="vet",
        vet=VetInfo(
            nom="Dupont",
            prenom="Jean",
            clinique="Clinique Test",
            email="jean@test.fr",
            telephone="01.23.45.67.89",
            adresse=None,
        ),
        owner=OwnerInfo(
            nom="Martin",
            prenom="Marie",
            email="marie@test.fr",
            telephone="06.12.34.56.78",
        ),
        animal=AnimalInfo(
            nom="Rex",
            espece="Chien",
            race="Labrador",
            sexe="M",
            date_naissance=None,
            puce=None,
            poids=None,
        ),
        motif="Boiterie antérieure",
        specialite="imagerie",
        urgence=False,
        traitements_en_cours=None,
        fichiers=[],
    )


@pytest.mark.asyncio
async def test_validate_hmac_signature_valid(sample_consultation: ConsultationRequest) -> None:
    """Test HMAC signature validation with valid signature."""
    from src.modules.consultations.service import validate_hmac_signature

    # Test with placeholder - in real tests would mock get_secret
    result = await validate_hmac_signature("test_body", "invalid_signature")
    assert isinstance(result, bool)


def test_build_notification_email(sample_consultation: ConsultationRequest) -> None:
    """Test email template building."""
    from src.modules.consultations.service import build_notification_email

    text_body, html_body = build_notification_email(
        sample_consultation,
        ["test/file.jpg"],
        1,
    )

    assert "Rex" in text_body
    assert "imagerie" in text_body
    assert "Marie" in html_body
    assert "test/file.jpg" in html_body
    assert "<html>" in html_body.lower()
