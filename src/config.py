"""Configuration pour le skill consultation-requests."""

import json
import logging
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load manifest.json
MANIFEST_PATH = Path(__file__).parent.parent / "manifest.json"
try:
    with open(MANIFEST_PATH) as f:
        MANIFEST = json.load(f)
except Exception as e:
    logger.error(f"Failed to load manifest.json: {e}")
    MANIFEST = {"core": {"routing": {"port": 8092}}}

# Configuration constantes
SERVICE_NAME = MANIFEST.get("name", "consultation-requests")
VERSION = MANIFEST.get("version", "1.0.0")
PORT = MANIFEST["core"]["routing"]["port"]
DATABASE_PATH = Path(__file__).parent.parent / "data" / "consultations.db"

# Vault
VAULT_URL = "http://10.0.0.44:8050/vault"
VAULT_TOKEN = os.environ.get("ONYX_VAULT_TOKEN", "")

# ERP Connector
ERP_URL = "http://10.0.0.44:8101"

# Onyx Mailbox
MAILBOX_URL = "http://10.0.0.44:8054"

# Notification email
NOTIFICATION_EMAIL = "consultations@verso-vet.com"

# File storage
FILES_DIR = Path(__file__).parent.parent / "data" / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Configuration: {SERVICE_NAME} v{VERSION} on port {PORT}")
logger.info(f"Database: {DATABASE_PATH}")
