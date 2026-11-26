"""Authentication session helper and role-based permission controller."""

import datetime
import streamlit as st
from typing import Tuple, Optional
from auth.crypto import hash_password, verify_password, needs_rehash
from persistence.repo import UserRepo, SessionRepo, AuditLogRepo


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
    """Initializes authentication variables and restores valid persistent sessions across reruns."""
    bootstrap_default_admin_if_empty()

    token = st.session_state.get("session_token")
    if token:
        sess = SessionRepo.get_valid_session(token)
        if sess:
            user = UserRepo.get_by_id(sess["user_id"])
            if user:
                st.session_state.authenticated = True
                st.session_state.username = user.username
                st.session_state.user_role = user.role
                return
        st.session_state.pop("session_token", None)

    if "authenticated" not in st.session_state or not st.session_state.get("session_token"):
        # Unauthenticated sessions always start as read-only VIEWER (never auto-grant ADMIN)
        st.session_state.authenticated = False
        st.session_state.username = "guest"
        st.session_state.user_role = "VIEWER"


def check_permission(action: str) -> bool:
    """Verifies whether the currently active user has permission to perform an action."""
    role = st.session_state.get("user_role", "VIEWER")
    if role != "VIEWER" and not st.session_state.get("authenticated", False):
        return False
    allowed = ROLE_PERMISSIONS.get(role, set())
    return action in allowed


def login_user(username: str, password: str) -> Tuple[bool, str]:
    """Authenticates a user against the SQLite database with lockout & persistent sessions."""
    clean_user = str(username or "").strip()
    if not clean_user or not password:
        return False, "Username and password are required."

    user = UserRepo.get_by_username(clean_user)
    if not user:
        AuditLogRepo.log(actor=clean_user, action="LOGIN_ATTEMPT", target="auth", status="FAILURE", details="Unknown username")
        return False, "Invalid username or password."

    # Enforce temporary account lockout
    if user.locked_until is not None:
        locked_dt = user.locked_until
        if isinstance(locked_dt, str):
            try:
                locked_dt = datetime.datetime.fromisoformat(locked_dt)
            except ValueError:
                locked_dt = None
        if locked_dt is not None and locked_dt > datetime.datetime.utcnow():
            AuditLogRepo.log(actor=user.username, action="LOGIN_BLOCKED", target="auth", status="WARNING", details="Account temporarily locked")
            return False, "Account temporarily locked due to repeated failed attempts. Try again later."

    try:
        valid = verify_password(user.password_hash, password)
    except ValueError:
        valid = False

    if not valid:
        UserRepo.increment_failed_attempt(user.id)
        AuditLogRepo.log(actor=user.username, action="LOGIN_ATTEMPT", target="auth", status="FAILURE", details="Invalid password")
        return False, "Invalid username or password."

    if needs_rehash(user.password_hash):
        UserRepo.update_password_hash(user.id, hash_password(password))

    UserRepo.update_login_success(user.id)
    token = SessionRepo.create_session(user.id)
    AuditLogRepo.log(actor=user.username, action="LOGIN_SUCCESS", target="auth", status="SUCCESS", details=f"Role={user.role}")

    st.session_state.authenticated = True
    st.session_state.username = user.username
    st.session_state.user_role = user.role
    st.session_state.session_token = token
    return True, f"Welcome back, {user.username} ({user.role})!"


def logout_user() -> None:
    """Terminates persistent session and resets user to VIEWER role."""
    token = st.session_state.get("session_token")
    actor = st.session_state.get("username", "guest")
    if token:
        SessionRepo.revoke_session(token)
    AuditLogRepo.log(actor=actor, action="LOGOUT", target="auth", status="SUCCESS", details="Session terminated")
    st.session_state.authenticated = False
    st.session_state.username = "guest"
    st.session_state.user_role = "VIEWER"
    st.session_state.pop("session_token", None)
