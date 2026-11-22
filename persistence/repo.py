"""Repository layer for Module 12 persistence.
Provides thin, typed wrappers around the SQLite database. All operations are
wrapped in explicit transactions and raise domain‑specific exceptions rather
than leaking sqlite3 errors.
"""

import datetime
import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .db import get_connection, run_migrations

logger = logging.getLogger(__name__)

# Ensure migrations have been applied on first import
run_migrations()

# ---------------------------------------------------------------------------
# Domain models (lightweight dataclasses)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: bytes
    role: str
    created_at: datetime.datetime
    last_login: Optional[datetime.datetime]
    failed_attempts: int
    locked_until: Optional[datetime.datetime]

@dataclass(frozen=True)
class Incident:
    id: int
    hazard_type: str
    severity: str
    status: str
    sensor_ids: Optional[str]
    device_id: Optional[str]
    coord: Tuple[int, int]
    value: float
    unit: str
    tick: int
    rule_id: str
    explanation: str
    recovery: str
    data_source: str
    created_at: datetime.datetime

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        role=row["role"],
        created_at=row["created_at"],
        last_login=row["last_login"],
        failed_attempts=row["failed_attempts"],
        locked_until=row["locked_until"],
    )

def _row_to_incident(row: sqlite3.Row) -> Incident:
    return Incident(
        id=row["id"],
        hazard_type=row["hazard_type"],
        severity=row["severity"],
        status=row["status"],
        sensor_ids=row["sensor_ids"],
        device_id=row["device_id"],
        coord=(row["coord_x"], row["coord_y"]),
        value=row["value"],
        unit=row["unit"],
        tick=row["tick"],
        rule_id=row["rule_id"],
        explanation=row["explanation"],
        recovery=row["recovery"],
        data_source=row["data_source"],
        created_at=row["created_at"],
    )

# ---------------------------------------------------------------------------
# User repository
# ---------------------------------------------------------------------------

class UserRepo:
    @staticmethod
    def create(username: str, password_hash: bytes, role: str = "VIEWER") -> User:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
            user_id = cur.lastrowid
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise ValueError(f"User creation failed: {e}")
        return UserRepo.get_by_id(user_id)

    @staticmethod
    def get_by_username(username: str) -> Optional[User]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return _row_to_user(row) if row else None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return _row_to_user(row) if row else None

    @staticmethod
    def update_login_success(user_id: int) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET last_login = ?, failed_attempts = 0, locked_until = NULL WHERE id = ?",
            (datetime.datetime.utcnow(), user_id),
        )
        conn.commit()

    @staticmethod
    def increment_failed_attempt(user_id: int, max_failed: int = 5) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT failed_attempts FROM users WHERE id = ?", (user_id,))
        attempts = cur.fetchone()["failed_attempts"] + 1
        lock_until = None
        if attempts >= max_failed:
            lock_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        cur.execute(
            "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
            (attempts, lock_until, user_id),
        )
        conn.commit()

    @staticmethod
    def set_role(user_id: int, role: str) -> None:
        if role not in {"ADMIN", "OPERATOR", "VIEWER"}:
            raise ValueError("Invalid role")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()

# ---------------------------------------------------------------------------
# Incident repository (historical copy of hazard incidents)
# ---------------------------------------------------------------------------

class IncidentRepo:
    @staticmethod
    def create_from_dict(data: dict) -> Incident:
        conn = get_connection()
        cur = conn.cursor()
        columns = (
            "hazard_type",
            "severity",
            "status",
            "sensor_ids",
            "device_id",
            "coord_x",
            "coord_y",
            "value",
            "unit",
            "tick",
            "rule_id",
            "explanation",
            "recovery",
            "data_source",
        )
        placeholders = ",".join(["?"] * len(columns))
        values = [
            data.get("hazard_type"),
            data.get("severity"),
            data.get("status"),
            json.dumps(data.get("sensor_ids")) if data.get("sensor_ids") else None,
            data.get("device_id"),
            data["coord"][0] if data.get("coord") else None,
            data["coord"][1] if data.get("coord") else None,
            data.get("value"),
            data.get("unit"),
            data.get("tick"),
            data.get("rule_id"),
            data.get("explanation"),
            data.get("recovery"),
            data.get("data_source"),
        ]
        cur.execute(
            f"INSERT INTO incidents ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        inc_id = cur.lastrowid
        conn.commit()
        return IncidentRepo.get_by_id(inc_id)

    @staticmethod
    def get_by_id(inc_id: int) -> Optional[Incident]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM incidents WHERE id = ?", (inc_id,))
        row = cur.fetchone()
        return _row_to_incident(row) if row else None

    @staticmethod
    def list_recent(limit: int = 100) -> List[Incident]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = cur.fetchall()
        return [_row_to_incident(r) for r in rows]
