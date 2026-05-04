# Consultation Requests - Architecture

## Overview

**Skill**: `consultation-requests` (port 8092, OnyxSoma)

Centralized management system for consultation requests from verso-vet.com. Receives requests via webhook from WordPress, stores them in SQLite, and integrates them into VetoPartner ERP.

### Key Features
- Receive consultation requests via secure webhook from WordPress
- Store requests in SQLite database
- Download documents from WordPress and store locally
- Send confirmation emails to consultations@verso-vet.com
- Search patients/owners in VetoPartner
- Create new clients/animals in VetoPartner (via erp-connector)
- Integrate consultations into VetoPartner with documents
- Dashboard for managing requests

---

## Component Structure

### Core Modules

#### `src/config.py`
- Load manifest.json and set configuration
- DATABASE_PATH, PORT, VAULT_URL, ERP_URL, MAILBOX_URL
- SERVICE_NAME, VERSION

#### `src/core/vault.py`
- Async client for Onyx Vault
- `get_secret(key)` - retrieve and cache (5 min TTL)
- `get_secret_json(key)` - retrieve and parse JSON

#### `src/core/database.py`
- SQLite async client (aiosqlite)
- Schema initialization
- CRUD operations for consultations

**Table: `consultations`**
```sql
id              INTEGER PRIMARY KEY
uuid            TEXT UNIQUE NOT NULL
submitted_at    TEXT NOT NULL
status          TEXT (pending|received|integrated|rejected)
submitter_type  TEXT (vet|owner)
data_json       TEXT (serialized ConsultationRequest)
files_local     TEXT (JSON list of local paths)
erp_client_id   INTEGER
erp_animal_id   INTEGER
erp_consult_id  INTEGER
integrated_at   TEXT
notes           TEXT
```

#### `src/core/models.py`
Pydantic models:
- `ConsultationRequest` - full request data
- `ConsultationResponse` - response with DB IDs
- `VetInfo`, `OwnerInfo`, `AnimalInfo` - sub-models
- `ConsultationStatus` enum
- `HealthResponse`

#### `src/core/alerting.py`
- Email sending via onyx-mailbox (`/api/send`)
- Internal notifications via onyx-mailbox (`/api/notify`)

### Modules

#### `modules/consultations/`

**`router.py`**
- `POST /consultations/submit` - receive from WordPress
- `GET /consultations` - list with filtering
- `GET /consultations/{id}` - get details
- `PATCH /consultations/{id}/status` - update status
- `PATCH /consultations/{id}/integrate` - integrate into ERP

**`service.py` (future)**
- Business logic for:
  - Downloading files from WordPress
  - Validating data
  - Building email content
  - Calling erp-connector

**`erp.py` (future)**
- Client for erp-connector API
- `search_client()`, `search_animal()`
- `create_client()`, `create_animal()`
- `create_consultation()`, `upload_document()`

#### `modules/dashboard/`

**`router.py`**
- `GET /dashboard` - serve HTML

---

## Request Flow

### 1. WordPress → Skill (Webhook)

```
WordPress form
  ↓
  upload files to /wp-content/uploads/consultations/{uuid}/
  ↓
  POST http://10.0.0.44:8092/consultations/submit
    (HMAC signature: X-Verso-Signature header)
    ConsultationRequest JSON
  ↓
Skill receives
  ↓
  validate HMAC
  ↓
  store in SQLite (status=pending)
  ↓
  return 201 (async processing)
```

### 2. Skill Processing (Async, Fire & Forget)

```
Post-receive:
  ↓
  generate file download URLs with HMAC tokens
  ↓
  build HTML email
  ↓
  send to consultations@verso-vet.com (via onyx-mailbox)
  ↓
  update status=received in SQLite
```

### 3. Dashboard → Integration

```
User clicks "Integrate" in dashboard
  ↓
  PATCH /consultations/{id}/integrate
  ↓
  search client in VetoPartner (erp-connector)
  ↓
  if found: use erp_client_id
  ↓
  if not found: create client (POST /clients)
  ↓
  search animal (GET /animals?client_id=X)
  ↓
  if found: use erp_animal_id
  ↓
  if not found: create animal (POST /animals)
  ↓
  create consultation (POST /consultations)
  ↓
  download files from WordPress
  ↓
  upload files to VetoPartner (POST /animals/{id}/documents/upload)
  ↓
  update SQLite (status=integrated, erp_*_id, integrated_at)
```

---

## Data Flow Diagram

```
┌──────────────────┐
│ verso-vet.com    │
│ WordPress Form   │
└────────┬─────────┘
         │
         │ 1. Upload files
         │ 2. POST /submit (HMAC)
         ↓
┌──────────────────────────────┐
│ consultation-requests (8092) │
│ ┌─────────────────────────┐  │
│ │ /consultations/submit   │  │
│ └────────┬────────────────┘  │
│          │                    │
│          ↓                    │
│ ┌─────────────────────────┐  │
│ │ SQLite Database         │  │
│ │ (pending)               │  │
│ └────────┬────────────────┘  │
│          │                    │
│          │ 3. Async: Download│
│          │    files, send    │
│          │    email          │
│          ↓                    │
│ (status=received)            │
└──────────┬───────────────────┘
           │
           │ 4. User integrates
           │    /integrate
           ↓
┌──────────────────────────────┐
│ erp-connector (8101)         │
│ - search_client              │
│ - create_client              │
│ - search_animal              │
│ - create_animal              │
│ - create_consultation        │
│ - upload_documents           │
└──────────┬───────────────────┘
           │
           ↓
┌──────────────────────────┐
│ VetoPartner (Firebird)   │
│ CLIENTS                  │
│ ANIMAUX                  │
│ CONSULT                  │
│ Documents/Images         │
└──────────────────────────┘
```

---

## Statuses

| Status | Meaning | Trigger |
|--------|---------|---------|
| `pending` | Created in DB, awaiting processing | Initial /submit |
| `received` | Email sent, docs ready | Async after webhook |
| `integrated` | Successfully integrated in VetoPartner | /integrate endpoint |
| `rejected` | Rejected by user | Manual status update |

---

## Security

### HMAC Signatures
- **Webhook validation**: `consultation_webhook_secret` from Vault
- **File download tokens**: `consultation_file_secret` from Vault (7-day TTL)
- Header: `X-Verso-Signature: HMAC-SHA256(...)`

### Secrets (from Vault)
- `consultation_webhook_secret` - WordPress → Skill
- `consultation_file_secret` - File download tokens
- `erp_api_key` - erp-connector authentication (if required)
- `email_config` - SMTP configuration (future)

### Files
- Stored locally on OnyxSoma: `/opt/onyx/data/consultation-requests/files/{uuid}/`
- Downloaded from WordPress via HTTPS (FileResponse + token)
- Not accessible without valid HMAC token

---

## Development Notes

### Current Status
- ✅ Database schema (SQLite)
- ✅ Core models
- ✅ API endpoints (basic)
- ✅ Dashboard template
- 🔄 **Next**: Email integration, ERP integration, file handling

### Dependencies
- FastAPI + uvicorn
- aiosqlite (async SQLite)
- httpx (async HTTP)
- pydantic (validation)
- onyx-sdk (optional, graceful fallback)

### Future Enhancements
- Bulk integration
- Status webhooks to WordPress
- File cleanup (30-day retention)
- Advanced filtering/search
- Analytics dashboard
