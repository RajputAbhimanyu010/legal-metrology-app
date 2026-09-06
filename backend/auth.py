"""
Authentication Module
Purpose: Simple username/password login with role-based access
(Officer vs Admin), using JWT tokens.

Uses Python's built-in hashlib (PBKDF2) for password hashing —
zero extra dependencies beyond PyJWT, which is easy to install anywhere.

Roles:
    "officer" — can scan products, view/search their own scan history
    "admin"   — can do everything an officer can, PLUS view all officers'
                scans and manage users

Run `python3 backend/auth.py` once to create the database table and
a default admin account for first login.
"""

import hashlib
import os
import sqlite3
import secrets
from datetime import datetime, timedelta

import jwt

DB_PATH = "compliance.db"
SECRET_KEY = "change-this-secret-key-before-real-deployment"  # TODO: move to env var
TOKEN_EXPIRY_HOURS = 12


def init_users_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'officer',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000).hex()


def create_user(username: str, password: str, role: str = "officer"):
    init_users_table()
    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, password_hash, salt, role, datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # username already exists
    finally:
        conn.close()


def verify_user(username: str, password: str):
    """Returns the user's role if credentials are valid, else None."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not row:
        return None
    expected_hash = _hash_password(password, row["salt"])
    if expected_hash == row["password_hash"]:
        return row["role"]
    return None


def create_access_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str):
    """Returns the payload dict if valid, else None (expired/invalid)."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


if __name__ == "__main__":
    init_users_table()
    # Create a default admin account for first login — CHANGE THIS PASSWORD
    # immediately after your first login in a real deployment.
    created = create_user("admin", "admin123", role="admin")
    if created:
        print("Default admin account created — username: admin / password: admin123")
        print("⚠️  Change this password before any real/public deployment.")
    else:
        print("Admin account already exists — skipping.")
