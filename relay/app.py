# relay/app.py
import os
from flask import Flask
from flask_cors import CORS
from relay.db import init_db, register_teardown
from relay.cache import init_cache
from relay.engine_client import register_engine_error_handlers
from relay.routes.auth      import auth_bp
from relay.routes.sessions  import sessions_bp
from relay.routes.dashboard import dashboard_bp
from relay.routes.topics    import topics_bp
from relay.routes.progress  import progress_bp


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config.from_mapping(
        JWT_SECRET             = os.environ.get('JWT_SECRET', 'change-me-in-production'),
        ENGINE_BASE_URL        = os.environ.get('ENGINE_BASE_URL', 'http://localhost:5001'),
        ENGINE_TIMEOUT_SECONDS = int(os.environ.get('ENGINE_TIMEOUT_SECONDS', '10')),
        DB_URL                 = os.environ.get(
            'DATABASE_URL',
            'mysql+pymysql://physiq:physiq@localhost:3306/physiq',
        ),
        REDIS_URL              = os.environ.get('REDIS_URL'),   # None → memory cache
    )

    if config:
        app.config.from_mapping(config)

    # CORS — only allow requests from the frontend origin
    frontend_origin = os.environ.get('FRONTEND_ORIGIN', 'http://localhost:3000')
    CORS(app, origins=[frontend_origin], supports_credentials=True)

    init_db(app)
    register_teardown(app)
    init_cache(app)
    register_engine_error_handlers(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(topics_bp)
    app.register_blueprint(progress_bp)

    @app.get('/healthz')
    def health():
        return {'status': 'ok'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
