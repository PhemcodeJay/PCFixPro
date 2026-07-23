# PCFixPro Deployment on Namecheap cPanel

## Prerequisites

- Namecheap hosting account with cPanel access
- Python 3.8+ supported on your hosting plan
- Domain pointed to Namecheap nameservers
- SSH access enabled (optional but recommended)

---

## Step 1: Pre-Deployment Preparation (Local)

### 1.1 Update app.py for Production

Create a production configuration file `production_config.py`:

```python
import os

class ProductionConfig:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-production-secret-key-here'
    
    # For Namecheap, typically run on the assigned port
    HOST = '0.0.0.0'
    PORT = 5000
    
    # File paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
    
    # Ensure directories exist
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'ssh_keys'), exist_ok=True)
```

### 1.2 Create Passenger WSGI Entry Point

Create `passenger_wsgi.py` in your project root (required for Namecheap Passenger):

```python
import sys
import os

# Add your project directory to Python path
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Import your Flask app
from app import app as application

# Namecheap Passenger looks for 'application' variable
```

### 1.3 Create .htaccess for Static File Handling

Create `.htaccess` in your project root:

```apache
# Enable Passenger Python
PassengerPython /home/username/python_virtualenv/bin/python

# Handle static files directly
<IfModule mod_rewrite.c>
    RewriteEngine On
    
    # Don't rewrite files that exist
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    
    # Rewrite everything else to passenger
    RewriteRule ^(.*)$ passenger_wsgi.py [QSA,L]
</IfModule>

# Security headers
<IfModule mod_headers.c>
    Header set X-Content-Type-Options nosniff
    Header set X-Frame-Options DENY
    Header set X-XSS-Protection "1; mode=block"
</IfModule>

# Deny access to sensitive files
<FilesMatch "\.(py|pyc|pyo|env|git)$">
    Order Allow,Deny
    Deny from all
</FilesMatch>

# Allow access to downloads
<FilesMatch "\.(zip|pdf)$">
    Order Deny,Allow
    Allow from all
</FilesMatch>
```

### 1.4 Update app.py for Namecheap Compatibility

Add this at the TOP of your `app.py` file (before other imports):

```python
import os
import sys

# Detect if running on Namecheap
IS_NAMECHEAP = os.path.exists('/home/username/public_html') or 'public_html' in os.getcwd()

# Update paths to be relative if on Namecheap
if IS_NAMECHEAP:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
```

### 1.5 Create requirements_production.txt

Optimize dependencies for production:

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

**Note:** Remove Solana dependencies (solana, solders, base58) to keep the deployment lightweight and avoid compilation issues.

---

## Step 2: Namecheap cPanel Setup

### 2.1 Log into cPanel

1. Go to `https://yourdomain.com/cpanel`
2. Enter your cPanel username and password

### 2.2 Set Up Python Application

#### Option A: Using cPanel Python App (Recommended)

1. In cPanel, search for **"Setup Python App"** or **"Application Manager"**
2. Click **"Create Application"**
3. Fill in the details:
   - **Python version:** 3.8, 3.9, or 3.10 (check what's available)
   - **Application root:** `pcfixpro` (or any name you prefer)
   - **Application URL:** `/` (for root) or `/app` (for subdirectory)
   - **Application startup file:** `passenger_wsgi.py`
   - **Application entry point:** `application`

4. Click **"Create"**

#### Option B: Manual Setup via SSH

If SSH access is available:

```bash
# 1. SSH into your Namecheap account
ssh username@yourdomain.com

# 2. Navigate to public_html
cd ~/public_html

# 3. Create virtual environment
python3 -m venv python_virtualenv
source python_virtualenv/bin/activate

# 4. Upgrade pip
pip install --upgrade pip
```

### 2.3 Upload Your Application Files

#### Method 1: Using cPanel File Manager

1. In cPanel, go to **"File Manager"**
2. Navigate to `public_html` (or your application directory)
3. Create a new folder named `pcfixpro` (or use root `public_html`)
4. Upload the following files/folders:

**Required Files:**
- `app.py`
- `passenger_wsgi.py`
- `requirements.txt` (or `requirements_production.txt`)
- `.htaccess`
- `index.html`
- `requirements_production.txt`

**Required Folders:**
- `templates/` (all HTML templates)
- `static/` (all CSS, JS files)
- `client_agent/dist/` (your compiled agent packages)
- `downloads/` (create empty folder for agent downloads)
- `ssh_keys/` (create empty folder - keys will be auto-generated)

**Optional Files:**
- `production_config.py`

#### Method 2: Using Git (if available)

```bash
cd ~/public_html
git clone https://github.com/PhemcodeJay/PCFixPro.git
cd PCFixPro
```

### 2.4 Install Dependencies

#### Using cPanel Terminal

1. In cPanel, search for **"Terminal"** or **"SSH Access"**
2. Navigate to your application directory:

```bash
cd ~/public_html/pcfixpro
# OR if using root:
cd ~/public_html
```

3. Activate virtual environment (if created manually):

```bash
source ~/python_virtualenv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements_production.txt
```

**OR install individually (if pip install fails):**

```bash
pip install Flask==2.3.3
pip install flask-socketio==5.3.5
pip install python-socketio==5.11.0
pip install python-dotenv==1.0.0
pip install paramiko==3.3.1
pip install eventlet==0.33.3
pip install reportlab==4.1.0
pip install gunicorn==21.2.0
pip install gevent==23.9.1
```

#### Using cPanel Python App Interface

If using the cPanel Python App:

1. In the app settings page, click **"Run Pip Install"**
2. Upload your `requirements.txt` to the app directory
3. Run: `pip install -r requirements.txt`

### 2.5 Configure Application Settings

1. In cPanel Python App settings:
   - **Python version:** Select 3.8 or 3.9 (recommended for best compatibility)
   - **Application startup file:** `passenger_wsgi.py`
   - **Application entry point:** `application`
   
2. Set environment variables (if needed):
   - Click **"Environment variables"**
   - Add:
     - `SECRET_KEY` = your-secret-key-here
     - `PYTHONPATH` = `/home/username/public_html/pcfixpro`

### 2.6 Restart Application

1. In cPanel Python App settings, click **"Restart"**
2. Or run this in terminal:

```bash
touch ~/public_html/pcfixpro/passenger_wsgi.py
# OR
touch ~/public_html/tmp/restart.txt
```

---

## Step 3: Static Files & Assets

### 3.1 Handle Static Files

Namecheap may not automatically serve static files through Flask. Modify your `.htaccess`:

```apache
# Direct static file access
<Directory "static">
    Options -Indexes +FollowSymLinks
    Require all granted
</Directory>

# If static folder is in public_html
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    
    # Don't rewrite existing files/directories
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    
    # Static files - let Apache serve directly
    RewriteRule ^static/(.*)$ - [L]
    
    # Pass everything else to Passenger
    RewriteRule ^(.*)$ passenger_wsgi.py [QSA,L]
</IfModule>
```

### 3.2 Fix Template Paths

Update your `app.py` to use absolute paths:

```python
# At the top of app.py, add:
import os

# Get absolute path to project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Update template and static folders
app = Flask(__name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
```

---

## Step 4: Enable SSL/HTTPS (Recommended)

### 4.1 Install SSL Certificate

1. In cPanel, search for **"SSL"** or **"Let's Encrypt"**
2. Select your domain
3. Click **"Issue"** for free Let's Encrypt SSL
4. Wait 5-10 minutes for propagation

### 4.2 Force HTTPS

Add to your `.htaccess`:

```apache
# Force HTTPS
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# HTTP Strict Transport Security
Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
```

---

## Step 5: Test Deployment

### 5.1 Access Application

1. Visit: `https://yourdomain.com`
2. Check if landing page loads
3. Try accessing: `https://yourdomain.com/dashboard`

### 5.2 Check Logs

If you encounter errors, check:

1. **Application Logs:**
   - cPanel → **"Errors"** or **"Metrics" → "Errors"**
   - Or: `~/pcfixpro/passenger_wsgi.py` output in cPanel Python App

2. **Apache Error Log:**
   - cPanel → **"Metrics" → "Errors"**
   - Or: `/home/username/logs/error_log`

3. **Access Logs:**
   - cPanel → **"Metrics" → "Raw Access Logs"**

### 5.3 Common Issues & Fixes

#### Issue: "500 Internal Server Error"

**Solution:**
```bash
# Check Python version compatibility
python3 --version

# Check if all dependencies installed
pip list

# Verify file permissions
chmod 755 ~/public_html/pcfixpro
chmod 644 ~/public_html/pcfixpro/*.py
chmod 644 ~/public_html/pcfixpro/.htaccess
```

#### Issue: "ModuleNotFoundError"

**Solution:**
```bash
# Activate virtual environment
source ~/python_virtualenv/bin/activate

# Reinstall package
pip install --force-reinstall modulename

# Or use cPanel's pip install interface
```

#### Issue: "Permission Denied"

**Solution:**
```bash
# Fix directory permissions
find ~/public_html/pcfixpro -type d -exec chmod 755 {} \;
find ~/public_html/pcfixpro -type f -exec chmod 644 {} \;

# Ensure writeable directories
chmod 777 ~/public_html/pcfixpro/downloads
chmod 777 ~/public_html/pcfixpro/ssh_keys
```

#### Issue: "Static Files Not Loading"

**Solution:**
```bash
# Check .htaccess exists
ls -la ~/public_html/.htaccess

# Verify mod_rewrite is enabled (should be by default)
# Test by creating test.html in public_html
echo "Test" > ~/public_html/test.html
# Then visit: https://yourdomain.com/test.html
```

---

## Step 6: Production Optimizations

### 6.1 Disable Debug Mode

In `app.py`, wrap startup code:

```python
if __name__ == '__main__':
    # Only run development server locally
    if not os.environ.get('PRODUCTION'):
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

### 6.2 Configure Secret Key

Set in cPanel Environment Variables:

```bash
# Generate a secure key
python3 -c "import secrets; print(secrets.token_hex(24))"

# Copy output and add to cPanel environment:
SECRET_KEY = <generated-key-here>
```

### 6.3 Optimize Database/Sessions

Current implementation uses in-memory storage. For production:

**Option A: Keep In-Memory (Simple)**
- Data resets on app restart
- OK for small deployments
- Add to `production_config.py`:
```python
# Periodic cleanup to prevent memory leaks
import atexit
import gc

def cleanup():
    gc.collect()
    
atexit.register(cleanup)
```

**Option B: Use File-based Sessions**
```bash
pip install Flask-Session
```

Update `app.py`:
```python
from flask_session import Session

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = '/home/username/flask_session'
Session(app)
```

### 6.4 Configure Email Notifications (Optional)

If you want to send payment confirmations:

```bash
pip install Flask-Mail
```

Add to `app.py`:
```python
from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.namecheap.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@yourdomain.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'

mail = Mail(app)
```

---

## Step 7: Deploy Agent Packages

### 7.1 Upload Agent Files

1. Create `downloads/` folder in `public_html`
2. Upload agent packages:
   - `PCFixPro_Agent_Windows.zip`
   - `PCFixPro_Agent_macOS.zip`
   - `PCFixPro_Agent_Universal.zip`

To `public_html/downloads/`

### 7.2 Generate Agent Packages (if needed)

On your local machine:

```bash
cd client_agent

# Windows
python create_embedded_installer.py
python create_sfx.py

# Copy generated files from client_agent/dist/ to your downloads folder
```

### 7.3 Test Download Links

Visit: `https://yourdomain.com/api/verify-payment`

After payment verification, test download links work.

---

## Step 8: Monitoring & Maintenance

### 8.1 Set Up Log Rotation

Create `logrotate.conf` (if you have SSH access):

```bash
# /home/username/logrotate.conf
/home/username/public_html/pcfixpro/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

Add to cron:
```bash
0 0 * * * /usr/sbin/logrotate /home/username/logrotate.conf
```

### 8.2 Monitor Application Health

Create `health_check.py`:

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'PCFixPro',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Visit: `https://yourdomain.com/health`

### 8.3 Backup Strategy

```bash
# Create backup script
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf ~/backups/pcfixpro_$DATE.tar.gz ~/public_html/pcfixpro

# Keep only last 7 backups
find ~/backups -name "pcfixpro_*.tar.gz" -mtime +7 -delete
```

Add to cron (daily at 2 AM):
```bash
0 2 * * * /home/username/backup.sh
```

---

## Step 9: Security Hardening

### 9.1 Restrict Admin Access

Add to `.htaccess`:

```apache
# Password protect admin routes
<Files "dashboard.html">
    AuthType Basic
    AuthName "Admin Access"
    AuthUserFile /home/username/.htpasswd
    Require valid-user
</Files>
```

Create `.htpasswd`:
```bash
htpasswd -c /home/username/.htpasswd admin
```

### 9.2 Rate Limiting

Already implemented in `app.py` (lines 14-34). Adjust limits:

```python
def rate_limit(max_requests=60, window_seconds=60):
    # Reduce limits for production
    max_requests = 30  # Stricter limit
```

### 9.3 Hide `.git` Directory

Add to `.htaccess`:

```apache
# Block .git directory
RedirectMatch 404 /\.git
```

### 9.4 Disable Directory Listing

Already included in `.htaccess`, but ensure:
```apache
Options -Indexes
```

---

## Step 10: Domain & DNS Configuration

### 10.1 Update Nameservers (if not already)

At Namecheap:
1. Go to **"Domain List"**
2. Select your domain
3. Click **"Manage"** next to Nameservers
4. Set to:
   - `dns1.registrar-servers.com`
   - `dns2.registrar-servers.com`

OR use custom nameservers if you have them.

### 10.2 Wait for Propagation

- DNS propagation: 24-48 hours
- Check status: `https://www.whatsmydns.net`

During propagation, access via IP:
- `http://server-ip/~username/pcfixpro`

---

## Step 11: Final Configuration

### 11.1 Update Landing Page

Update `index.html` with your actual:
- Payment wallet addresses
- Domain URL
- Contact information
- Pricing plans

### 11.2 Configure Payment Settings

In `app.py` (lines 569-615):

```python
# Update payment mode
payment_verified = True  # Enable real Solana verification
# OR keep False for testing
```

Update wallet addresses:
```python
RECIPIENT_WALLET = "your-actual-solana-wallet-address"
```

### 11.3 Test Payment Flow

1. Visit your domain
2. Complete test payment
3. Download agent package
4. Verify token-based access works

---

## Troubleshooting Namecheap-Specific Issues

### Issue: "No module named 'eventlet'"

**Solution:**
```bash
# Some hosts don't support eventlet well
# Use gevent instead
pip uninstall eventlet
pip install gevent
```

Update `passenger_wsgi.py`:
```python
from gevent import monkey
monkey.patch_all()

from app import app as application
```

### Issue: "Application failed to start"

**Solution:**
```bash
# Check Python version in cPanel
# Some hosts only support Python 3.6
# Update app.py to be compatible:

import sys
print(f"Python version: {sys.version}")
```

### Issue: "502 Bad Gateway"

**Solution:**
```bash
# Increase timeout in .htaccess
PassengerAppEnv production
PassengerMaxPoolSize 3
PassengerPoolIdleTime 300
```

### Issue: "Module uses incompatible Python version"

**Solution:**
```bash
# Downgrade packages or upgrade Python
# Check available Python versions:
python3.8 --version
python3.9 --version

# Reinstall with specific version:
/usr/local/bin/python3.9 -m pip install -r requirements.txt
```

---

## Alternative: Use cPanel's Built-in Python App

If you prefer cPanel's Application Manager:

1. **Create App:**
   - cPanel → **"Setup Python App"**
   - Python 3.9
   - App directory: `pcfixpro`
   - Startup file: `passenger_wsgi.py`
   - Entry point: `application`

2. **Upload files** via File Manager to the app directory

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Restart app** from cPanel interface

---

## Post-Deployment Checklist

- [ ] Application loads at `https://yourdomain.com`
- [ ] Dashboard accessible at `/dashboard`
- [ ] Static files (CSS/JS) loading correctly
- [ ] Downloads folder accessible
- [ ] SSL certificate installed and working
- [ ] HTTPS redirect working
- [ ] Admin dashboard password protected (optional)
- [ ] Error logs checked (no 500 errors)
- [ ] Payment verification tested
- [ ] Agent download links working
- [ ] Backup script running (if configured)
- [ ] Health check endpoint responding

---

## Support & Resources

- **Namecheap Documentation:** https://www.namecheap.com/support/python/
- **Passenger Docs:** https://www.phusionpassenger.com/docs/
- **Flask Deployment:** https://flask.palletsprojects.com/en/2.3.x/deploying/

**Common Namecheap Paths:**
- Home directory: `/home/username`
- Public HTML: `/home/username/public_html`
- Python virtualenv: `/home/username/python_virtualenv`
- Error logs: `/home/username/logs/error_log`
- Access logs: `/home/username/logs/access_log`

---

## Quick Reference Commands

```bash
# SSH into Namecheap
ssh username@yourdomain.com

# Navigate to app
cd ~/public_html/pcfixpro

# Activate virtualenv
source ~/python_virtualenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Restart app
touch passenger_wsgi.py

# Check logs
tail -f ~/logs/error_log

# Check Python version
python3 --version

# Test app locally
python3 passenger_wsgi.py
```

---

**Deployment Time Estimate:** 30-60 minutes  
**Testing Time:** 15-30 minutes  
**Total Estimated Time:** 1-2 hours