from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from config import Config

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Admin users for dashboard access"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin')  # admin, technician, viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    sessions = db.relationship('Session', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        from cryptography.fernet import Fernet
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

class Agent(db.Model):
    """Connected client agents"""
    __tablename__ = 'agents'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    hostname = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    mac_address = db.Column(db.String(17), nullable=True)
    os = db.Column(db.String(100), nullable=True)
    os_version = db.Column(db.String(100), nullable=True)
    agent_version = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='offline')  # online, offline, warning
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    customer_id = db.Column(db.String(100), nullable=True, index=True)
    assigned_ip = db.Column(db.String(45), nullable=True)
    session_status = db.Column(db.String(50), nullable=True)
    active_connections = db.Column(db.Integer, default=0)
    metadata_json = db.Column(db.JSON, nullable=True)
    
    # Relationships
    sessions = db.relationship('Session', backref='agent', lazy=True, cascade='all, delete-orphan')
    files = db.relationship('File', backref='agent', lazy=True, cascade='all, delete-orphan')
    
    def update_last_seen(self):
        self.last_seen = datetime.utcnow()
        self.status = 'online'

class Session(db.Model):
    """RDP/SSH sessions"""
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=True)
    customer_id = db.Column(db.String(100), nullable=True, index=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, default=3389)
    protocol = db.Column(db.String(10), default='rdp')  # rdp, ssh, vnc
    username = db.Column(db.String(100), nullable=True)
    password_encrypted = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='disconnected')  # connected, disconnected, error
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Session {self.session_id} to {self.host}>'

class Payment(db.Model):
    """Payment records"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    tx_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    customer_email = db.Column(db.String(120), nullable=True)
    customer_id = db.Column(db.String(100), nullable=False, index=True)
    plan = db.Column(db.String(50), nullable=False)
    amount_usd = db.Column(db.Float, nullable=False)
    amount_crypto = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(20), default='USDT')
    status = db.Column(db.String(20), default='pending')  # pending, verified, confirmed, failed
    blockchain_verified = db.Column(db.Boolean, default=False)
    verification_attempts = db.Column(db.Integer, default=0)
    last_verification = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

class CustomerSession(db.Model):
    """Customer plan assignments"""
    __tablename__ = 'customer_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    agent_id = db.Column(db.String(100), nullable=True)
    plan = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, expired, revoked
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SessionToken(db.Model):
    """Download tokens for agent packages"""
    __tablename__ = 'session_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.String(100), nullable=False, index=True)
    plan = db.Column(db.String(50), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45), nullable=True)

class File(db.Model):
    """Agent file system tracking"""
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    path = db.Column(db.String(1000), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    is_directory = db.Column(db.Boolean, default=False)
    size_bytes = db.Column(db.BigInteger, default=0)
    modified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('agent_id', 'path', name='unique_agent_file'),
    )

class Log(db.Model):
    """Application logs for debugging"""
    # __tablename__ = 'logs'\"]=\..,/]??"
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    category = db.Column(db.String(50), nullable=True, index=True)  # auth, payment, agent, session, system
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.JSON, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', backref='logs', lazy=True)

class AuditLog(db.Model):
    """Audit trail for security events"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref='audit_logs', lazy=True)'p.?'