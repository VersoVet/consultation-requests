# Consultation Requests - API Reference

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

### GET /dashboard
Dashboard HTML interface for managing consultation requests.
```bash
curl http://10.0.0.44:8092/dashboard
```

## Consultation Endpoints

### POST /consultations/submit
Receive a consultation request from WordPress (webhook).

**Authentication**: HMAC-SHA256 signature in header `X-Verso-Signature` (requires `consultation_webhook_secret` from Vault)

**Request body**:
```json
{
  "uuid": "consult_65f4c2b1234567",
  "submitter_type": "vet",
  "vet": {
    "nom": "Dupont",
    "prenom": "Jean",
    "clinique": "Clinique Vétérinaire des Alpes",
    "email": "jean.dupont@clinique.fr",
    "telephone": "04.XX.XX.XX.XX",
    "adresse": "123 rue de la Paix, 73000 Chambéry"
  },
  "owner": {
    "nom": "Martin",
    "prenom": "Marie",
    "email": "marie@example.com",
    "telephone": "06.XX.XX.XX.XX"
  },
  "animal": {
    "nom": "Rex",
    "espece": "Chien",
    "race": "Labrador",
    "sexe": "M",
    "date_naissance": "2020-03-15",
    "puce": "250123456789012",
    "poids": 35.5
  },
  "motif": "Boiterie antérieure droite depuis 3 semaines",
  "specialite": "imagerie",
  "urgence": false,
  "traitements_en_cours": "Amoxicilline 500mg x2/jour",
  "fichiers": [
    "https://verso-vet.com/wp-content/uploads/consultations/consult_65f4c2b1234567/radiographie.jpg"
  ]
}
```

**Response**:
```json
{
  "success": true,
  "id": 1,
  "uuid": "consult_65f4c2b1234567",
  "status": "pending"
}
```

### GET /consultations
List all consultation requests with optional filtering.

**Query parameters**:
- `status` (optional): Filter by status - `pending`, `received`, `integrated`, `rejected`
- `limit` (optional, default 100, max 500): Number of results
- `offset` (optional, default 0): Pagination offset

**Example**:
```bash
curl "http://10.0.0.44:8092/consultations?status=pending&limit=50"
```

**Response**:
```json
{
  "count": 3,
  "limit": 50,
  "offset": 0,
  "status_filter": "pending",
  "consultations": [
    {
      "id": 1,
      "uuid": "consult_65f4c2b1234567",
      "status": "pending",
      "submitted_at": "2026-05-04T10:30:45.123456+00:00",
      "submitter_type": "vet",
      "data_json": "{...}",
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

**Response**: Full consultation object (see GET /consultations response)

### PATCH /consultations/{id}/status
Update consultation status.

**Request body**:
```json
{
  "status": "received"
}
```

**Valid statuses**: `pending`, `received`, `integrated`, `rejected`

**Example**:
```bash
curl -X PATCH http://10.0.0.44:8092/consultations/1/status \
  -H "Content-Type: application/json" \
  -d '{"status":"received"}'
```

### PATCH /consultations/{id}/integrate
Integrate consultation into VetoPartner ERP.

Will:
1. Search for or create client in VetoPartner
2. Search for or create animal in VetoPartner
3. Create consultation in VetoPartner
4. Upload documents to VetoPartner

**Request body** (optional):
```json
{
  "erp_client_id": null,
  "erp_animal_id": null
}
```

**Example**:
```bash
curl -X PATCH http://10.0.0.44:8092/consultations/1/integrate \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response**:
```json
{
  "success": true,
  "id": 1,
  "message": "Integration scheduled",
  "erp_client_id": 12345,
  "erp_animal_id": 54321
}
```

### GET /files/{uuid}/{filename}
Download consultation document (secure token-based access).

**Query parameters**:
- `token` (required): HMAC-SHA256 token (valid for 7 days)

**Example**:
```bash
curl "http://10.0.0.44:8092/files/consult_65f4c2b1234567/radiographie.jpg?token=xxx"
```

**Response**: File download (with appropriate Content-Type)

---

## Integration with VetoPartner

When integrating a consultation into VetoPartner (via `PATCH /consultations/{id}/integrate`):

### 1. Client Search
```
GET http://10.0.0.44:8101/clients?search={owner_name}
```

### 2. Create Client (if not found)
```
POST http://10.0.0.44:8101/clients
```

### 3. Animal Search
```
GET http://10.0.0.44:8101/animals?client_id={id}&search={animal_name}
```

### 4. Create Animal (if not found)
```
POST http://10.0.0.44:8101/animals
```

### 5. Create Consultation
```
POST http://10.0.0.44:8101/consultations
```

### 6. Upload Documents
```
POST http://10.0.0.44:8101/animals/{animal_id}/documents/upload
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
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
  "detail": "Internal server error"
}
```

---

## Workflow Example

```bash
# 1. Submit consultation from WordPress (via webhook)
# POST /consultations/submit

# 2. List pending consultations
curl http://10.0.0.44:8092/consultations?status=pending

# 3. Get details of a consultation
curl http://10.0.0.44:8092/consultations/1

# 4. Integrate into VetoPartner
curl -X PATCH http://10.0.0.44:8092/consultations/1/integrate -H "Content-Type: application/json" -d '{}'

# 5. Verify integration
curl http://10.0.0.44:8092/consultations/1
```
