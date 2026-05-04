# TODO - Consultation Requests

## Current Status
**In development** - Étape 2 (structure complète + réception webhook)

## Implemented ✅

### Phase 1: Structure & Foundation
- [x] Create directory structure
- [x] manifest.json (port 8092, target OnyxSoma)
- [x] requirements.txt (FastAPI, uvicorn, httpx, aiosqlite)
- [x] src/config.py (load manifest, constants)
- [x] src/core/vault.py (async secret retrieval)
- [x] src/core/models.py (Pydantic models)
- [x] src/core/database.py (SQLite async CRUD)
- [x] src/core/alerting.py (email via onyx-mailbox)
- [x] src/main.py (FastAPI app + lifespan)
- [x] modules/consultations/router.py (API endpoints)
- [x] modules/dashboard/router.py (dashboard HTML)
- [x] API.md (endpoint documentation)
- [x] ARCHITECTURE.md (system design)

### Phase 2: erp-connector Extensions (Step 1 - COMPLETED)
- [x] AddCreateClientRequest model
- [x] Add CreateAnimalRequest model
- [x] Create VetoPartnerClientWriteMixin
- [x] Add POST /clients endpoint
- [x] Add POST /animals endpoint

## In Progress 🔄

### Phase 3: Core Skill Features

#### Webhook Reception & Storage
- [ ] POST /consultations/submit - full validation + HMAC verification
- [ ] File storage on OnyxSoma (download from WP)
- [ ] Status workflow (pending → received)

#### Email Notifications
- [ ] Build HTML email template
- [ ] Send to consultations@verso-vet.com
- [ ] Include file links with HMAC tokens
- [ ] Link to dashboard

#### File Management
- [ ] GET /files/{uuid}/{filename}?token=X - secure download
- [ ] HMAC token generation (7-day TTL)
- [ ] Cleanup old files (30-day retention)

#### ERP Integration
- [ ] modules/consultations/erp.py - erp-connector API client
- [ ] Search client: GET /clients?search=...
- [ ] Create client: POST /clients
- [ ] Search animal: GET /animals?client_id=...&search=...
- [ ] Create animal: POST /animals
- [ ] Create consultation: POST /consultations
- [ ] Upload documents: POST /animals/{id}/documents/upload

#### Dashboard
- [ ] Full dashboard HTML (Bootstrap + JS)
- [ ] List consultations (paginated, filterable)
- [ ] Search client/animal in VetoPartner
- [ ] One-click integration (PATCH /integrate)
- [ ] Create new client/animal flow
- [ ] Real-time status updates

### Phase 4: Testing & Deployment

#### Validation
- [ ] ruff check (linting)
- [ ] mypy (type checking)
- [ ] pytest (unit tests)

#### Forge Pipeline
- [ ] Validate: `curl -X POST http://10.0.0.13:4080/api/validate/consultation-requests`
- [ ] Review: `curl -X POST http://10.0.0.13:4080/api/review/consultation-requests`
- [ ] Deploy: `curl -X POST http://10.0.0.13:4080/api/deploy/consultation-requests`

#### Vault Secrets
- [ ] Create `consultation_webhook_secret` (32 random chars)
- [ ] Create `consultation_file_secret` (32 random chars)

### Phase 5: WordPress Plugin

#### Form & Upload
- [ ] verso-consultation-plugin.php (main plugin)
- [ ] Adaptive form (vet referrer / owner)
- [ ] File upload (PDF, JPEG, DICOM)
- [ ] Validation (server-side + client-side)

#### Integration
- [ ] wp_mail() to consultations@verso-vet.com
- [ ] webhook POST to consultation-requests/submit
- [ ] HMAC signature generation
- [ ] Confirmation page to user

#### Documentation
- [ ] Plugin installation guide
- [ ] Contact email display

## Not Started ⏳

### Phase 6: Refinements
- [ ] Async email background task
- [ ] Retry logic for failed operations
- [ ] Logging & monitoring
- [ ] Performance optimization

### Phase 7: Advanced Features
- [ ] Bulk integration
- [ ] API key authentication (if required)
- [ ] Webhook signature webhook to WP (status updates)
- [ ] File preview in dashboard
- [ ] Export consultation data (CSV, PDF)

---

## Critical Path

1. ✅ Étape 1: erp-connector (POST /clients, POST /animals)
2. 🔄 Étape 2: skill structure + /submit endpoint + validation
3. [ ] Étape 3: Email notifications + file handling
4. [ ] Étape 4: ERP integration (erp.py)
5. [ ] Étape 5: Dashboard HTML + search + integrate button
6. [ ] Étape 6: WordPress plugin
7. [ ] Étape 7: Testing + validation + deployment
8. [ ] Étape 8: Secrets in Vault + go live

---

## Notes

### Secrets to Create in Vault
```bash
curl -X POST http://10.0.0.44:8050/vault \
  -H "X-Vault-Token: $ONYX_VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "consultation_webhook_secret": "xxxxx32-random-chars",
    "consultation_file_secret": "xxxxx32-random-chars"
  }'
```

### File Storage
- Local: `/opt/onyx/data/consultation-requests/files/{uuid}/`
- OnyxSoma accessible via: `http://10.0.0.44:8092/files/{uuid}/{filename}?token=...`
- Retention: 30 days (configurable)

### WordPress Integration
- Form page: `/demande-consultation/`
- Webhook endpoint: `http://10.0.0.44:8092/consultations/submit`
- Contact email displayed: `consultations@verso-vet.com`

### Testing Commands
```bash
# 1. Test health
curl http://10.0.0.44:8092/health

# 2. Test dashboard
curl http://10.0.0.44:8092/dashboard

# 3. Test list (empty)
curl http://10.0.0.44:8092/consultations

# 4. Test submit (fake)
curl -X POST http://10.0.0.44:8092/consultations/submit \
  -H "Content-Type: application/json" \
  -d '{...}'

# 5. Test erp-connector clients
curl -X POST http://10.0.0.44:8101/clients \
  -H "Content-Type: application/json" \
  -d '{"nom": "Test"}'

# 6. Forge validate
curl -X POST http://10.0.0.13:4080/api/validate/consultation-requests | jq .
```
