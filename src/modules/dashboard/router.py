"""Dashboard routes."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.config import logger
from pathlib import Path

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard() -> FileResponse:
    """Serve dashboard HTML."""
    dashboard_file = Path(__file__).parent.parent.parent.parent / "static" / "dashboard.html"

    if dashboard_file.exists():
        return FileResponse(path=dashboard_file, media_type="text/html")

    # Fallback if dashboard.html doesn't exist
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Consultation Requests - Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1>Consultation Requests Dashboard</h1>
            <p>Loading dashboard...</p>
            <div id="consultations"></div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            fetch('/consultations')
                .then(r => r.json())
                .then(data => {
                    const div = document.getElementById('consultations');
                    div.innerHTML = '<h2>Consultations (' + data.count + ')</h2>';
                    div.innerHTML += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                });
        </script>
    </body>
    </html>
    """
    return FileResponse(
        content=html,
        media_type="text/html",
    )
