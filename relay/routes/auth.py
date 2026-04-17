# relay/routes/auth.py
import bcrypt
import jwt as pyjwt
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g, current_app
from relay.db import db
from relay.auth import generate_tokens, jwt_required, verify_token_hash
from relay.engine_client import engine_post

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    body     = request.get_json() or {}
    username = body.get('username', '').strip()
    email    = body.get('email', '').strip().lower()
    password = body.get('password', '')

    errors = {}
    if not username or len(username) < 3:
        errors['username'] = 'Must be at least 3 characters'
    if not email or '@' not in email:
        errors['email'] = 'Invalid email address'
    if not password or len(password) < 8:
        errors['password'] = 'Must be at least 8 characters'
    if errors:
        return jsonify(errors=errors), 422

    existing = db.fetch_one("""
        SELECT user_id FROM user WHERE username = :uname OR email = :email
    """, uname=username, email=email)
    if existing:
        return jsonify(error='Username or email already registered'), 409

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = db.execute_returning("""
        INSERT INTO user (username, email, password_hash, created_at)
        VALUES (:uname, :email, :hash, NOW())
    """, uname=username, email=email, hash=password_hash)

    # Seed first topic + subtopic as unlocked
    engine_post('/engine/users/initialize', {'user_id': user_id})

    tokens = generate_tokens(user_id)
    return jsonify(user_id=user_id, username=username, **tokens), 201


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    body     = request.get_json() or {}
    email    = body.get('email', '').strip().lower()
    password = body.get('password', '')

    user = db.fetch_one("""
        SELECT user_id, username, password_hash FROM user WHERE email = :email
    """, email=email)

    # Constant-time comparison — don't reveal whether the email exists
    dummy = '$2b$12$dummyhashfortimingattackpreventionXXXXXXXXXX'
    stored = user.password_hash if user else dummy
    match  = bcrypt.checkpw(password.encode(), stored.encode())

    if not user or not match:
        return jsonify(error='Invalid email or password'), 401

    db.execute(
        'UPDATE user SET last_login = NOW() WHERE user_id = :uid',
        uid=user.user_id,
    )

    tokens = generate_tokens(user.user_id)
    return jsonify(user_id=user.user_id, username=user.username, **tokens), 200


@auth_bp.route('/auth/refresh', methods=['POST'])
def refresh():
    body  = request.get_json() or {}
    token = body.get('refresh_token', '')

    try:
        payload = pyjwt.decode(
            token,
            current_app.config['JWT_SECRET'],
            algorithms=['HS256'],
        )
    except pyjwt.ExpiredSignatureError:
        return jsonify(error='Refresh token expired, please log in again'), 401
    except pyjwt.InvalidTokenError:
        return jsonify(error='Invalid refresh token'), 401

    if payload.get('type') != 'refresh':
        return jsonify(error='Wrong token type'), 401

    user_id = payload['sub']
    stored  = db.fetch_one("""
        SELECT token_hash, expires_at FROM refresh_token WHERE user_id = :uid
    """, uid=user_id)

    if not stored:
        return jsonify(error='Session not found, please log in again'), 401

    if datetime.now(timezone.utc) > stored.expires_at.replace(tzinfo=timezone.utc):
        return jsonify(error='Refresh token expired'), 401

    if not verify_token_hash(token, stored.token_hash):
        # Hash mismatch — possible token theft; invalidate immediately
        db.execute('DELETE FROM refresh_token WHERE user_id = :uid', uid=user_id)
        return jsonify(error='Invalid refresh token'), 401

    tokens = generate_tokens(user_id)
    return jsonify(**tokens), 200


@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required
def logout():
    db.execute('DELETE FROM refresh_token WHERE user_id = :uid', uid=g.user_id)
    return jsonify(message='Logged out'), 200
