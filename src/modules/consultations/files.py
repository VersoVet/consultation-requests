"""File handling for consultation attachments."""

import io
import shutil
from pathlib import Path

import httpx

from src.config import FILES_DIR, logger


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


async def scan_file_with_clamd(file_path: Path) -> tuple[bool, str | None]:
    """Scan a file with ClamAV antivirus via clamd socket.

    Args:
        file_path: Path to file to scan

    Returns:
        Tuple of (is_clean, threat_name_or_None)
        - (True, None): File is clean
        - (False, "threat_name"): File is infected
        - (True, None): ClamAV unavailable (non-blocking, logs warning)
    """
    try:
        import clamd

        # Try Unix socket first (preferred on OnyxSoma)
        try:
            c = clamd.ClamdUnixSocket(path="/var/run/clamav/clamd.ctl")
            c.ping()
        except Exception:
            # Fallback to network socket
            try:
                c = clamd.ClamdNetworkSocket(host="127.0.0.1", port=3310)
                c.ping()
            except Exception:
                logger.warning("ClamAV daemon not available, allowing file through")
                return (True, None)

        # Read file and scan
        with open(file_path, "rb") as f:
            result = c.instream(io.BytesIO(f.read()))

        # Result format: {"/<path>": ("FOUND", "threat_name")} or {"/<path>": ("OK", None)}
        if not result:
            logger.info(f"ClamAV scan clean: {file_path.name}")
            return (True, None)

        for filepath, (status, threat) in result.items():
            if status == "FOUND":
                logger.warning(f"ClamAV detected threat in {file_path.name}: {threat}")
                return (False, threat)
            elif status == "OK":
                logger.info(f"ClamAV scan clean: {file_path.name}")
                return (True, None)
            else:
                logger.warning(f"ClamAV scan error for {file_path.name}: {status}")
                return (True, None)

        return (True, None)

    except ImportError:
        logger.warning("clamd module not installed, allowing file through")
        return (True, None)
    except Exception as e:
        logger.warning(f"Error scanning file with ClamAV: {e}, allowing file through")
        return (True, None)


def delete_local_files(uuid: str) -> None:
    """Delete all downloaded files for a consultation after ERP upload.

    Args:
        uuid: Consultation UUID
    """
    uuid_dir = FILES_DIR / uuid

    if uuid_dir.exists() and uuid_dir.is_dir():
        try:
            shutil.rmtree(uuid_dir)
            logger.info(f"Deleted local files for consultation {uuid}")
        except Exception as e:
            logger.error(f"Failed to delete local files for {uuid}: {e}")
    else:
        logger.debug(f"No local files directory found for {uuid}")
