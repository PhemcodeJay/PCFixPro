"""
Windows Service Installer for PCFixPro Agent
"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class PCFixProAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PCFixProAgent"
    _svc_display_name_ = "PCFixPro Remote Support Agent"
    _svc_description_ = "Remote support agent for PCFixPro Command & Control Center"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.agent_process = None
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Import and run agent
        try:
            from agent import RemoteAgent
            agent = RemoteAgent()
            agent.run()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Agent error: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PCFixProAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PCFixProAgentService)