"""Unit tests for UI components, navigation, and role-based permissions (Module 13 Stage 6 & 7)."""

import pytest
from ui.components import render_provenance_badge, render_status_chip
from ui.auth_helper import ROLE_PERMISSIONS, check_permission
from analytics.models import ProvenanceType


def test_provenance_badge_rendering():
    b_measured = render_provenance_badge(ProvenanceType.MEASURED)
    assert "badge-measured" in b_measured
    assert "MEASURED" in b_measured

    b_sim = render_provenance_badge(ProvenanceType.SIMULATED)
    assert "badge-simulated" in b_sim

    b_tel = render_provenance_badge(ProvenanceType.SIMULATED_TELEMETRY)
    assert "badge-telemetry" in b_tel

    b_est = render_provenance_badge(ProvenanceType.ESTIMATED)
    assert "badge-estimated" in b_est


def test_status_chip_rendering():
    chip_idle = render_status_chip("IDLE")
    assert "chip-normal" in chip_idle
    assert "IDLE" in chip_idle

    chip_crit = render_status_chip("EMERGENCY")
    assert "chip-critical" in chip_crit
    assert "EMERGENCY" in chip_crit


def test_role_permissions_matrix():
    # Admin has all permissions
    admin_perms = ROLE_PERMISSIONS["ADMIN"]
    assert "manage_users" in admin_perms
    assert "run_benchmarks" in admin_perms
    assert "export_reports" in admin_perms

    # Operator has operations & exports, but not user management
    op_perms = ROLE_PERMISSIONS["OPERATOR"]
    assert "manage_users" not in op_perms
    assert "run_benchmarks" in op_perms
    assert "export_reports" in op_perms
    assert "manage_tasks" in op_perms

    # Viewer has strictly read-only permissions
    viewer_perms = ROLE_PERMISSIONS["VIEWER"]
    assert "run_benchmarks" not in viewer_perms
    assert "export_reports" not in viewer_perms
    assert "manage_tasks" not in viewer_perms
    assert "view_dashboard" in viewer_perms
    assert "view_3d" in viewer_perms


def test_robot_inspector_and_search_components(monkeypatch):
    """Verifies UI helper components execute cleanly without error."""
    from ui.components import render_notification_tray, render_robot_inspector_drawer
    import streamlit as st
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "text_input", lambda *args, **kwargs: "")
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: None)

    class MockRobot:
        state = "IDLE"
        pos = (1, 1)
        goal = None
        battery = 95.0
        completed_tasks = 3

    render_notification_tray()
    render_robot_inspector_drawer(MockRobot(), 1)
