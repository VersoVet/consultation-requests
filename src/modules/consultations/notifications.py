"""Email notification building for consultations."""

from datetime import UTC, datetime

from src.core.models import ConsultationRequest


def build_notification_email(
    request: ConsultationRequest,
    file_urls: list[str],
    consultation_id: int,
) -> tuple[str, str]:
    """Build HTML email notification.

    Args:
        request: ConsultationRequest data
        file_urls: List of local file paths
        consultation_id: Database ID for dashboard link

    Returns:
        Tuple of (plain_text_body, html_body)
    """
    # Build owner/vet section based on submitter_type
    if request.submitter_type == "vet" and request.vet:
        contact_section = f"""
--- Référant Vétérinaire ---
Nom: {request.vet.nom} {request.vet.prenom}
Clinique: {request.vet.clinique}
Email: {request.vet.email}
Tél: {request.vet.telephone}
"""
    elif request.owner:
        contact_section = f"""
--- Propriétaire ---
Nom: {request.owner.nom} {request.owner.prenom}
Email: {request.owner.email or "N/A"}
Tél: {request.owner.telephone or "N/A"}
"""
    else:
        contact_section = "--- Contact info non disponible ---\n"

    # Plain text
    text_body = f"""
Nouvelle demande de consultation reçue

ID: {consultation_id}
UUID: {request.uuid}
Type: {request.submitter_type.upper()}

--- Animal ---
Nom: {request.animal.nom}
Espèce: {request.animal.espece}
Race: {request.animal.race or "N/A"}

{contact_section}
--- Motif ---
Spécialité: {request.specialite}
Urgence: {"Oui" if request.urgence else "Non"}
Motif: {request.motif}

Accédez au dashboard: http://10.0.0.44:8092/dashboard
"""

    # HTML body
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2196F3; color: white; padding: 15px; border-radius: 5px; }}
        .section {{ margin: 15px 0; padding: 10px; border-left: 3px solid #2196F3; }}
        .field {{ margin: 8px 0; }}
        .label {{ font-weight: bold; color: #555; }}
        .urgent {{ color: #d32f2f; font-weight: bold; }}
        .button {{ display: inline-block; padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 3px; }}
        .files {{ background: #f5f5f5; padding: 10px; border-radius: 3px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🏥 Nouvelle Demande de Consultation</h2>
        </div>

        <div class="section">
            <div class="field"><span class="label">ID:</span> {consultation_id}</div>
            <div class="field"><span class="label">UUID:</span> {request.uuid}</div>
            <div class="field"><span class="label">Type:</span> {request.submitter_type.upper()}</div>
        </div>

        <div class="section">
            <h3>🐾 Patient</h3>
            <div class="field"><span class="label">Nom:</span> {request.animal.nom}</div>
            <div class="field"><span class="label">Espèce:</span> {request.animal.espece}</div>
            <div class="field"><span class="label">Race:</span> {request.animal.race or "Non spécifiée"}</div>
        </div>

        <div class="section">
            {"<h3>🩺 Référant Vétérinaire</h3>" if request.submitter_type == "vet" else "<h3>👤 Propriétaire</h3>"}
            {f"<div class=\"field\"><span class=\"label\">Nom:</span> {request.vet.nom} {request.vet.prenom}</div>" if request.vet else ""}
            {f"<div class=\"field\"><span class=\"label\">Clinique:</span> {request.vet.clinique}</div>" if request.vet else ""}
            {f"<div class=\"field\"><span class=\"label\">Email:</span> {request.vet.email}</div>" if request.vet else ""}
            {f"<div class=\"field\"><span class=\"label\">Tél:</span> {request.vet.telephone}</div>" if request.vet else ""}
            {f"<div class=\"field\"><span class=\"label\">Nom:</span> {request.owner.nom} {request.owner.prenom}</div>" if request.owner else ""}
            {f"<div class=\"field\"><span class=\"label\">Email:</span> {request.owner.email or 'N/A'}</div>" if request.owner else ""}
            {f"<div class=\"field\"><span class=\"label\">Tél:</span> {request.owner.telephone or 'N/A'}</div>" if request.owner else ""}
        </div>

        <div class="section">
            <h3>📋 Motif</h3>
            <div class="field"><span class="label">Spécialité:</span> {request.specialite}</div>
            <div class="field"><span class="label">Urgence:</span> <span class="{"urgent" if request.urgence else ""}">{
        "🔴 OUI" if request.urgence else "⚪ Non"
    }</span></div>
            <div class="field"><span class="label">Motif:</span><br>{request.motif}</div>
        </div>

        {
        f'''<div class="files">
            <h3>📎 Fichiers ({len(file_urls)})</h3>
            <ul>{"".join(f"<li>{f.split('/')[-1]}</li>" for f in file_urls)}</ul>
        </div>'''
        if file_urls
        else ""
    }

        <div class="section" style="text-align: center; margin-top: 30px;">
            <a href="http://10.0.0.44:8092/dashboard" class="button">Accéder au Dashboard</a>
        </div>

        <hr>
        <p style="font-size: 12px; color: #999;">
            Consultation #{consultation_id} • {datetime.now(UTC).isoformat()}
        </p>
    </div>
</body>
</html>
"""

    return text_body, html_body
