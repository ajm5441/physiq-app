# engine/app.py
import os
from flask import Flask, request, abort
from engine.db import init_db, register_teardown
from engine.routes.sessions  import sessions_bp
from engine.routes.questions import questions_bp
from engine.routes.progress  import progress_bp
from engine.routes.users     import users_bp


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config.from_mapping(
        DB_URL = os.environ.get(
            'DATABASE_URL',
            'mysql+pymysql://physiq:physiq@localhost:3306/physiq',
        ),
        # Comma-separated list of IPs allowed to call this engine.
        # In Docker Compose the relay container's name resolves to its IP;
        # 127.0.0.1 covers local development without Docker.
        ALLOWED_RELAY_HOSTS = set(
            os.environ.get('ALLOWED_RELAY_HOSTS', '127.0.0.1,relay').split(',')
        ),
    )

    if config:
        app.config.from_mapping(config)

    init_db(app)
    register_teardown(app)

    app.register_blueprint(sessions_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(users_bp)

    # ── Internal-only guard ───────────────────────────────────────────────────
    # The engine is never exposed to the internet. Any request whose source IP
    # is not the relay is rejected immediately, before any route logic runs.
    @app.before_request
    def restrict_to_relay():
        allowed = app.config['ALLOWED_RELAY_HOSTS']
        if request.remote_addr not in allowed:
            app.logger.warning(
                f'Engine: rejected request from {request.remote_addr}'
            )
            abort(403)

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=False)
