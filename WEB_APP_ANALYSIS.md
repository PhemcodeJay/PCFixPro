# PCFixPro Web Application Analysis

## Architecture Overview

**Type:** Flask-based Command & Control Dashboard with Socket.IO real-time communication  
**Structure:** Single-page application with multiple views (Dashboard, Session Manager, Agent Manager, Terminal, Security, Settings)  
**Purpose:** Remote PC repair/ICT service platform with payment gateway and agent-based remote access

---

## Front-End Components

### 1. Public Landing Page (`index.html`)
**Size:** 1121 lines  
**Technology:** Static HTML with inline CSS and vanilla JavaScript

#### Key Sections:
- **Hero Section:** Full-screen gradient overlay with background image, primary CTA buttons
- **Trust Bar:** Partner/competitor logos (TeamViewer, AnyDesk, UltraViewer, ScreenConnect, WhatsApp)
- **Command & Control Center:** Live metrics dashboard (hardcoded demo data)
  - Active Sessions (42/100)
  - Network Status (99.9% uptime)
  - Security Monitor
  - Active Alerts
  - Support Queue
  - System Health
- **Services Grid:** 6 service cards (Virus Removal, Software Install, Data Recovery, Network, Security Audits, Performance)
- **Pricing Section:** 3-tier pricing with NOWPayments crypto payment integration
  - Starter: $20/session
  - Pro: $50/session (popular)
  - Enterprise: $100/session
- **Testimonials:** Auto-rotating carousel with 3 testimonials
- **Legal/Privacy:** Privacy Policy, Terms, Advertising/Cookies
- **Contact Form:** Name, email, date picker, message with WhatsApp integration
- **Footer:** 4-column layout with navigation and copyright

#### Interactive Modals:
- **Plan Selection Modal:** 3-column plan selector with hover effects
- **Payment Modal:** Solana USDT payment details with NOWPayments integration
- **Download Modal:** Agent download links (Windows, macOS, Universal) with token authentication
- **Remote Session Modal:** Directs users to WhatsApp for remote connection

#### Payment Flow:
1. User selects plan → Proceeds to payment
2. Payment modal shows Solana USDT wallet address
3. User pays via NOWPayments or direct wallet transfer
4. User enters transaction ID
5. Backend verifies (or falls back to mock)
6. Token-based download links generated

---

### 2. Admin Dashboard (`templates/dashboard.html`)
**Size:** 377 lines  
**Technology:** Flask template with Jinja2, external CSS/JS

#### Structure:
- **Fixed Sidebar (260px):**
  - Logo: Command Center
  - Navigation: Dashboard, Sessions, Agents, Terminal, Security, Settings
  - Status indicator (System Online)

- **Top Bar (70px):**
  - Page title
  - Clock
  - Active session counter
  - New Session button

- **Pages (SPA-style navigation):**
  1. **Dashboard:** 4 metric cards + agents list
  2. **Sessions:** RDP session table with actions
  3. **Agents:** Agent management table with file manager integration
  4. **Terminal:** Embedded terminal emulator
  5. **Security:** Security center status
  6. **Settings:** Configuration form

- **File Manager (conditional):**
  - File browser table with columns: Name, Size, Modified, Type, Actions
  - Toolbar: Upload, Download, Delete, Screenshot, Processes, Registry, Wake-on-LAN
  - Screenshot preview panel

- **Connect Modal:**
  - Form for new RDP/SSH/VNC connection
  - Fields: Client Name, Host/IP, Port, Protocol, Username, Password

#### Design:
- CSS variables for consistent theming
- Dark sidebar, light content area
- Card-based layout with hover effects
- Status badges and indicators
- Responsive: mobile sidebar toggle

---

## Static Assets

### CSS (`static/css/dashboard.css`)
**Size:** 669 lines  
**Features:**
- CSS custom properties (primary, dark, success, warning, danger colors)
- Flexbox/Grid layouts
- Terminal styling with dark theme
- Modal animations (fadeUp)
- File manager table
- Responsive breakpoints: 768px, 480px
- Animations: blink, flashAlert, growBar

**Key Components:**
- Sidebar with fixed positioning
- Sticky top bar
- Dashboard cards with hover lift
- Terminal emulator
- Modal system
- File browser

### JavaScript (`static/js/dashboard.js`)
**Size:** 828 lines  
**Technology:** Vanilla JS with Socket.IO client

#### Features:
- **Real-time Updates:**
  - Socket.IO listeners for server events
  - Heartbeat updates from agents
  - Agent registration notifications

- **Session Management:**
  - Load sessions via REST API (`/api/sessions`)
  - Create/delete sessions
  - Duration calculation
  - Session table rendering

- **Agent Management:**
  - Load agents via REST API (`/api/agents`)
  - Status tracking (online/offline)
  - Agent list rendering with file manager integration

- **Terminal Emulator:**
  - Built-in terminal UI with commands: help, sessions, agents, connect, clear, status, ls, pwd, whoami
  - Command history simulation
  - Real command execution via `/api/execute`
  - Terminal output with color-coded message types

- **File Manager:**
  - Socket.IO-based file operations
  - Upload/download/delete via base64
  - Screenshot capture
  - Process listing and killing
  - Registry reading
  - Wake-on-LAN support

- **Navigation:** SPA-style page switching without reload

---

## Back-End Architecture (`app.py`)

**Size:** 713 lines  
**Framework:** Flask + Flask-SocketIO  
**Storage:** In-memory (dictionaries) - resets on restart

### Core Components:

#### 1. Rate Limiting
```python
rate_limit(max_requests=60, window_seconds=60)
```
Per-IP rate limiting decorator for API protection

#### 2. Security
- `safe_path()` - Path traversal prevention using `os.path.realpath()`
- Filename sanitization with `os.path.basename()`
- Download whitelist (Windows, macOS, Universal ZIPs)

#### 3. Key Storage (In-Memory)
```python
active_sessions = {}      # session_id: {host, port, credentials, start_time}
connected_agents = {}     # agent_id: {hostname, ip, os, status, last_seen}
payments = {}            # tx_id: {customer_id, email, plan, amount, status}
customer_sessions = {}   # customer_id: {agent_id, plan, expires_at}
session_tokens = {}      # token: {customer_id, plan, expires_at}
```

#### 4. API Endpoints

**REST API (HTTP):**
- `POST /api/connect` - Create RDP/SSH session
- `POST /api/disconnect` - End session
- `POST /api/execute` - Execute command on session
- `GET /api/sessions` - List all sessions + agents
- `GET /api/agents` - List connected agents
- `POST /api/agent/<id>/files` - List agent files
- `POST /api/agent/<id>/upload` - Upload file to agent
- `POST /api/agent/<id>/download` - Download file from agent
- `POST /api/agent/<id>/delete` - Delete file on agent
- `POST /api/agent/<id>/screenshot` - Capture screenshot
- `POST /api/verify-payment` - Verify Solana USDT payment
- `GET /downloads/<filename>` - Download agent packages
- `GET /api/ssh/public-key` - Get server SSH public key
- `POST /api/ssh/install` - Install key on agent
- `POST /api/agent/<id>/customer` - Assign agent to customer

**Socket.IO Events:**
- `connect` / `disconnect` - Connection management
- `command` - Send command to session
- `command_result` - Receive command output
- `register_agent` - Agent registration
- `heartbeat` - Real-time agent heartbeat
- `heartbeat_update` - Broadcast heartbeat to dashboard
- `list_files` / `file_list` - File browsing
- `upload_file` / `upload_result` - File upload
- `download_file` / `download_result` - File download
- `delete_file` / `delete_result` - File deletion
- `screenshot` / `screenshot_result` - Screenshot capture
- `execute_command` - Execute command on agent
- `list_processes` / `processes_result` - Process listing
- `kill_process` / `kill_result` - Process termination
- `read_registry` / `registry_result` - Registry read
- `wake_on_lan` / `wol_result` - Wake-on-LAN

#### 5. Payment Integration
- **Solana Blockchain:** Optional real USDT verification
- **Fallback:** Mock verification for testing
- **Dependencies:** `solana`, `solders`, `base58` (optional)
- **Wallet:** `CJJvHNh6FRjx3PK5zCKzwhzC7Hr1vwxxYETb7FaaA1PY`
- **USDT Mint:** `EPjFWdd5AufqSSqeM2qN1xzybapC8G4w45844Nh9D9Jv`

#### 6. SSH Key Generation
- Auto-generates RSA key pair on startup if not exists
- Stored in `ssh_keys/id_rsa` and `ssh_keys/id_rsa.pub`
- Used for passwordless agent communication

---

## Data Flow

### Payment & Download Flow
```
User → Selects Plan → Payment Modal → Pays via Solana/NOWPayments
     → Enters tx_id → Backend verifies (or mocks) → Generates token
     → Shows download links with token → User downloads agent
```

### Agent Connection Flow
```
Agent installs → Connects via WebSocket → Sends register_agent event
    → Server stores in connected_agents → Dashboard detects via REST API
    → Technician clicks "Files" → Socket.IO commands sent to agent
    → Agent executes and returns results → Dashboard displays
```

### Session Management Flow
```
Technician → Opens Connect Modal → Enters RDP/SSH credentials
    → Server creates session in active_sessions → Dashboard polls /api/sessions
    → Technician clicks Execute → Terminal sends command
    → Server executes via Paramiko SSH → Returns output
    → Dashboard displays in terminal
```

---

## Current Limitations

### 1. In-Memory Storage
**Issue:** All data resets on server restart
**Impact:** Session loss, agent disconnection, payment verification reset
**Solution:** Implement Redis, database, or file-based session storage

### 2. No Authentication
**Issue:** Dashboard accessible without login
**Impact:** Anyone with URL can view/manage sessions
**Solution:** Add login system (Flask-Login, OAuth, or HTTP basic auth)

### 3. Dummy Metrics
**Issue:** Landing page C&C metrics are hardcoded
**Impact:** Misleading "live" data display
**Solution:** Connect to real metrics API or remove hardcoded values

### 4. Mock Payment Fallback
**Issue:** `verify_payment()` falls back to mock if Solana unavailable
**Impact:** Unauthorized downloads possible
**Solution:** Remove fallback or implement strict manual review

### 5. Simulated Commands
**Issue:** Terminal returns fake responses when no agent connected
**Impact:** Confusing demo mode
**Solution:** Disable simulated mode in production or show clear warning

### 6. CORS Configuration
**Issue:** `cors_allowed_origins="*"` allows all origins
**Impact:** Security risk in production
**Solution:** Specify exact domains in production

---

## Production Readiness

### Security Issues:
1. **No HTTPS enforcement** - Add Flask-Talisman or force HTTPS in Nginx
2. **Weak secret key** - Generate cryptographically secure key
3. **Debug mode** - Disable `debug=True` in production
4. **File upload validation** - No size limits, no content type checks
5. **SQL injection** - No database (mitigated)
6. **XSS risks** - User inputs in terminal not sanitized

### Performance Issues:
1. **Polling:** Dashboard polls `/api/sessions` and `/api/agents` every 5 seconds
2. **In-memory bottleneck:** Not scalable beyond single process
3. **No caching:** Static files and API responses not cached
4. **Large inline JavaScript:** index.html has 180+ lines of inline JS

### Monitoring:
1. **No logging:** No structured logging for debugging
2. **No health checks:** No dedicated health endpoint
3. **No metrics:** No Prometheus/monitoring integration

---

## Deployment Complexity

### Simple (Current State):
- Single Flask process
- In-memory storage
- No external dependencies except Solana RPC (optional)

### Production Scale:
- Requires Redis for multi-process/multi-server
- Needs load balancer for WebSocket
- Requires persistent storage (PostgreSQL/SQLite)
- Needs process manager (Gunicorn + Nginx)
- SSL termination required

---

## File Structure Summary

```
PCFixPro/
├── app.py                      # Main Flask app (713 lines)
├── index.html                  # Public landing page (1121 lines)
├── templates/
│   └── dashboard.html          # Admin dashboard (377 lines)
├── static/
│   ├── css/
│   │   └── dashboard.css       # Dashboard styles (669 lines)
│   └── js/
│       └── dashboard.js        # Dashboard logic (828 lines)
├── requirements.txt            # Python dependencies
├── client_agent/
│   ├── agent.py                # Client agent script
│   ├── admin_agent.py          # Admin agent with advanced features
│   ├── requirements.txt        # Agent dependencies
│   └── dist/                   # Compiled agent packages
├── downloads/                  # Agent download directory
├── ssh_keys/                   # Auto-generated SSH keys
├── NAMECHEAP_CPANEL_DEPLOY.md  # Cloud deployment guide
└── DEPLOYMENT_GUIDE.md         # On-premise deployment guide
```

---

## Feature Matrix

| Feature | Status | Technology | Notes |
|---------|--------|------------|-------|
| User Authentication | ❌ Missing | None | Dashboard public |
| Landing Page | ✅ Complete | HTML/CSS/JS | Responsive |
| Payment Gateway | ⚠️ Partial | Solana/NOWPayments | Has fallback |
| Agent Management | ✅ Complete | Socket.IO | Real-time |
| RDP/SSH Sessions | ✅ Mock | Paramiko | Paramiko available |
| File Manager | ⚠️ Partial | Socket.IO + Base64 | Works if agent connected |
| Screenshots | ✅ Implemented | Socket.IO | Requires agent |
| Process Management | ✅ Implemented | Socket.IO | Requires agent |
| Registry Access | ✅ Implemented | Socket.IO | Windows only |
| Wake-on-LAN | ✅ Implemented | Socket.IO | Requires MAC |
| Terminal Emulator | ✅ Built-in | JavaScript | Simulated demo |
| Real-time Dashboard | ✅ Complete | Socket.IO | Live updates |
| Rate Limiting | ✅ Implemented | Decorator | Per-IP |
| Path Security | ✅ Implemented | realpath | Dir traversal blocked |
| Input Validation | ⚠️ Partial | Basic | Needs enhancement |
| Error Handling | ⚠️ Basic | Try/except | Generic messages |
| Logging | ❌ Missing | None | No debug logs |
| Backup | ❌ Missing | None | No export |

---

## Strengths
1. Clean, modern UI with professional design
2. Real-time WebSocket communication
3. Multi-platform support (Windows, macOS, Linux agents)
4. Crypto payment integration for global reach
5. Comprehensive agent capabilities (files, processes, registry, WOL)
6. Responsive design for mobile/tablet

## Weaknesses
1. No user authentication/authorization
2. Data loss on restart (in-memory only)
3. Mock payment fallback undermines real verification
4. Hardcoded demo metrics on landing page
5. No production logging or monitoring
6. CORS set to wildcard
7. Missing input sanitization in terminal

---

## Recommendations

### Immediate (Before Launch):
1. Add HTTP Basic Auth or simple login to `/dashboard`
2. Set secure `SECRET_KEY` via environment variable
3. Disable mock payment fallback
4. Replace hardcoded metrics with real data or remove
5. Restrict CORS to actual domain
6. Set `debug=False` in production

### Short-term (1 week):
1. Implement file-based or Redis session storage
2. Add structured logging to all API endpoints
3. Add file upload size limits and content validation
4. Create admin password protection via `.htpasswd`
5. Add SSL monitoring and auto-renewal check

### Long-term (1 month):
1. Migrate to PostgreSQL for persistent storage
2. Implement proper user authentication (Flask-Login)
3. Add audit logs for all actions
4. Implement backup/restore functionality
5. Add monitoring dashboard (Prometheus/Grafana)
6. Create mobile app for agent management

---

## Target Users
- IT technicians managing multiple client PCs
- Small/medium remote support businesses
- Individuals needing reliable remote access

## Competitive Position
Similar to TeamViewer, AnyDesk, UltraViewer, but with:
- Crypto payment integration
- C2-style command center
- Multi-protocol support (RDP + SSH + VNC)
- Open-source self-hosted option

---

**Analysis Date:** 2024-01-01  
**Analyst:** Cline (AI Assistant)  
**Project Version:** PCFixPro v1.0