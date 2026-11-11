"""Database access: configuration from the environment, pooled connections, safe cleanup.

Works out of the box with the development defaults below (matching setup_user.sql).
For anything beyond local use, override them with environment variables
(FITFUSION_DB_HOST, FITFUSION_DB_PORT, FITFUSION_DB_USER, FITFUSION_DB_PASSWORD,
FITFUSION_DB_NAME) or a [mysql] section in .streamlit/secrets.toml.
Priority: environment variables > secrets file > defaults.
"""
import os
import threading
from contextlib import contextmanager
from decimal import Decimal

import mysql.connector
from mysql.connector import pooling

_pool = None
_pool_lock = threading.Lock()


def _config():
    cfg = {
        "host": "localhost",
        "port": 3306,
        "user": "fitfusion_user",
        "password": "fit1234",  # development default; override for real use
        "database": "fitfusion",
    }

    # 1) Streamlit secrets (optional)
    try:
        import streamlit as st

        section = st.secrets.get("mysql", {})
        for key in cfg:
            if key in section:
                cfg[key] = section[key]
    except Exception:
        pass  # no secrets file / not running under Streamlit

    # 2) Environment variables override
    env_map = {
        "host": "FITFUSION_DB_HOST",
        "port": "FITFUSION_DB_PORT",
        "user": "FITFUSION_DB_USER",
        "password": "FITFUSION_DB_PASSWORD",
        "database": "FITFUSION_DB_NAME",
    }
    for key, var in env_map.items():
        if os.environ.get(var):
            cfg[key] = os.environ[var]

    cfg["port"] = int(cfg["port"])
    return cfg


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pooling.MySQLConnectionPool(
                    pool_name="fitfusion", pool_size=5, **_config()
                )
    return _pool


@contextmanager
def _connection():
    """Borrow a connection from the pool and ALWAYS give it back."""
    conn = _get_pool().get_connection()
    try:
        try:
            conn.ping(reconnect=True, attempts=2, delay=1)
        except Exception:
            pass
        yield conn
    finally:
        conn.close()  # returns it to the pool


def _clean(row):
    """DECIMAL columns come back as Decimal; the app works with plain floats."""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}


def query(sql, params=None):
    """Run a SELECT and return a list of dicts."""
    with _connection() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params or ())
            return [_clean(r) for r in cur.fetchall()]
        finally:
            cur.close()


def execute(sql, params=None):
    """Run INSERT/UPDATE/DELETE. Commits on success, rolls back on error.
    Returns the new row id (0 if the statement did not create one)."""
    with transaction() as cur:
        cur.execute(sql, params or ())
        return cur.lastrowid


@contextmanager
def transaction():
    """Several statements, one commit. Rolls everything back if anything fails.

        with transaction() as cur:
            cur.execute(...)
            cur.execute(...)
    """
    with _connection() as conn:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


IntegrityError = mysql.connector.errors.IntegrityError
