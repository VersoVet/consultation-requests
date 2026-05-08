"""Main FastAPI application for consultation-requests skill."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if TYPE_CHECKING:
    from pathlib import Path

from src.config import PORT, SERVICE_NAME, VERSION, logger
from src.core.database import init_db
from src.core.models import HealthResponse
from src.modules.consultations import router as consultation_router
from src.modules.consultations.files import get_file_path
from src.modules.consultations.security import validate_file_token
from src.modules.dashboard import router as dashboard_router

# OnyxSDK - graceful fallback
try:
    from onyx_sdk import OnyxClient, SkillStatus

    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    OnyxClient = None
    SkillStatus = None

onyx = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global onyx

    logger.info(f"Starting {SERVICE_NAME} v{VERSION} on port {PORT}")

    # Initialize database
    await init_db()

    # Initialize OnyxSDK
    if HAS_SDK:
        try:
            onyx = OnyxClient(skill_name=SERVICE_NAME, port=PORT)
            onyx.status(SkillStatus.UP)
            logger.info("OnyxSDK initialized")
        except Exception as e:
            logger.warning(f"OnyxSDK initialization failed: {e}")
            onyx = None

    yield

    # Shutdown
    if HAS_SDK and onyx:
        try:
            onyx.status(SkillStatus.DOWN)
            logger.info("OnyxSDK status set to DOWN")
        except Exception as e:
            logger.warning(f"OnyxSDK shutdown error: {e}")

    logger.info(f"Shutting down {SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title=SERVICE_NAME,
    version=VERSION,
    description="Centralized consultation request management",
    lifespan=lifespan,
)

# Include routers
app.include_router(consultation_router)
app.include_router(dashboard_router)

# Mount static files if they exist
try:
    from pathlib import Path

    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Static files mounted from {static_dir}")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=VERSION,
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/cron")
async def cron() -> dict:
    """Periodic task - publish WORKING status.

    Called by Onyx scheduler every minute to report processing status.
    """
    if HAS_SDK and onyx:
        try:
            from onyx_sdk import SkillStatus

            onyx.status(SkillStatus.WORKING)
            logger.debug("Cron: WORKING status published")
        except Exception as e:
            logger.warning(f"Could not publish WORKING status: {e}")

    return {"status": "cron_executed"}


@app.post("/refresh-db")
async def refresh_database() -> dict:
    """Refresh the database connection cache.

    Useful when the database file has been modified externally.
    Forces the skill to reconnect to the database on next query.

    Returns:
        Status message
    """
    from src.core.database import reset_db

    reset_db()
    logger.info("Database connection refreshed")
    return {"status": "success", "message": "Database connection reset and will reconnect on next query"}


@app.get("/files/{uuid}/{filename}")
async def download_file(
    uuid: str,
    filename: str,
    token: str,
) -> "FileResponse":
    """Download consultation document (secure token-based access).

    Args:
        uuid: Consultation UUID
        filename: File name
        token: HMAC token for security

    Returns:
        File download
    """
    try:
        # Validate token
        is_valid = await validate_file_token(f"{uuid}/{filename}", token)
        if not is_valid:
            logger.warning(f"Invalid file token: {uuid}/{filename}")
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get file path
        file_path = get_file_path(uuid, filename)
        if not file_path:
            logger.warning(f"File not found: {uuid}/{filename}")
            raise HTTPException(status_code=404, detail="File not found")

        # Log access
        logger.info(f"File download: {uuid}/{filename}")

        return FileResponse(path=file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/dashboard")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
