import os
import sqlite3
import threading
import datetime
from typing import Generator, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Register standard ISO adapters and converters for Python 3.12+ SQLite compliance
def _adapt_datetime_iso(val: datetime.datetime) -> str:
    return val.isoformat()

def _convert_datetime_iso(val: bytes) -> datetime.datetime:
    return datetime.datetime.fromisoformat(val.decode("utf-8"))

sqlite3.register_adapter(datetime.datetime, _adapt_datetime_iso)
sqlite3.register_converter("timestamp", _convert_datetime_iso)
sqlite3.register_converter("TIMESTAMP", _convert_datetime_iso)

DEFAULT_DB_PATH = os.getenv('SMARTWAREHOUSE_DB_PATH', os.path.join(os.getcwd(), 'data', 'smartwarehouse.db'))

# Ensure the data directory exists
os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)

# Thread‑local storage for connections (avoid sharing across threads)
_thread_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection for the current thread.
    The connection is cached in thread‑local storage and will be closed when the
    thread exits. All connections use ``detect_types=sqlite3.PARSE_DECLTYPES``
    so ``datetime`` objects are returned correctly.
    """
    conn = getattr(_thread_local, 'conn', None)
    if conn is None:
        conn = sqlite3.connect(
            DEFAULT_DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,  # autocommit mode – we manage transactions manually
        )
        conn.execute('PRAGMA foreign_keys = ON;')
        conn.execute('PRAGMA journal_mode = WAL;')
        conn.execute('PRAGMA busy_timeout = 5000;')
        conn.row_factory = sqlite3.Row
        _thread_local.conn = conn
    return conn


def run_migrations() -> None:
    """Execute all migration scripts in ``persistence/migrations`` that have not yet run.
    Migration scripts are ordered lexicographically and must be valid SQL.
    """
    conn = get_connection()
    cur = conn.cursor()
    # Create migration_meta table if missing
    cur.execute(
        "CREATE TABLE IF NOT EXISTS migration_meta (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    # Discover migration files
    migration_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    migration_files = sorted(
        f for f in os.listdir(migration_dir) if f.endswith('.sql')
    )
    for filename in migration_files:
        cur.execute('SELECT 1 FROM migration_meta WHERE name = ?', (filename,))
        if cur.fetchone():
            continue  # already applied
        path = os.path.join(migration_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            sql = f.read()
        logger.info('Applying migration %s', filename)
        try:
            conn.executescript(sql)
            cur.execute('INSERT INTO migration_meta (name) VALUES (?)', (filename,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error('Migration %s failed: %s', filename, e)
            raise
    cur.close()

def close_connection() -> None:
    """Close the thread‑local connection if it exists."""
    conn = getattr(_thread_local, 'conn', None)
    if conn is not None:
        conn.close()
        del _thread_local.conn
