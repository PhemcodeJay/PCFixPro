# PCFixPro Command & Control Center

A Flask-based remote desktop management dashboard for managing RDP/SSH/VNC connections to client PCs with crypto payment integration.

## 📋 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Features](#features)
- [Project Structure](#project-structure)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

PCFixPro C&C Center provides a web-based dashboard for IT professionals to:
- Remotely access client computers via RDP, SSH, or VNC
- Manage files on connected machines
- Execute commands and view output
- Monitor system health and processes
- Handle payments with crypto integration

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step-by-Step

1. **Clone or download the project**
   ```bash
   cd /path/to/RemoteFix
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the dashboard**
   - Local: http://127.0.0.1:5000
   - Network: http://YOUR_IP:5000 (e.g., http://192.168.100.253:5000)

## 🚀 Quick Start

### For IT Technicians - Auto-Install Distribution

The system includes pre-built distribution files in the `downloads/` folder:

```
downloads/
├── PCFixPro.pdf                    # Client guide (PDF)
├── PCFixPro_AutoInstall.bat        # ONE-CLICK auto-installer
├── PCFixPro_Agent_Windows.zip
├── PCFixPro_Agent_macOS.zip
└── PCFixPro_Agent_Universal.zip
```

**Option 1: Send the Auto-Install BAT** (Easiest)
- Send `PCFixPro_AutoInstall.bat` to any Windows client
- Client double-clicks it and installation runs automatically
- Agent connects to your dashboard silently

**Option 2: Send ZIP + PDF**
- Send `PCFixPro_Agent_Universal.zip` and `PCFixPro.pdf`
- Client extracts ZIP and runs `INSTALL.bat` or `INSTALL.command`
- Agent auto-connects to dashboard

### For Clients - How to Install

**Windows:**
1. Double-click `PCFixPro_AutoInstall.bat` (recommended)
   OR extract ZIP and run `INSTALL.bat`
2. Click "Yes" when UAC prompt appears
3. Installation runs silently - watch for toast notification
4. ✅ Agent automatically connects to technician's dashboard

**macOS:**
1. Extract ZIP file
2. Right-click `INSTALL.command` → "Open"
3. Enter your password when prompted
4. Installation runs silently
5. ✅ Agent automatically connects to technician's dashboard

## ✨ Features

### For IT Technicians

1. **Start the dashboard**
   ```bash
   python app.py
   ```

2. **Build agent packages (if not already built)**
   ```bash
   cd client_agent
   python package_agent.py
   ```

3. **Share the ZIP files with clients**
   - Distribute `PCFixPro_Agent_Windows.zip` for Windows PCs
   - Distribute `PCFixPro_Agent_macOS.zip` for Mac computers

4. **Wait for agent connections**
   - Clients run INSTALL.bat (Windows) or INSTALL.command (macOS)
   - Agents appear automatically in your dashboard

5. **Start remote management**
   - Click "Files" to browse client files
   - Use terminal to execute commands
   - Take screenshots for documentation

### For Clients (Recipients)

1. **Extract the ZIP file** you received from your IT support provider

2. **Run the installer**
   - **Windows**: Right-click `INSTALL.bat` → "Run as administrator"
   - **macOS**: Right-click `INSTALL.command` → "Open"

3. **Installation runs automatically**
   - Silent installation with logging
   - Desktop shortcut to logs is created
   - Agent starts and connects to dashboard

## ✨ Features

### Real-time Dashboard
- Monitor active sessions and connected agents
- View system health metrics
- WebSocket-powered live updates

### Session Management
- Create RDP, SSH, and VNC sessions
- Store and manage connection credentials
- Disconnect sessions when done

### Multi-Protocol Support
| Protocol | Default Port | Use Case |
|----------|-------------|----------|
| RDP | 3389 | Windows desktop access |
| SSH | 22 | Linux/macOS command line |
| VNC | 5900 | Cross-platform desktop |

### File Management
- Browse client file systems
- Upload files to client PCs
- Download files from client PCs
- Delete files and folders
- Directory navigation

### System Management
- **Process List**: View running processes with CPU/memory usage
- **Kill Process**: Terminate processes by PID
- **Registry Editor** (Windows): Read HKLM/HKCU registry values
- **Screenshots**: Capture live screenshots from clients
- **Wake-on-LAN**: Power on remote PCs remotely

### Payment Integration
- Solana blockchain verification (optional)
- Token-based download access
- Three pricing tiers: Starter ($20), Pro ($50), Enterprise ($100)

## 📁 Project Structure

```
RemoteFix/
├── app.py                    # Flask application (main C&C server)
├── requirements.txt          # Python dependencies
├── FIX_SUMMARY.md           # Changelog of fixes
├── README.md                # This file
├── index.html               # Business landing page
├── templates/
│   └── dashboard.html       # Main dashboard template
├── static/
│   ├── css/
│   │   └── dashboard.css    # Dashboard styles
│   └── js/
│       └── dashboard.js     # Dashboard functionality
├── ssh_keys/                # Generated SSH keys (auto-created)
├── client_agent/            # Remote client agent
│   ├── agent.py             # Windows agent
│   ├── admin_agent.py       # Windows admin agent (full access)
│   ├── macos_agent.py       # macOS agent
│   ├── requirements.txt     # Agent dependencies
│   ├── package_agent.py     # Build packages
│   ├── INSTALL.bat          # Windows auto-installer
│   ├── INSTALL.command      # macOS auto-installer
│   ├── install_silent.bat   # Windows silent installer
│   ├── install_complete.ps1 # Windows advanced installer
│   ├── install_macos.sh     # macOS installer
│   ├── com.pcfixpro.agent.plist # macOS LaunchAgent
│   ├── CLIENT_README.md     # Client installation guide
│   └── dist/                # Built packages
│       ├── PCFixPro_Agent_Windows.zip
│       ├── PCFixPro_Agent_macOS.zip
│       └── PCFixPro_Universal.zip
└── logs/                    # Log files (created at runtime)
```

## 📖 Usage Guide

### 1. Connect to a Remote PC
- Click "New Session" button
- Enter: client name, host/IP, port, protocol
- Enter username and password
- Click "Connect"

### 2. Browse Client Files
- Click "Files" button on any connected agent
- Navigate directories by clicking folders
- Upload: Click upload button, select file
- Download: Select file, click download
- Delete: Select file, click delete, confirm

### 3. Take Screenshots
- Open file manager for an agent
- Click "Screenshot" button
- Screenshot appears in preview area
- Download as PNG file

### 4. Manage Processes
- Open file manager for an agent
- Click "Processes" tab
- Click "Kill" and enter PID to terminate

### 5. Read Registry
- Open file manager for an agent
- Click "Registry" tab
- Enter hive (HKLM/HKCU) and key path
- View values in terminal output

### 6. Wake-on-LAN
- Open file manager for an agent
- Click "Wake" tab
- Enter MAC address (format: AA:BB:CC:DD:EE:FF)
- Click "Send" to power on remote PC

### 7. Execute Commands
- Select a session from the table
- Type commands in the terminal
- Press Enter to execute
- View output in real-time

### 8. Terminal Commands
```
help      - Show available commands
sessions  - List all active sessions
agents    - List connected client agents
clear     - Clear terminal
status    - Show system status
```

## ⚙️ Configuration

### Environment Variables (.env file)
Create a `.env` file for production settings:
```env
# Server configuration
HOST=0.0.0.0
PORT=5000
DEBUG=false

# Solana payment verification (optional)
SOLANA_RPC=https://api.mainnet-beta.solana.com
# Your receiving wallet address
RECIPIENT_WALLET=your_wallet_address_here
```

### Agent Configuration
Edit `client_agent/agent.py` to change the server URL:
```python
SERVER_URL = "http://YOUR_SERVER_IP:5000"
```

## 🔧 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Agent not connecting | Check firewall, verify SERVER_URL, check logs |
| Dashboard not loading | Install dependencies, check port 5000 |
| File upload fails | Check client path permissions |
| Screenshot not working | Install Pillow: `pip install Pillow` |
| SSH connection fails | Install paramiko, check credentials |

### Logs
- Dashboard logs: Console output
- Agent logs: Desktop shortcut "PCFixPro Agent Logs"
- Installation logs: `%TEMP%\PCFixPro_Install_*.log`

## 🔒 Security

- All agent communication uses WebSocket
- Token-based authentication for downloads
- Rate limiting on API endpoints
- Path traversal protection for file operations

**Important**: Only install agents on systems you own or have explicit permission to access.

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

Contact: support@pcfixpro.com
Phone: +1-XXX-XXX-XXXX