# TODO - Consultation Requests

> **Status**: 🟢 **PRODUCTION** | Version 1.0.55 | Last Updated: 2026-06-08

## Current Status
✅ **OPERATIONAL** - Unified consultation platform with IMAP monitoring, Scorimmo integration, and ERP lifecycle management.

**Latest (2026-06-08 - v1.0.55)**:
- ✅ Scorimmo lead centralization in dashboard with source badges
- ✅ Source-based filtering (Web / Scorimmo)
- ✅ Non-blocking HTTP forwarding from scorimmo-relay
- ✅ IMAP email monitoring with full document handling
- ✅ ClamAV antivirus scanning of uploaded files
- ✅ ERP document upload with HMAC-SHA256 signature
- ✅ Local file cleanup after successful ERP upload
- 🔄 WordPress file deletion (awaiting verso-consultation-plugin update with file-manager endpoint)
- ✅ DELETE endpoint - mark consultation deleted + remove from IMAP
- ✅ Dashboard delete + integrate buttons with full UI
- ✅ Dashboard file attachment indicators (count badge per consultation)
- Forge validation: ✅ PASS (0 errors, 2 info warnings)

## Completed ✅

### Phase 0: Architecture Refactor (2026-05-08) ✅
- [x] Switched from webhook-based to email-based IMAP monitoring
- [x] Implemented IMAP client for consultations@verso-vet.com monitoring
- [x] JSON attachment extraction from verso-consultation-plugin emails
- [x] SQLite database storage with connection cache management
- [x] /refresh-db endpoint for manual cache invalidation
- [x] Documentation updated (ARCHITECTURE.md, API.md)
- [x] Forge validation passing (18/18 phases)

### Phase 1: Core Foundation ✅
- [x] Directory structure (src/, modules/, tests/)
- [x] manifest.json (port 8092, OnyxSoma)
- [x] requirements.txt (FastAPI, uvicorn, imapclient, httpx, pydantic)
- [x] src/config.py (configuration loader)
- [x] src/core/vault.py (secret retrieval from Onyx Vault)
- [x] src/core/models.py (Pydantic data models)
- [x] src/core/database.py (SQLite with ThreadPoolExecutor)
- [x] src/core/imap_monitor.py (IMAP email monitoring)
- [x] src/main.py (FastAPI application + lifespan)

### Phase 2: API Modules ✅
- [x] modules/consultations/router.py (GET /consultations, GET /{id})
- [x] modules/consultations/service.py (store_consultation_from_json)
- [x] modules/consultations/security.py (HMAC token validation)
- [x] modules/consultations/files.py (file download with path protection)
- [x] modules/dashboard/router.py (GET /dashboard)
- [x] modules/dashboard/service.py (dashboard service layer)

### Phase 3: API Endpoints ✅
- [x] GET /health (health check)
- [x] GET /cron (IMAP monitoring trigger)
- [x] POST /refresh-db (cache refresh)
- [x] GET /consultations (list with filtering & pagination)
- [x] GET /consultations/{id} (detail view)
- [x] GET /dashboard (web interface)
- [x] GET /files/{uuid}/{filename} (secure download)

### Phase 4: Documentation ✅
- [x] README.md (skill overview)
- [x] API.md (endpoint documentation)
- [x] ARCHITECTURE.md (system design)
- [x] docs/DEPLOYMENT.md (deployment procedures)
- [x] docs/DASHBOARD-TROUBLESHOOTING.md (troubleshooting guide)

### Phase 5: Code Quality ✅
- [x] Ruff linting - PASS (E/F/W fixed)
- [x] Mypy type checking - PASS (union-attr fixed)
- [x] Google-style docstrings - 100% coverage
- [x] Type annotations - 100% coverage
- [x] All modules < 300 lines - PASS
- [x] Cron tasks defined (cron.json)

### Phase 6: Validation & Testing ✅
- [x] Forge validation (18/18 phases) - PASS
- [x] Database initialization - PASS
- [x] IMAP connectivity test - PASS
- [x] JSON parsing from emails - PASS
- [x] API response validation - PASS
- [x] Token validation - PASS

### Phase 7: Production Deployment ✅
- [x] Forge validate - PASS (0 errors, 7 warnings resolved)
- [x] Repository clean (no obsolete files)
- [x] Secrets configured in Vault
- [x] Database initialized (/data/consultations.db)
- [x] Service ready on port 8092
- [x] Health endpoint responding
- [x] Production (v1.0.18) - active

## System Status

### Test Results ✅
| Test | Status | Details |
|------|--------|---------|
| Email parsing | ✅ PASS | JSON extraction from IMAP emails |
| SQLite storage | ✅ PASS | Consultations persisted correctly |
| IMAP UID tracking | ✅ PASS | imap_uid stored on import |
| DELETE endpoint | ✅ PASS | Soft delete + email removal from IMAP |
| API /consultations | ✅ PASS | List with filtering and pagination |
| API /consultations/{id} | ✅ PASS | Detail view returns full data |
| API /search | ✅ PASS | ERP patient search (1-2 words) |
| File download | ✅ PASS | Token-based HMAC validation |
| Dashboard HTML | ✅ PASS | Loads correctly with delete button ready |
| Health check | ✅ PASS | Service status reporting |

### Metrics
- **Code Quality**: 6 modules, all < 300 lines
- **Documentation**: 5 comprehensive guides
- **Validation**: Forge 18/18 phases - PASS (0 errors)
- **Status**: 🟢 Production Ready (v1.0.18)
- **Response Time**: < 100ms average

## In Progress (Current Sprint)

### Phase 12: Scorimmo Lead Centralization (v1.0.55) ✅ COMPLETE
- [x] Create POST /consultations/from-scorimmo endpoint
- [x] Add source column to consultations table with auto-migration
- [x] Map Scorimmo fields to consultation format
- [x] Dashboard source column with visual badges
- [x] Source-based filtering in sidebar (Web/Scorimmo toggles)
- [x] Non-blocking HTTP forwarding from scorimmo-relay
- [x] Handle custom_fields key variants in Scorimmo data
- [x] End-to-end testing with live Scorimmo webhook
- [x] Graceful error handling and fallback

**Status**: ✅ DEPLOYED v1.0.55
- Both skills deployed and tested
- scorimmo-relay changes pushed to origin
- Dashboard shows Scorimmo leads with source badges
- Filtering works for both Web and Scorimmo sources

---

## Phase 9 Summary (2026-05-09)

**Document Handling Complete** ✅

**New Features in v1.0.32:**
- Download files from WordPress URLs in `fichiers` field during IMAP ingestion
- ClamAV scanning of downloaded files (non-blocking, logs warning if unavailable)
- Files stored locally at `data/files/{uuid}/{filename}`
- HMAC-SHA256 signed upload to ERP `/animals/{id}/documents/upload` endpoint
- Automatic cleanup of local files after successful ERP upload
- Stub for WordPress deletion (awaiting plugin endpoint implementation)

**Implementation Details:**
- `download_and_scan_files()` in service.py downloads + scans files
- `scan_file_with_clamd()` in files.py connects via clamd socket
- `_upload_document_to_erp()` in integration.py handles ERP upload with HMAC
- `_delete_wordpress_files()` stub logs warning (plugin endpoint needed)
- `delete_local_files()` removes local directory after upload

**Pending: WordPress File Deletion**
- Plugin endpoint `DELETE /wp-json/verso/v1/consultations/{uuid}/files` not yet implemented
- verso-consultation-plugin v1.0.1 development in separate session
- Once available, uncomment/enable the deletion call in integration.py

**Test Checklist:**
- [x] Submit test consultation with document attachments
- [x] Verify files downloaded to `data/files/{uuid}/`
- [x] Verify ClamAV scan results (check logs)
- [x] Verify ERP upload with HMAC signature success
- [x] Verify local files deleted after upload
- [x] Test with infected file (ClamAV rejection)
- [ ] Once plugin ready: test WordPress file deletion

---

## Phase 10: Dashboard UX Improvements (v1.0.36) ✅ COMPLETE
- [x] Add "Files" column to consultations table
- [x] Display file count with visual badge when documents attached
- [x] Show dash (-) when no documents
- [x] Handle both JSON string and array formats for files_local
- [x] Blue info badge with PDF icon for easy visual scanning
- [x] Eliminates need to open detail modal to check for attachments

**Implementation Details:**
- Updated table header to include "Files" column
- Added file parsing logic in `displayConsultations()` function
- Files count displayed as `<badge bg-info>📄 {count}</badge>` or `-`
- Handles JSON string parsing with try/catch fallback

**User Benefit:**
Users can now see at a glance in the main consultations table which submissions have attached documents, improving dashboard usability and reducing clicks needed to assess consultation status.

---

## Phase 11: Email Attachment Processing (v1.0.37) ✅ COMPLETE
- [x] Plugin updated to send documents as email attachments (no server storage)
- [x] Extract document attachments from email message (not just JSON)
- [x] Store attachments locally with ClamAV scanning (non-blocking)
- [x] Delete infected files automatically during ingestion
- [x] Clarified code & documentation for email attachment workflow
- [x] Updated ARCHITECTURE.md with new data flow diagram

**Implementation Details:**
- New `extract_file_attachments()` in imap_monitor.py extracts non-JSON attachments
- New `store_email_attachments()` in files.py handles local storage + ClamAV scanning
- Modified `store_consultation_from_json()` to accept attachments parameter
- Updated `monitor_imap()` to pass attachments to service layer
- Removed references to WordPress file server storage (no longer needed)

**Key Behavior:**
- Documents sent as email attachments by verso-consultation-plugin
- Files saved locally to `/data/files/{uuid}/{filename}`
- ClamAV scans immediately; infected files deleted during ingestion
- Clean files tracked in `files_local` JSON array in database
- Files uploaded to ERP during integration with HMAC signatures
- Local cleanup after successful ERP upload

**Deployment Note:**
Plugin already sends attachments; no plugin changes needed. Code now properly handles this workflow.

---

## Phase 12: Scorimmo Lead Centralization (v1.0.55) ✅ COMPLETE

**Centralized Dashboard Complete** ✅

**Objective**: Unify Scorimmo call center leads with web-based consultations in a single dashboard, eliminating data silos and enabling consistent ERP integration.

**New Features in v1.0.55:**
- POST /consultations/from-scorimmo endpoint for receiving Scorimmo leads
- "Source" column in dashboard with visual badges (🔵 Web / 🟠 Scorimmo)
- Source filtering in sidebar (toggle Web/Scorimmo visibility)
- Automatic schema migration (add source column if missing)
- Non-blocking HTTP forwarding from scorimmo-relay to consultation-requests
- Full ERP integration support for Scorimmo leads

**Architecture**:
```
scorimmo-relay (port 8110)
  ↓ (new_lead event)
  → forward_lead_to_consultation_requests()
    ↓ (HTTP POST)
    → consultation-requests (port 8092)
      ↓
      POST /consultations/from-scorimmo
        ↓
        Store in SQLite with source="scorimmo"
        ↓
        Dashboard displays with badge + filtering
```

**Implementation Details**:

1. **Backend (consultation-requests)**:
   - New module: `src/modules/consultations/ingest.py` (74 lines)
   - Endpoint: `POST /consultations/from-scorimmo`
   - Maps Scorimmo fields to consultation format:
     - `customer_*` → `owner_*`
     - `custom_fields["Nom de l'animal"]` → `animal_nom`
     - Missing `animal_espece` → defaults to "Non renseigné"
     - `specialite` set to "call-center"
   - Database: Added `source TEXT DEFAULT 'web'` column with auto-migration
   - Modified `store_consultation()` to accept `source: str = "web"` parameter

2. **Frontend (dashboard.html)**:
   - Added "Source" column in consultations table
   - Visual badges:
     - `source === 'scorimmo'` → `<span class="badge bg-warning text-dark">🟠 Scorimmo</span>`
     - Otherwise → `<span class="badge bg-info text-white">🔵 Web</span>`
   - New filter section in sidebar: "Source" with two toggle buttons (Web / Scorimmo)
   - Updated `filterConsultations()` to check source visibility
   - Modified `resetFilters()` to reset source toggles

3. **Forwarding (scorimmo-relay)**:
   - New module: `src/forwarder.py` (85 lines)
   - Function: `async forward_lead_to_consultation_requests(lead_data: dict) -> bool`
   - Handles dual custom_fields key variants:
     - "Nom de l'animal" OR "Nom de l animal"
     - "Race de l'animal" OR "Race de l animal"
   - Non-blocking with httpx (timeouts, error handling)
   - Returns False on error with logger.warning (graceful degradation)
   - Constant: `CONSULTATION_REQUESTS_URL = "http://10.0.0.44:8092"`

4. **Integration (scorimmo-relay main.py)**:
   - Added async forwarding call in `handle_new_lead()` using `asyncio.create_task()`
   - Ensures webhook response isn't delayed by HTTP forward
   - Fires-and-forgets: lead is stored locally first, then forwarded

**Data Format**:
```json
{
  "uuid": "scorimmo-{lead_id}",
  "submitter_type": "scorimmo",
  "source": "scorimmo",
  "animal_nom": "Rex",
  "animal_espece": "Non renseigné",
  "animal_race": "Labrador",
  "owner_nom": "Dupont",
  "owner_prenom": "Jean",
  "owner_email": "jean@example.com",
  "owner_telephone": "0612345678",
  "motif": "Consultation chirurgie",
  "specialite": "call-center",
  "urgence": false,
  "scorimmo_lead_id": 12345,
  "scorimmo_origin": "Web",
  "scorimmo_veto_habituel": "Dr Martin"
}
```

**Key Benefits**:
- ✅ Single source of truth for all consultations (web + Scorimmo)
- ✅ Unified dashboard eliminates need for separate Scorimmo tracking
- ✅ Both sources can be integrated into ERP with same workflow
- ✅ Visual distinction with badges and filtering by source
- ✅ Non-blocking architecture (Scorimmo webhook not delayed)
- ✅ Graceful fallback if consultation-requests is unavailable

**Testing**:
- [x] Validate POST /consultations/from-scorimmo endpoint
- [x] End-to-end: Send Scorimmo webhook → verify in consultation-requests dashboard
- [x] Verify source column displays with correct badges
- [x] Test source filtering (Web/Scorimmo toggles)
- [x] Verify ERP integration works for Scorimmo leads
- [x] Test graceful fallback when endpoint unavailable

**Deployment Notes**:
- Both skills must be deployed for full integration
- scorimmo-relay forwards to consultation-requests URL (configurable)
- No database migration needed (auto-applied on first run)
- Schema backward-compatible (new source column defaults to 'web')

---

## Phase 8 Summary (2026-05-09)

**Dashboard UI Complete** ✅

**New Features in v1.0.25:**
- Delete consultation: Red button with confirmation dialog in table + modal
- ERP Integration modal: Search patients via `GET /search?q=`, select existing or create new
- Soft delete: Mark as deleted in DB, hidden from dashboard
- End-to-end flow: Email → SQLite → Delete/Integrate UI

**Endpoints Used:**
- `DELETE /consultations/{id}` - soft delete + IMAP removal
- `GET /search?q=` - search ERP for patients
- `POST /consultations/{id}/integrate?erp_animal_id=X` - integrate with existing patient
- `POST /consultations/{id}/integrate?create_new_client=true` - create new client

---

## Future Enhancements (Optional)

### Phase 13: Advanced Dashboard Features
- [ ] Real-time consultation updates (WebSocket)
- [ ] File preview/thumbnail display
- [ ] Export data (CSV, PDF)
- [ ] Bulk status updates
- [ ] Consultation statistics dashboard
- [ ] Advanced filtering (date range, multi-status)
- [ ] Timeline view of consultation lifecycle
- [ ] Comment/note system for collaboration

### Phase 14: Monitoring & Observability
- [ ] Email processing metrics (success rate, latency)
- [ ] IMAP connection health monitoring
- [ ] Database query performance tracking
- [ ] Alert system for processing failures
- [ ] Audit logs for compliance
- [ ] Consultation statistics (by status, submitter, source, etc.)
- [ ] Scorimmo lead forwarding metrics
- [ ] ERP integration success rate dashboard

### Phase 15: Integration Enhancements
- [ ] VetoPartner ERP document upload after integration
- [ ] Status webhooks back to verso-consultation-plugin
- [ ] Automatic file cleanup (30-day retention policy)
- [ ] Batch email processing optimization
- [ ] Support for multiple IMAP mailboxes
- [ ] Scorimmo lead status synchronization (bidirectional)
- [ ] ERP consultation status feedback to dashboard

### Phase 16: Quality & Performance
- [ ] Database query indexing optimization
- [ ] IMAP connection pooling
- [ ] Email attachment size limits & compression
- [ ] Automated backups with retention policy
- [ ] Performance benchmarking & optimization
- [ ] Load testing for concurrent email/webhook processing

## Architecture Notes

### Email-Based Processing (Web Consultations)
```
verso-vet.com (WordPress)
  ↓ (form submission)
Email to consultations@verso-vet.com (with JSON + attachments)
  ↓ (IMAP polling every 60s)
consultation-requests /cron endpoint
  ↓ (IMAP monitor)
Parse JSON + download attachments + ClamAV scan
  ↓ (REST API)
Store in SQLite with source='web'
  ↓ (REST API)
GET /consultations (list/filter by source)
GET /dashboard (unified web interface)
```

### Scorimmo Lead Processing (Call Center)
```
scorimmo-relay webhook receiver (port 8110)
  ↓ (new_lead event)
Handle webhook + store in local DB
  ↓ (fire-and-forget async)
forward_lead_to_consultation_requests()
  ↓ (HTTP POST)
consultation-requests (port 8092)
  ↓
POST /consultations/from-scorimmo
  ↓
Map fields + store in SQLite with source='scorimmo'
  ↓ (REST API)
GET /consultations (unified list with source filtering)
GET /dashboard (shows both Web 🔵 and Scorimmo 🟠 badges)
```

### Unified Data Model
```
SQLite consultations table:
- uuid (primary key)
- source ('web' or 'scorimmo')
- submitter_type (e.g., 'scorimmo', 'web')
- status (pending, integrated, deleted, etc.)
- data_json (flat structure with owner_*, animal_*, scorimmo_* fields)
- files_local (JSON array of locally stored files)
- created_at, updated_at, deleted_at
```

### Production Endpoints
```
Health: GET http://10.0.0.44:8092/health
IMAP Monitor: GET http://10.0.0.44:8092/cron (triggered by scheduler)
Cache Refresh: POST http://10.0.0.44:8092/refresh-db
API Base: http://10.0.0.44:8092/consultations
Dashboard: http://10.0.0.44:8092/dashboard
```

### Secrets in Vault ✅
- `imap_host` - IMAP server hostname
- `imap_username` - IMAP login
- `imap_password` - IMAP password
- `verso_webhook_email` - Mailbox to monitor (fallback: consultations@verso-vet.com)
- `consultation_file_secret` - HMAC secret for file downloads

### Database
- **Type**: SQLite (async-safe with ThreadPoolExecutor)
- **Location**: `/opt/onyx/data/consultation-requests/data/consultations.db`
- **Schema**: consultations table with uuid, status, data_json, etc.
- **Connection**: Global cache with refresh endpoint

### Monitoring
- **IMAP Check**: Every 60 seconds via /cron endpoint
- **Health Check**: GET /health returns service status
- **Cron Tasks**: Defined in cron.json

---

## Production Status ✅

The skill is **fully operational** with IMAP-based email monitoring:
- ✅ Email monitoring (IMAP)
- ✅ JSON attachment extraction
- ✅ SQLite database storage & retrieval
- ✅ REST API endpoints (list, filter, detail)
- ✅ Web dashboard interface
- ✅ Secure file downloads (HMAC tokens)
- ✅ Cache management (/refresh-db)
- ✅ Health monitoring
- ✅ Forge validation (18/18 PASS)
- ✅ Production deployment (v1.0.18)

**Ready for production use with verso-consultation-plugin.**
