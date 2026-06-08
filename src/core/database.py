"""SQLite database setup and management."""

import asyncio
import json
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from src.config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Ensure data directory exists
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Global thread pool for database operations
_executor = ThreadPoolExecutor(max_workers=1)

# Global SQLite connection
_db_conn: sqlite3.Connection | None = None


def _get_sync_db() -> sqlite3.Connection:
    """Get a synchronous SQLite connection."""
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False, timeout=10.0)
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def reset_db() -> None:
    """Reset the global database connection (useful after file changes)."""
    global _db_conn
    if _db_conn is not None:
        try:
            _db_conn.close()
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")
    _db_conn = None
    logger.info("Database connection reset")


async def init_db() -> None:
    """Initialize SQLite database with schema."""
    loop = asyncio.get_event_loop()

    def _init():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                submitter_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                files_local TEXT,
                imap_uid INTEGER,
                erp_client_id INTEGER,
                erp_animal_id INTEGER,
                erp_consult_id INTEGER,
                integrated_at TEXT,
                notes TEXT,
                source TEXT DEFAULT 'web'
            )
            """
        )
        conn.commit()

        # Add imap_uid column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE consultations ADD COLUMN imap_uid INTEGER")
            conn.commit()
            logger.info("Added imap_uid column to consultations table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add source column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE consultations ADD COLUMN source TEXT DEFAULT 'web'")
            conn.commit()
            logger.info("Added source column to consultations table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create configuration table for alerts
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT
            )
            """
        )
        conn.commit()

        logger.info(f"Database initialized: {DATABASE_PATH}")

    await loop.run_in_executor(_executor, _init)


async def get_db() -> sqlite3.Connection:
    """Get database connection (synchronous)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_sync_db)


async def create_consultation(
    uuid: str,
    submitted_at: str,
    submitter_type: str,
    data_json: str,
    source: str = "web",
) -> int:
    """Create a new consultation request.

    Args:
        uuid: Unique identifier
        submitted_at: Submission datetime (ISO)
        submitter_type: Type of submitter (e.g., 'vet', 'owner', 'scorimmo')
        data_json: JSON-serialized ConsultationRequest
        source: Source of consultation ('web' for IMAP, 'scorimmo' for leads)

    Returns:
        Database ID of created consultation
    """
    loop = asyncio.get_event_loop()

    def _create():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO consultations (uuid, submitted_at, submitter_type, data_json, status, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uuid, submitted_at, submitter_type, data_json, "pending", source),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)

    return await loop.run_in_executor(_executor, _create)


async def get_consultation(consultation_id: int) -> dict | None:
    """Get consultation by ID."""
    loop = asyncio.get_event_loop()

    def _get():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM consultations WHERE id = ?", (consultation_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cols = [desc[0] for desc in cursor.description]
        return {cols[i]: row[i] for i in range(len(cols))}

    return await loop.run_in_executor(_executor, _get)


async def list_consultations(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List consultations with optional filtering."""
    loop = asyncio.get_event_loop()

    def _list():
        conn = _get_sync_db()
        cursor = conn.cursor()
        if status:
            cursor.execute(
                """
                SELECT * FROM consultations
                WHERE status = ?
                ORDER BY submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                (status, limit, offset),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM consultations
                ORDER BY submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        return [{cols[i]: row[i] for i in range(len(cols))} for row in rows]

    return await loop.run_in_executor(_executor, _list)


async def update_consultation_status(
    consultation_id: int,
    status: str,
) -> None:
    """Update consultation status."""
    loop = asyncio.get_event_loop()

    def _update():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE consultations SET status = ? WHERE id = ?",
            (status, consultation_id),
        )
        conn.commit()

    await loop.run_in_executor(_executor, _update)


async def delete_consultation(consultation_id: int) -> None:
    """Mark consultation as deleted.

    Args:
        consultation_id: ID of consultation to delete
    """
    await update_consultation_status(consultation_id, "deleted")


async def update_imap_uid(consultation_uuid: str, imap_uid: int) -> None:
    """Store IMAP UID for later deletion.

    Args:
        consultation_uuid: UUID of consultation
        imap_uid: IMAP message UID
    """
    loop = asyncio.get_event_loop()

    def _update():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE consultations SET imap_uid = ? WHERE uuid = ?",
            (imap_uid, consultation_uuid),
        )
        conn.commit()

    await loop.run_in_executor(_executor, _update)


async def update_consultation_erp_ids(
    consultation_id: int,
    erp_client_id: int,
    erp_animal_id: int,
    erp_consult_id: int,
    integrated_at: str,
) -> None:
    """Update ERP IDs after integration."""
    loop = asyncio.get_event_loop()

    def _update():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE consultations
            SET erp_client_id = ?, erp_animal_id = ?, erp_consult_id = ?,
                integrated_at = ?, status = ?
            WHERE id = ?
            """,
            (erp_client_id, erp_animal_id, erp_consult_id, integrated_at, "integrated", consultation_id),
        )
        conn.commit()

    await loop.run_in_executor(_executor, _update)


async def update_files_local(
    consultation_id: int,
    files: list[str],
) -> None:
    """Update local file paths."""
    files_json = json.dumps(files)
    loop = asyncio.get_event_loop()

    def _update():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE consultations SET files_local = ? WHERE id = ?",
            (files_json, consultation_id),
        )
        conn.commit()

    await loop.run_in_executor(_executor, _update)


async def get_config(key: str, default: str = "") -> str:
    """Get configuration value by key.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    loop = asyncio.get_event_loop()

    def _get():
        conn = _get_sync_db()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    return await loop.run_in_executor(_executor, _get)


async def set_config(key: str, value: str) -> None:
    """Set configuration value.

    Args:
        key: Configuration key
        value: Configuration value
    """
    from datetime import UTC, datetime

    loop = asyncio.get_event_loop()

    def _set():
        conn = _get_sync_db()
        cursor = conn.cursor()
        updated_at = datetime.now(UTC).isoformat()
        cursor.execute(
            "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, updated_at),
        )
        conn.commit()

    await loop.run_in_executor(_executor, _set)
