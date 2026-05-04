"""Dashboard routes."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard() -> FileResponse:
    """Serve dashboard HTML.

    Returns the interactive Bootstrap dashboard for managing consultations.
    """
    dashboard_file = Path(__file__).parent.parent.parent.parent / "static" / "dashboard.html"
    return FileResponse(path=dashboard_file, media_type="text/html")
