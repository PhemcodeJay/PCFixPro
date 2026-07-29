import os
import secrets
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # PostgreSQL Database - Set DATABASE_URL environment variable in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Encryption key for password encryption/decryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or secrets.token_urlsafe(32)

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Security
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CORS - restrict to actual domain
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000,https://yourdomain.com').split(',')

    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS = 60
    RATE_LIMIT_WINDOW = 60

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/app.log'

    # Payment
    SOLANA_RPC = "https://api.mainnet-beta.solana.com"
    RECIPIENT_WALLET = os.environ.get('RECIPIENT_WALLET') or 'CJJvHNh6FRjx3PK5zCKzwhzC7Hr1vwxxYETb7FaaA1PY'
    USDT_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4w45844Nh9D9Jv"

    # App settings
    DEBUG = False
    TESTING = False
