# How to Use Distribution Files

## Distribution Package Contents

Located in the `downloads/` folder:

```
downloads/
├── PCFixPro.pdf                    # Client instruction guide (PDF)
├── PCFixPro_AutoInstall.bat        # One-click Windows installer
├── PCFixPro_Agent_Windows.zip      # Windows package
├── PCFixPro_Agent_macOS.zip        # macOS package  
└── PCFixPro_Agent_Universal.zip    # Cross-platform package
```

---

## For IT Technicians (Support Providers)

### Starting the Dashboard
```bash
cd c:\Users\Bossman\Desktop\RemoteFix
python app.py
```
Dashboard opens at: http://YOUR_IP:5000

### Distribution Options

**Option 1: One-Click Installer (Recommended for Windows)**
1. Send `PCFixPro_AutoInstall.bat` to client
2. Client double-clicks the file
3. Installation runs automatically with admin privileges
4. Agent connects to your dashboard silently

**Option 2: PDF + ZIP (Universal)**
1. Send both `PCFixPro.pdf` and `PCFixPro_Agent_Universal.zip` to client
2. Client opens PDF for instructions
3. Extracts ZIP and runs INSTALL.bat (Windows) or INSTALL.command (macOS)

**Option 3: Platform-Specific ZIP**
- Windows clients: Send `PCFixPro_Agent_Windows.zip`
- macOS clients: Send `PCFixPro_Agent_macOS.zip`

---

## For Clients (End Users)

### Quick Install (Windows - Recommended)
1. **Double-click** `PCFixPro_AutoInstall.bat`
2. Click "YES" when Windows asks for permission
3. Watch for installation toast notification
4. ✅ Done! Technician will see your PC in their dashboard

### Manual Install (Windows)
1. Extract `PCFixPro_Agent_Windows.zip`
2. Right-click `INSTALL.bat` → "Run as administrator"
3. Installation runs silently
4. ✅ Agent connects to dashboard automatically

### Manual Install (macOS)
1. Extract `PCFixPro_Agent_macOS.zip`
2. Right-click `INSTALL.command` → "Open"
3. Enter your password when prompted
4. ✅ Agent connects to dashboard automatically

### Using the PDF
1. Open `PCFixPro.pdf` to read installation instructions
2. Follow the steps in the PDF
3. The ZIP file is in the same folder as the PDF

---

## What Happens After Installation

1. **Agent Service Starts** - Runs in background (invisible to user)
2. **WebSocket Connection** - Connects to your dashboard
3. **Registration** - Your PC appears in "Connected Agents" list
4. **Ready for Support** - Technician can now access your PC

---

## Files Inside Each ZIP Package

### Windows ZIP Contains:
```
PCFixPro_Agent_Windows/
├── agent.py              # Main agent script
├── admin_agent.py        # Full system access module
├── requirements.txt      # Python dependencies
├── install_service.py    # Windows service wrapper
├── install_silent.bat    # Silent installer
├── INSTALL.bat           # Auto-installer (double-click to run)
└── CLIENT_README.md      # Instructions
```

### macOS ZIP Contains:
```
PCFixPro_Agent_macOS/
├── macos_agent.py        # Main macOS agent
├── requirements.txt      
├── install_macos.sh      # Installer script
├── INSTALL.command       # Auto-installer
└── CLIENT_README.md      # Instructions
```

---

## Troubleshooting

**Installation doesn't start:**
- Make sure you're running as Administrator (Windows)
- Check Windows Defender or antivirus isn't blocking

**Agent not appearing in dashboard:**
- Check internet connection
- Verify your firewall allows outbound connections
- Check desktop shortcut for `PCFixPro Install Logs`

**Need help:**
- Call your IT support provider
- Email: support@pcfixpro.com