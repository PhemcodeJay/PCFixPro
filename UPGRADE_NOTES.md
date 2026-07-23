# PCFixPro v2.0 Upgrade Notes

## Major Changes from v1.0

### 1. Database Migration (SQLite → PostgreSQL)

**Old:** In-memory dictionaries (data lost on restart)  
**New:** Persistent PostgreSQL database

**Connection String:**
```
postgresql://neondb_owner:npg_iX2Nku1PgDqr@ep-old-pond-ay0oecd8-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

### 2. User Authentication Required

**Old:** Dashboard publicly accessible  
**New:** Login required for all dashboard routes

**Default Credentials:**
- Username: `admin`
- Password: `change-this-password` (CHANGE ON FIRST LOGIN)

**New Files:**
- `config.py` - Configuration management
- `models.py` - Database models (User, Agent, Session, Payment, Log, AuditLog)
- `templates/login.html` - Login page

### 3. Security Improvements

**Implemented:**
- Password hashing with pbkdf2:sha256
- Session tokens with expiration
- Rate limiting per IP
- Audit logs for all actions
- Encrypted password storage for sessions
- CORS restricted to specific domains
- No mock payment fallback (real Solana verification only)

### 4. Logging & Monitoring

**New Features:**
- Application logs stored in database (`logs` table)
- Audit trail (`audit_logs` table)
- Action logging for all operations
- Error tracking with IP addresses

**Log Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL

### 5. Front-End Updates

**Removed:**
- Hardcoded demo metrics (42 sessions, 99.9% uptime, etc.)
- Simulated terminal commands (ls, pwd, whoami)
- Dummy data from landing page

**Added:**
- Real-time data from database
- File Explorer button on client PC
- Agent status indicators (online/offline)
- SSH/RDP/VNC protocol selection

### 6. API Changes

**Added Authentication:**
All `/api/*` endpoints now require `@login_required`

**Removed Endpoints:**
- None (all v1.0 endpoints preserved)

**New Response Fields:**
```json
{
  "agents": [{
    "agent_id": "...",
    "hostname": "...",
    "ip_address": "...",
    "os": "...",
    "status": "online|offline",
    "last_seen": "ISO timestamp",
    "customer_id": "...",
    "assigned_ip": "...",
    "session_status": "...",
    "active_connections": 0
  }]
}
```

---

## Installation Steps

### 1. Install New Dependencies

```bash
pip install -r requirements_production.txt
```

**New Packages:**
- `psycopg2-binary==2.9.9` (PostgreSQL driver)
- `SQLAlchemy==2.0.23` (ORM)
- `Flask-Login==0.6.2` (authentication)
- `Flask-SQLAlchemy==3.1.1` (Flask integration)
- `cryptography==41.0.7` (password hashing)

### 2. Database Setup

The app auto-creates tables on first run:

```bash
python app.py
```

**Tables Created:**
- `users` - Admin users
- `agents` - Connected client agents
- `sessions` - RDP/SSH sessions
- `payments` - Payment records
- `customer_sessions` - Customer plan assignments
- `session_tokens` - Download tokens
- `files` - Agent file tracking
- `logs` - Application logs
- `audit_logs` - Security audit trail

### 3. First Login

1. Visit `/login` (or `/dashboard` - auto-redirects)
2. Login with: `admin` / `change-this-password`
3. **Immediately change password** (via database or admin panel)

### 4. Configuration

**Environment Variables (set in cPanel or .env):**

```bash
# Required
SECRET_KEY=generate-with-python-secrets.token_hex(24)
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://yourdomain.com

# Optional
LOG_LEVEL=INFO
RECIPIENT_WALLET=your-solana-wallet
SOLANA_RPC=https://api.mainnet-beta.solana.com
```

**Generate SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(24))"
```

### 5. Create Admin User (Manual)

If auto-creation fails:

```python
from app import app
from models import db, User

with app.app_context():
    admin = User(username='admin', email='admin@yourdomain.com', role='admin')
    admin.set_password('your-secure-password')
    db.session.add(admin)
    db.session.commit()
```

---

## File Changes

**New Files:**
- `config.py` - Centralized configuration
- `models.py` - SQLAlchemy models
- `requirements_production.txt` - Updated dependencies
- `templates/login.html` - Login page
- `UPGRADE_NOTES.md` - This file

**Modified Files:**
- `app.py` - Complete rewrite with database + auth
- `index.html` - Removed hardcoded metrics
- `templates/dashboard.html` - Updated agent list, added File Explorer button
- `static/js/dashboard.js` - Removed simulated commands, added openFileExplorer()

---

## Breaking Changes

### 1. Password Storage

**Old:** Plaintext in memory  
**New:** Encrypted in database

**Migration:** Not applicable (fresh database)

### 2. Agent IDs

**Old:** `agent_1`, `agent_2` (sequential)  
**New:** `agent_{timestamp}` (based on registration time)

Example: `agent_1706851200`

### 3. Session Storage

**Old:** In-memory dict, lost on restart  
**New:** Database-backed, persists across restarts

### 4. Payment Verification

**Old:** Mock fallback allowed  
**New:** Strict Solana verification only

**If Solana fails:** Returns 400 error, no downloads

### 5. CORS

**Old:** `cors_allowed_origins="*"`  
**New:** Restricted to `CORS_ORIGINS` config

**Update for your domain:**
```python
# config.py
CORS_ORIGINS = ['https://yourdomain.com', 'https://www.yourdomain.com']
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Backup existing data (if any)
- [ ] Export PostgreSQL database from Neon
- [ ] Note down current admin credentials
- [ ] Update `config.py` with production values
- [ ] Generate secure `SECRET_KEY`
- [ ] Update `CORS_ORIGINS` with actual domain

### Deployment
- [ ] Upload new files to Namecheap
- [ ] Install `requirements_production.txt`
- [ ] Run `python app.py` (auto-creates tables)
- [ ] Verify database connection
- [ ] Test login with default credentials
- [ ] Change default admin password
- [ ] Test payment flow
- [ ] Test agent connection
- [ ] Check logs for errors

### Post-Deployment
- [ ] Monitor `logs/app.log`
- [ ] Check `audit_logs` table for suspicious activity
- [ ] Verify SSL certificate active
- [ ] Test all agent features (files, processes, screenshots)
- [ ] Update .htaccess with production CORS

---

## Troubleshooting

### Database Connection Failed

**Error:** `could not connect to server`  
**Fix:** Check `DATABASE_URL` in config.py

### Login Not Working

**Error:** `Invalid username or password`  
**Fix:**
1. Check `users` table exists
2. Verify password hash generated
3. Check `is_active=True`

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'psycopg2'`  
**Fix:**
```bash
pip install psycopg2-binary
```

### CORS Errors

**Error:** `Access-Control-Allow-Origin`  
**Fix:** Update `CORS_ORIGINS` in config.py

---

## Support

- GitHub: https://github.com/PhemcodeJay/PCFixPro/issues
- Documentation: See `NAMECHEAP_CPANEL_DEPLOY.md`

---

**Version:** 2.0  
**Release Date:** 2024-01-01  
**Compatibility:** PostgreSQL 12+, Python 3.8+