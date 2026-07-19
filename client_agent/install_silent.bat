@echo off
REM PCFixPro Silent Agent Installer
REM Fully automated installation with logging

setlocal

REM Configuration - EDIT THESE VALUES
set SERVER_IP=192.168.100.253
set INSTALL_DIR=C:\Program Files\PCFixPro Agent
set LOG_FILE=%INSTALL_DIR%\install.log
set DESKTOP=%USERPROFILE%\Desktop

echo [%date% %time%] Starting silent installation... > "%LOG_FILE%"

REM Check administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [%date% %time%] ERROR: Administrator required >> "%LOG_FILE%"
    pause
    exit /b 1
)

echo [%date% %time%] Administrator privileges confirmed >> "%LOG_FILE%"

REM Install Python dependencies silently
echo [%date% %time%] Installing dependencies... >> "%LOG_FILE%"
pip install python-socketio requests pywin32 --quiet >> "%LOG_FILE%" 2>&1

if %errorLevel% neq 0 (
    echo [%date% %time%] ERROR: Failed to install dependencies >> "%LOG_FILE%"
    pause
    exit /b 1
)

echo [%date% %time%] Dependencies installed >> "%LOG_FILE%"

REM Create install directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy agent files
copy /Y "%~dp0agent.py" "%INSTALL_DIR%\agent.py" >> "%LOG_FILE%"
copy /Y "%~dp0requirements.txt" "%INSTALL_DIR%\requirements.txt" >> "%LOG_FILE%"
copy /Y "%~dp0install_service.py" "%INSTALL_DIR%\install_service.py" >> "%LOG_FILE%"

echo [%date% %time%] Agent files copied >> "%LOG_FILE%"

REM Configure server URL
powershell -Command "(Get-Content '%INSTALL_DIR%\agent.py') -replace 'SERVER_URL = \".*\"', 'SERVER_URL = \"http://%SERVER_IP%:5000\"' | Set-Content '%INSTALL_DIR%\agent.py'" >> "%LOG_FILE%" 2>&1

echo [%date% %time%] Configuration updated >> "%LOG_FILE%"

REM Install service
cd /d "%INSTALL_DIR%"
python install_service.py install >> "%LOG_FILE%" 2>&1

if %errorLevel% equ 0 (
    python install_service.py start >> "%LOG_FILE%" 2>&1
    echo [%date% %time%] Service installed and started >> "%LOG_FILE%"
) else (
    echo [%date% %time%] Service install failed, using startup folder >> "%LOG_FILE%"
    pythonw.exe agent.py
)

REM Create firewall rule
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=in action=allow program="%INSTALL_DIR%\pythonw.exe" enable=yes >> "%LOG_FILE%" 2>&1

REM Create desktop shortcut to logs
echo [%date% %time%] Creating desktop shortcut... >> "%LOG_FILE%"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\PCFixPro Agent Logs.lnk'); $s.TargetPath = '%INSTALL_DIR%\agent.log'; $s.Save()"

echo [%date% %time%] Installation complete >> "%LOG_FILE%"
echo.
echo Installation complete!
echo Server: http://%SERVER_IP%:5000
echo Logs: %INSTALL_DIR%\agent.log
echo.
pause