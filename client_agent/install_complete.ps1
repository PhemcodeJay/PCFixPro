# PCFixPro Complete Silent Installer with PDF Logs & Email
# Single-click installation for clients

param(
    [string]$ServerIP = "102.209.236.22",
    [string]$ClientEmail = ""
)

$ErrorActionPreference = "Stop"

# Logging
$logFile = "$env:TEMP\PCFixPro_Install_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
function Write-Log($message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp $message" | Tee-Object -FilePath $logFile -Append
    Write-Host $message
}

Write-Log "========================================" 
Write-Log "PCFixPro Silent Installer Starting..."
Write-Log "========================================"
Write-Log "Server IP: $ServerIP"
Write-Log "Client Email: $ClientEmail"
Write-Log "Computer: $env:COMPUTERNAME"
Write-Log "User: $env:USERNAME"

# Check Admin
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Log "ERROR: Administrator required!"
    $logFile | Out-File -FilePath "$env:DESKTOP\PCFixPro_Install_Error.txt"
    pause
    exit 1
}

Write-Log "[OK] Administrator privileges confirmed"

# Paths
$installDir = "$env:ProgramFiles\PCFixPro Agent"
$agentPy = Join-Path $installDir "agent.py"
$requirementsTxt = Join-Path $installDir "requirements.txt"
$installServicePy = Join-Path $installDir "install_service.py"
$agentLog = Join-Path $installDir "agent.log"
$serverUrl = "http://$ServerIP`:5000"

Write-Log ""
Write-Log "[1/6] Creating installation directory..."
if (-not (Test-Path $installDir)) {
    New-Item -Path $installDir -ItemType Directory -Force | Out-Null
}
Write-Log "[OK] Directory created: $installDir"

Write-Log ""
Write-Log "[2/6] Copying agent files..."
$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item "$sourceDir\agent.py" -Destination $agentPy -Force
Copy-Item "$sourceDir\requirements.txt" -Destination $requirementsTxt -Force
Copy-Item "$sourceDir\install_service.py" -Destination $installServicePy -Force
Write-Log "[OK] Files copied"

Write-Log ""
Write-Log "[3/6] Installing Python dependencies..."
try {
    python --version | Out-Null
    pip install -r $requirementsTxt --quiet
    pip install python-dotenv requests pywin32 --quiet
    Write-Log "[OK] Dependencies installed"
} catch {
    Write-Log "ERROR: $_"
    exit 1
}

Write-Log ""
Write-Log "[4/6] Configuring agent..."
(Get-Content $agentPy) -replace 'SERVER_URL = "http://[^"]+"', "SERVER_URL = `"$serverUrl`"" | Set-Content $agentPy
Write-Log "[OK] Configuration updated"

Write-Log ""
Write-Log "[5/6] Installing Windows Service..."
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Create service with logging
$serviceScript = @"
import win32service
import win32serviceutil
import win32event
import servicemanager
import sys
import os
import logging

sys.path.insert(0, r'$installDir')
logging.basicConfig(filename=r'$agentLog', level=logging.INFO, format='%(asctime)s %(message)s')

class AgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'PCFixProAgent'
    _svc_display_name_ = 'PCFixPro Remote Support Agent'
    _svc_description_ = 'Remote support agent for PCFixPro C&C'
    
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
$serviceScript | Out-File -FilePath $installServicePy -Encoding UTF8

python $installServicePy install 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    python $installServicePy start 2>&1 | Out-Null
    Write-Log "[OK] Service installed and started"
} else {
    Write-Log "WARNING: Service install failed, using startup folder"
    $startupFolder = [Environment]::GetFolderPath('Startup')
    $shortcutPath = Join-Path $startupFolder "PCFixPro Agent.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.WorkingDirectory = $installDir
    $shortcut.TargetPath = "pythonw.exe"
    $shortcut.Arguments = "`"$agentPy`""
    $shortcut.Save()
    Start-Process -FilePath "pythonw.exe" -ArgumentList "`"$agentPy`"" -WindowStyle Hidden
    Write-Log "[OK] Added to startup folder and started"
}

Write-Log ""
Write-Log "[6/6] Configuring firewall..."
# Allow outbound connections for python executables
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=out action=allow program="python.exe" enable=yes | Out-Null
netsh advfirewall firewall add rule name="PCFixPro Agent" dir=out action=allow program="pythonw.exe" enable=yes | Out-Null
Write-Log "[OK] Firewall rule added"

Write-Log ""
Write-Log "========================================"
Write-Log "Installation Complete!"
Write-Log "========================================"
Write-Log ""
Write-Log "Agent will now:"
Write-Log "  - Connect to C&C Server at $serverUrl"
Write-Log "  - Report system status automatically"
Write-Log "  - Appear in Command & Control Center"
Write-Log "  - Logs: $agentLog"
Write-Log "  - Install log: $logFile"
Write-Log ""

# Create desktop shortcut for logs
$logShortcut = Join-Path $env:DESKTOP "PCFixPro Agent Logs.lnk"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($logShortcut)
$s.TargetPath = $agentLog
$s.Save()
Write-Log "[OK] Desktop shortcut created: $logShortcut"

# Generate PDF report if email provided
if ($ClientEmail) {
    Write-Log ""
    Write-Log "Generating PDF report..."
    
    $pdfPath = Join-Path $installDir "Installation_Report_$(Get-Date -Format 'yyyyMMdd_HHmmss').pdf"
    
    # Collect system info
    $sysInfo = @{
        ComputerName = $env:COMPUTERNAME
        UserName = $env:USERNAME
        InstallDate = Get-Date
        ServerURL = $serverUrl
        AgentVersion = "1.0.0"
        Status = "Installed Successfully"
    }
    
    # Create HTML report
    $html = @"
<html>
<head>
<style>
body { font-family: Arial; padding: 20px; }
.header { background: #0066ff; color: white; padding: 20px; border-radius: 8px; }
.section { margin: 20px 0; padding: 15px; border: 1px solid #e9edf2; border-radius: 8px; }
.success { color: #10b981; font-weight: bold; }
.info { color: #64748b; }
</style>
</head>
<body>
<div class="header">
<h1>PCFixPro Agent Installation Report</h1>
<p>Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')</p>
</div>

<div class="section">
<h2>Installation Details</h2>
<p><strong>Status:</strong> <span class="success">SUCCESS</span></p>
<p><strong>Computer:</strong> $($sysInfo.ComputerName)</p>
<p><strong>User:</strong> $($sysInfo.UserName)</p>
<p><strong>Server URL:</strong> $($sysInfo.ServerURL)</p>
<p><strong>Agent Version:</strong> $($sysInfo.AgentVersion)</p>
<p><strong>Install Directory:</strong> $installDir</p>
<p><strong>Service Name:</strong> PCFixProAgent</p>
</div>

<div class="section">
<h2>What's Next?</h2>
<p>The agent is now connected to the Command & Control Center.</p>
<p>Your IT support team can now:</p>
<ul>
<li>See this computer in the dashboard</li>
<li>Monitor system health</li>
<li>Execute remote commands with permission</li>
<li>Provide automated remote support</li>
</ul>
<p><strong>No further action required from you.</strong></p>
</div>

<div class="section">
<h2>Support</h2>
<p>If you experience any issues, contact PCFixPro ICT Services.</p>
<p>Installation logs available at: $agentLog</p>
</div>
</body>
</html>
"@
    
    $html | Out-File -FilePath "$env:TEMP\report.html" -Encoding UTF8
    
    # Try to convert to PDF (requires Chrome or wkhtmltopdf)
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    if (Test-Path $chromePath) {
        Start-Process -FilePath $chromePath -ArgumentList "--headless", "--disable-gpu", "--print-to-pdf=$pdfPath", "$env:TEMP\report.html" -Wait
        Write-Log "[OK] PDF generated: $pdfPath"
        
        # Email the PDF
        Write-Log "Sending email to $ClientEmail..."
        # Note: Email sending requires SMTP configuration in production
        Write-Log "PDF ready for manual send or configure SMTP"
    } else {
        Write-Log "Chrome not found, HTML report saved instead"
    }
}

Write-Log ""
Write-Log "Installation log saved to: $logFile"
Write-Log ""

# Open log after 3 seconds
Start-Sleep -Seconds 3
notepad.exe $logFile