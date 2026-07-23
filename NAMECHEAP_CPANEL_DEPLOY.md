# PCFixPro - Namecheap cPanel Deployment Checklist

Quick deployment guide for deploying PCFixPro on Namecheap hosting with cPanel.

---

## Prerequisites

- Namecheap hosting account with Python support (3.8+)
- Domain pointed to Namecheap nameservers
- cPanel access credentials
- SSH access (optional but helpful)

---

## Phase 1: Local Preparation

### Files to Upload

**Root directory files:**
- `app.py`
- `passenger_wsgi.py`
- `.htaccess`
- `index.html`
- `requirements.txt`

**Folders:**
- `templates/` (all HTML templates)
- `static/` (CSS/JS files)
- `client_agent/dist/` (agent ZIP packages)
- `downloads/` (empty folder - for agent downloads)
- `ssh_keys/` (empty folder - auto-generated on first run)

**Create locally before upload:**

```python
# passenger_wsgi.py
import sys
import os

project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from app import app as application
```

```apache
# .htaccess
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    
    RewriteRule ^static/(.*)$ - [L]
    RewriteRule ^(.*)$ passenger_wsgi.py [QSA,L]
</IfModule>

# Security
<FilesMatch "\.(py|pyc|pyo|env|git)$">
    Order Allow,Deny
    Deny from all
</FilesMatch>

<FilesMatch "\.(zip|pdf)$">
    Order Deny,Allow
    Allow from all
</FilesMatch>
```

---

## Phase 2: cPanel Python Application Setup

### Option A: Using cPanel App Manager (Recommended)

1. **Log into cPanel:** `https://yourdomain.com/cpanel`

2. **Find Python App:**
   - Search "Setup Python App" or "Application Manager"

3. **Create Application:**
   - **Python version:** Select 3.9 or 3.10
   - **Application root:** `pcfixpro`
   - **Application URL:** `/` (root)
   - **Startup file:** `passenger_wsgi.py`
   - **Entry point:** `application`

4. **Click "Create"**

### Option B: Manual via SSH

```bash
# SSH into Namecheap
ssh username@yourdomain.com

# Navigate to public_html
cd ~/public_html

# Create virtual environment
python3 -m venv python_virtualenv
source python_virtualenv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

---

## Phase 3: Upload Application Files

### Using cPanel File Manager

1. **Open File Manager** in cPanel

2. **Navigate to:** `public_html`

3. **Create folder:** `pcfixpro` (or use root `public_html`)

4. **Upload files:**
   - Upload all files from Phase 1
   - Ensure folders maintain structure:
     ```
     public_html/pcfixpro/
     ├── app.py
     ├── passenger_wsgi.py
     ├── .htaccess
     ├── index.html
     ├── requirements.txt
     ├── templates/
     ├── static/
     ├── client_agent/dist/
     ├── downloads/
     └── ssh_keys/
     ```

---

## Phase 4: Install Dependencies

### Using cPanel Terminal

1. **Open Terminal** in cPanel

2. **Navigate to app directory:**
   ```bash
   cd ~/public_html/pcfixpro
   # OR if using root:
   cd ~/public_html
   ```

3. **Activate virtual environment (if using Option B):**
   ```bash
   source ~/python_virtualenv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **If cPanel Python App (Option A):**
   - Go to app settings
   - Click "Run Pip Install"
   - Upload `requirements.txt`
   - Run: `pip install -r requirements.txt`

**Production requirements.txt (recommended):**
```
Flask==2.3.3
flask-socketio==5.3.5
python-socketio==5.11.0
python-dotenv==1.0.0
paramiko==3.3.1
eventlet==0.33.3
reportlab==4.1.0
gunicorn==21.2.0
gevent==23.9.1
```

**Note:** Remove Solana dependencies (solana, solders, base58) for production to avoid compilation issues.

---

## Phase 5: Configure Application

### 5.1 Set Environment Variables

If using cPanel Python App:
1. Go to app settings
2. Click "Environment variables"
3. Add: `SECRET_KEY` = your-secret-key-here
4. Add: `PYTHONPATH` = `/home/username/public_html/pcfixpro`

### 5.2 Update app.py for Production

Add at TOP of `app.py` (before imports):

```python
import os
import sys

# Detect production environment
IS_NAMECHEAP = os.path.exists('/home') and 'public_html' in os.getcwd()

# Set working directory
if IS_NAMECHEAP:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
```

Update Flask initialization for absolute paths:

```python
# At end of app.py, before routes:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)
```

### 5.3 Fix restart code

Update the bottom of `app.py`:

```python
if __name__ == '__main__':
    # Only run development server locally
    if os.environ.get('PRODUCTION') != 'true':
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
```

---

## Phase 6: Set Permissions

### Using Terminal or File Manager

```bash
# Navigate to app directory
cd ~/public_html/pcfixpro

# Set directory permissions
find . -type d -exec chmod 755 {} \;

# Set file permissions
find . -type f -exec chmod 644 {} \;

# Ensure writeable directories
chmod 777 downloads/
chmod 777 ssh_keys/
```

---

## Phase 7: Restart Application

### Method 1: cPanel Interface

1. Go to Python App settings
2. Click "Restart"

### Method 2: Terminal

```bash
# Touch the WSGI file to trigger restart
touch ~/public_html/pcfixpro/passenger_wsgi.py

# OR create restart file
touch ~/public_html/tmp/restart.txt
```

---

## Phase 8: Enable SSL (Recommended)

### Install SSL Certificate

1. In cPanel, search "SSL" or "Let's Encrypt"
2. Select your domain
3. Click "Issue" for free certificate
4. Wait 5-10 minutes

### Force HTTPS in .htaccess

Add to `.htaccess`:

```apache
# Force HTTPS
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Security headers
Header always set X-Content-Type-Options nosniff
Header always set X-Frame-Options DENY
```

---

## Phase 9: Verification Testing

### Test Checklist

- [ ] **Homepage loads:** Visit `https://yourdomain.com`
  - Should see landing page (index.html)

- [ ] **Dashboard accessible:** Visit `https://yourdomain.com/dashboard`
  - Should load dashboard.html

- [ ] **Static files load:** Check CSS/JS
  - Open browser DevTools → Network tab
  - No 404 errors for static files

- [ ] **Downloads folder accessible:** Visit `https://yourdomain.com/downloads/`
  - Should show directory or download files

- [ ] **API endpoint works:** Visit `https://yourdomain.com/api/sessions`
  - Should return JSON response

- [ ] **SSL certificate valid:** Check padlock icon in browser

### Check Logs

**Application Logs:**
- cPanel → Metrics → Errors
- Or cPanel Python App → View logs

**Apache Error Log:**
- cPanel → Metrics → Errors
- Path: `/home/username/logs/error_log`

**Access Logs:**
- cPanel → Metrics → Raw Access Logs

---

## Phase 10: Optional Configuration

### 10.1 Admin Dashboard Password Protection

Create `.htpasswd` file:
```bash
htpasswd -c /home/username/.htpasswd admin
```

Add to `.htaccess`:
```apache
<Files "dashboard.html">
    AuthType Basic
    AuthName "Admin Access"
    AuthUserFile /home/username/.htpasswd
    Require valid-user
</Files>
```

### 10.2 Install Let's Encrypt Auto-Renewal

Most Namecheap plans auto-renew SSL. Verify in cPanel → SSL → Manage SSL.

### 10.3 Configure Email Notifications (Optional)

```bash
pip install Flask-Mail
```

Add to `app.py` (optional):
```python
app.config['MAIL_SERVER'] = 'smtp.your-email.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@domain.com'
app.config['MAIL_PASSWORD'] = 'your-password'
```

---

## Phase 11: Update Application Content

### 11.1 Update Landing Page

Edit `index.html`:
- Payment wallet addresses
- Domain URL
- Contact info
- Pricing plans

### 11.2 Configure Payment Settings

In `app.py`, update lines 77-79:
```python
SOLANA_RPC = "https://api.mainnet-beta.solana.com"
RECIPIENT_WALLET = "your-actual-wallet-address"
```

Generate secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(24))"
```

Set in cPanel environment: `SECRET_KEY` = generated-key

---

## Common Issues & Quick Fixes

### Issue: "500 Internal Server Error"

**Fix:**
```bash
# Check Python version
python3 --version

# Verify permissions
chmod 755 ~/public_html/pcfixpro
chmod 644 ~/public_html/pcfixpro/*.py

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Issue: "ModuleNotFoundError"

**Fix:**
```bash
# Use cPanel pip install or
source ~/python_virtualenv/bin/activate
pip install modulename
```

### Issue: "Static Files 404"

**Fix:**
1. Verify `.htaccess` exists in root
2. Check static folder permissions
3. Clear browser cache

### Issue: "502 Bad Gateway"

**Fix:**
```bash
# Touch restart file
touch ~/public_html/tmp/restart.txt

# OR in .htaccess:
PassengerAppEnv production
PassengerMaxPoolSize 3
```

### Issue: "eventlet/gevent import errors"

**Fix:**
```bash
# Try gevent instead
pip uninstall eventlet
pip install gevent==23.9.1 gunicorn==21.2.0
```

---

## Post-Deployment Checklist

- [ ] Application loads at `https://yourdomain.com`
- [ ] Dashboard at `/dashboard` works
- [ ] Static files (CSS/JS) load correctly
- [ ] SSL certificate active (https:// in URL)
- [ ] HTTPS redirect working
- [ ] Error logs show no critical errors
- [ ] `api/sessions` endpoint returns JSON
- [ ] Downloads folder accessible
- [ ] Agent packages downloadable (after payment flow)
- [ ] Admin dashboard password protected (if configured)
- [ ] Backup script scheduled (optional)
- [ ] Email notifications configured (optional)

---

## Support Resources

- Namecheap Python Hosting: https://www.namecheap.com/support/python/
- Flask Deployment Guide: https://flask.palletsprojects.com/en/2.3.x/deploying/
- Phusion Passenger Docs: https://www.phusionpassenger.com/docs/

---

## Deployment Timeline

- **Preparation:** 15-20 minutes
- **cPanel Setup:** 5-10 minutes
- **File Upload:** 10-15 minutes
- **Dependency Install:** 10-15 minutes
- **Testing:** 15-20 minutes
- **SSL Setup:** 5-10 minutes

**Total Estimated Time:** 1-2 hours

---

## Contact Information

- Repository: https://github.com/PhemcodeJay/PCFixPro
- Support: https://github.com/PhemcodeJay/PCFixPro/issues

---

**Last Updated:** 2024-01-01  
**Version:** 1.0  
**For:** PCFixPro v1.0+