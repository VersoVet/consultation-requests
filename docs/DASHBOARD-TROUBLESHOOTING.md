# Dashboard Troubleshooting Guide

## Problem: Dashboard Shows 0 Consultations

If consultations are received and processed by the IMAP monitor but don't appear in the dashboard API, this is likely due to **stale database connection cache**.

### Root Cause

The skill maintains a global SQLite connection cache (`_db_conn`) that is initialized when the skill starts. If the database file is modified after the skill has started, the cached connection may not reflect the new data until the connection is reset.

**Timeline:**
1. Skill starts → creates connection to empty/initial database
2. IMAP monitor processes email → writes consultation to database file
3. API queries use cached connection → returns stale/empty data
4. Solution: Reset connection cache

### Solution: Refresh Database Connection

The skill provides an endpoint to reset the database connection cache:

```bash
# Reset the database connection
curl -X POST http://10.0.0.44:8092/refresh-db

# Expected response:
{
  "status": "success",
  "message": "Database connection reset and will reconnect on next query"
}
```

Then query the API again:

```bash
# Get consultations (should now show fresh data)
curl http://10.0.0.44:8092/consultations
```

### When to Use This

After running the IMAP monitor manually or waiting for scheduled IMAP sync, if the consultations don't appear:

```bash
# 1. Verify IMAP processed the emails
curl http://10.0.0.44:8092/cron

# 2. Refresh database connection
curl -X POST http://10.0.0.44:8092/refresh-db

# 3. Check dashboard
curl http://10.0.0.44:8092/consultations
```

### Why This Happens

SQLite uses in-memory caching for connections. When:
- The skill process has been running for a while with an established connection
- External processes (like IMAP monitor) write directly to the database file
- The skill's connection cache doesn't immediately reflect those changes

The solution forces a new connection that reads the current state of the file.

### Prevention for Future Deployments

To prevent this issue in future deployments:

1. **Option A**: Deploy the updated consultation-requests skill with the refresh endpoint
   ```bash
   # Deploy new version
   forge deploy consultation-requests
   ```

2. **Option B**: Ensure IMAP monitor runs in the same process/container as the API
   - This way they share the same connection cache

3. **Option C**: Use a database that auto-reconnects (e.g., with connection pooling)
   - Consider migrating from SQLite to PostgreSQL for multi-process scenarios

### Dashboard URL

Once consultations appear in the API, view them in the web dashboard:

```
http://10.0.0.44:8092/dashboard
```

### Manual Testing

Test the complete pipeline locally:

```bash
cd /home/onyx/projects/skills/consultation-requests

# 1. Start a fresh instance of the API (opens data/consultations.db)
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8099 &

# 2. Verify consultations are visible
curl http://localhost:8099/consultations

# 3. Test refresh endpoint
curl -X POST http://localhost:8099/refresh-db
```

### Technical Details

The global connection is defined in `src/core/database.py`:

```python
_db_conn: sqlite3.Connection | None = None

def _get_sync_db() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(str(DATABASE_PATH), ...)
    return _db_conn
```

The refresh endpoint calls:

```python
def reset_db() -> None:
    global _db_conn
    if _db_conn is not None:
        _db_conn.close()
    _db_conn = None
```

Next query will create a new connection and read fresh data.

## Other Potential Issues

### 1. Email Not Being Received by IMAP

```bash
# Check if emails exist in consultations@verso-vet.com inbox
python3 << 'PYEOF'
import imapclient
# Get credentials from Vault and check manually
PYEOF
```

### 2. IMAP Parser Failing

Check the IMAP monitor logs:

```bash
# Run IMAP monitor manually with output
cd /home/onyx/projects/skills/consultation-requests
python3 << 'PYEOF'
import asyncio
from src.core.imap_monitor import monitor_imap
result = asyncio.run(monitor_imap())
print(f"Processed: {len(result)} consultations")
PYEOF
```

### 3. Database Schema Mismatch

Verify the table exists with correct columns:

```bash
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('data/consultations.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(consultations)")
for col in cursor.fetchall():
    print(f"  {col[1]}: {col[2]}")
conn.close()
PYEOF
```

Expected columns: `id, uuid, submitted_at, status, submitter_type, data_json, files_local, erp_client_id, erp_animal_id, erp_consult_id, integrated_at, notes`
