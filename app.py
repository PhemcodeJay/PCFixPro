import os
import sys
import logging
import json
import base64
from datetime import datetime, timedelta
from functools import wraps
import time

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import paramiko

from config import Config
from models import db, User, Agent, Session, Payment, CustomerSession, SessionToken, File, Log, AuditLog

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins=Config.CORS_ORIGINS, async_mode='threading')
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the dashboard.'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default admin user if none exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@yourdomain.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logger.info("Created default admin user: admin / admin123")

# Rate limiting storage
rate_limit_storage = {}

# Track connected agents for socket communication
connected_agents = {}

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
                logger.warning(f"Rate limit exceeded for IP: {ip}")
                return jsonify({'status': 'error', 'message': 'Rate limit exceeded'}), 429
            
            rate_limit_storage[ip].append(current_time)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def log_action(level, category, message, details=None, user_id=None, agent_id=None, session_id=None):
    """Log action to database"""
    try:
        log_entry = Log(
            level=level,
            category=category,
            message=message,
            details=details,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            ip_address=request.remote_addr if request else None
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")

def audit_action(action, resource_type=None, resource_id=None, user=None, agent=None, success=True, error_message=None, metadata=None):
    """Create audit log entry"""
    try:
        audit = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user.id if user else None,
            agent_id=agent.id if agent else None,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None,
            success=success,
            error_message=error_message,
            metadata_json=metadata
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_action('INFO', 'auth', f'User logged in: {username}', user_id=user.id)
            audit_action('login', 'user', str(user.id), user=user, success=True)
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        log_action('WARNING', 'auth', f'Failed login attempt: {username}')
        audit_action('login', 'user', username, success=False, error_message='Invalid credentials')
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_action('INFO', 'auth', f'User logged out: {current_user.username}', user_id=current_user.id)
    audit_action('logout', 'user', str(current_user.id), user=current_user, success=True)
    logout_user()
    return redirect(url_for('login'))

# Import path security - will be added after db models are loaded
# Note: app.py now requires database initialization before routes

# Routes
@app.route('/')
def index():
    # Serve index.html for public landing page
    try:
        return send_file('index.html')
    except:
        return render_template('dashboard.html')

@app.route('/dashboard')
@login_required
def dashboard():
    log_action('INFO', 'navigation', 'Accessed dashboard', user_id=current_user.id)
    return render_template('dashboard.html', page='dashboard')

@app.route('/sessions')
@login_required
def sessions_page():
    return render_template('dashboard.html', page='sessions')

@app.route('/agents')
@login_required
def agents_page():
    return render_template('dashboard.html', page='agents')

@app.route('/security')
@login_required
def security_page():
    return render_template('dashboard.html', page='security')

@app.route('/settings')
@login_required
def settings_page():
    return render_template('dashboard.html', page='settings')

@app.route('/terminal')
@login_required
def terminal_page():
    return render_template('dashboard.html', page='terminal')

@app.route('/api/connect', methods=['POST'])
@login_required
@rate_limit(max_requests=30, window_seconds=60)
def connect_rdp():
    data = request.json
    session_id = data.get('session_id')
    host = data.get('host')
    port = data.get('port', 3389)
    username = data.get('username')
    password = data.get('password')
    protocol = data.get('protocol', 'rdp')
    
    try:
        # Create session in database
        db_session = Session(
            session_id=session_id,
            user_id=current_user.id,
            host=host,
            port=port,
            protocol=protocol,
            username=username,
            status='connected'
        )
        
        # Encrypt password if provided
        if password:
            from cryptography.fernet import Fernet
            key = app.config.get('ENCRYPTION_KEY') or Fernet.generate_key()
            f = Fernet(key)
            db_session.password_encrypted = f.encrypt(password.encode()).decode()
        
        db.session.add(db_session)
        db.session.commit()
        
        log_action('INFO', 'session', f'Created {protocol} session to {host}:{port}', 
                   user_id=current_user.id, session_id=session_id)
        audit_action('create', 'session', session_id, user=current_user, success=True)
        
        return jsonify({
            'status': 'connected',
            'message': f'{protocol.upper()} session established to {host}',
            'session_id': session_id
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create session: {e}")
        log_action('ERROR', 'session', f'Failed to create session: {str(e)}', 
                   user_id=current_user.id)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/disconnect', methods=['POST'])
@login_required
def disconnect_rdp():
    data = request.json
    session_id = data.get('session_id')
    
    try:
        db_session = Session.query.filter_by(session_id=session_id).first()
        if db_session:
            db_session.status = 'disconnected'
            db_session.end_time = datetime.utcnow()
            db.session.commit()
            
            log_action('INFO', 'session', f'Disconnected session {session_id}', 
                       user_id=current_user.id, session_id=session_id)
            audit_action('disconnect', 'session', session_id, user=current_user, success=True)
        
        return jsonify({'status': 'disconnected'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to disconnect session: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/execute', methods=['POST'])
@login_required
def execute_command():
    data = request.json
    session_id = data.get('session_id')
    command = data.get('command')
    
    try:
        db_session = Session.query.filter_by(session_id=session_id).first()
        if not db_session:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404
        
        # Try SSH execution if available
        try:
            from cryptography.fernet import Fernet
            key = app.config.get('ENCRYPTION_KEY')
            f = Fernet(key)
            decrypted_password = f.decrypt(db_session.password_encrypted.encode()).decode()
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(db_session.host, port=db_session.port, 
                       username=db_session.username, 
                       password=decrypted_password,
                       timeout=5)
            stdin, stdout, stderr = ssh.exec_command(command)
            output = (stdout.read().decode() or '') + (stderr.read().decode() or '')
            ssh.close()
            
            log_action('INFO', 'command', f'Executed command on {session_id}: {command}', 
                       user_id=current_user.id, session_id=session_id)
            
            return jsonify({
                'status': 'success',
                'output': output or f"Executed: {command}",
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as ssh_error:
            # Return error - no more fake responses
            logger.warning(f"SSH execution failed for session {session_id}: {ssh_error}")
            return jsonify({
                'status': 'error',
                'message': f'SSH connection failed: {str(ssh_error)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    try:
        # Get active sessions from database
        sessions = Session.query.filter_by(status='connected').all()
        
        # Update agent statuses
        agents = Agent.query.all()
        now = datetime.utcnow()
        for agent in agents:
            if (now - agent.last_seen).total_seconds() > 60:
                agent.status = 'offline'
                db.session.commit()
        
        # Format response
        sessions_data = []
        for s in sessions:
            sessions_data.append({
                'session_id': s.session_id,
                'host': s.host,
                'port': s.port,
                'protocol': s.protocol,
                'username': s.username,
                'status': s.status,
                'start_time': s.start_time.isoformat() if s.start_time else None
            })
        
        agents_data = []
        for agent in agents:
            agents_data.append({
                'agent_id': agent.agent_id,
                'hostname': agent.hostname,
                'ip_address': agent.ip_address,
                'os': agent.os,
                'status': agent.status,
                'last_seen': agent.last_seen.isoformat() if agent.last_seen else None,
                'agent_version': agent.agent_version
            })
        
        return jsonify({
            'active_sessions': len(sessions_data),
            'sessions': sessions_data,
            'agents': agents_data,
            'total_agents': len(agents_data)
        })
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/agents', methods=['GET'])
@login_required
def get_agents():
    try:
        agents = Agent.query.all()
        now = datetime.utcnow()
        
        # Update status based on last seen
        for agent in agents:
            if (now - agent.last_seen).total_seconds() > 60:
                agent.status = 'offline'
        
        db.session.commit()
        
        agents_data = []
        for agent in agents:
            agents_data.append({
                'agent_id': agent.agent_id,
                'hostname': agent.hostname,
                'ip_address': agent.ip_address,
                'os': agent.os,
                'status': agent.status,
                'last_seen': agent.last_seen.isoformat() if agent.last_seen else None,
                'agent_version': agent.agent_version,
                'customer_id': agent.customer_id,
                'assigned_ip': agent.assigned_ip,
                'session_status': agent.session_status,
                'active_connections': agent.active_connections
            })
        
        return jsonify({
            'agents': agents_data,
            'total_agents': len(agents_data),
            'online_count': sum(1 for a in agents if a.status == 'online')
        })
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Socket.IO handlers
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        emit('status', {'msg': f'Connected as {current_user.username}'})
        log_action('INFO', 'websocket', f'WebSocket connected: {current_user.username}', user_id=current_user.id)
    else:
        emit('status', {'msg': 'Connected (not authenticated)'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')
    # Clean up connected_agents tracking
    sid = request.sid
    to_remove = [aid for aid, s in connected_agents.items() if s == sid]
    for aid in to_remove:
        connected_agents.pop(aid, None)

@socketio.on('register_agent')
def handle_register_agent(data):
    try:
        hostname = data.get('hostname', 'Unknown')
        ip_address = data.get('ip_address', 'N/A')
        os_type = data.get('os', 'Unknown')
        agent_version = data.get('agent_version', '1.0.0')
        
        # Check if agent already exists
        existing = Agent.query.filter_by(hostname=hostname, ip_address=ip_address).first()
        if existing:
            existing.update_last_seen()
            existing.metadata_json = data
            db.session.commit()
            agent_id = existing.agent_id
            logger.info(f"Agent reconnected: {hostname} ({ip_address})")
        else:
            # Create new agent
            agent_id = f"agent_{int(time.time())}"
            agent = Agent(
                agent_id=agent_id,
                hostname=hostname,
                ip_address=ip_address,
                os=os_type,
                agent_version=agent_version,
                status='online',
                metadata_json=data
            )
            db.session.add(agent)
            db.session.commit()
            logger.info(f"New agent registered: {hostname} ({ip_address})")
        
        emit('agent_registered', {
            'agent_id': agent_id,
            'message': f"Agent {hostname} registered successfully"
        })
        
        # Track connected agent
        connected_agents[agent_id] = request.sid
        
        log_action('INFO', 'agent', f'Agent registered: {hostname} ({ip_address})')
        audit_action('register', 'agent', agent_id, success=True)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to register agent: {e}")
        emit('error', {'message': 'Registration failed'})

@socketio.on('heartbeat')
def handle_heartbeat(data):
    try:
        agent_id = data.get('agent_id')
        customer_id = data.get('customer_id')
        assigned_ip = data.get('assigned_ip')
        session_status = data.get('session_status')
        
        agent = Agent.query.filter_by(agent_id=agent_id).first()
        if agent:
            agent.update_last_seen()
            agent.customer_id = customer_id
            agent.assigned_ip = assigned_ip
            agent.session_status = session_status
            agent.active_connections = data.get('active_connections', 0)
            db.session.commit()
            
            # Broadcast to all connected clients
            socketio.emit('heartbeat_update', {
                'agent_id': agent_id,
                'customer_id': customer_id,
                'assigned_ip': assigned_ip,
                'session_status': session_status,
                'timestamp': datetime.utcnow().isoformat(),
                'active_connections': data.get('active_connections', 0)
            }, broadcast=True)
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")

@socketio.on('command_result')
def handle_command_result(data):
    emit('command_output', {
        'command_id': data.get('command_id'),
        'output': data.get('output'),
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('file_list')
def handle_list_files(data):
    agent_id = data.get('agent_id')
    path = data.get('path', '.')
    emit('file_list', data, to=agent_id)

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
    emit('screenshot', data, to=agent_id)

@socketio.on('file_list_result')
def handle_file_list_result(data):
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

@socketio.on('execute_command')
def handle_execute_command(data):
    agent_id = data.get('agent_id')
    command = data.get('command')
    
    if agent_id in connected_agents:
        socketio.emit('execute_command', {
            'agent_id': agent_id,
            'command': command,
            'command_id': data.get('command_id')
        }, to=agent_id)
    else:
        emit('command_output', {'output': 'Agent not found', 'error': True})

@socketio.on('list_processes')
def handle_list_processes(data):
    agent_id = data.get('agent_id')
    if agent_id in connected_agents:
        socketio.emit('list_processes', data, to=agent_id)

@socketio.on('kill_process')
def handle_kill_process(data):
    agent_id = data.get('agent_id')
    if agent_id in connected_agents:
        socketio.emit('kill_process', data, to=agent_id)

@socketio.on('read_registry')
def handle_read_registry(data):
    agent_id = data.get('agent_id')
    if agent_id in connected_agents:
        socketio.emit('read_registry', data, to=agent_id)

@socketio.on('wake_on_lan')
def handle_wake_on_lan(data):
    agent_id = data.get('agent_id')
    if agent_id in connected_agents:
        socketio.emit('wake_on_lan', data, to=agent_id)

# Payment endpoints
@app.route('/api/verify-payment', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=300)
def verify_payment():
    data = request.json
    tx_id = data.get('tx_id')
    customer_email = data.get('email')
    plan = data.get('plan', 'pro')
    expected_amount_usd = {'starter': 20, 'pro': 50, 'enterprise': 100}.get(plan, 50)
    
    if not tx_id:
        return jsonify({'status': 'error', 'message': 'Transaction ID required'}), 400
    
    # Check if payment already processed
    existing = Payment.query.filter_by(tx_id=tx_id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'Payment already processed'}), 400
    
    # Verify payment on Solana blockchain (REQUIRED - no mock fallback)
    payment_verified = False
    
    try:
        from solana.rpc.api import Client
        from solders.signature import Signature
        
        client = Client(Config.SOLANA_RPC)
        tx_response = client.get_transaction(Signature.from_string(tx_id))
        
        if tx_response and tx_response.value:
            tx = tx_response.value
            if tx.meta and tx.meta.err is None:
                payment_verified = True
                logger.info(f"Payment verified on blockchain: {tx_id}")
    except Exception as e:
        logger.error(f"Solana verification failed: {e}")
        # NO MOCK FALLBACK - return error
        return jsonify({'status': 'error', 'message': 'Payment verification failed. Please try again or contact support.'}), 400
    
    if not payment_verified:
        return jsonify({'status': 'error', 'message': 'Payment not found on blockchain. Please ensure transaction is confirmed.'}), 400
    
    # Create payment record
    payment = Payment(
        tx_id=tx_id,
        customer_email=customer_email,
        customer_id=f"customer_{Payment.query.count() + 1}",
        plan=plan,
        amount_usd=expected_amount_usd,
        status='verified',
        blockchain_verified=True,
        verified_at=datetime.utcnow()
    )
    db.session.add(payment)
    
    # Create customer session
    customer_session = CustomerSession(
        customer_id=payment.customer_id,
        plan=plan,
        status='active',
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(customer_session)
    db.session.commit()
    
    # Generate session token
    token = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    session_token = SessionToken(
        token=token,
        customer_id=payment.customer_id,
        plan=plan,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        ip_address=request.remote_addr
    )
    db.session.add(session_token)
    db.session.commit()
    
    log_action('INFO', 'payment', f'Payment verified: {tx_id}', 
               details={'plan': plan, 'amount': expected_amount_usd})
    audit_action('verify_payment', 'payment', tx_id, user=current_user if current_user.is_authenticated else None, 
                 success=True)
    
    return jsonify({
        'status': 'success',
        'token': token,
        'customer_id': payment.customer_id,
        'blockchain_verified': True,
        'downloads': [
            {'name': 'Windows', 'url': f'/downloads/PCFixPro_Agent_Windows.zip?token={token}'},
            {'name': 'macOS', 'url': f'/downloads/PCFixPro_Agent_macOS.zip?token={token}'},
            {'name': 'Universal', 'url': f'/downloads/PCFixPro_Agent_Universal.zip?token={token}'}
        ]
    })

@app.route('/downloads/<filename>')
def serve_download(filename):
    token = request.args.get('token')
    
    if not token:
        log_action('WARNING', 'download', 'Download attempt without token')
        return jsonify({'status': 'error', 'message': 'Token required'}), 403
    
    # Verify token
    session_token = SessionToken.query.filter_by(token=token, is_used=False).first()
    if not session_token:
        log_action('WARNING', 'download', f'Invalid token used: {token[:20]}...')
        return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 403
    
    # Check if token expired
    if session_token.expires_at < datetime.utcnow():
        log_action('WARNING', 'download', f'Expired token used: {token[:20]}...')
        return jsonify({'status': 'error', 'message': 'Token expired'}), 403
    
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    # Whitelist allowed files
    allowed_files = [
        'PCFixPro_Agent_Windows.zip',
        'PCFixPro_Agent_macOS.zip',
        'PCFixPro_Agent_Universal.zip'
    ]
    if safe_filename not in allowed_files:
        return jsonify({'status': 'error', 'message': 'File not allowed'}), 403
    
    # Serve file
    downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
    file_path = os.path.join(downloads_dir, safe_filename)
    
    if not os.path.exists(file_path):
        dist_dir = os.path.join(os.path.dirname(__file__), 'client_agent', 'dist')
        file_path = os.path.join(dist_dir, safe_filename)
    
    if not os.path.exists(file_path):
        log_action('ERROR', 'download', f'File not found: {safe_filename}')
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    # Mark token as used
    session_token.is_used = True
    session_token.used_at = datetime.utcnow()
    db.session.commit()
    
    log_action('INFO', 'download', f'Downloaded: {safe_filename}', 
               details={'token': token[:20] + '...'})
    
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    logger.info("Starting PCFixPro application...")
    socketio.run(app, debug=Config.DEBUG, host='0.0.0.0', port=5000)