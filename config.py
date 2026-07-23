import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production'
    
    # PostgreSQL Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://neondb_owner:npg_iX2Nku1PgDqr@ep-old-pond-ay0oecd8-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS - restrict to actual domain
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://yourdomain.com').split(',')
    
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