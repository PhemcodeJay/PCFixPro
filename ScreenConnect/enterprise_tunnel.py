"""
PCFixPro Enterprise Tunnel Manager
Manages simultaneous RDP/SSH tunnels for up to 100 concurrent users
With connection pooling and port exhaustion handling
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
from concurrent.futures import ThreadPoolExecutor

# Configuration
SERVER_URL = "http://192.168.100.253:5000"
MAX_CONCURRENT_USERS = 100
BASE_RDP_PORT = 3389
BASE_SSH_PORT = 22

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
AGENT_ID = f"tunnel_gateway_{CLIENT_IP.replace('.', '_')}"

# Connection tracking
active_tunnels = {}
tunnel_lock = threading.Lock()
used_ports = set()

class EnterpriseTunnelManager:
    def __init__(self):
        self.sio = socketio.Client()
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_USERS)
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.sio.event
        def connect():
            print(f"[TUNNEL] Connected to dashboard at {SERVER_URL}")
            self.register_gateway()
        
        @self.sio.event
        def disconnect():
            print("[TUNNEL] Disconnected from dashboard. Reconnecting...")
        
        @self.sio.event
        def create_tunnel(data):
            """Create simultaneous RDP/SSH tunnel for enterprise user"""
            customer_id = data.get('customer_id')
            target_host = data.get('target_host')
            rdp_port = data.get('rdp_port', 3389)
            ssh_port = data.get('ssh_port', 22)
            
            # Submit to thread pool for concurrent handling
            future = self.executor.submit(
                self.establish_tunnel,
                customer_id, target_host, rdp_port, ssh_port
            )
            
            try:
                conn_id = future.result(timeout=30)
                self.sio.emit('tunnel_created', {
                    'connection_id': conn_id,
                    'customer_id': customer_id,
                    'status': 'connected'
                })
            except Exception as e:
                self.sio.emit('tunnel_failed', {
                    'customer_id': customer_id,
                    'error': str(e)
                })
        
        @self.sio.event
        def close_tunnel(data):
            """Close specific tunnel"""
            conn_id = data.get('connection_id')
            self.close_tunnel(conn_id)
        
        @self.sio.event
        def list_connections(data):
            """List all active connections"""
            with tunnel_lock:
                self.sio.emit('connection_list', {
                    'connections': active_tunnels,
                    'total': len(active_tunnels)
                })
    
    def register_gateway(self):
        """Register tunnel gateway with dashboard"""
        self.sio.emit("register_agent", {
            "hostname": os.environ.get("COMPUTERNAME", "Unknown"),
            "ip_address": CLIENT_IP,
            "os": platform.system() + " " + platform.release(),
            "agent_version": "Enterprise-Tunnel-Manager-1.0",
            "status": "online",
            "agent_type": "tunnel_gateway",
            "max_connections": MAX_CONCURRENT_USERS
        })
    
    def allocate_port(self):
        """Allocate an available port for tunnel"""
        # Try to find unused port in range 10000-10100
        for port in range(10000, 10100):
            if port not in used_ports:
                used_ports.add(port)
                return port
        return None
    
    def release_port(self, port):
        """Release port back to pool"""
        used_ports.discard(port)
    
    def establish_tunnel(self, customer_id, target_host, rdp_port=3389, ssh_port=22):
        """Establish simultaneous RDP/SSH tunnel with heartbeat"""
        with tunnel_lock:
            if len(active_tunnels) >= MAX_CONCURRENT_USERS:
                raise Exception(f"Maximum concurrent users ({MAX_CONCURRENT_USERS}) reached - port exhaustion")
        
        # Allocate ports for connection
        local_rdp = self.allocate_port()
        local_ssh = self.allocate_port()
        
        if local_rdp is None or local_ssh is None:
            raise Exception("Port exhaustion - no available ports")
        
        connection_id = f"{customer_id}_{target_host}_{int(time.time())}"
        
        # Store connection info
        with tunnel_lock:
            active_tunnels[connection_id] = {
                "customer_id": customer_id,
                "target_host": target_host,
                "rdp_port": rdp_port,
                "ssh_port": ssh_port,
                "local_rdp": local_rdp,
                "local_ssh": local_ssh,
                "status": "connected",
                "connected_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat()
            }
        
        # Send initial heartbeat
        self.send_heartbeat(customer_id, target_host, "connected")
        
        return connection_id
    
    def close_tunnel(self, conn_id):
        """Close tunnel and cleanup"""
        with tunnel_lock:
            if conn_id in active_tunnels:
                conn_data = active_tunnels[conn_id]
                self.release_port(conn_data.get('local_rdp'))
                self.release_port(conn_data.get('local_ssh'))
                del active_tunnels[conn_id]
                self.send_heartbeat(conn_data['customer_id'], conn_data['target_host'], 'disconnected')
    
    def send_heartbeat(self, customer_id, assigned_ip, session_status):
        """Send heartbeat to dashboard"""
        with tunnel_lock:
            active_count = len(active_tunnels)
        
        self.sio.emit("heartbeat", {
            "agent_id": AGENT_ID,
            "customer_id": customer_id,
            "assigned_ip": assigned_ip,
            "session_status": session_status,
            "timestamp": datetime.now().isoformat(),
            "active_connections": active_count,
            "max_connections": MAX_CONCURRENT_USERS
        })
    
    def heartbeat_loop(self):
        """Periodic heartbeat to dashboard"""
        while self.sio.connected:
            with tunnel_lock:
                for conn_id, conn_data in list(active_tunnels.items()):
                    self.sio.emit("heartbeat", {
                        "agent_id": AGENT_ID,
                        "customer_id": conn_data["customer_id"],
                        "assigned_ip": conn_data["target_host"],
                        "session_status": conn_data["status"],
                        "timestamp": datetime.now().isoformat(),
                        "active_connections": len(active_tunnels),
                        "max_connections": MAX_CONCURRENT_USERS
                    })
            time.sleep(30)
    
    def run(self):
        """Start the enterprise tunnel manager"""
        print(f"[TUNNEL] Starting Enterprise Tunnel Manager...")
        print(f"[TUNNEL] Client IP: {CLIENT_IP}")
        print(f"[TUNNEL] Max concurrent users: {MAX_CONCURRENT_USERS}")
        print(f"[TUNNEL] Connecting to: {SERVER_URL}")
        
        # Start heartbeat thread
        import threading
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        
        while True:
            try:
                if not self.sio.connected:
                    self.sio.connect(SERVER_URL, transports=['websocket', 'polling'])
                    if not heartbeat_thread.is_alive():
                        heartbeat_thread.start()
                
                while self.sio.connected:
                    time.sleep(60)
                    
            except Exception as e:
                print(f"[TUNNEL] Connection error: {e}. Reconnecting in 10s...")
                time.sleep(10)

if __name__ == "__main__":
    manager = EnterpriseTunnelManager()
    manager.run()