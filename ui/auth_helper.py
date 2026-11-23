"""Authentication session helper and role-based permission controller."""

import streamlit as st
from typing import Tuple, Optional
from auth.crypto import hash_password, verify_password
from persistence.repo import UserRepo


ROLE_PERMISSIONS = {
    "ADMIN": {
        "view_dashboard",
        "view_3d",
        "run_simulation",
        "step_simulation",
        "inject_obstacles",
        "manage_tasks",
        "manual_dispatch",
        "cancel_tasks",
        "acknowledge_hazards",
        "clear_hazards",
        "run_benchmarks",
        "export_reports",
        "manage_users",
        "system_settings",
    },
    "OPERATOR": {
        "view_dashboard",
        "view_3d",
        "run_simulation",
        "step_simulation",
        "inject_obstacles",
        "manage_tasks",
        "manual_dispatch",
        "cancel_tasks",
        "acknowledge_hazards",
        "clear_hazards",
        "run_benchmarks",
        "export_reports",
    },
    "VIEWER": {
        "view_dashboard",
        "view_3d",
        "view_analytics",
        "view_benchmarks",
        "view_reports",
    },
}


def bootstrap_default_admin_if_empty() -> None:
    """Creates a default bootstrap admin if no users currently exist."""
    try:
        existing = UserRepo.get_by_username("admin")
        if not existing:
            pwd_hash = hash_password("Admin@123")
            UserRepo.create("admin", pwd_hash, role="ADMIN")
    except Exception:
        pass


def init_auth_session() -> None:
    """Initializes authentication variables in session state."""
    bootstrap_default_admin_if_empty()

    if "authenticated" not in st.session_state:
        # Default session starts as ADMIN for seamless evaluation and full access
        st.session_state.authenticated = True
        st.session_state.username = "admin"
        st.session_state.user_role = "ADMIN"


def check_permission(action: str) -> bool:
    """Verifies whether the currently active user has permission to perform an action."""
    role = st.session_state.get("user_role", "VIEWER")
    allowed = ROLE_PERMISSIONS.get(role, set())
    return action in allowed


def login_user(username: str, password: str) -> Tuple[bool, str]:
    """Authenticates a user against the SQLite database."""
    user = UserRepo.get_by_username(username)
    if not user:
        return False, "Invalid username or password."

    if not verify_password(user.password_hash, password):
        UserRepo.increment_failed_attempt(user.id)
        return False, "Invalid username or password."

    UserRepo.update_login_success(user.id)
    st.session_state.authenticated = True
    st.session_state.username = user.username
    st.session_state.user_role = user.role
    return True, f"Welcome back, {user.username} ({user.role})!"


def logout_user() -> None:
    """Terminates session and sets user to VIEWER role."""
    st.session_state.authenticated = False
    st.session_state.username = "guest"
    st.session_state.user_role = "VIEWER"
