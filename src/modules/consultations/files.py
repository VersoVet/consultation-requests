"""File handling for consultation attachments."""

from pathlib import Path

import httpx

from src.config import DATABASE_PATH, logger

# Local file storage directory
FILES_DIR = DATABASE_PATH.parent / "consultation-requests" / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)


async def download_and_store_files(
    uuid: str,
    file_urls: list[str],
) -> list[str]:
    """Download files from WordPress and store locally.

    Args:
        uuid: Consultation UUID
        file_urls: List of file URLs from WordPress

    Returns:
        List of local file paths

    Raises:
        Exception: If download fails
    """
    local_paths: list[str] = []
    uuid_dir = FILES_DIR / uuid
    uuid_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for url in file_urls:
            try:
                # Download file
                response = await client.get(url)
                response.raise_for_status()

                # Extract filename from URL
                filename = url.split("/")[-1]
                if not filename or "." not in filename:
                    filename = f"file_{len(local_paths)}.bin"

                # Save locally
                local_path = uuid_dir / filename
                local_path.write_bytes(response.content)

                local_paths.append(f"{uuid}/{filename}")
                logger.info(f"Downloaded file: {filename} ({len(response.content)} bytes)")

            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")
                # Continue with other files

    if not local_paths:
        logger.warning(f"No files downloaded for consultation {uuid}")

    return local_paths


def get_file_path(uuid: str, filename: str) -> Path | None:
    """Get local file path for a consultation file.

    Args:
        uuid: Consultation UUID
        filename: File name

    Returns:
        Path to file if it exists, None otherwise
    """
    file_path = FILES_DIR / uuid / filename

    # Security: ensure path is within FILES_DIR (prevent directory traversal)
    try:
        file_path.resolve().relative_to(FILES_DIR.resolve())
    except ValueError:
        logger.error(f"Attempted directory traversal: {file_path}")
        return None

    if file_path.exists() and file_path.is_file():
        return file_path

    return None
