"""Comprehensive non-destructive Database, Authentication, Security & Backup tests (isolated temp DB)."""

import datetime
import os
import sqlite3
import tempfile
import pytest

import persistence.db as db_mod
import persistence.repo as repo_mod
import ui.auth_helper as auth_helper
from auth.crypto import hash_password, verify_password
from core.task_manager import WarehouseTask
from core.parcels import Parcel, ParcelType, PARCEL_SPECS


@pytest.fixture()
def temp_db(monkeypatch):
    """Isolate every test onto a fresh temporary SQLite database; never touch data/smartwarehouse.db."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_smartwarehouse.db")
        db_mod.close_connection()
        monkeypatch.setattr(db_mod, "DEFAULT_DB_PATH", db_path)
        db_mod.run_migrations()
        yield db_path, tmpdir
        db_mod.close_connection()


def test_db_schema_fk_and_persistence_across_restart(temp_db):
    db_path, _ = temp_db
    conn = db_mod.get_connection()
    assert conn.execute("PRAGMA integrity_check;").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for required in ("users", "sessions", "incidents", "hazard_audits", "sensor_readings", "system_config", "benchmark_runs", "benchmark_trials", "report_records", "audit_logs", "warehouse_tasks", "parcel_records"):
        assert required in tables

    # Persist config & task, close connection (simulating restart), reopen and verify
    repo_mod.ConfigRepo.set("qa_key", "persisted_value")
    task = WarehouseTask(task_id=901, shelf_loc=(2, 3), pick_spot=(1, 3), delivery_station=(2, 14), status="COMPLETED", completed_at_step=12)
    repo_mod.WarehouseOpsRepo.upsert_task(task)
    parcel = Parcel(parcel_id="PKG-9001", parcel_type=ParcelType.TOTE_BLUE, spec=PARCEL_SPECS[ParcelType.TOTE_BLUE], rack_slot_id="RACK-A01-L1", status="DELIVERED", location=(2, 14), destination=(2, 14))
    repo_mod.WarehouseOpsRepo.upsert_parcel(parcel)

    db_mod.close_connection()
    assert repo_mod.ConfigRepo.get("qa_key") == "persisted_value"
    assert repo_mod.WarehouseOpsRepo.list_tasks()[0]["status"] == "COMPLETED"
    assert repo_mod.WarehouseOpsRepo.list_parcels()[0]["parcel_id"] == "PKG-9001"


def test_auth_login_case_whitespace_lockout_and_sessions(temp_db, monkeypatch):
    # Mock Streamlit session_state cleanly
    class FakeSessionState(dict):
        __getattr__ = dict.get
        __setattr__ = dict.__setitem__

    fake_ss = FakeSessionState()
    monkeypatch.setattr(auth_helper.st, "session_state", fake_ss)

    # Create admin user
    u = repo_mod.UserRepo.create("admin", hash_password("Admin@123"), role="ADMIN")
    assert u.username == "admin"

    # Duplicate case-insensitive registration rejected
    with pytest.raises(ValueError):
        repo_mod.UserRepo.create("  ADMIN ", hash_password("Other@123"), role="VIEWER")

    # Empty credentials rejected
    ok_empty, _ = auth_helper.login_user("", "")
    assert not ok_empty

    # Unknown user rejected
    ok_unk, _ = auth_helper.login_user("unknown_user", "Admin@123")
    assert not ok_unk

    # Case & whitespace normalization succeeds and creates persistent session
    ok, msg = auth_helper.login_user("  ADMIN  ", "Admin@123")
    assert ok, msg
    assert fake_ss.authenticated is True
    assert fake_ss.user_role == "ADMIN"
    token = fake_ss.get("session_token")
    assert token
    assert repo_mod.SessionRepo.get_valid_session(token) is not None

    # Logout revokes session token
    auth_helper.logout_user()
    assert fake_ss.authenticated is False
    assert fake_ss.user_role == "VIEWER"
    assert repo_mod.SessionRepo.get_valid_session(token) is None

    # 5 failed attempts lock the account
    for _ in range(5):
        ok_bad, _ = auth_helper.login_user("admin", "WrongPass!")
        assert not ok_bad
    ok_locked, lock_msg = auth_helper.login_user("admin", "Admin@123")
    assert not ok_locked
    assert "locked" in lock_msg.lower()

    # Admin unlock restores login
    repo_mod.UserRepo.unlock_user(u.id)
    ok_unlocked, _ = auth_helper.login_user("admin", "Admin@123")
    assert ok_unlocked

    # Audit log recorded events without leaking passwords or tokens
    audits = repo_mod.AuditLogRepo.list_recent(20)
    assert len(audits) >= 3
    joined = str(audits)
    assert "Admin@123" not in joined
    assert token not in joined


def test_backup_and_temp_restore_verification(temp_db):
    _, tmpdir = temp_db
    repo_mod.UserRepo.create("qa_user", hash_password("QaPass@123"), role="OPERATOR")
    repo_mod.SensorRepo.record("temp_01", 23.4, "°C", tick=5)

    bk_path, integrity = db_mod.backup_database(backup_dir=os.path.join(tmpdir, "bk"))
    assert integrity == "ok"
    assert os.path.isfile(bk_path)

    ok_restore, msg = db_mod.verify_backup_restore_to_temp(bk_path)
    assert ok_restore, msg


def test_init_auth_never_auto_admin_and_restores_session(temp_db, monkeypatch):
    class FakeSessionState(dict):
        def __getattr__(self, k):
            try:
                return self[k]
            except KeyError:
                raise AttributeError(k)
        def __setattr__(self, k, v):
            self[k] = v

    import ui.auth_helper as auth_helper
    fake_ss = FakeSessionState()
    monkeypatch.setattr(auth_helper.st, "session_state", fake_ss)

    # Fresh session must start as unauthenticated VIEWER, never ADMIN
    auth_helper.init_auth_session()
    assert fake_ss.authenticated is False
    assert fake_ss.user_role == "VIEWER"
    assert auth_helper.check_permission("manage_users") is False
    assert auth_helper.check_permission("view_dashboard") is True

    # Log in as admin, simulate rerun (clear username/role/authenticated while keeping session_token)
    ok, _ = auth_helper.login_user("admin", "Admin@123")
    assert ok is True
    tok = fake_ss.session_token
    fake_ss.pop("authenticated", None)
    fake_ss.pop("user_role", None)
    fake_ss.pop("username", None)
    fake_ss["session_token"] = tok

    auth_helper.init_auth_session()
    assert fake_ss.authenticated is True
    assert fake_ss.user_role == "ADMIN"
    assert fake_ss.username == "admin"
    assert auth_helper.check_permission("manage_users") is True


def test_ops_parcel_task_incident_audit_and_config_persistence(temp_db):
    from types import SimpleNamespace

    task_obj = SimpleNamespace(
        task_id=101,
        pick_spot=(2, 3),
        delivery_station=(8, 9),
        priority=2,
        status="PENDING",
        assigned_robot=None,
        created_at_step=5,
        completed_at_step=None,
    )
    repo_mod.WarehouseOpsRepo.upsert_task(task_obj)
    tasks = repo_mod.WarehouseOpsRepo.list_tasks(limit=10)
    assert any(t["task_id"] == 101 and t["status"] == "PENDING" for t in tasks)

    parcel_obj = SimpleNamespace(
        parcel_id="PCL-900",
        parcel_type="STANDARD",
        rack_slot_id="RACK-A1",
        status="IN_TRANSIT",
        location=(2, 3),
        destination=(8, 9),
        carrier_robot=1,
    )
    repo_mod.WarehouseOpsRepo.upsert_parcel(parcel_obj)
    parcels = repo_mod.WarehouseOpsRepo.list_parcels(limit=10)
    assert any(p["parcel_id"] == "PCL-900" and p["assigned_robot"] == 1 for p in parcels)

    repo_mod.IncidentRepo.create_from_dict({
        "hazard_type": "FIRE",
        "severity": "CRITICAL",
        "status": "ACTIVE",
        "coord": (4, 4),
        "value": 46.5,
        "unit": "°C",
        "tick": 10,
        "rule_id": "FIRE_RULE",
        "explanation": "Test fire",
        "recovery": "Pending",
        "data_source": "SIMULATED",
    })
    cleared = repo_mod.IncidentRepo.clear_active_incidents(actor="admin", tick=10, notes="QA clear")
    assert cleared == 1
    conn = db_mod.get_connection()
    audits = conn.execute("SELECT COUNT(*) FROM hazard_audits WHERE action = 'CLEAR'").fetchone()[0]
    assert audits == 1

    repo_mod.ConfigRepo.set("default_sim_speed", "2.0x")
    assert repo_mod.ConfigRepo.get("default_sim_speed") == "2.0x"
