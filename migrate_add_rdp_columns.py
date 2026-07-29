#!/usr/bin/env python3
"""
Migration script to add RDP columns to agents table
"""
import sys
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        # Get database dialect
        dialect = db.engine.dialect.name
        
        print(f"Database dialect: {dialect}")
        
        if dialect == 'sqlite':
            # SQLite doesn't support ADD COLUMN IF NOT EXISTS before 3.35.0
            # But we can try/except
            statements = [
                "ALTER TABLE agents ADD COLUMN rdp_username VARCHAR(100)",
                "ALTER TABLE agents ADD COLUMN rdp_password_encrypted VARCHAR(500)",
                "ALTER TABLE agents ADD COLUMN rdp_enabled BOOLEAN DEFAULT 0",
                "ALTER TABLE agents ADD COLUMN rdp_created_at DATETIME",
                "ALTER TABLE agents ADD COLUMN rdp_port INTEGER DEFAULT 3389"
            ]
        elif dialect == 'postgresql':
            statements = [
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS rdp_username VARCHAR(100)",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS rdp_password_encrypted VARCHAR(500)",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS rdp_enabled BOOLEAN DEFAULT FALSE",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS rdp_created_at TIMESTAMP",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS rdp_port INTEGER DEFAULT 3389"
            ]
        else:
            statements = [
                "ALTER TABLE agents ADD COLUMN rdp_username VARCHAR(100)",
                "ALTER TABLE agents ADD COLUMN rdp_password_encrypted VARCHAR(500)",
                "ALTER TABLE agents ADD COLUMN rdp_enabled BOOLEAN DEFAULT 0",
                "ALTER TABLE agents ADD COLUMN rdp_created_at DATETIME",
                "ALTER TABLE agents ADD COLUMN rdp_port INTEGER DEFAULT 3389"
            ]
        
        with db.engine.connect() as conn:
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                    print(f"✓ Executed: {stmt}")
                except Exception as e:
                    if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                        print(f"⚠ Column already exists: {stmt.split('ADD COLUMN')[1].strip()}")
                    else:
                        print(f"✗ Error executing: {stmt}")
                        print(f"  {e}")
        
        print("\nMigration completed!")

if __name__ == '__main__':
    migrate()