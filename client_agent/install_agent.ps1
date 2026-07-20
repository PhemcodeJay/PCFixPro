# PCFixPro Remote Support Agent - MSI/PowerShell Installer
# This script creates the MSI and installs the agent

param(
    [string]$ServerIP = "102.209.236.22"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PCFixPro Remote Support Agent Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for administrator privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[ERROR] Please run this script as Administrator!" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Running with administrator privileges" -ForegroundColor Green

# Configuration
$installDir = "$env:ProgramFiles\PCFixPro Agent"
$agentSource = Join-Path $PSScriptRoot "agent"
$serverUrl = "http://$ServerIP`:5000"

Write-Host ""
Write-Host "Installing PCFixPro Remote Support Agent..." -ForegroundColor Yellow
Write-Host "Server URL: $serverUrl" -ForegroundColor Gray
Write-Host "Install Dir: $installDir" -ForegroundColor Gray

# Create installation directory
if (-not (Test-Path $installDir)) {
    New-Item -Path $installDir -ItemType Directory -Force | Out-Null
}
Set-Location $installDir

# Copy agent files
Write-Host "[1/5] Copying agent files..." -ForegroundColor Yellow
Copy-Item "$agentSource\agent.py" -Destination "agent.py" -Force
Copy-Item "$agentSource\requirements.txt" -Destination "requirements.txt" -Force
Copy-Item "$agentSource\install_service.py" -Destination "install_service.py" -Force

# Create startup script
$startupBat = @"
@echo off
cd /d "$installDir"
start /B pythonw.exe agent.py
"@
$startupBat | Out-File -FilePath "start_agent.bat" -Encoding ASCII

# Create uninstaller
$uninstallBat = @"
@echo off
echo Uninstalling PCFixPro Agent...
net stop PCFixProAgent 2>nul
sc delete PCFixProAgent 2>nul
rmdir /s /q "$installDir" 2>nul
echo Uninstall complete.
pause
"@
$uninstallBat | Out-File -FilePath "uninstall.bat" -Encoding ASCII

# Install Python dependencies
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Yellow
python --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python is not installed!" -ForegroundColor Red
    exit 1
}

pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# Configure agent
Write-Host "[3/5] Configuring agent..." -ForegroundColor Yellow
(Get-Content "agent.py") -replace 'SERVER_URL = "http://[^"]+"', "SERVER_URL = `"$serverUrl`"" | Set-Content "agent.py"
Write-Host "[OK] Configuration saved" -ForegroundColor Green

# Install Windows Service
Write-Host "[4/5] Installing Windows Service..." -ForegroundColor Yellow
pip install pywin32 --quiet | Out-Null

# Create service wrapper
$serviceWrapper = @"
import win32service
import win32serviceutil
import win32event
import servicemanager
import sys
import os

sys.path.insert(0, r'$installDir')

class AgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'PCFixProAgent'
    _svc_display_name_ = 'PCFixPro Remote Support Agent'
    _svc_description_ = 'Runs PCFixPro remote support agent in background'
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                             servicemanager.PYS_SERVICE_STARTED,
                             (self._svc_name_, ''))
        try:
            from agent import RemoteAgent
            agent = RemoteAgent()
            agent.run()
        except Exception as e:
            servicemanager.LogErrorMsg(str(e))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AgentService)
"@
$serviceWrapper | Out-File -FilePath "install_service.py" -Encoding UTF8

# Try to install service
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
python install_service.py install | Out-Null

if ($LASTEXITCODE -eq 0) {
    python install_service.py start | Out-Null
    Write-Host "[OK] Service installed and started" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Service installation failed, using alternative startup" -ForegroundColor Yellow
    # Add to startup folder
    $startupFolder = [Environment]::GetFolderPath('Startup')
    $shortcutPath = Join-Path $startupFolder "PCFixPro Agent.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.WorkingDirectory = $installDir
    $shortcut.TargetPath = "pythonw.exe"
    $shortcut.Arguments = "`"$installDir\agent.py`""
    $shortcut.Save()
    Write-Host "[OK] Added to startup folder" -ForegroundColor Green
    
    # Start immediately
    Start-Process -FilePath "pythonw.exe" -ArgumentList "`"$installDir\agent.py`"" -WindowStyle Hidden
}

# Create firewall exception
Write-Host "[5/5] Configuring firewall..." -ForegroundColor Yellow
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=out action=allow program="pythonw.exe" enable=yes | Out-Null
Write-Host "[OK] Firewall rule added" -ForegroundColor Green

# Completion
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "The agent is now active and will:" -ForegroundColor White
Write-Host "  - Connect to C&C Server at $serverUrl" -ForegroundColor Gray
Write-Host "  - Report system status automatically" -ForegroundColor Gray
Write-Host "  - Appear in your Command & Control Center" -ForegroundColor Gray
Write-Host "  - Execute remote commands when authorized" -ForegroundColor Gray
Write-Host ""
Write-Host "To uninstall, run: uninstall.bat" -ForegroundColor Yellow
Write-Host ""

pause