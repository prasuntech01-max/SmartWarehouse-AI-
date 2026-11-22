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

