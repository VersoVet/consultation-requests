# Consultation Requests - API Reference v2.0

> **Status**: 🟢 **PRODUCTION** | Version 2.0.0 | Architecture: IMAP-based

## Overview

**Simplified architecture**: Emails → IMAP Monitor → Dashboard → Smart Association → ERP Integration

No webhook required. Service automatically monitors `consultations@verso-vet.com` for incoming requests.

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
  - `unmatched` - Awaiting association with ERP animal
  - `matched` - Associated with ERP animal, ready for integration
  - `integrated` - Pushed to VetoPartner
  - `rejected` - Rejected by user
- `limit` (optional, default 100, max 500): Number of results
- `offset` (optional, default 0): Pagination offset

**Example**:

```bash
curl "http://10.0.0.44:8092/consultations?status=unmatched&limit=50"
```

**Response**:

```json
{
  "count": 3,
  "limit": 50,
  "offset": 0,
  "status_filter": "unmatched",
  "consultations": [
    {
      "id": 1,
      "uuid": "email_20260505_001",
      "status": "unmatched",
      "submitted_at": "2026-05-05T06:30:00+00:00",
      "submitter_type": "email",
      "data_json": "{...}",
      "data": {
        "animal_name": "Rex",
        "animal_species": "Chien",
        "owner_name": "Martin Pierre",
        "owner_email": "pierre@example.com",
        "owner_phone": "06.12.34.56.78",
        "motif": "Boiterie antérieure",
        "specialite": "orthopédie",
        "urgence": true
      },
      "erp_animal_id": null,
      "integrated_at": null
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

**Response**: Full consultation object (see GET /consultations response)

---

## Smart Association (ERP Search)

### GET /consultations/{id}/search

Propose animal matches from ERP for a consultation.

Automatically searches ERP based on animal name and owner name from the email.

**Query parameters**:

- `search_query` (optional): Override auto-generated search query

**Example**:

```bash
curl "http://10.0.0.44:8092/consultations/1/search"
```

**Response**:

```json
{
  "consultation_id": 1,
  "search_query": "Rex Martin",
  "email_data": {
    "animal_name": "Rex",
    "owner_name": "Martin Pierre",
    "motif": "Boiterie antérieure"
  },
  "suggestions": [
    {
      "erp_animal_id": 123,
      "animal_name": "Rex",
      "race": "Labrador",
      "owner": "Martin Pierre",
      "species": "Chien",
      "last_visit": "2026-04-15",
      "weight": 32.5
    },
    {
      "erp_animal_id": 124,
      "animal_name": "Bella",
      "race": "Labrador",
      "owner": "Martin Jean",
      "species": "Chien",
      "last_visit": "2026-03-20",
      "weight": 28.0
    }
  ]
}
```

### GET /search

Direct search in ERP without consultation context.

**Query parameters**:

- `q` (required): Search query (animal name or owner name)

**Example**:

```bash
curl "http://10.0.0.44:8092/search?q=Rex"
```

**Response**:

```json
{
  "query": "Rex",
  "count": 2,
  "matches": [
    {
      "erp_animal_id": 123,
      "animal_name": "Rex",
      "race": "Labrador",
      "owner": "Martin Pierre",
      "species": "Chien"
    }
  ]
}
```

---

## Integration Endpoints

### POST /consultations/{id}/integrate

Integrate consultation into VetoPartner ERP.

Two options:
1. **Match existing animal**: Provide `erp_animal_id`
2. **Create new client+animal**: Set `create_new_client=true`

**Query parameters**:

- `erp_animal_id` (optional): Animal ID from ERP search results
- `create_new_client` (optional): If true, create new client and animal in ERP

**Example 1: Match existing animal**:

```bash
curl -X POST "http://10.0.0.44:8092/consultations/1/integrate?erp_animal_id=123"
```

**Example 2: Create new client+animal**:

```bash
curl -X POST "http://10.0.0.44:8092/consultations/1/integrate?create_new_client=true"
```

**Response**:

```json
{
  "success": true,
  "id": 1,
  "erp_consult_id": 5678,
  "message": "Integrated into VetoPartner"
}
```

---

## Workflow Example

```bash
# 1. List unmatched consultations (from emails)
curl "http://10.0.0.44:8092/consultations?status=unmatched"

# 2. Get details of a consultation
curl http://10.0.0.44:8092/consultations/1

# 3. Search for animal matches in ERP
curl "http://10.0.0.44:8092/consultations/1/search"

# 4a. OPTION A: Integrate with existing animal
curl -X POST "http://10.0.0.44:8092/consultations/1/integrate?erp_animal_id=123"

# 4b. OPTION B: Create new client+animal
curl -X POST "http://10.0.0.44:8092/consultations/1/integrate?create_new_client=true"

# 5. Verify integration
curl http://10.0.0.44:8092/consultations/1
# status should now be "integrated"
```

---

## Email Monitoring (Automatic)

The service automatically monitors `consultations@verso-vet.com` inbox every minute.

When an email is received:

1. ✅ Email is parsed for consultation data
2. ✅ Data is stored in SQLite (status=unmatched)
3. ✅ User sees new consultation in dashboard
4. ✅ User searches for matching animals
5. ✅ User selects match or creates new client
6. ✅ Consultation is pushed to VetoPartner with all attachments

**No configuration needed** - just send emails to `consultations@verso-vet.com`

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Either erp_animal_id or create_new_client required"
}
```

### 404 Not Found

```json
{
  "detail": "Consultation not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Integration failed"
}
```

---

## Data Models

### Consultation Status Values

- `unmatched` - Waiting for user to find/create ERP animal
- `matched` - Animal matched with ERP
- `integrated` - Pushed to VetoPartner
- `rejected` - User rejected / manual deletion

### Email Data Extracted

Emails to `consultations@verso-vet.com` should contain (patterns extracted automatically):

```
Animal: [animal name]
Espèce: [species]
Propriétaire: [owner name]
Email: [optional owner email]
Téléphone: [optional phone]
Motif: [consultation reason]
Spécialité: [veterinary specialty]
Urgent: [yes/no]
```

Attachments are automatically collected and will be uploaded to VetoPartner.

---

## Integration with VetoPartner

The `/integrate` endpoint orchestrates:

1. **Search/Create Client**:
   - If `create_new_client=true`: POST /clients
   - Otherwise: Uses existing client from matched animal

2. **Search/Create Animal**:
   - If `create_new_client=true`: POST /animals
   - Otherwise: Uses matched `erp_animal_id`

3. **Create Consultation**:
   - POST /consultations with motif, specialite, urgence

4. **Upload Documents**:
   - POST /animals/{id}/documents/upload for each email attachment

---

## Security Notes

- ✅ No webhook secrets needed
- ✅ No HMAC signatures required
- ✅ IMAP credentials stored securely in Vault
- ✅ Email attachments scanned before upload
- ✅ All operations logged with consultation ID
