"""UI package for SmartWarehouse AI (Module 13)."""

from .theme import inject_custom_theme
from .components import (
    render_kpi_card,
    render_provenance_badge,
    render_status_chip,
    render_alert_banner,
    render_section_header,
)
from .navigation import render_sidebar_navigation
from .auth_helper import init_auth_session, check_permission, login_user, logout_user

__all__ = [
    "inject_custom_theme",
    "render_kpi_card",
    "render_provenance_badge",
    "render_status_chip",
    "render_alert_banner",
    "render_section_header",
    "render_sidebar_navigation",
    "init_auth_session",
    "check_permission",
    "login_user",
    "logout_user",
]
