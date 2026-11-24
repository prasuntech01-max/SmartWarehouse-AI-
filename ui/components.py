"""Reusable visual components for SmartWarehouse AI."""

import html
import textwrap
import streamlit as st
from typing import Optional, Any
from analytics.models import ProvenanceType


def render_provenance_badge(provenance: Any) -> str:
    """Returns HTML for an explicit data provenance badge."""
    p_val = provenance.value if hasattr(provenance, "value") else str(provenance)
    badge_cls = {
        "MEASURED": "badge-measured",
        "SIMULATED": "badge-simulated",
        "SIMULATED-TELEMETRY": "badge-telemetry",
        "ESTIMATED": "badge-estimated",
    }.get(p_val, "badge-simulated")
    return f'<span class="badge-provenance {badge_cls}">{html.escape(p_val)}</span>'


def render_kpi_card(
    title: str,
    value: Any,
    unit: str = "",
    delta: Optional[str] = None,
    delta_positive: bool = True,
    provenance: Optional[Any] = None,
    help_text: str = "",
) -> None:
    """Renders a styled industrial KPI metric card."""
    delta_html = ""
    if delta:
        delta_cls = "kpi-delta-positive" if delta_positive else "kpi-delta-negative"
        arrow = "↑" if delta_positive else "↓"
        delta_html = f'<div class="{delta_cls}">{arrow} {html.escape(delta)}</div>'

    badge_html = render_provenance_badge(provenance) if provenance else ""
    help_html = f'<div style="font-size: 10px; color: #64748B; margin-top: 4px;">{html.escape(help_text)}</div>' if help_text else ""

    card_html = (
        f'<div class="industry-kpi">'
        f'<div class="kpi-label">{html.escape(title)}</div>'
        f'<div class="kpi-main-val">{html.escape(str(value))} <span class="kpi-unit-val">{html.escape(unit)}</span></div>'
        f'{delta_html}{badge_html}{help_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_status_chip(status: str) -> str:
    """Returns an inline HTML status chip."""
    s_upper = str(status).upper()
    if s_upper in ("IDLE", "DOCKED", "NORMAL"):
        cls = "chip-normal"
    elif s_upper in ("MOVING_TO_PICK", "MOVING_TO_DELIVERY", "WARNING"):
        cls = "chip-warning"
    elif s_upper in ("EMERGENCY", "CRITICAL", "FAILED"):
        cls = "chip-critical"
    else:
        cls = "chip-idle"
    return f'<span class="status-chip {cls}">{html.escape(str(status))}</span>'


def render_alert_banner(message: str, level: str = "info") -> None:
    """Renders a prominent alert banner."""
    if level == "error" or level == "critical":
        st.error(f"🚨 {message}")
    elif level == "warning":
        st.warning(f"⚠️ {message}")
    elif level == "success":
        st.success(f"✅ {message}")
    else:
        st.info(f"ℹ️ {message}")


def render_section_header(title: str, subtitle: Optional[str] = None, icon: str = "🤖") -> None:
    """Renders a consistent section title with icon and subtitle."""
    st.subheader(f"{icon} {title}")
    if subtitle:
        st.caption(subtitle)


def render_global_search_bar(sim: Any) -> None:
    """Renders an instant global finder across Robots, Tasks, Sensors, and Incidents."""
    with st.expander("🔍 Global Warehouse Quick-Finder (Robots / Tasks / Sensors)", expanded=False):
        q = st.text_input("Enter Robot ID (e.g. R1), Task ID (e.g. 5), or State keyword", key="global_search_query", placeholder="Search fleet...")
        if q:
            q_clean = q.strip().lower()
            matches = []
            # Search robots
            for r_id, r in getattr(sim, 'robots', {}).items():
                if f"r{r_id}" in q_clean or str(r_id) == q_clean or q_clean in r.state.lower():
                    matches.append(("Robot", f"R{r_id}", f"State: {r.state} | Pos: {r.pos} | Battery: {getattr(r, 'battery', 100.0):.1f}%"))
            # Search tasks
            if hasattr(sim, 'task_manager'):
                for t in getattr(sim.task_manager, 'active_tasks', []):
                    if str(t.task_id) == q_clean or f"#{t.task_id}" in q_clean or q_clean in t.status.lower():
                        matches.append(("Task", f"#{t.task_id}", f"Status: {t.status} | Priority: {t.priority_label} | Assigned: R{t.assigned_robot_id}"))

            if matches:
                st.markdown(f"**Found {len(matches)} matching result(s):**")
                for kind, ident, details in matches:
                    st.markdown(
                        textwrap.dedent(f"""
                        <div style="background: #0F172A; border-left: 3px solid #00F0FF; padding: 6px 12px; margin-bottom: 6px; border-radius: 4px;">
                            <span style="color: #38BDF8; font-weight: 700; font-size: 11px;">[{kind.upper()}]</span>
                            <strong style="color: #F8FAFC; margin-left: 6px;">{ident}</strong>
                            <span style="color: #94A3B8; font-size: 12px; margin-left: 10px;">{details}</span>
                        </div>
                        """).strip(),
                        unsafe_allow_html=True,
                    )
            else:
                st.info(f"No direct matches found for '{q}'. Try searching 'R1', 'idle', or 'moving'.")


def render_notification_tray(events: Optional[list] = None) -> None:
    """Renders a collapsible industrial activity and notification tray."""
    default_events = [
        {"time": "Just now", "type": "INFO", "msg": "Fleet telemetry stream synchronized across WebGL twin."},
        {"time": "1 min ago", "type": "SUCCESS", "msg": "Spatiotemporal conflict detector verified 0 vertex/edge collisions."},
        {"time": "3 mins ago", "type": "ALERT", "msg": "Dynamic obstacle avoidance algorithm calibrated for narrow aisle yield."},
    ]
    items = events or default_events
    with st.expander(f"🔔 Live Operations Stream ({len(items)} events)", expanded=False):
        for it in items:
            color = "#10B981" if it["type"] == "SUCCESS" else "#38BDF8" if it["type"] == "INFO" else "#F59E0B"
            st.markdown(
                textwrap.dedent(f"""
                <div style="display: flex; gap: 8px; font-size: 12px; padding: 4px 0; border-bottom: 1px solid #1E293B;">
                    <span style="color: #64748B; font-family: monospace;">[{it['time']}]</span>
                    <span style="color: {color}; font-weight: 700;">[{it['type']}]</span>
                    <span style="color: #CBD5E1;">{it['msg']}</span>
                </div>
                """).strip(),
                unsafe_allow_html=True,
            )


def render_robot_inspector_drawer(robot: Any, robot_id: int) -> None:
    """Renders detailed diagnostics and status drawer for a single selected robot."""
    st.markdown(
        textwrap.dedent(f"""
        <div style="background: #0B132B; border: 1px solid #1E293B; border-radius: 8px; padding: 14px; margin-top: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-bottom: 10px;">
                <h4 style="margin: 0; color: #00F0FF;">🤖 Autonomous Mobile Robot R{robot_id} (AMR-500)</h4>
                <span class="status-chip chip-normal">{robot.state}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 12px;">
                <div><span style="color: #64748B;">Current Position:</span><br><strong style="color: #F8FAFC;">{robot.pos}</strong></div>
                <div><span style="color: #64748B;">Target Goal:</span><br><strong style="color: #F8FAFC;">{robot.goal or 'None'}</strong></div>
                <div><span style="color: #64748B;">Battery Level:</span><br><strong style="color: #10B981;">{getattr(robot, 'battery', 100.0):.1f}%</strong></div>
                <div><span style="color: #64748B;">Tasks Completed:</span><br><strong style="color: #38BDF8;">{getattr(robot, 'completed_tasks', 0)}</strong></div>
            </div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )
