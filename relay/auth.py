# relay/auth.py
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, g, current_app
from relay.db import db


def generate_tokens(user_id: int) -> dict:
    now = datetime.now(timezone.utc)

    access_payload = {
        'sub':  user_id,
        'iat':  now,
        'exp':  now + timedelta(minutes=30),
        'type': 'access',
    }
    refresh_payload = {
        'sub':  user_id,
        'iat':  now,
        'exp':  now + timedelta(days=30),
        'type': 'refresh',
    }

    secret        = current_app.config['JWT_SECRET']
    access_token  = jwt.encode(access_payload,  secret, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, secret, algorithm='HS256')

    db.execute("""
        INSERT INTO refresh_token (user_id, token_hash, expires_at, created_at)
        VALUES (:uid, :hash, :exp, NOW())
        ON DUPLICATE KEY UPDATE
            token_hash = :hash,
            expires_at = :exp,
            created_at = NOW()
    """,
        uid  = user_id,
        hash = _hash_token(refresh_token),
        exp  = now + timedelta(days=30),
    )

    return {'access_token': access_token, 'refresh_token': refresh_token}


def _hash_token(token: str) -> str:
    return bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()


def verify_token_hash(token: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(token.encode(), stored_hash.encode())


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(error='Missing authorization header'), 401

        token = auth_header.split(' ', 1)[1]
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET'],
                algorithms=['HS256'],
            )
        except jwt.ExpiredSignatureError:
            return jsonify(error='Token expired', code='token_expired'), 401
        except jwt.InvalidTokenError:
            return jsonify(error='Invalid token'), 401

        if payload.get('type') != 'access':
            return jsonify(error='Wrong token type'), 401

        g.user_id = payload['sub']
        return f(*args, **kwargs)

    return decorated
