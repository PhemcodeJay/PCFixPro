#!/usr/bin/env python3
"""
PCFixPro Embedded Installer Creator - Creates ONE .bat file
No external ZIP files needed - everything is embedded
"""
import os
import base64
from pathlib import Path

def create_embedded_installer(server_ip=None):
    """Create a single embedded .bat installer"""
    script_dir = Path(__file__).parent
    downloads_dir = script_dir.parent / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    # Read agent.py and create clean version
    agent_content = (script_dir / "agent.py").read_text()
    agent_lines = []
    for line in agent_content.split('\n'):
        if 'SERVER_URL = "' in line and '192.168' in line:
            continue  # Remove hardcoded URL
        agent_lines.append(line)
    
    # Build PowerShell script
    ps_script = '''
param($ServerIP = "SERVERIPPLACEHOLDER")

$ErrorActionPreference = "SilentlyContinue"
$InstallDir = "$env:ProgramFiles\\PCFixPro Agent"

if (-not (Test-Path $InstallDir)) {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
}

$ClientIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {{ $_.InterfaceAlias -ne "Loopback" }}).IPAddress
if (-not $ClientIP) {{ $ClientIP = "unknown" }}

'''
    ps_script = ps_script.replace('SERVERIPPLACEHOLDER', server_ip or '192.168.100.253')
    
    # Add agent.py content as heredoc
    ps_script += '@"\n'
    for line in agent_lines:
        escaped = line.replace('"', "'")
        ps_script += escaped + '\n'
    ps_script += '"@ | Out-File -FilePath "$InstallDir\\agent.py" -Encoding UTF8\n\n'
    
    ps_script += '''
# Write config
$Config = '{"server_url":"http://'+server_ip+'"}'| ConvertTo-Json
$Config | Out-File -FilePath "$InstallDir\\config.json" -Encoding UTF8

# Install dependencies
pip install python-socketio requests pywin32 --quiet 2>$null

# Create startup
"import os; os.chdir(r'$InstallDir'); exec(open(r'$InstallDir\\agent.py').read())" > "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\pcfixpro_agent.py"

# Start hidden
Start-Process pythonw -ArgumentList "`"$InstallDir\\agent.py`"" -WindowStyle Hidden

# Firewall
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=in action=allow program="pythonw.exe" enable=yes 2>$null

# Status file
"PCFixPro Agent Installed`nServer: http://''' + (server_ip or '192.168.100.253') + ''':5000`nClient IP: $ClientIP`nHostname: $env:COMPUTERNAME" > "$env:USERPROFILE\\Desktop\\PCFixPro_Status.txt"
'''

    # Encode to base64
    ps_bytes = ps_script.encode('utf-8')
    ps_b64 = base64.b64encode(ps_bytes).decode('utf-8')
    
    # Create batch file
    installer_path = downloads_dir / "PCFixPro_Installer.bat"
    batch_content = f'''@echo off
:: PCFixPro Remote Support Agent - Embedded Installer v3.0
:: All code embedded - no external files needed

net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs" -WindowStyle Hidden
    exit /b
)

echo Installing PCFixPro Agent...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{ps_b64}')) | Invoke-Expression"
echo.
echo Installation Complete!
echo Status file on desktop: PCFixPro_Status.txt
pause
'''
    
    installer_path.write_text(batch_content)
    print(f"[OK] Created: {installer_path}")
    print(f"[INFO] Server IP: {server_ip or '192.168.100.253'}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-ip', default='192.168.100.253')
    args = parser.parse_args()
    create_embedded_installer(args.server_ip)