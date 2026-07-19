@echo off
REM PCFixPro Remote Support Agent Installer
REM This script installs the agent on Windows client PCs

setlocal enabledelayedexpansion

echo ========================================
echo PCFixPro Remote Support Agent Setup
echo ========================================
echo.

REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with administrator privileges
) else (
    echo [ERROR] Please run this script as Administrator!
    pause
    exit /b 1
)

REM Set installation directory
set "INSTALL_DIR=C:\Program Files\PCFixPro Agent"
set "SERVICE_NAME=PCFixProAgent"

echo.
echo Installing PCFixPro Remote Support Agent...
echo Installation directory: %INSTALL_DIR%

REM Create installation directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

REM Copy agent files
echo [1/5] Copying agent files...
echo. > agent.log

REM Create virtual environment
echo [2/5] Setting up Python environment...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python is not installed! Please install Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python found

REM Install dependencies
echo [3/5] Installing dependencies...
pip install -r requirements.txt --quiet
if %errorLevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Configure agent
echo [4/5] Configuring agent...
set /p SERVER_IP=Enter C&C Server IP (default: 192.168.100.253): 
if "%SERVER_IP%"=="" set SERVER_IP=192.168.100.253

REM Update configuration in agent.py
powershell -Command "(Get-Content agent.py) -replace 'SERVER_URL = \".*\"', 'SERVER_URL = \"http://%SERVER_IP%:5000\"' | Set-Content agent.py"
echo [OK] Configuration saved

REM Install as Windows Service
echo [5/5] Installing as Windows Service...
pip install pywin32 --quiet
python install_service.py

if %errorLevel% neq 0 (
    echo [WARNING] Service installation failed, running in user mode
    REM Start agent in background
    start /B pythonw.exe agent.py
) else (
    echo [OK] Service installed and started
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo The agent will now automatically:
echo - Connect to C&C Server at http://%SERVER_IP%:5000
echo - Report system status
echo - Execute remote commands
echo - Appear in your Command Center
echo.
echo View logs at: %INSTALL_DIR%\agent.log
echo.
pause