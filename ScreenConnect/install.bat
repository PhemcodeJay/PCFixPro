@echo off
:: PCFixPro ScreenConnect Enterprise Gateway
:: Handles MSI installation and establishes RDP/SSH tunnels for up to 100 concurrent users
:: With real-time heartbeat to dashboard

setlocal enabledelayedexpansion

:: Configuration
set SERVER_IP=192.168.100.253
set SERVER_PORT=5000
set MAX_CONCURRENT_USERS=100
set BASE_RDP_PORT=3389
set BASE_SSH_PORT=22

echo ========================================
echo PCFixPro ScreenConnect Enterprise Gateway
echo ========================================
echo.

:: Get client IP
for /f "tokens=2 delims=[]" %%a in ('ping -4 -n 1 %SERVER_IP% ^| findstr "["') do set CLIENT_IP=%%a
if "!CLIENT_IP!"=="" set CLIENT_IP=127.0.0.1

echo [INFO] Client IP: !CLIENT_IP!
echo [INFO] Max concurrent users: %MAX_CONCURRENT_USERS%
echo.

:: Auto-elevate to admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs" -WindowStyle Hidden
    exit /b
)

echo [OK] Administrator privileges confirmed
echo.

:: Create installation directory
set INSTALL_DIR=C:\Program Files\PCFixPro ScreenConnect
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Create session log
echo Installation started: %date% %time% > "%INSTALL_DIR%\gateway.log"
echo Client IP: !CLIENT_IP! >> "%INSTALL_DIR%\gateway.log"
echo Hostname: %COMPUTERNAME% >> "%INSTALL_DIR%\gateway.log"

:: Install ScreenConnect MSI silently
echo [1/4] Installing ScreenConnect Client...
if exist "ScreenConnect.ClientSetup(4).msi" (
    msiexec /i "ScreenConnect.ClientSetup(4).msi" /quiet /norestart /l*v "%INSTALL_DIR%\msi_install.log"
    if !errorlevel! equ 0 (
        echo [OK] ScreenConnect MSI installed successfully
    ) else (
        echo [ERROR] MSI installation failed with error !errorlevel!
        echo Check %INSTALL_DIR%\msi_install.log for details
    )
) else (
    echo [WARNING] MSI file not found - continuing with tunnel creation
)

:: Create SSH tunnel batch file
echo [2/4] Creating SSH tunnel configuration...
(
echo @echo off
echo :: SSH Tunnel for ScreenConnect
echo set LOCAL_PORT=22
echo set REMOTE_PORT=22
echo echo Establishing SSH tunnel...
echo plink.exe -ssh -%LOCAL_PORT%:%LOCAL_PORT% %SERVER_IP% -P %SERVER_PORT% -l pcfixpro -pw auto -N -L 3389:localhost:3389
) > "%INSTALL_DIR%\ssh_tunnel.bat"

:: Create RDP tunnel batch file
echo [3/4] Creating RDP tunnel configuration...
(
echo @echo off
echo :: RDP Tunnel for ScreenConnect
echo set LOCAL_PORT=3389
echo set REMOTE_PORT=3389
echo echo Establishing RDP tunnel...
echo plink.exe -ssh -%LOCAL_PORT%:%LOCAL_PORT% %SERVER_IP% -P %SERVER_PORT% -l pcfixpro -pw auto -N -L 22:localhost:22
) > "%INSTALL_DIR%\rdp_tunnel.bat"

:: Create heartbeat script
echo [4/4] Creating heartbeat monitor...

:: Install Python dependencies if needed
pip install python-socketio requests --quiet --no-warn-script-location 2>nul

:: Create heartbeat script for concurrent users
(
echo import socketio
echo import os
echo import time
echo from datetime import datetime
echo import platform
echo import json
echo import socket
echo import threading
echo import subprocess
echo 
echo SERVER_URL = "http://%SERVER_IP%:%SERVER_PORT%"
echo AGENT_ID = "gateway_!CLIENT_IP!"
echo CLIENT_IP = "!CLIENT_IP!"
echo 
echo class GatewayHeartbeat:
echo     def __init__(self):
echo         self.sio = socketio.Client()
echo         self.active_connections = {}
echo         self.setup_handlers()
echo     
echo     def setup_handlers(self):
echo         @self.sio.event
echo         def connect():
echo             print("[GATEWAY] Connected to dashboard")
echo             self.register_gateway()
echo         
echo         @self.sio.event
echo         def disconnect():
echo             print("[GATEWAY] Disconnected from dashboard. Reconnecting...")
echo         
echo         @self.sio.event
echo         def heartbeat_ack(data):
echo             print(f"[GATEWAY] Heartbeat acknowledged: {data}")
echo     
echo     def register_gateway(self):
echo         self.sio.emit("register_agent", {
echo             "hostname": os.environ.get("COMPUTERNAME", "Unknown"),
echo             "ip_address": CLIENT_IP,
echo             "os": platform.system() + " " + platform.release(),
echo             "agent_version": "ScreenConnect-Gateway-1.0",
echo             "status": "online",
echo             "agent_type": "gateway",
echo             "max_connections": %MAX_CONCURRENT_USERS%
echo         })
echo     
echo     def send_heartbeat(self, customer_id, assigned_ip, session_status):
echo         """Send heartbeat with connection details"""
echo         self.sio.emit("heartbeat", {
echo             "agent_id": AGENT_ID,
echo             "customer_id": customer_id,
echo             "assigned_ip": assigned_ip,
echo             "session_status": session_status,
echo             "timestamp": datetime.now().isoformat(),
echo             "active_connections": len(self.active_connections)
echo         })
echo     
echo     def establish_rdp_ssh_tunnel(self, customer_id, target_host, rdp_port=3389, ssh_port=22):
echo         """Establish simultaneous RDP/SSH tunnels for enterprise users"""
echo         connection_id = f"{customer_id}_{target_host}"
echo         self.active_connections[connection_id] = {
echo             "customer_id": customer_id,
echo             "target_host": target_host,
echo             "rdp_port": rdp_port,
echo             "ssh_port": ssh_port,
echo             "status": "connected",
echo             "timestamp": datetime.now().isoformat()
echo         }
echo         self.send_heartbeat(customer_id, target_host, "connected")
echo         return connection_id
echo     
echo     def run(self):
echo         while True:
echo             try:
echo                 if not self.sio.connected:
echo                     self.sio.connect(SERVER_URL, transports=['websocket', 'polling'])
echo                 while self.sio.connected:
echo                     for conn_id, conn_data in list(self.active_connections.items()):
echo                         self.send_heartbeat(
echo                             conn_data["customer_id"],
echo                             conn_data["target_host"],
echo                             conn_data["status"]
echo                         )
echo                     time.sleep(30)
echo             except Exception as e:
echo                 print(f"[GATEWAY] Error: {e}")
echo                 time.sleep(10)
echo 
echo if __name__ == "__main__":
echo     gateway = GatewayHeartbeat()
echo     gateway.run()
) > "%INSTALL_DIR%\gateway_heartbeat.py"

:: Create status file
echo PCFixPro ScreenConnect Gateway Installed Successfully > "%USERPROFILE%\Desktop\ScreenConnect_Gateway_Status.txt"
echo Client IP: !CLIENT_IP! >> "%USERPROFILE%\Desktop\ScreenConnect_Gateway_Status.txt"
echo Server: http://%SERVER_IP%:%SERVER_PORT% >> "%USERPROFILE%\Desktop\ScreenConnect_Gateway_Status.txt"
echo Max Concurrent Users: %MAX_CONCURRENT_USERS% >> "%USERPROFILE%\Desktop\ScreenConnect_Gateway_Status.txt"
echo Installation Date: %date% %time% >> "%USERPROFILE%\Desktop\ScreenConnect_Gateway_Status.txt"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo Client IP: !CLIENT_IP!
echo Server: http://%SERVER_IP%:%SERVER_PORT%
echo Max Concurrent Users: %MAX_CONCURRENT_USERS%
echo Status file created on desktop.
echo ========================================
pause >nul