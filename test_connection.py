#!/usr/bin/env python
"""Test script to simulate agent connection and heartbeat"""
import socketio
import time
import threading
import random

SERVER_URL = "http://192.168.100.253:5000"

class TestAgent:
    def __init__(self, agent_id):
        self.sio = socketio.Client()
        self.agent_id = agent_id
        self.customer_id = f"customer_{random.randint(1000, 9999)}"
        self.assigned_ip = f"192.168.1.{random.randint(100, 200)}"
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.sio.event
        def connect():
            print(f"[AGENT {self.agent_id}] Connected to dashboard")
            # Auto-register on connect
            self.register()
        
        @self.sio.event
        def disconnect():
            print(f"[AGENT {self.agent_id}] Disconnected")
        
        @self.sio.event
        def agent_registered(data):
            print(f"[AGENT {self.agent_id}] Registered: {data}")
    
    def register(self):
        """Register agent with dashboard"""
        self.sio.emit("register_agent", {
            "hostname": f"TestPC-{self.agent_id}",
            "ip_address": self.assigned_ip,
            "os": "Windows 11",
            "agent_version": "Test-Agent-1.0",
            "status": "online"
        })
        # Send initial heartbeat immediately
        self.send_heartbeat()
    
    def send_heartbeat(self):
        """Send heartbeat to dashboard"""
        self.sio.emit("heartbeat", {
            "agent_id": self.agent_id,
            "customer_id": self.customer_id,
            "assigned_ip": self.assigned_ip,
            "session_status": "connected",
            "timestamp": time.time(),
            "active_connections": 1
        })
    
    def run(self):
        try:
            self.sio.connect(SERVER_URL, transports=['websocket', 'polling'])
            while True:
                time.sleep(10)
                self.send_heartbeat()
        except Exception as e:
            print(f"[AGENT {self.agent_id}] Error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("PCFixPro Connection Test")
    print("=" * 50)
    print(f"Server: {SERVER_URL}")
    print("Connecting test agent...")
    
    agent = TestAgent("test_agent_001")
    agent.run()