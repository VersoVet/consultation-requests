# Consultation Requests Skill

FastAPI-based skill for managing consultation requests from verso-vet.com.

## Purpose

Centralizes consultation request processing from multiple sources (WordPress form, email) into a single SQLite database with REST API and web dashboard.

## Features

- **IMAP Monitoring**: Listens for consultation emails from `consultations@verso-vet.com`
- **Data Extraction**: Extracts JSON attachments from emails into structured database
- **REST API**: Endpoints for querying, filtering, and managing consultations
- **Web Dashboard**: Visual interface for tracking consultation status
- **Database Persistence**: SQLite for reliable local storage
- **Connection Refresh**: `/refresh-db` endpoint for cache invalidation

## Architecture

```
verso-vet.com (WordPress form)
    ↓
Email → consultations@verso-vet.com
    ↓
IMAP Monitor (skill /cron)
    ↓
SQLite Database (data/consultations.db)
    ↓
REST API (8092)
    ↓
Dashboard UI
```

## Files

```
consultation-requests/
├── src/
│   ├── main.py                      # FastAPI app + endpoints
│   ├── config.py                    # Configuration
│   ├── models.py                    # Pydantic models
│   ├── core/
│   │   ├── database.py              # SQLite connection management
│   │   ├── imap_monitor.py          # IMAP email monitor
│   │   └── vault.py                 # Secret retrieval
│   └── modules/
│       ├── consultations/           # Consultation module
│       │   ├── service.py           # Business logic
│       │   ├── routes.py            # API endpoints
│       │   ├── security.py          # Token validation
│       │   └── files.py             # File management
│       └── dashboard/               # Dashboard module
│           ├── service.py           # Query logic
│           └── routes.py            # UI endpoints
├── static/                          # Dashboard HTML/CSS/JS
├── data/                            # SQLite database (local)
├── tests/                           # Test suite
├── manifest.json                    # Forge configuration
├── requirements.txt                 # Python dependencies
├── CLAUDE.md                        # Forge guide (auto-generated)
├── API.md                           # REST API documentation
├── ARCHITECTURE.md                  # Code structure details
├── DEPLOYMENT.md                    # Deployment procedures
├── DASHBOARD-TROUBLESHOOTING.md    # Common issues & solutions
├── TODO.md                          # In-progress work
└── README.md                        # This file
```

## Deployment

### Prerequisites

Requires:
- Python 3.12+
- Access to Onyx Vault for email credentials
- OnyxSDK for health status reporting (graceful fallback if unavailable)

### Configuration

The skill is configured via `/opt/onyx/forge` during deployment. No manual configuration needed.

### Deploy

```bash
# Validate
curl -X POST http://10.0.0.13:4080/api/validate/consultation-requests

# Deploy
curl -X POST http://10.0.0.13:4080/api/deploy/consultation-requests
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service status and version.

### Consultations

```bash
# List all consultations
GET /consultations

# List with filters
GET /consultations?status=pending&limit=50&offset=0

# Get single consultation
GET /consultations/{id}
```

### Dashboard

```bash
# Web UI
GET /dashboard

# Redirect home to dashboard
GET /
```

### Maintenance

```bash
# Refresh database connection (use if stale data)
POST /refresh-db

# Cron endpoint (called by scheduler)
GET /cron
```

## Data Flow

### 1. WordPress Form Submission

User submits form on `https://verso-vet.com/demande-de-consultation/`

→ verso-consultation-plugin sends email to `consultations@verso-vet.com`

### 2. IMAP Monitoring

Runs on `/cron` endpoint (called by scheduler every minute):

1. Connects to IMAP server
2. Searches for unread emails with subject "[Verso Vet] Demande"
3. Extracts JSON attachment
4. Stores in SQLite database
5. Marks email as read

### 3. REST API

Serves consultations via JSON endpoints for:
- Integration with other systems
- Dashboard queries
- Bulk operations

### 4. Dashboard

Web interface displays:
- Consultation list (filterable by status)
- Consultation details
- Status history
- File downloads (with token-based security)

## Database Schema

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

**Statuses**: `pending`, `reviewed`, `integrated`, `archived`

## Testing

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8099

# Test endpoints
curl http://localhost:8099/health
curl http://localhost:8099/consultations
```

### Production Testing

```bash
# Check deployment
curl http://10.0.0.44:8092/health

# View consultations
curl http://10.0.0.44:8092/consultations | python3 -m json.tool

# Refresh cache if needed
curl -X POST http://10.0.0.44:8092/refresh-db

# View dashboard
open http://10.0.0.44:8092/dashboard
```

## Troubleshooting

See **[DASHBOARD-TROUBLESHOOTING.md](DASHBOARD-TROUBLESHOOTING.md)** for:
- Dashboard shows 0 consultations (stale cache)
- Email not being received by IMAP
- IMAP parser failing
- Database schema issues

## Integration with verso-consultation-plugin

This skill listens for emails from the verso-consultation-plugin WordPress plugin:

1. Plugin sends email to `consultations@verso-vet.com`
2. Skill IMAP monitor fetches and processes email
3. Consultation data stored and exposed via API
4. Dashboard displays all submissions

## Security

- **File Access**: Token-based HMAC validation
- **Email Credentials**: Stored in Onyx Vault (not in code)
- **Database**: SQLite with proper path validation
- **API**: Unauthenticated (internal network only)

## Support

- **API questions**: See [API.md](API.md)
- **Architecture details**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Common issues**: See [DASHBOARD-TROUBLESHOOTING.md](DASHBOARD-TROUBLESHOOTING.md)
- **Deployment help**: See [DEPLOYMENT.md](DEPLOYMENT.md)
