# Consultation Requests - Architecture

> **Status**: 🟢 **PRODUCTION** | Version 1.0.34

## Overview

**Skill**: `consultation-requests` (port 8092, OnyxSoma)

Centralized management system for consultation requests from verso-vet.com. Email-based architecture: receives requests from WordPress plugin via email to `consultations@verso-vet.com`, monitors mailbox via IMAP, extracts and stores data in SQLite, and provides REST API + dashboard for tracking.

**Operational**: ✅ IMAP monitoring, email parsing, SQLite storage, REST API, web dashboard

### Key Features
- **IMAP Monitoring**: Listens for emails from verso-consultation-plugin on consultations@verso-vet.com
- **Email Parsing**: Extracts JSON metadata and document attachments from emails
- **Document Handling**: Receives files directly as email attachments, scans with ClamAV, stores locally
- **Antivirus Scanning**: ClamAV scanning of all received documents (non-blocking if unavailable)
- **ERP Integration**: Uploads consultations and documents to VetoPartner with HMAC signatures
- **SQLite Storage**: Persistent database with consultation records and file path tracking
- **REST API**: Query consultations with filtering, pagination, and integration endpoints
- **Web Dashboard**: Visual interface with file indicators, status tracking, delete/integrate actions
- **Token Security**: HMAC-based token validation for file downloads
- **Database Cache Refresh**: `/refresh-db` endpoint for manual cache invalidation

---

## Component Structure

### Core Modules

#### `src/config.py`
- Loads manifest.json configuration
- DATABASE_PATH, PORT, SERVICE_NAME, VERSION
- Setup logging and environment variables

#### `src/core/vault.py`
- Async client for Onyx Vault secret retrieval
- `get_secret(key)` - retrieve secrets (IMAP credentials, etc.)

#### `src/core/database.py`
- SQLite connection management with ThreadPoolExecutor
- Async-safe pattern using thread pool for sync database operations
- Schema initialization and CRUD operations
- Global connection cache with `reset_db()` method for manual refresh

**Table: `consultations`**
```sql
id              INTEGER PRIMARY KEY AUTOINCREMENT
uuid            TEXT UNIQUE NOT NULL
submitted_at    TEXT NOT NULL (ISO format)
status          TEXT NOT NULL DEFAULT 'pending'
submitter_type  TEXT NOT NULL ('vet' or 'owner')
data_json       TEXT NOT NULL (JSON-serialized consultation data)
files_local     TEXT (JSON list of local file paths)
erp_client_id   INTEGER
erp_animal_id   INTEGER
erp_consult_id  INTEGER
integrated_at   TEXT
notes           TEXT
```

#### `src/core/models.py`
Pydantic data models:
- `HealthResponse` - health check response
- Standard validation and type checking

#### `src/core/imap_monitor.py`
- IMAP client for email monitoring
- `get_imap_credentials()` - retrieve from Vault
- `extract_json_attachment()` - parse JSON from email
- `monitor_imap()` - connect, search for "[Verso Vet] Demande" emails, extract attachments

### Modules

#### `modules/consultations/`

**`service.py`**
- `store_consultation_from_json()` - parse JSON and store in database
- Receives data from IMAP monitor

**`routes.py`**
- `GET /consultations` - list consultations with optional filtering
- `GET /consultations/{id}` - get single consultation details

**`security.py`**
- `validate_file_token()` - HMAC token validation for file downloads
- `generate_file_token()` - create secure download tokens

**`files.py`**
- `get_file_path()` - secure file retrieval with path traversal protection
- File management and download handling

#### `modules/dashboard/`

**`routes.py`**
- `GET /dashboard` - serve dashboard HTML interface

---

## Request Flow

### 1. WordPress Plugin Sends Email

```
verso-vet.com (WordPress form)
  ↓
verso-consultation-plugin generates UUID
  ↓
Builds email with:
  - To: consultations@verso-vet.com
  - From: Verso Vet <consultations@verso-vet.com> (OVH SPF/DKIM)
  - Subject: [Verso Vet] Demande {uuid} - {animal_nom}
  - Body: Formatted text with consultation details
  - Attachment 1: consultation.json (structured data)
  - Attachments 2+: Document files (PDF, JPEG, PNG, DICOM, etc.)
             sent directly by plugin, NOT saved to WordPress server
  ↓
WordPress wp_mail() sends via PHP-FPM context
```

### 2. IMAP Monitoring (Automatic)

```
Skill runs /cron endpoint (every 60 seconds)
  ↓
IMAP monitor connects to consultations@verso-vet.com
  (credentials from Vault)
  ↓
Search for unread emails with subject "[Verso Vet] Demande"
  ↓
For each email:
  - Extract consultation.json attachment (metadata)
  - Extract document attachments (PDF, JPEG, PNG, DICOM, etc.)
  - Save documents locally: /data/files/{uuid}/{filename}
  - ClamAV scan each document (non-blocking if unavailable)
  - Delete infected files, keep clean ones
  - Parse JSON data
  - Store in SQLite with status='pending' + files_local JSON array
  - Mark email as read
  ↓
Update dashboard with new consultations (with file indicators)
```

### 3. Dashboard Display

```
User accesses http://10.0.0.44:8092/dashboard
  ↓
Dashboard queries /consultations endpoint
  ↓
Displays all stored consultations
  ↓
Can filter by status
  ↓
Can view details and download files
```

### 4. Database Connection Cache

```
If dashboard shows stale data:
  ↓
POST /refresh-db to reset connection cache
  ↓
Next query will read fresh data from database file
```

---

## Data Flow Diagram

```
┌──────────────────────────────────┐
│ verso-vet.com                    │
│ (WordPress consultation form)    │
└──────────┬───────────────────────┘
           │
           │ 1. Form submission
           │ 2. Send email to consultations@verso-vet.com
           │    - Attachment 1: consultation.json (metadata)
           │    - Attachments 2+: documents (PDF, JPEG, PNG, etc.)
           ↓
┌──────────────────────────────────┐
│ OVH Email Server                 │
│ consultations@verso-vet.com      │
│ (IMAP mailbox - no server storage)
└──────────┬───────────────────────┘
           │
           │ 3. IMAP Monitor (every 60s via /cron)
           ↓
┌──────────────────────────────────┐
│ consultation-requests (8092)     │
│ ┌──────────────────────────────┐ │
│ │ IMAP Monitor                 │ │
│ │ - Connect to IMAP            │ │
│ │ - Search for emails          │ │
│ │ - Extract JSON metadata      │ │
│ │ - Extract documents          │ │
│ └────────┬──────────────────────┘ │
│          │                         │
│          ↓                         │
│ ┌──────────────────────────────┐ │
│ │ ClamAV Scanning              │ │
│ │ - Scan each document         │ │
│ │ - Delete if infected         │ │
│ │ - Keep clean files           │ │
│ └────────┬──────────────────────┘ │
│          │                         │
│          ↓                         │
│ ┌──────────────────────────────┐ │
│ │ Local File Storage           │ │
│ │ /data/files/{uuid}/{file}    │ │
│ └────────┬──────────────────────┘ │
│          │                         │
│          ↓                         │
│ ┌──────────────────────────────┐ │
│ │ SQLite Database              │ │
│ │ - consultations table        │ │
│ │ - status='pending'           │ │
│ │ - files_local=[paths]        │ │
│ └──────────┬──────────────────┘ │
│            │                     │
│            │ 4. Dashboard reads
│            ↓                     │
│ ┌──────────────────────────────┐ │
│ │ REST API (/consultations)    │ │
│ │ - Filter & pagination        │ │
│ │ - File downloads             │ │
│ └──────────────────────────────┘ │
└──────────┬───────────────────────┘
           │
           ↓
┌──────────────────────────────────┐
│ Web Dashboard                    │
│ http://10.0.0.44:8092/dashboard │
│ - View consultations             │
│ - Download attachments           │
│ - Track status with file badges  │
└──────────────────────────────────┘
```

---

## Statuses

| Status | Meaning | When Set |
|--------|---------|----------|
| `pending` | Received from email, stored in database | Initial storage from IMAP |
| `reviewed` | User has reviewed the consultation | Manual status update |
| `integrated` | Data integrated into external system | Manual status update |
| `archived` | Closed/archived consultation | Manual status update |

---

## Security

### IMAP Credentials
- Stored securely in Onyx Vault
- `imap_host`, `imap_username`, `imap_password`
- Retrieved at runtime, never in code or config

### File Download Tokens
- HMAC-SHA256 based tokens for secure file access
- `consultation_file_secret` from Vault
- 7-day TTL token validation
- Path traversal protection with `realpath()`

### Database
- SQLite local file storage
- Proper user/group permissions on file system
- No credentials stored in database

---

## Development Notes

### Current Status ✅ **PRODUCTION READY**
- ✅ Email-based architecture (IMAP monitoring)
- ✅ JSON attachment extraction from emails
- ✅ SQLite database with async-safe ThreadPoolExecutor
- ✅ Pydantic model validation
- ✅ REST API endpoints (list, filter, download)
- ✅ Web dashboard for viewing consultations
- ✅ HMAC token validation for file downloads
- ✅ Vault integration for secret management
- ✅ OnyxSDK health status reporting
- ✅ Database connection cache refresh endpoint
- ✅ Production deployment on OnyxSoma

### Dependencies
- FastAPI 0.104.1 + uvicorn 0.24.0
- sqlite3 (built-in) + ThreadPoolExecutor (async-safe)
- httpx 0.25.2 (async HTTP client)
- pydantic 2.5.0 (data validation)
- imapclient >=2.3.1 (IMAP email monitoring)
- onyx-sdk (optional, graceful fallback)

### Key Design Decisions
1. **ThreadPoolExecutor for SQLite**: Async-safe pattern for sync database operations
2. **Global Connection Cache**: `_db_conn` with `reset_db()` for manual refresh
3. **Email-based** not webhook-based: Simpler, no signature validation needed
4. **IMAP Polling**: Scheduled via /cron endpoint (every 60s by default)
5. **Local File Storage**: Consultations stored locally, not in external ERP initially
