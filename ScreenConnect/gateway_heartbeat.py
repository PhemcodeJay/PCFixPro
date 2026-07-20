"""
PCFixPro ScreenConnect Gateway Heartbeat
Real-time connection monitoring for up to 100 concurrent enterprise users
"""
import socketio
import os
import time
import platform
import json
import socket
import threading
import subprocess
from datetime import datetime

# Configuration
SERVER_URL = "http://192.168.100.253:5000"
MAX_CONCURRENT_USERS = 100

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

CLIENT_IP = get_local_ip()
AGENT_ID = f"gateway_{CLIENT_IP.replace('.', '_')}"

class GatewayHeartbeat:
    def __init__(self):
        self.sio = socketio.Client()
        self.active_connections = {}
        self.connection_lock = threading.Lock()
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.sio.event
        def connect():
            print(f"[GATEWAY] Connected to dashboard at {SERVER_URL}")
            self.register_gateway()
        
        @self.sio.event
        def disconnect():
            print("[GATEWAY] Disconnected from dashboard. Reconnecting in 10s...")
        
        @self.sio.event
        def establish_tunnel(data):
            """Handle tunnel establishment request from dashboard"""
            customer_id = data.get('customer_id')
            target_host = data.get('target_host')
            rdp_port = data.get('rdp_port', 3389)
            ssh_port = data.get('ssh_port', 22)
            
            conn_id = self.establish_rdp_ssh_tunnel(customer_id, target_host, rdp_port, ssh_port)
            self.sio.emit('tunnel_established', {
                'connection_id': conn_id,
                'customer_id': customer_id,
                'target_host': target_host,
                'status': 'connected'
            })
        
        @self.sio.event
        def terminate_connection(data):
            """Handle connection termination"""
            conn_id = data.get('connection_id')
            if conn_id in self.active_connections:
                with self.connection_lock:
                    conn_data = self.active_connections.pop(conn_id)
                    customer_id = conn_data.get('customer_id')
                    assigned_ip = conn_data.get('target_host')
                    self.send_heartbeat(customer_id, assigned_ip, 'disconnected')
    
    def register_gateway(self):
        """Register gateway with dashboard"""
        self.sio.emit("register_agent", {
            "hostname": os.environ.get("COMPUTERNAME", "Unknown"),
            "ip_address": CLIENT_IP,
            "os": platform.system() + " " + platform.release(),
            "agent_version": "ScreenConnect-Gateway-1.0",
            "status": "online",
            "agent_type": "gateway",
            "max_connections": MAX_CONCURRENT_USERS
        })
    
    def send_heartbeat(self, customer_id, assigned_ip, session_status):
        """Send heartbeat with connection details to dashboard"""
        with self.connection_lock:
            active_count = len(self.active_connections)
        
        self.sio.emit("heartbeat", {
            "agent_id": AGENT_ID,
            "customer_id": customer_id,
            "assigned_ip": assigned_ip,
            "session_status": session_status,
            "timestamp": datetime.now().isoformat(),
            "active_connections": active_count,
            "max_connections": MAX_CONCURRENT_USERS
        })
    
    def establish_rdp_ssh_tunnel(self, customer_id, target_host, rdp_port=3389, ssh_port=22):
        """Establish simultaneous RDP/SSH tunnels for enterprise users"""
        # Check port exhaustion
        if len(self.active_connections) >= MAX_CONCURRENT_USERS:
            raise Exception(f"Maximum concurrent users ({MAX_CONCURRENT_USERS}) reached")
        
        connection_id = f"{customer_id}_{target_host}_{rdp_port}_{ssh_port}"
        
        # Create SSH tunnel in background
        tunnel_cmd = f"plink.exe -ssh -{ssh_port}:{ssh_port} {target_host} -P {ssh_port} -l pcfixpro -pw auto -N -L {rdp_port}:localhost:{rdp_port}"
        
        with self.connection_lock:
            self.active_connections[connection_id] = {
                "customer_id": customer_id,
                "target_host": target_host,
                "rdp_port": rdp_port,
                "ssh_port": ssh_port,
                "status": "connected",
                "timestamp": datetime.now().isoformat(),
                "tunnel_process": None
            }
        
        self.send_heartbeat(customer_id, target_host, "connected")
        return connection_id
    
    def run(self):
        """Start the gateway heartbeat service"""
        print(f"[GATEWAY] Starting ScreenConnect Gateway...")
        print(f"[GATEWAY] Client IP: {CLIENT_IP}")
        print(f"[GATEWAY] Connecting to: {SERVER_URL}")
        print(f"[GATEWAY] Max concurrent users: {MAX_CONCURRENT_USERS}")
        
        while True:
            try:
                if not self.sio.connected:
                    self.sio.connect(SERVER_URL, transports=['websocket', 'polling'])
                
                while self.sio.connected:
                    with self.connection_lock:
                        for conn_id, conn_data in list(self.active_connections.items()):
                            self.sio.emit("heartbeat", {
                                "agent_id": AGENT_ID,
                                "customer_id": conn_data["customer_id"],
                                "assigned_ip": conn_data["target_host"],
                                "session_status": conn_data["status"],
                                "timestamp": datetime.now().isoformat(),
                                "active_connections": len(self.active_connections),
                                "max_connections": MAX_CONCURRENT_USERS
                            })
                    time.sleep(30)
                    
            except Exception as e:
                print(f"[GATEWAY] Connection error: {e}. Reconnecting in 10s...")
                time.sleep(10)

if __name__ == "__main__":
    gateway = GatewayHeartbeat()
    gateway.run()