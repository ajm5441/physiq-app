# relay/cache.py
# Stores active session state between question submissions.
# Uses Redis when REDIS_URL is configured, falls back to a thread-safe
# in-memory dict for local development without Redis.

import json
import threading
from datetime import timedelta


class _RedisCache:
    SESSION_TTL = timedelta(hours=2)

    def __init__(self, redis_url: str):
        import redis
        self._r = redis.from_url(redis_url, decode_responses=True)

    def _key(self, user_id: int) -> str:
        return f'physiq:session:{user_id}'

    def get_active(self, user_id: int) -> dict | None:
        raw = self._r.get(self._key(user_id))
        return json.loads(raw) if raw else None

    def set(self, user_id: int, state: dict):
        self._r.setex(
            self._key(user_id),
            int(self.SESSION_TTL.total_seconds()),
            json.dumps(state),
        )

    def clear(self, user_id: int):
        self._r.delete(self._key(user_id))


class _MemoryCache:
    """Thread-safe fallback for development."""

    def __init__(self):
        self._store: dict[int, dict] = {}
        self._lock  = threading.Lock()

    def get_active(self, user_id: int) -> dict | None:
        with self._lock:
            return self._store.get(user_id)

    def set(self, user_id: int, state: dict):
        with self._lock:
            self._store[user_id] = state

    def clear(self, user_id: int):
        with self._lock:
            self._store.pop(user_id, None)


def init_cache(app) -> '_RedisCache | _MemoryCache':
    redis_url = app.config.get('REDIS_URL')
    if redis_url:
        cache = _RedisCache(redis_url)
        app.logger.info('Session cache: Redis')
    else:
        cache = _MemoryCache()
        app.logger.info('Session cache: in-memory (dev mode)')
    app.extensions['session_cache'] = cache
    return cache


def get_cache(app=None) -> '_RedisCache | _MemoryCache':
    from flask import current_app
    return (app or current_app).extensions['session_cache']


# Module-level proxy so route files can just do `from relay.cache import session_cache`
class _CacheProxy:
    def get_active(self, user_id):  return get_cache().get_active(user_id)
    def set(self, user_id, state):  return get_cache().set(user_id, state)
    def clear(self, user_id):       return get_cache().clear(user_id)


session_cache = _CacheProxy()
