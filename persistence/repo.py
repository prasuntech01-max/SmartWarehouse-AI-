"""Repository layer for Module 12 persistence.
Provides thin, typed wrappers around the SQLite database. All operations are
wrapped in explicit transactions and raise domain‑specific exceptions rather
than leaking sqlite3 errors.
"""

import datetime
import json
import logging
import secrets
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
        clean_name = str(username or "").strip()
        if not clean_name:
            raise ValueError("Username cannot be empty.")
        if role not in {"ADMIN", "OPERATOR", "VIEWER"}:
            raise ValueError(f"Invalid role: {role}")
        if UserRepo.get_by_username(clean_name) is not None:
            raise ValueError(f"User creation failed: username '{clean_name}' already exists.")
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (clean_name, password_hash, role),
            )
            user_id = cur.lastrowid
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise ValueError(f"User creation failed: {e}")
        return UserRepo.get_by_id(user_id)

    @staticmethod
    def get_by_username(username: str) -> Optional[User]:
        clean_name = str(username or "").strip()
        if not clean_name:
            return None
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE LOWER(TRIM(username)) = LOWER(?)", (clean_name,))
        row = cur.fetchone()
        return _row_to_user(row) if row else None

    @staticmethod
    def unlock_user(user_id: int) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (user_id,))
        conn.commit()

    @staticmethod
    def update_password_hash(user_id: int, new_hash: bytes) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.commit()

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

    @staticmethod
    def list_all() -> List[User]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash, role, created_at, last_login, failed_attempts, locked_until FROM users ORDER BY id ASC")
        rows = cur.fetchall()
        return [
            User(
                id=r[0],
                username=r[1],
                password_hash=r[2],
                role=r[3],
                created_at=r[4],
                last_login=r[5],
                failed_attempts=r[6],
                locked_until=r[7],
            )
            for r in rows
        ]

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

    @staticmethod
    def clear_active_incidents(actor: str, tick: int = 0, notes: str = "Operator acknowledged and cleared") -> int:
        import hashlib
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id FROM incidents WHERE status = 'ACTIVE'")
            active_ids = [r[0] for r in cur.fetchall()]
            if not active_ids:
                return 0
            cur.execute("UPDATE incidents SET status = 'CLEARED' WHERE status = 'ACTIVE'")
            prev_row = cur.execute("SELECT hash FROM hazard_audits ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = prev_row[0] if prev_row else None
            for inc_id in active_ids:
                payload = f"{inc_id}|CLEAR|{actor}|{tick}|{notes}|{prev_hash or ''}"
                cur_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                cur.execute(
                    "INSERT INTO hazard_audits (incident_id, action, username, tick, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?)",
                    (inc_id, "CLEAR", actor, int(tick), prev_hash, cur_hash),
                )
                prev_hash = cur_hash
            conn.commit()
            return len(active_ids)
        except Exception:
            conn.rollback()
            raise


# ---------------------------------------------------------------------------
# Module 13: Benchmark Repository
# ---------------------------------------------------------------------------

class BenchmarkRepo:
    MAX_RETENTION = 50

    @staticmethod
    def save_run(
        run_id: str,
        benchmark_name: str,
        parameters: dict,
        environment: dict,
        total_trials: int,
        executed_by: str,
        trials: List[dict],
    ) -> None:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO benchmark_runs 
                   (run_id, benchmark_name, parameters_json, environment_json, total_trials, executed_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    benchmark_name,
                    json.dumps(parameters),
                    json.dumps(environment),
                    total_trials,
                    executed_by,
                ),
            )
            for t in trials:
                cur.execute(
                    """INSERT INTO benchmark_trials
                       (run_id, algorithm_name, scenario_seed, num_robots, grid_size, obstacle_density,
                        execution_time_ms, memory_peak_kb, path_length, optimal_path_length,
                        optimality_ratio, conflicts_detected, replan_count, success)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        t.get("algorithm_name", ""),
                        t.get("scenario_seed", 0),
                        t.get("num_robots", 1),
                        t.get("grid_size", "15x15"),
                        float(t.get("obstacle_density", 0.0)),
                        float(t.get("execution_time_ms", 0.0)),
                        float(t.get("memory_peak_kb", 0.0)),
                        int(t.get("path_length", 0)),
                        int(t.get("optimal_path_length", 0)),
                        float(t.get("optimality_ratio", 1.0)),
                        int(t.get("conflicts_detected", 0)),
                        int(t.get("replan_count", 0)),
                        1 if t.get("success", True) else 0,
                    ),
                )
            # Prune runs older than MAX_RETENTION
            cur.execute(
                """DELETE FROM benchmark_runs WHERE id NOT IN (
                       SELECT id FROM benchmark_runs ORDER BY id DESC LIMIT ?
                   )""",
                (BenchmarkRepo.MAX_RETENTION,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    @staticmethod
    def list_runs(limit: int = 50) -> List[dict]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM benchmark_runs ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "run_id": r["run_id"],
                "benchmark_name": r["benchmark_name"],
                "parameters": json.loads(r["parameters_json"]) if r["parameters_json"] else {},
                "environment": json.loads(r["environment_json"]) if r["environment_json"] else {},
                "total_trials": r["total_trials"],
                "executed_by": r["executed_by"],
                "created_at": r["created_at"],
            })
        return result



    @staticmethod
    def get_run(run_id: str) -> Optional[dict]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM benchmark_runs WHERE run_id = ?", (run_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "run_id": r["run_id"],
            "benchmark_name": r["benchmark_name"],
            "parameters": json.loads(r["parameters_json"]) if r["parameters_json"] else {},
            "environment": json.loads(r["environment_json"]) if r["environment_json"] else {},
            "total_trials": r["total_trials"],
            "executed_by": r["executed_by"],
            "created_at": r["created_at"],
        }

    @staticmethod
    def get_trials(run_id: str) -> List[dict]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM benchmark_trials WHERE run_id = ? ORDER BY id ASC", (run_id,)
        )
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "run_id": r["run_id"],
                "algorithm_name": r["algorithm_name"],
                "scenario_seed": r["scenario_seed"],
                "num_robots": r["num_robots"],
                "grid_size": r["grid_size"],
                "obstacle_density": r["obstacle_density"],
                "execution_time_ms": r["execution_time_ms"],
                "memory_peak_kb": r["memory_peak_kb"],
                "path_length": r["path_length"],
                "optimal_path_length": r["optimal_path_length"],
                "optimality_ratio": r["optimality_ratio"],
                "conflicts_detected": r["conflicts_detected"],
                "replan_count": r["replan_count"],
                "success": bool(r["success"]),
            })
        return result


# ---------------------------------------------------------------------------
# Module 13: Report Repository
# ---------------------------------------------------------------------------

class ReportRepo:
    @staticmethod
    def save_report(
        report_id: str,
        title: str,
        generated_by: str,
        time_range_start: Optional[datetime.datetime],
        time_range_end: Optional[datetime.datetime],
        summary: dict,
        export_format: str,
    ) -> None:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO report_records
                   (report_id, title, generated_by, time_range_start, time_range_end, summary_json, export_format)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    report_id,
                    title,
                    generated_by,
                    time_range_start,
                    time_range_end,
                    json.dumps(summary),
                    export_format,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    @staticmethod
    def list_reports(limit: int = 50) -> List[dict]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM report_records ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "report_id": r["report_id"],
                "title": r["title"],
                "generated_by": r["generated_by"],
                "time_range_start": r["time_range_start"],
                "time_range_end": r["time_range_end"],
                "summary": json.loads(r["summary_json"]) if r["summary_json"] else {},
                "export_format": r["export_format"],
                "created_at": r["created_at"],
            })
        return result


# ---------------------------------------------------------------------------
# Session, Audit, Config, Sensor & Warehouse Ops Repositories
# ---------------------------------------------------------------------------

class SessionRepo:
    @staticmethod
    def create_session(user_id: int, ttl_hours: int = 12) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(hours=ttl_hours)
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO sessions (token, user_id, issued_at, last_activity, expires_at) VALUES (?, ?, ?, ?, ?)",
                (token, user_id, now, now, expires),
            )
            conn.commit()
            return token
        except Exception:
            conn.rollback()
            raise

    @staticmethod
    def get_valid_session(token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE token = ?", (token,))
        row = cur.fetchone()
        if not row:
            return None
        expires_at = row["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.datetime.fromisoformat(expires_at)
        if expires_at <= datetime.datetime.utcnow():
            SessionRepo.revoke_session(token)
            return None
        return {
            "token": row["token"],
            "user_id": row["user_id"],
            "issued_at": row["issued_at"],
            "last_activity": row["last_activity"],
            "expires_at": expires_at,
        }

    @staticmethod
    def revoke_session(token: str) -> None:
        if not token:
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

    @staticmethod
    def purge_expired() -> int:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE expires_at <= ?", (datetime.datetime.utcnow(),))
        deleted = cur.rowcount
        conn.commit()
        return deleted


class AuditLogRepo:
    @staticmethod
    def log(actor: str, action: str, target: str = "", status: str = "SUCCESS", details: str = "") -> None:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO audit_logs (actor, action, target, status, details) VALUES (?, ?, ?, ?, ?)",
                (str(actor or "system"), str(action), str(target), str(status), str(details)),
            )
            conn.commit()
        except Exception:
            conn.rollback()

    @staticmethod
    def list_recent(limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, actor, action, target, status, details, created_at FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [
            {
                "id": r["id"],
                "actor": r["actor"],
                "action": r["action"],
                "target": r["target"],
                "status": r["status"],
                "details": r["details"],
                "created_at": r["created_at"],
            }
            for r in cur.fetchall()
        ]


class ConfigRepo:
    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    @staticmethod
    def set(key: str, value: str) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO system_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()


class SensorRepo:
    @staticmethod
    def record(sensor_id: str, value: float, unit: str, tick: int, data_source: str = "SIMULATED") -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensor_readings (sensor_id, value, unit, tick, data_source) VALUES (?, ?, ?, ?, ?)",
            (sensor_id, float(value), unit, int(tick), data_source),
        )
        conn.commit()

    @staticmethod
    def list_recent(limit: int = 100) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sensor_readings ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


class WarehouseOpsRepo:
    @staticmethod
    def upsert_task(task: Any) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO warehouse_tasks
               (task_id, pick_x, pick_y, drop_x, drop_y, priority, status, assigned_robot, created_at_step, completed_at_step)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(task_id) DO UPDATE SET
                 status = excluded.status,
                 assigned_robot = excluded.assigned_robot,
                 completed_at_step = excluded.completed_at_step,
                 updated_at = CURRENT_TIMESTAMP""",
            (
                int(task.task_id),
                int(task.pick_spot[0]), int(task.pick_spot[1]),
                int(task.delivery_station[0]), int(task.delivery_station[1]),
                int(task.priority),
                str(task.status),
                task.assigned_robot,
                int(task.created_at_step),
                task.completed_at_step,
            ),
        )
        conn.commit()

    @staticmethod
    def list_tasks(limit: int = 100) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM warehouse_tasks ORDER BY task_id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def upsert_parcel(parcel: Any) -> None:
        conn = get_connection()
        cur = conn.cursor()
        loc = parcel.location
        dest = parcel.destination
        ptype = parcel.parcel_type.value if hasattr(parcel.parcel_type, "value") else str(parcel.parcel_type)
        assigned = getattr(parcel, "assigned_robot", getattr(parcel, "carrier_robot", None))
        cur.execute(
            """INSERT INTO parcel_records
               (parcel_id, parcel_type, rack_slot_id, status, location_x, location_y, dest_x, dest_y, assigned_robot)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(parcel_id) DO UPDATE SET
                 status = excluded.status,
                 location_x = excluded.location_x,
                 location_y = excluded.location_y,
                 dest_x = excluded.dest_x,
                 dest_y = excluded.dest_y,
                 assigned_robot = excluded.assigned_robot,
                 updated_at = CURRENT_TIMESTAMP""",
            (
                str(parcel.parcel_id),
                str(ptype),
                parcel.rack_slot_id,
                str(parcel.status),
                int(loc[0]) if loc else None,
                int(loc[1]) if loc else None,
                int(dest[0]) if dest else None,
                int(dest[1]) if dest else None,
                assigned,
            ),
        )
        conn.commit()

    @staticmethod
    def list_parcels(limit: int = 100) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM parcel_records ORDER BY parcel_id ASC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

