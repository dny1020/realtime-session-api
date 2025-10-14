#!/usr/bin/env python3
"""
Create admin user for Contact Center API v1

Usage:
    python scripts/create_admin.py
    
Or non-interactive:
    ADMIN_USERNAME=admin ADMIN_PASSWORD=secure123 python scripts/create_admin.py
"""
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.user import User
from app.auth.jwt import get_password_hash
import getpass


def main():
    # Get credentials
    username = os.getenv('ADMIN_USERNAME') or input("Username (default: admin): ").strip() or "admin"
    password = os.getenv('ADMIN_PASSWORD')
    
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("❌ Passwords don't match")
            sys.exit(1)
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        sys.exit(1)
    
    # Create user
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            print(f"❌ User '{username}' already exists")
            sys.exit(1)
        
        user = User(
            username=username,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
            email=f"{username}@localhost"
        )
        db.add(user)
        db.commit()
        
        print(f"✅ User '{username}' created")
        print(f"\nTest with:")
        print(f"  curl -X POST http://localhost:8000/api/v1/token \\")
        print(f"    -d 'username={username}&password=YOUR_PASSWORD'")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
