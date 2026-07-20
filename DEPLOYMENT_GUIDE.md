# PCFixPro ScreenConnect Enterprise - Complete Deployment Guide

## Executive Summary

This system provides enterprise-grade remote access with:
- **100 concurrent user support** via RDP/SSH tunnels
- **Real-time heartbeat monitoring** to dashboard
- **Auto-executable deployment package** (screenconnect.zip)
- **Enterprise scaling** with reverse proxy support

---

## System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client PC     │     │   Client PC     │     │   Client PC     │
│  (192.168.1.x)│     │  (192.168.1.x)│     │  (192.168.1.x)│
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │ install.bat            │ gateway_heartbeat.py │ enterprise_   
         ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FLASK DASHBOARD SERVER                          │
│                    (192.168.100.253:5000)                         │
│                          - Heartbeat Handler                         │
│                          - Session Management                         │
│                          - Real-time WebSocket                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                   http://192.168.100.253:5000
                                │
                                ▼
                    ┌─────────────────────────┐
                    │      Web Browser          │
                    │   Real-time Dashboard   │
                    └─────────────────────────┘
```

---

## How It Works

### 1. Connection Flow

**Step 1: Client Installation**
- Client runs `install.bat` (requires admin privileges)
- ScreenConnect MSI installs silently
- Gateway heartbeat script configures tunnels

**Step 2: Agent Registration**
- Client connects to `http://192.168.100.253:5000`
- Sends `register_agent` event with:
  - Hostname, IP address, OS version
  - Agent type (gateway/tunnel_manager)

**Step 3: Heartbeat Monitoring**
- Every 30 seconds, agent sends heartbeat:
  ```json
  {
    "agent_id": "gateway_192_168_1_100",
    "customer_id": "customer_1234",
    "assigned_ip": "192.168.1.50",
    "session_status": "connected",
    "active_connections": 1,
    "max_connections": 100
  }
  ```

**Step 4: Dashboard Display**
- Dashboard receives heartbeat via WebSocket
- Updates agent status in real-time
- Shows active connections count

---

## Files Explanation

### ScreenConnect/install.bat
**Purpose:** Main installation script
- Auto-elevates to Administrator privileges
- Installs ScreenConnect MSI silently (`/quiet /norestart`)
- Creates SSH/RDP tunnel configurations
- Generates heartbeat monitor script

### ScreenConnect/gateway_heartbeat.py
**Purpose:** Real-time connection monitoring
- Auto-detects server IP (localhost or configured)
- Manages up to 100 concurrent connections
- Port allocation (10000-10100 range)
- Thread-safe connection tracking

### ScreenConnect/enterprise_tunnel.py
**Purpose:** Tunnel management for enterprise scale
- ThreadPoolExecutor for concurrent operations
- `establish_rdp_ssh_tunnel()` - Creates simultaneous tunnels
- `send_heartbeat()` - Pushes connection data to dashboard
- `heartbeat_loop()` - Periodic status updates

### static/js/dashboard.js
**Purpose:** User interface
- Receives `heartbeat_update` events
- Displays: Customer ID, Assigned IP, Session Status
- Auto-refreshes agent list every 5 seconds

---

## Deployment Instructions

### For Server (Your Machine):
```powershell
# 1. Start the dashboard
cd "c:\Users\Bossman\Documents\PCFixPro"
python app.py

# 2. Dashboard available at:
http://192.168.100.253:5000
```

### For Client PCs:
```powershell
# 1. Copy screenconnect.zip to client
# 2. Extract on client PC
# 3. Edit config_server.txt if needed:
echo 192.168.100.253 > config_server.txt

# 4. Run as Administrator:
install.bat
```

### For Internet Access:
```powershell
# Port forward TCP 5000 from router to this machine
# Update config_server.txt with public IP:
echo 102.209.236.22 > config_server.txt
```

---

## Scaling Strategies

### Reverse Proxy (Nginx)
```nginx
upstream pcfixpro_backend {
    server 192.168.100.253:5000;
}
server {
    listen 443 ssl;
    location /socket.io/ {
        proxy_pass http://pcfixpro_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Redis Clustering
- Multiple gateway instances
- Shared session storage
- Load balancing across servers

### Port Management
- **Dynamic allocation:** Ports 10000-10100
- **Registry tuning:** 
  - `MaxUserPort = 65534`
  - `TcpTimedWaitDelay = 30` seconds

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection fails | Check firewall port 5000 |
| Heartbeat not showing | Verify IP in config_server.txt |
| MSI install error | Run as Administrator |
| Port exhaustion | Increase MaxUserPort registry value |

Run verification:
```powershell
python bat_checker.py