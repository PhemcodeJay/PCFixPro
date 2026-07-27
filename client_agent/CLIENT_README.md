# PCFixPro Remote Support Agent - Installation Guide

## Overview
The PCFixPro Remote Support Agent enables secure remote management of your computer. Once installed, it allows authorized technicians to provide remote support through the Command & Control Center.

## Quick Installation

### For Windows Users

#### Method 1: INSTALL.bat (Easiest)
1. Extract the ZIP file you received
2. Right-click `INSTALL.bat` → "Run as administrator"
3. The installation runs silently with logging
4. A desktop shortcut to logs will be created
5. Done! The agent automatically connects to the dashboard

#### Method 2: PowerShell Installer
1. Right-click `install_complete.ps1` → "Run with PowerShell"
2. Enter your C&C Server IP when prompted
3. The agent installs automatically and starts in the background

#### Method 3: Silent Installation
1. Right-click `install_silent.bat` → "Run as administrator"
2. Installation proceeds without prompts
3. Check desktop shortcut for logs after completion

### For macOS Users
1. Extract the ZIP file you received
2. Right-click `INSTALL.command` → "Open"
3. Enter your password when prompted
4. Installation runs silently with logging
5. Done! The agent automatically connects to the dashboard

## What Happens During Installation

The installer will:
- Install Python 3.8+ if not present
- Install required dependencies (python-socketio, requests, psutil, Pillow)
- Configure the agent with your C&C Server IP
- Install as a background service (auto-starts on boot)
- Add firewall exception for outbound connections
- Start the agent immediately

## Verification

After installation:
1. Look for the "PCFixPro Agent Logs" shortcut on your desktop
2. The agent will appear in your Command & Control Center dashboard
3. Check the "Connected Agents" section in the dashboard
4. The agent will show: hostname, IP address, OS, and online status

## How to Use the Agent

### For Clients (End Users)
- The agent runs silently in the background
- No action required - it connects automatically
- View logs via desktop shortcut if needed
- Contact your support provider for assistance

### For Technicians (Remote Access)
Once agents are connected, you can:

#### 1. Connect to a Remote PC
- Click "New Session" button
- Enter client name, host/IP, port, protocol (RDP/SSH/VNC)
- Enter saved credentials or get from client
- Click "Connect"

#### 2. Browse Client Files
- Click "Files" button on any connected agent
- Navigate directories by clicking folders
- Upload files using the Upload button
- Download files by selecting and clicking Download
- Delete files with confirmation prompt

#### 3. Take Screenshots
- Open file manager for an agent
- Click "Screenshot" button
- Screenshot appears in preview area
- Download screenshot as PNG file

#### 4. Manage Processes
- Open file manager for an agent
- Click "Processes" to see running processes
- Click "Kill" and enter PID to terminate a process

#### 5. Read Registry (Windows Only)
- Open file manager for an agent
- Click "Registry"
- Enter hive (HKLM/HKCU) and key path
- View registry values in terminal

#### 6. Wake-on-LAN
- Open file manager for an agent
- Click "Wake"
- Enter MAC address of target PC
- Magic packet sent to power on remote PC

#### 7. Execute Commands
- Select a session from the table
- Type commands in the terminal at the bottom
- Press Enter to execute
- View output in real-time

## Terminal Commands

Available commands in the integrated terminal:
- `help` - Show available commands
- `sessions` - List all active sessions
- `agents` - List connected client agents
- `clear` - Clear terminal
- `status` - Show system status

## How to Use - Remote Access Guide

### For Clients:
1. Receive zip file from PCFixPro
2. Extract and run installer (INSTALL.bat or INSTALL.command)
3. Installation runs silently in background
4. Desktop shortcut to logs is created
5. Done! Agent automatically connects to dashboard

### For Technicians:
1. Run the dashboard: `python app.py` (http://127.0.0.1:5000)
2. Connect to agents via WebSocket
3. Use the web interface to:
   - Execute commands remotely
   - Transfer files (upload/download)
   - Take screenshots
   - View process list
   - Read Windows Registry
   - Send Wake-on-LAN packets

## Files Installed

### Windows Location
```
C:\Program Files\PCFixPro Agent\
├── agent.py              # Main agent script
├── admin_agent.py        # Full system access module
├── requirements.txt      # Python dependencies
├── install_service.py    # Windows service wrapper
├── start_agent.bat       # Manual startup script
├── install_agent.ps1     # PowerShell installer
├── install_silent.bat    # Silent installer
└── uninstall.bat         # Uninstaller
```

### macOS Location
```
/Library/LaunchAgents/
├── com.pcfixpro.agent.plist   # LaunchAgent config
├── macos_agent.py             # Main agent script
└── install_macos.sh           # Installer script
```

## Manual Start/Stop

### Windows
```powershell
# Start service
net start PCFixProAgent

# Stop service
net stop PCFixProAgent

# Uninstall service
python install_service.py remove
```

### macOS
```bash
# Start agent
sudo launchctl load /Library/LaunchAgents/com.pcfixpro.agent.plist

# Stop agent
sudo launchctl unload /Library/LaunchAgents/com.pcfixpro.agent.plist
```

## Troubleshooting

**Agent not appearing in dashboard:**
- Check firewall allows outbound port 5000
- Verify SERVER_URL in agent.py matches your C&C server IP
- Check agent.log for errors (desktop shortcut)

**Python not found:**
- Install Python 3.8+ from python.org
- Check "Add Python to PATH" during installation

**Service won't start:**
- Run `python install_service.py remove` to clean up
- Re-run installer as Administrator

**Connection issues:**
- Verify network connectivity to C&C server
- Check if port 5000 is open on server
- Ensure server is running

## Log Files

- **Installation logs**: `%TEMP%\PCFixPro_Install_*.log` (Windows) or `/tmp/PCFixPro_Install_*.log` (macOS)
- **Agent logs**: Desktop shortcut "PCFixPro Agent Logs" or `/var/log/pcfixpro_agent.log` (macOS)

## Security Note

This agent allows remote command execution. Only install on:
- Client PCs you own or have permission to access
- Systems where you have explicit admin rights
- Trusted networks with proper security

The agent uses encrypted WebSocket connections and requires token-based authentication for download access.

## Support

Contact PCFixPro ICT Services for assistance.
Email: support@pcfixpro.com
Phone: +1-XXX-XXX-XXXX