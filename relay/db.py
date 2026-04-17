# relay/db.py
from flask import g
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool


_engine = None


def init_db(app):
    global _engine
    _engine = create_engine(
        app.config['DB_URL'],
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,      # reconnect after Cloud SQL proxy restarts
        pool_recycle=1800,
    )


class _DB:
    """Thin wrapper so route code reads like readable SQL, not ORM chains."""

    def _conn(self):
        if 'db_conn' not in g:
            g.db_conn = _engine.connect()
        return g.db_conn

    def fetch_one(self, sql, **params):
        row = self._conn().execute(text(sql), params).fetchone()
        return row

    def fetch_all(self, sql, **params):
        return self._conn().execute(text(sql), params).fetchall()

    def fetch_scalar(self, sql, **params):
        row = self._conn().execute(text(sql), params).fetchone()
        return row[0] if row else None

    def execute(self, sql, **params):
        self._conn().execute(text(sql), params)
        self._conn().commit()

    def execute_returning(self, sql, **params):
        """INSERT … and return the new auto-increment id."""
        result = self._conn().execute(text(sql), params)
        self._conn().commit()
        return result.lastrowid


db = _DB()


def close_db(e=None):
    conn = g.pop('db_conn', None)
    if conn is not None:
        conn.close()


def register_teardown(app):
    app.teardown_appcontext(close_db)
