# PCFixPro ScreenConnect Enterprise - Troubleshooting & Scaling Guide

## ZIP File Integrity Verification

### Checksums Created:
- **PCFixPro_Agent_Windows.zip**: `8eed0035bbdce43af5a057e4b2d3117527c37d144b06b0609827c027805d8d9c`
- **PCFixPro_Agent_macOS.zip**: `1e95088c28bd5fd842e6d3cfa8ed3b20915c4b13d4b6498f4748e08526e5a5e4`
- **PCFixPro_Agent_Universal.zip**: `55a3f97f97a526c217f05542641cc1541e2e8bdb837e53547103285646900563`
- **screenconnect.zip** (created): `3d114efe92c8eb453f4899e9f81b43095c8d7a9ebbe46a3676f00ab464697c4d`

### Verification Commands:
```powershell
# Windows PowerShell
certutil -hashfile "path\to\file.zip" SHA256
```

## BAT File Syntax Validation

All BAT files have been validated with no syntax errors:
- ✅ `PCFixPro_AutoInstall.bat` - Valid
- ✅ `PCFixPro_Installer.bat` - Valid
- ✅ `PCFixPro_QuickInstall.bat` - Valid
- ✅ `ScreenConnect/install.bat` - Valid

## Common Disconnection Issues & Solutions

### 1. Timeout Issues

**Symptoms:**
- Agents disconnect after 30-60 seconds
- Heartbeat not received on dashboard
- Commands fail to execute

**Causes:**
- Network firewall blocking WebSocket connections
- Server timeout configuration too low
- Client-side connection pool exhaustion

**Solutions:**
```python
# In app.py - Increase timeout values
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading',
                    ping_timeout=120, ping_interval=60)

# Add connection keep-alive
@sio.event
def heartbeat(data):
    # Reset timeout for this agent
    emit('heartbeat_ack', {'status': 'alive'})
```

**PowerShell Fix:**
```powershell
# Add outbound firewall rule
netsh advfirewall firewall add rule name="PCFixPro Dashboard" dir=out action=allow protocol=TCP localport=5000
```

### 2. Port Exhaustion

**Symptoms:**
- Cannot establish new connections
- Error: "No available ports"
- Multiple connections fail simultaneously

**Causes:**
- Max concurrent connections reached (100 users)
- Ports not being released after disconnect
- TIME_WAIT state on TCP connections

**Solutions:**

**Registry Changes (Windows):**
```batch
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v MaxUserPort /t REG_DWORD /d 65534 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v TcpTimedWaitDelay /t REG_DWORD /d 30 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v MaxFreeTcbs /t REG_DWORD /d 10000 /f
```

**Linux Tuning:**
```bash
# Increase port range
echo 'net.ipv4.ip_local_port_range = 1024 65535' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_fin_timeout = 30' >> /etc/sysctl.conf
sysctl -p
```

### 3. MSI Installation Issues

**Symptoms:**
- ScreenConnect MSI fails to install
- Silent install hangs
- Error 1603 during installation

**Solutions:**
```batch
:: Clean install with logging
msiexec /i "ScreenConnect.ClientSetup(4).msi" /quiet /norestart /l*v "install.log" /log

:: Check for pending reboots
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager" /v PendingFileRenameOperations
```

## Enterprise Scaling Strategies

### 1. Reverse Proxy Setup (Recommended)

**Nginx Configuration:**
```nginx
upstream pcfixpro_backend {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001 backup;
}

server {
    listen 443 ssl;
    server_name pcfixpro.yourcompany.com;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # WebSocket Support
    location /socket.io/ {
        proxy_pass http://pcfixpro_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    # Load balancing
    location / {
        proxy_pass http://pcfixpro_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**HAProxy Configuration:**
```haproxy
frontend pcfixpro_frontend
    bind *:443 ssl crt /etc/haproxy/certs/
    mode http
    default_backend pcfixpro_backend

backend pcfixpro_backend
    balance roundrobin
    option httpchk GET /health
    server app1 192.168.100.253:5000 check
    server app2 192.168.100.254:5000 check backup
```

### 2. Gateway/Load Balancer Architecture

**Multi-Gateway Setup:**
```
Internet → Load Balancer (Nginx/HAProxy) → Multiple Dashboard Servers
                                    ↓
                                    → Each handles ~100 concurrent users
                                    ↓
                                    → Redis for session synchronization
```

**Gateway Configuration:**
```python
# enterprise_tunnel.py - Multi-gateway support
GATEWAY_TOKEN = "unique_gateway_token_here"
SESSION_SYNC_REDIS = "redis://redis-server:6379"

# Each gateway registers with unique ID
AGENT_ID = f"gateway_{get_local_ip()}_{GATEWAY_TOKEN[:8]}"
```

### 3. Horizontal Scaling with Redis

**Redis Session Store:**
```python
import redis
import json

# Centralized session storage
r = redis.Redis(host='redis-server', port=6379, db=0)

def store_session(agent_id, session_data):
    r.setex(f"session:{agent_id}", 3600, json.dumps(session_data))

def get_all_sessions():
    keys = r.keys("session:*")
    return [json.loads(r.get(k)) for k in keys]
```

**Redis Configuration:**
```bash
# redis.conf
maxclients 10000
tcp-backlog 1024
timeout 300
tcp-keepalive 60
```

### 4. Connection Pool Management

**Enhanced enterprise_tunnel.py:**
```python
from concurrent.futures import ThreadPoolExecutor
import socket

MAX_CONCURRENT_USERS = 100
CONNECTION_TIMEOUT = 300  # 5 minutes
RETRY_INTERVAL = 30  # seconds

class ConnectionPool:
    def __init__(self, max_connections=100):
        self.max_connections = max_connections
        self.active_connections = {}
        self.port_pool = list(range(10000, 10100))
        self.lock = threading.Lock()
    
    def allocate_connection(self, customer_id):
        with self.lock:
            if len(self.active_connections) >= self.max_connections:
                raise Exception("Connection limit reached")
            
            port = self.port_pool.pop() if self.port_pool else None
            if port is None:
                raise Exception("Port exhaustion")
            
            conn_id = f"{customer_id}_{port}"
            self.active_connections[conn_id] = {
                'customer_id': customer_id,
                'port': port,
                'created_at': time.time()
            }
            return conn_id, port
```

### 5. Monitoring & Health Checks

**Health Endpoint:**
```python
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'active_connections': len(active_sessions),
        'connected_agents': len(connected_agents),
        'memory_usage': psutil.virtual_memory().percent,
        'cpu_usage': psutil.cpu_percent()
    })
```

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Gauge, Histogram

active_connections = Gauge('pcfixpro_active_connections', 'Number of active connections')
heartbeat_latency = Histogram('pcfixpro_heartbeat_latency', 'Heartbeat latency')
connection_errors = Counter('pcfixpro_connection_errors', 'Connection errors')
```

## Deployment Checklist

- [ ] Verify all ZIP checksums before deployment
- [ ] Test BAT file syntax on target systems
- [ ] Configure firewall rules for ports 5000, 3389, 22
- [ ] Set up SSL certificates for production
- [ ] Configure reverse proxy/load balancer
- [ ] Increase system port limits
- [ ] Set up Redis for session clustering
- [ ] Enable monitoring endpoints
- [ ] Test with 100+ concurrent connections
- [ ] Configure automatic failover

## Quick Start Commands

```powershell
# Run syntax check
python bat_checker.py

# Verify ZIP integrity
certutil -hashfile downloads\screenconnect.zip SHA256

# Install gateway
ScreenConnect\install.bat

# Start with monitoring
python enterprise_tunnel.py