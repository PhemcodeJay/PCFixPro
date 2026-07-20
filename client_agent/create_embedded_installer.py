#!/usr/bin/env python3
"""
PCFixPro Embedded Installer Creator
Creates a single self-contained .bat file that auto-installs without external ZIP
"""
import os
import sys
import base64
import zipfile
from pathlib import Path

def create_embedded_installer(server_ip=None):
    """Create a fully embedded self-contained installer"""
    script_dir = Path(__file__).parent
    downloads_dir = script_dir.parent / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    
    # Files to embed
    files_to_embed = {
        "agent.py": (script_dir / "agent.py").read_text(),
        "requirements.txt": (script_dir / "requirements.txt").read_text(),
        "install_service.py": (script_dir / "install_service.py").read_text() if (script_dir / "install_service.py").exists() else "",
    }
    
    # Create embedded installer
    installer_path = downloads_dir / "PCFixPro_AutoInstall.bat"
    
    # Build the installer content
    installer_content = f"""@echo off
:: PCFixPro Auto-Installer v2.0
:: Fully embedded self-contained installer - no external files needed
:: Auto-extracts and installs silently with IP logging

setlocal enabledelayedexpansion

:: Configuration - Auto-detected server IP
"""
    
    if server_ip:
        installer_content += f"set SERVER_IP={server_ip}\n"
    else:
        installer_content += f"set SERVER_IP=192.168.100.253\n"
    
    installer_content += """
echo ========================================
echo PCFixPro Remote Support Agent v2.0
echo ========================================
echo.

:: Get client IP and log it
for /f "tokens=2 delims=[]" %%a in ('ping -4 -n 1 %SERVER_IP% ^| findstr "["') do set CLIENT_IP=%%a
echo [INFO] Client IP: %CLIENT_IP%
echo.

:: Check admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %%~f0' -Verb RunAs" -WindowStyle Hidden
    exit /b
)

echo [OK] Running with administrator privileges
echo [OK] Server: http://%SERVER_IP%:5000
echo [OK] Client IP: %CLIENT_IP%
echo.

:: Create installation directory
set "INSTALL_DIR=C:\\Program Files\\PCFixPro Agent"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Log session with IP
echo %date% %time% - Installing agent - Server: %SERVER_IP% - Client IP: %CLIENT_IP% >> "%INSTALL_DIR%\\sessions.log"

:: Install Python dependencies silently
echo [1/4] Installing dependencies...
pip install python-socketio requests pywin32 Pillow wmi mss --quiet --disable-pip-version-check >> nul 2>&1

:: Create agent script with embedded server URL
echo [2/4] Creating agent configuration...
"""
    
    # Embed agent.py with server URL
    agent_content = files_to_embed["agent.py"]
    # Replace the server URL with the configured one
    agent_lines = []
    for line in agent_content.split('\n'):
        if 'SERVER_URL = "' in line and '192.168' in line:
            agent_lines.append(f'SERVER_URL = "http://%SERVER_IP%:5000"  # Auto-configured server IP')
        else:
            agent_lines.append(line)
    
    # Write embedded agent.py
    for line in agent_lines:
        installer_content += f"echo {line} >> \"%INSTALL_DIR%\\agent.py\"\n"
    
    installer_content += """
echo [3/4] Starting agent service...
cd /d "%INSTALL_DIR%"

:: Try to install as service, fallback to startup
python -c "import win32service" 2>nul
if %errorLevel% equ 0 (
    python -c "import servicemanager" 2>nul
    if %errorLevel% equ 0 (
        :: Create service wrapper
        echo import win32serviceutil > "%INSTALL_DIR%\\service_wrapper.py"
        echo import servicemanager >> "%INSTALL_DIR%\\service_wrapper.py"
        echo import win32service >> "%INSTALL_DIR%\\service_wrapper.py"
        echo import win32event >> "%INSTALL_DIR%\\service_wrapper.py"
        echo import sys >> "%INSTALL_DIR%\\service_wrapper.py"
        echo sys.path.insert(0, r'%INSTALL_DIR%') >> "%INSTALL_DIR%\\service_wrapper.py"
        echo class AgentService^(win32serviceutil.ServiceFramework^): >> "%INSTALL_DIR%\\service_wrapper.py"
        echo     _svc_name_ = 'PCFixProAgent' >> "%INSTALL_DIR%\\service_wrapper.py"
        echo     _svc_display_name_ = 'PCFixPro Remote Support Agent' >> "%INSTALL_DIR%\\service_wrapper.py"
        echo     _svc_description_ = 'Remote support agent for PCFixPro' >> "%INSTALL_DIR%\\service_wrapper.py"
        echo     def __init__(self, args^): >> "%INSTALL_DIR%\\service_wrapper.py"
        echo         win32serviceutil.ServiceFramework.__init__(self, args^) >> "%INSTALL_DIR%\\service_wrapper.py"
        echo     def SvcStop^(self^): self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING^); win32event.SetEvent^(self.stop_event^) >> "%INSTALL_DIR%\\service_wrapper.py"
        echo     def SvcDoRun^(self^): >> "%INSTALL_DIR%\\service_wrapper.py"
        echo         servicemanager.LogMsg^(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STARTED, ^(self._svc_name_, ''^)^) >> "%INSTALL_DIR%\\service_wrapper.py"
        echo         from agent import RemoteAgent >> "%INSTALL_DIR%\\service_wrapper.py"
        echo         RemoteAgent^(^).run^(^) >> "%INSTALL_DIR%\\service_wrapper.py"
        python "%INSTALL_DIR%\\service_wrapper.py" install 2>nul
        python "%INSTALL_DIR%\\service_wrapper.py" start 2>nul
        echo [OK] Service started
    )
)

if not exist "%INSTALL_DIR%\\service_wrapper.py" (
    echo [INFO] Using startup method for auto-start
    :: Add to startup
    copy "%INSTALL_DIR%\\agent.py" "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\agent.py" >nul
    echo [OK] Added to startup
    
    :: Start immediately
    start /B pythonw.exe "%INSTALL_DIR%\\agent.py"
    echo [OK] Agent started
)

:: Create firewall exception
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=in action=allow program="python.exe" enable=yes >nul 2>&1
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=in action=allow program="pythonw.exe" enable=yes >nul 2>&1

:: Log completion with IP
echo %date% %time% - Installation complete - Client IP: %CLIENT_IP% >> "%INSTALL_DIR%\\sessions.log"

:: Create desktop notification
echo PCFixPro Agent Installed Successfully > "%USERPROFILE%\\Desktop\\PCFixPro_Status.txt"
echo Server: http://%SERVER_IP%:5000 >> "%USERPROFILE%\\Desktop\\PCFixPro_Status.txt"
echo Client IP: %CLIENT_IP% >> "%USERPROFILE%\\Desktop\\PCFixPro_Status.txt"
echo Installation Date: %date% %time% >> "%USERPROFILE%\\Desktop\\PCFixPro_Status.txt"

echo.
echo ========================================
echo Installation Complete!
echo Server: http://%SERVER_IP%:5000
echo Client IP: %CLIENT_IP%
echo Log: %%INSTALL_DIR%%\\sessions.log
echo ========================================
echo.
echo [SUCCESS] Agent is now running and will appear in the dashboard.
echo [INFO] Press any key to close this window...
pause >nul
"""
    
    installer_path.write_text(installer_content)
    print(f"[OK] Created: {installer_path}")
    print(f"[INFO] Server IP: {server_ip or '192.168.100.253'}")
    print("[INFO] This installer is fully self-contained - no external ZIP needed!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create embedded installer')
    parser.add_argument('--server-ip', help='Server IP address to configure', default='192.168.100.253')
    args = parser.parse_args()
    create_embedded_installer(args.server_ip)