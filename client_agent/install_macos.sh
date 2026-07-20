#!/bin/bash
# PCFixPro macOS Agent Installer
# Silent installation for macOS clients

# Configuration
SERVER_IP="${1:-102.209.236.22}"
INSTALL_DIR="/Library/PCFixPro Agent"
LOG_FILE="/tmp/PCFixPro_Install_$(date +%Y%m%d_%H%M%S).log"
AGENT_LOG="$INSTALL_DIR/agent.log"
SERVER_URL="http://$SERVER_IP:5000"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================"
log "PCFixPro macOS Agent Installer"
log "========================================"
log "Server IP: $SERVER_IP"
log "Computer: $(hostname)"
log "User: $(whoami)"

# Check for administrator privileges
if [ "$EUID" -ne 0 ]; then
    log "ERROR: Please run with sudo!"
    echo "Please run: sudo ./install_macos.sh"
    exit 1
fi

log "[OK] Administrator privileges confirmed"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    log "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

log "[OK] Python 3 found: $(python3 --version)"

# Create installation directory
log "[1/6] Creating installation directory..."
mkdir -p "$INSTALL_DIR"
log "[OK] Directory created: $INSTALL_DIR"

# Copy agent files
log "[2/6] Copying agent files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/macos_agent.py" "$INSTALL_DIR/agent.py"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/requirements.txt"
log "[OK] Files copied"

# Create config file
log "[3/6] Configuring agent..."
echo "SERVER_URL=$SERVER_URL" > "$INSTALL_DIR/agent_config.txt"
log "[OK] Configuration updated"

# Install Python dependencies
log "[4/6] Installing Python dependencies..."
pip3 install -r "$INSTALL_DIR/requirements.txt" --quiet >> "$LOG_FILE" 2>&1
pip3 install python-dotenv requests --quiet >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    log "WARNING: Some dependencies failed to install"
else
    log "[OK] Dependencies installed"
fi

# Create LaunchAgent for auto-start
log "[5/6] Installing LaunchAgent..."
PLIST_FILE="/Library/LaunchAgents/com.pcfixpro.agent.plist"
cp "$SCRIPT_DIR/com.pcfixpro.agent.plist" "$PLIST_FILE"

# Update plist with actual paths
PYTHON_PATH=$(which python3)
sed -i '' "s|/usr/local/bin/python3|$PYTHON_PATH|" "$PLIST_FILE"
sed -i '' "s|/Library/PCFixPro Agent/agent.py|$INSTALL_DIR/agent.py|" "$PLIST_FILE"
sed -i '' "s|/Library/PCFixPro Agent/agent.log|$AGENT_LOG|" "$PLIST_FILE"

# Load the LaunchAgent
launchctl unload "$PLIST_FILE" 2>/dev/null
launchctl load "$PLIST_FILE" 2>/dev/null
launchctl start com.pcfixpro.agent 2>/dev/null

log "[OK] LaunchAgent installed and started"

# Configure firewall (if applicable)
log "[6/6] Configuring firewall..."
if [ -f "/usr/libexec/ApplicationFirewall/socketfilterfw" ]; then
    /usr/libexec/ApplicationFirewall/socketfilterfw --add "$(which python3)" >> "$LOG_FILE" 2>&1
    /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$(which python3)" >> "$LOG_FILE" 2>&1
    log "[OK] Firewall configured"
else
    log "Firewall not configured (not available)"
fi

# Create desktop shortcut to logs
log ""
log "Creating desktop shortcut..."
DESKTOP_SHORTCUT="$HOME/Desktop/PCFixPro Agent Logs.command"
cat > "$DESKTOP_SHORTCUT" <<EOF
#!/bin/bash
open "$AGENT_LOG"
EOF
chmod +x "$DESKTOP_SHORTCUT"
log "[OK] Desktop shortcut created"

# Completion
log ""
log "========================================"
log "Installation Complete!"
log "========================================"
log ""
log "The agent will now:"
log "  - Connect to C&C Server at $SERVER_URL"
log "  - Report system status automatically"
log "  - Appear in Command & Control Center"
log "  - Logs: $AGENT_LOG"
log "  - Install log: $LOG_FILE"
log ""
log "Desktop shortcut created for easy log access"
log ""

echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Server: $SERVER_URL"
echo "Logs: $AGENT_LOG"
echo "Install Log: $LOG_FILE"
echo ""
echo "The agent will now appear in your Command & Control Center"
echo ""

# Open log file
sleep 2
open "$LOG_FILE"