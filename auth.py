import hashlib
import secrets
import hmac
from database import get_connection


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()

    return password_hash, salt


def verify_password(password, stored_hash, stored_salt):
    new_hash, _ = hash_password(password, stored_salt)
    return hmac.compare_digest(new_hash, stored_hash)


def user_exists(email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    conn.close()
    return user is not None


def register_user(full_name, email, password):
    full_name = full_name.strip()
    email = email.strip().lower()

    if full_name == "":
        return False, "Full name is required."

    if email == "":
        return False, "Email is required."

    if password == "":
        return False, "Password is required."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    if user_exists(email):
        return False, "That email is already registered."

    password_hash, salt = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (full_name, email, password_hash, salt)
            VALUES (?, ?, ?, ?)
        """, (full_name, email, password_hash, salt))

        conn.commit()
        return True, "Account created successfully."
    except Exception as e:
        return False, f"Error creating account: {e}"
    finally:
        conn.close()


def login_user(email, password):
    email = email.strip().lower()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, full_name, email, password_hash, salt
        FROM users
        WHERE email = ?
    """, (email,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return False, "No account found with that email."

    user_id, full_name, email, stored_hash, stored_salt = user

    if verify_password(password, stored_hash, stored_salt):
        return True, {
            "id": user_id,
            "full_name": full_name,
            "email": email
        }

    return False, "Incorrect password."