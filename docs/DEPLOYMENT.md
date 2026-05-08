# Deployment Guide - Consultation Requests Skill

## Current Status (2026-05-05)

✅ **Code is ready** - All fixes applied and tested locally
⏳ **Service restart pending** - Updated code needs to be deployed to live service

## Recent Changes

### Bug Fixes Applied
Fixed ERP API field name mappings to match erp-connector expectations:

```python
# Fixed in src/modules/consultations/erp.py
- create_animal() now uses "idclient" instead of "client_id"
- create_consultation() now uses "synthese" instead of "motif"
- create_animal() now uses "puce_num" instead of "puce"
```

**Verification**: ✅ All ERP operations tested and working locally

## Deployment Steps

### Option 1: Using Forge CLI (Recommended)

```bash
cd /home/onyx/projects/skills/consultation-requests

# Deploy with automatic version bump
/opt/onyx/forge/forge deploy consultation-requests

# Follow prompts:
# - Choose "2. patch" for version bump (bugfix)
# - Choose "2. fix" for commit type
# - Service will restart automatically
```

### Option 2: Manual Service Restart

On OnyxSoma (10.0.0.44):

```bash
sudo systemctl restart consultation-requests

# Verify restart
sudo systemctl status consultation-requests
curl http://10.0.0.44:8092/health
```

### Option 3: Git Push to Trigger CD/CD

```bash
cd /home/onyx/projects/skills/consultation-requests
git push -u origin dev

# If CI/CD pipeline configured, deployment happens automatically
# Check Forge dashboard for deployment status
```

## Post-Deployment Verification

### 1. Health Check
```bash
curl http://10.0.0.44:8092/health | jq .
# Expected: {"status": "ok"}
```

### 2. Test ERP Integration
```bash
# Trigger integration on a stored consultation
curl -X PATCH http://10.0.0.44:8092/consultations/11/integrate

# Check result (should be status "integrated" not "rejected")
curl http://10.0.0.44:8092/consultations/11 | jq '.status'
```

### 3. Full Workflow Test
```bash
# 1. Check for unprocessed consultations from WordPress
curl http://10.0.0.44:8092/consultations/cron/pull-wordpress | jq .

# 2. List consultations
curl http://10.0.0.44:8092/consultations | jq '.consultations | length'

# 3. Get a consultation detail
curl http://10.0.0.44:8092/consultations/1 | jq '.data'

# 4. Check dashboard access
curl -I http://10.0.0.44:8092/dashboard
```

## What Was Fixed

### Before (Broken)
```python
# create_animal() sent wrong field names
response = await client.post(
    f"{ERP_BASE_URL}/animals",
    json={
        "client_id": 12345,      # ❌ Wrong - ERP expects "idclient"
        "puce": "123456789"      # ❌ Wrong - ERP expects "puce_num"
    }
)
# Result: Pydantic validation error, consultation rejected

# create_consultation() sent wrong field
response = await client.post(
    f"{ERP_BASE_URL}/consultations",
    json={"motif": "..."}        # ❌ Wrong - ERP expects "synthese"
)
# Result: Field required error, integration failed
```

### After (Fixed)
```python
# create_animal() now sends correct field names
response = await client.post(
    f"{ERP_BASE_URL}/animals",
    json={
        "idclient": 12345,       # ✅ Correct
        "puce_num": "123456789"  # ✅ Correct
    }
)

# create_consultation() now sends correct field
response = await client.post(
    f"{ERP_BASE_URL}/consultations",
    json={"synthese": "..."}     # ✅ Correct
)
```

## Testing Results

Local test run (2026-05-05 07:04):
```
✓ Client created: 13635
✓ Animal created: 21852
✓ Consultation created: 113233
✓ All ERP operations successful!
```

## Rollback Plan (if needed)

```bash
cd /home/onyx/projects/skills/consultation-requests

# Revert to previous version
git revert ae16e30  # Commit before the fix

# Redeploy
/opt/onyx/forge/forge deploy consultation-requests
```

## Support

If deployment fails:

1. Check service logs
   ```bash
   sudo journalctl -u consultation-requests -n 50
   ```

2. Verify ERP connector is running
   ```bash
   curl http://10.0.0.44:8101/health
   ```

3. Check manifest.json is valid
   ```bash
   cd /home/onyx/projects/skills/consultation-requests
   jq . manifest.json
   ```

4. Validate the skill
   ```bash
   /opt/onyx/forge/forge validate consultation-requests
   ```

---

**Next Action**: Run the Forge deploy command above to apply the ERP fixes to the live service.
