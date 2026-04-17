# relay/engine_client.py
import threading
import requests
from flask import current_app


def _engine_url(path: str) -> str:
    return f"{current_app.config['ENGINE_BASE_URL']}{path}"


def engine_post(path: str, payload: dict, async_: bool = False) -> dict | None:
    if async_:
        _fire_and_forget(path, payload)
        return None
    return _post_sync(path, payload)


def _post_sync(path: str, payload: dict) -> dict:
    url     = _engine_url(path)
    timeout = current_app.config.get('ENGINE_TIMEOUT_SECONDS', 10)
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        raise EngineTimeoutError(f'Engine timed out: {path}')
    except requests.HTTPError as e:
        body = {}
        try:
            body = e.response.json()
        except Exception:
            pass
        raise EngineError(
            f'Engine {e.response.status_code} on {path}',
            status_code=e.response.status_code,
            detail=body.get('error', str(e)),
        )
    except requests.ConnectionError:
        raise EngineError(f'Cannot connect to engine: {path}')


def _fire_and_forget(path: str, payload: dict):
    url     = _engine_url(path)
    timeout = current_app.config.get('ENGINE_TIMEOUT_SECONDS', 10)

    def _call():
        try:
            requests.post(url, json=payload, timeout=timeout)
        except Exception as exc:
            current_app.logger.error(f'[engine_client] async {path} failed: {exc}')

    threading.Thread(target=_call, daemon=True).start()


class EngineError(Exception):
    def __init__(self, message, status_code=500, detail=''):
        super().__init__(message)
        self.status_code = status_code
        self.detail      = detail


class EngineTimeoutError(EngineError):
    def __init__(self, message):
        super().__init__(message, status_code=504)


def register_engine_error_handlers(app):
    @app.errorhandler(EngineError)
    def handle_engine_error(e):
        return {'error': 'Engine unavailable', 'detail': e.detail}, e.status_code

    @app.errorhandler(EngineTimeoutError)
    def handle_timeout(e):
        return {'error': 'Engine timed out — please try again'}, 504
