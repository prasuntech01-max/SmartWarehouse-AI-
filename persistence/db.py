import os
import sqlite3
import threading
import datetime
from typing import Generator, List, Optional, Tuple
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

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.getenv('SMARTWAREHOUSE_DB_PATH', os.path.join(_PROJECT_ROOT, 'data', 'smartwarehouse.db'))

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


def backup_database(backup_dir: Optional[str] = None) -> Tuple[str, str]:
    """Create an online WAL-safe timestamped backup and verify its SQLite integrity.
    Returns (backup_path, integrity_result). Never modifies the active database.
    """
    target_dir = backup_dir or os.path.join(_PROJECT_ROOT, 'backups')
    os.makedirs(target_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(target_dir, f'smartwarehouse_backup_{ts}.db')

    src_conn = get_connection()
    dst_conn = sqlite3.connect(backup_path)
    try:
        src_conn.backup(dst_conn)
        integrity = dst_conn.execute('PRAGMA integrity_check;').fetchone()[0]
        if integrity != 'ok':
            raise RuntimeError(f'Backup integrity check failed: {integrity}')
        return backup_path, integrity
    finally:
        dst_conn.close()


def verify_backup_restore_to_temp(backup_path: str) -> Tuple[bool, str]:
    """Test restoring a backup onto a separate temporary database file and verify integrity + FK checks."""
    import tempfile
    if not os.path.isfile(backup_path):
        return False, f'Backup file not found: {backup_path}'
    with tempfile.TemporaryDirectory() as tmpdir:
        restore_path = os.path.join(tmpdir, 'restored_test.db')
        src = sqlite3.connect(backup_path)
        dst = sqlite3.connect(restore_path)
        try:
            src.backup(dst)
            dst.execute('PRAGMA foreign_keys = ON;')
            integrity = dst.execute('PRAGMA integrity_check;').fetchone()[0]
            fk_issues = dst.execute('PRAGMA foreign_key_check;').fetchall()
            if integrity != 'ok' or fk_issues:
                return False, f'Restore verification failed (integrity={integrity}, fk_issues={len(fk_issues)})'
            return True, f'Verified restore of {os.path.basename(backup_path)} (integrity=ok, fk_issues=0)'
        finally:
            dst.close()
            src.close()
