"""SQLite database setup and management."""

import json
import logging
from typing import Any

import aiosqlite

from src.config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Ensure data directory exists
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


async def init_db() -> None:
    """Initialize SQLite database with schema."""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                submitter_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                files_local TEXT,
                erp_client_id INTEGER,
                erp_animal_id INTEGER,
                erp_consult_id INTEGER,
                integrated_at TEXT,
                notes TEXT
            )
            """
        )
        await db.commit()
        logger.info(f"Database initialized: {DATABASE_PATH}")


async def get_db() -> aiosqlite.Connection:
    """Get database connection."""
    return await aiosqlite.connect(str(DATABASE_PATH))


async def create_consultation(
    uuid: str,
    submitted_at: str,
    submitter_type: str,
    data_json: str,
) -> int:
    """Create a new consultation request.

    Args:
        uuid: Unique identifier
        submitted_at: Submission datetime (ISO)
        submitter_type: 'vet' or 'owner'
        data_json: JSON-serialized ConsultationRequest

    Returns:
        Database ID of created consultation
    """
    async with await get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO consultations (uuid, submitted_at, submitter_type, data_json, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (uuid, submitted_at, submitter_type, data_json, "pending"),
        )
        await db.commit()
        return int(cursor.lastrowid or 0)


async def get_consultation(consultation_id: int) -> dict | None:
    """Get consultation by ID."""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM consultations WHERE id = ?", (consultation_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_dict(row, cursor.description)


async def list_consultations(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List consultations with optional filtering."""
    async with await get_db() as db:
        if status:
            cursor = await db.execute(
                """
                SELECT * FROM consultations
                WHERE status = ?
                ORDER BY submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                (status, limit, offset),
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM consultations
                ORDER BY submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        rows = await cursor.fetchall()
        return [_row_to_dict(row, cursor.description) for row in rows]


async def update_consultation_status(
    consultation_id: int,
    status: str,
) -> None:
    """Update consultation status."""
    async with await get_db() as db:
        await db.execute(
            "UPDATE consultations SET status = ? WHERE id = ?",
            (status, consultation_id),
        )
        await db.commit()


async def update_consultation_erp_ids(
    consultation_id: int,
    erp_client_id: int,
    erp_animal_id: int,
    erp_consult_id: int,
    integrated_at: str,
) -> None:
    """Update ERP IDs after integration."""
    async with await get_db() as db:
        await db.execute(
            """
            UPDATE consultations
            SET erp_client_id = ?, erp_animal_id = ?, erp_consult_id = ?,
                integrated_at = ?, status = ?
            WHERE id = ?
            """,
            (erp_client_id, erp_animal_id, erp_consult_id, integrated_at, "integrated", consultation_id),
        )
        await db.commit()


async def update_files_local(
    consultation_id: int,
    files: list[str],
) -> None:
    """Update local file paths."""
    files_json = json.dumps(files)
    async with await get_db() as db:
        await db.execute(
            "UPDATE consultations SET files_local = ? WHERE id = ?",
            (files_json, consultation_id),
        )
        await db.commit()


def _row_to_dict(row: Any, description: Any) -> dict:
    """Convert database row to dict.

    Args:
        row: Database row
        description: Column descriptions from cursor

    Returns:
        Dictionary representation of row
    """
    if not row:
        return {}
    return {description[i][0]: row[i] for i in range(len(row))}
