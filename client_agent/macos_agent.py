"""
PCFixPro Remote Support Agent - macOS compatible
Runs on client PCs (Windows/macOS) and reports to the Command & Control Center
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
from datetime import datetime
import base64
from io import BytesIO
import socket

def get_local_ip():
    """Get local IP address"""
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
            "hostname": socket.gethostname(),
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
        return {"hostname": socket.gethostname(), "status": "online"}

class RemoteAgent:
    def __init__(self, server_url):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.agent_id = None
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
                    'output': result.stdout + result.stderr,
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
            """List files in directory"""
            path = data.get('path', '.')
            print(f"[AGENT] Listing files: {path}")
            
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
            remote_path = data.get('path', '.')
            
            print(f"[AGENT] Uploading file: {filename} to {remote_path}")
            
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
            """Delete file or directory"""
            file_path = data.get('path')
            print(f"[AGENT] Deleting: {file_path}")
            
            try:
                if os.path.isdir(file_path):
                    os.rmdir(file_path)
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
            """Take screenshot"""
            print(f"[AGENT] Taking screenshot...")
            
            try:
                # Try to use PIL/Pillow if available
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
    
    def connect(self):
        """Connect to C&C server with auto-reconnect"""
        while True:
            try:
                if not self.sio.connected:
                    print(f"[AGENT] Connecting to {self.server_url}...")
                    self.sio.connect(self.server_url, transports=['websocket', 'polling'])
                    
                    while self.sio.connected:
                        time.sleep(30)
                        if self.agent_id:
                            self.sio.emit('heartbeat', {'agent_id': self.agent_id})
            except Exception as e:
                print(f"[AGENT] Connection error: {e}. Reconnecting in 10s...")
                time.sleep(10)
    
    def run(self):
        """Start the agent"""
        print(f"[AGENT] Starting Remote Support Agent...")
        print(f"[AGENT] Hostname: {socket.gethostname()}")
        print(f"[AGENT] Local IP: {get_local_ip()}")
        print(f"[AGENT] Connecting to: {self.server_url}")
        
        self.connect()

if __name__ == "__main__":
    # Default server URL - can be overridden by environment variable
    SERVER_URL = os.environ.get('PCFIXPRO_SERVER_URL', 'http://192.168.100.253:5000')
    
    # If running as installed service/LaunchAgent, read config from install directory
    if hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle
        config_path = os.path.join(sys._MEIPASS, 'agent_config.txt')
    else:
        # Running from script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'agent_config.txt')
    
    # Try to read config file
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                if line.startswith('SERVER_URL='):
                    SERVER_URL = line.strip().split('=', 1)[1]
                    break
    
    agent = RemoteAgent(SERVER_URL)
    agent.run()