# Consultation Requests - API Reference

> **Status**: 🟢 **PRODUCTION** | Version 1.0.18 | Architecture: IMAP-based

## Overview

**Email-based architecture**: verso-consultation-plugin sends emails to `consultations@verso-vet.com` → IMAP monitor fetches and parses → SQLite storage → REST API + Dashboard.

No webhook required. Service automatically monitors the mailbox every 60 seconds via `/cron` endpoint.

## Base URL

```
http://10.0.0.44:8092
```

## Health & Status

### GET /health

Health check endpoint.

```bash
curl http://10.0.0.44:8092/health
```

**Response**:

```json
{
  "status": "ok",
  "service": "consultation-requests",
  "version": "2.0.0",
  "timestamp": "2026-05-05T07:30:00.000000+00:00"
}
```

---

## Consultation Endpoints

### GET /consultations

List all consultation requests with optional filtering.

**Query parameters**:

- `status` (optional): Filter by status
  - `pending` - Newly received from email
  - `reviewed` - User has reviewed
  - `integrated` - Integrated into external system
  - `archived` - Closed/archived
- `limit` (optional, default 100, max 500): Number of results
- `offset` (optional, default 0): Pagination offset

**Example**:

```bash
curl "http://10.0.0.44:8092/consultations"
curl "http://10.0.0.44:8092/consultations?status=pending&limit=50&offset=0"
```

**Response**:

```json
{
  "count": 3,
  "limit": 100,
  "offset": 0,
  "consultations": [
    {
      "id": 1,
      "uuid": "verso-1715234567-a1b2c3d4",
      "submitted_at": "2026-05-08T14:30:00+00:00",
      "status": "pending",
      "submitter_type": "owner",
      "data_json": "{\"uuid\": \"verso-...\", \"owner_nom\": \"Dupont\", ...}",
      "files_local": null,
      "erp_client_id": null,
      "erp_animal_id": null,
      "erp_consult_id": null,
      "integrated_at": null,
      "notes": null
    }
  ]
}
```

### GET /consultations/{id}

Get consultation request details by ID.

**Example**:

```bash
curl http://10.0.0.44:8092/consultations/1
```

**Response**:

```json
{
  "id": 1,
  "uuid": "verso-1715234567-a1b2c3d4",
  "submitted_at": "2026-05-08T14:30:00+00:00",
  "status": "pending",
  "submitter_type": "owner",
  "data_json": "{\"uuid\": \"verso-1715234567-a1b2c3d4\", \"submitted_at\": \"2026-05-08T14:30:00+00:00\", \"owner_nom\": \"Dupont\", \"owner_prenom\": \"Jean\", \"owner_email\": \"jean@example.com\", \"owner_telephone\": \"+33612345678\", \"owner_address\": \"123 Rue de Paris, 75001 Paris\", \"vet_nom\": \"Smith\", \"vet_prenom\": \"Dr\", \"vet_clinique\": \"Clinique Vétérinaire Paris\", \"vet_email\": \"doctor@clinic.fr\", \"vet_telephone\": \"+33145678901\", \"animal_nom\": \"Rex\", \"animal_espece\": \"Chien\", \"animal_race\": \"Labrador\", \"motif\": \"Boiterie antérieure droite\"}",
  "files_local": null,
  "erp_client_id": null,
  "erp_animal_id": null,
  "erp_consult_id": null,
  "integrated_at": null,
  "notes": null
}
```

---

## System Endpoints

### GET /health

Health check endpoint with service status.

**Example**:

```bash
curl http://10.0.0.44:8092/health
```

**Response**:

```json
{
  "status": "ok",
  "service": "consultation-requests",
  "version": "1.0.18",
  "timestamp": "2026-05-08T22:30:00+00:00"
}
```

### GET /cron

Periodic task endpoint. Called by the Onyx scheduler every 60 seconds.

Triggers IMAP monitoring to fetch new consultation emails.

**Example**:

```bash
curl http://10.0.0.44:8092/cron
```

**Response**:

```json
{
  "status": "cron_executed"
}
```

### POST /refresh-db

Refresh the database connection cache. Useful when the database file has been modified externally and the skill's cached connection is stale.

**Example**:

```bash
curl -X POST http://10.0.0.44:8092/refresh-db
```

**Response**:

```json
{
  "status": "success",
  "message": "Database connection reset and will reconnect on next query"
}
```

---

## Dashboard

### GET /dashboard

Web dashboard interface for viewing and managing consultations.

**Example**:

```bash
open http://10.0.0.44:8092/dashboard
```

Returns HTML page with:
- List of all consultations
- Filter by status
- View consultation details
- Download attachments (if any)

---

## Typical Workflow

```bash
# 1. Service automatically monitors emails every 60 seconds
#    (via /cron endpoint called by scheduler)

# 2. Check current consultations
curl "http://10.0.0.44:8092/consultations"

# 3. Get details of a specific consultation
curl http://10.0.0.44:8092/consultations/1

# 4. View in dashboard
open http://10.0.0.44:8092/dashboard

# 5. If dashboard shows stale data, refresh connection
curl -X POST http://10.0.0.44:8092/refresh-db

# 6. Query again to see fresh data
curl http://10.0.0.44:8092/consultations
```

---

## Email Monitoring (Automatic)

The service automatically monitors `consultations@verso-vet.com` inbox every 60 seconds via the `/cron` endpoint.

### Flow:

1. ✅ **Scheduler calls /cron** every 60 seconds
2. ✅ **IMAP connects** to consultations@verso-vet.com (credentials from Vault)
3. ✅ **Search for emails** with subject containing "[Verso Vet] Demande"
4. ✅ **Extract JSON attachment** (consultation.json) from each email
5. ✅ **Parse JSON data** with consultation details
6. ✅ **Store in SQLite** database with status='pending'
7. ✅ **Mark email as read** in IMAP

### No configuration needed

Just have verso-consultation-plugin send emails to `consultations@verso-vet.com` with JSON attachment.

---

## Consultation Data Format

Emails from verso-consultation-plugin contain a JSON attachment with this structure:

```json
{
  "uuid": "verso-1715234567-a1b2c3d4",
  "submitted_at": "2026-05-08T14:30:00+00:00",
  "owner_nom": "Dupont",
  "owner_prenom": "Jean",
  "owner_email": "jean@example.com",
  "owner_telephone": "+33612345678",
  "owner_address": "123 Rue de Paris, 75001 Paris",
  "vet_nom": "Smith",
  "vet_prenom": "Dr",
  "vet_clinique": "Clinique Vétérinaire Paris",
  "vet_email": "doctor@clinic.fr",
  "vet_telephone": "+33145678901",
  "animal_nom": "Rex",
  "animal_espece": "Chien",
  "animal_race": "Labrador",
  "motif": "Boiterie antérieure droite"
}
```

---

## Error Responses

### 404 Not Found

```json
{
  "detail": "Consultation not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error message"
}
```

---

## Database Schema

Consultations are stored in SQLite with this schema:

```sql
CREATE TABLE consultations (
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
```

**Fields**:
- `uuid` - Unique identifier from email
- `submitted_at` - ISO format submission timestamp
- `status` - Current status (pending, reviewed, integrated, archived)
- `submitter_type` - Type of submitter (owner, vet)
- `data_json` - Complete JSON consultation data
- `files_local` - JSON list of local file paths (if any)
- `erp_*_id` - External system IDs after integration
- `integrated_at` - Integration timestamp
- `notes` - Manual notes

---

## Security

- ✅ **IMAP credentials** stored in Onyx Vault (not in code)
- ✅ **File downloads** protected by HMAC-SHA256 token validation
- ✅ **Path traversal** protection with realpath() validation
- ✅ **Database** local SQLite with proper file permissions
- ✅ **All operations** logged with consultation UUID
