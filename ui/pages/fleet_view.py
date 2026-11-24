"""Robot Fleet Telemetry and Diagnostic Health view."""

import streamlit as st
from typing import Any
from ui.components import render_section_header, render_kpi_card, render_robot_inspector_drawer
from analytics.service import AnalyticsService
from visualization.ai_dashboard import render_fleet_health_dashboard, render_maintenance_priority


def render_fleet_page(sim: Any, ai_engine: Any, analytics_service: AnalyticsService) -> None:
    """Renders comprehensive robot fleet telemetry and predictive maintenance."""
    render_section_header(
        "Autonomous Robot Fleet Telemetry",
        "Individual mobile robot states, battery depletion curves, wear telemetry, and predictive maintenance diagnostics.",
        icon="🤖",
    )

    snapshot = analytics_service.get_snapshot()

    # Fleet Overview KPIs
    wb = snapshot.workload_balance
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Fleet Count", len(sim.robots), "units", provenance=snapshot.summary_kpis["total_tasks"].provenance)
    with k2:
        render_kpi_card("Workload Gini Index", wb.get("gini_index", {}).value or 0.0, "equality", provenance=wb["gini_index"].provenance, help_text="0.0 = perfect fairness")
    with k3:
        render_kpi_card("Mean Tasks / Bot", wb.get("mean_tasks", {}).value or 0.0, "tasks", provenance=wb["mean_tasks"].provenance)
    with k4:
        tot_dist = snapshot.path_efficiency.get("total_fleet_distance", {}).value or 0
        render_kpi_card("Cumulative Distance", tot_dist, "m", provenance=snapshot.path_efficiency["total_fleet_distance"].provenance)

    st.divider()

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("#### 🩺 Fleet Diagnostic Health Scores")
        fig_health = render_fleet_health_dashboard(ai_engine.health_monitor)
        st.plotly_chart(fig_health, use_container_width=True)
    with col_h2:
        st.markdown("#### 🔧 Maintenance Urgency Priority")
        fig_pri = render_maintenance_priority(ai_engine.health_monitor)
        st.plotly_chart(fig_pri, use_container_width=True)

    st.divider()
    st.markdown("#### 📋 Detailed Per-Robot Diagnostic Telemetry")

    fleet_meta = {
        1: {"name": "TITAN-X", "type": "Heavy AMR", "color": "#00D4FF", "duty": "Heavy Pallet Transport"},
        2: {"name": "ATLAS", "type": "Humanoid", "color": "#0077FF", "duty": "Package Picking & Handling"},
        3: {"name": "VORTEX", "type": "Humanoid", "color": "#FF8800", "duty": "High-Speed Sorter"},
        4: {"name": "NOVA", "type": "Humanoid", "color": "#00FF66", "duty": "Inventory & Inspection"},
        5: {"name": "SPECTRE", "type": "Humanoid", "color": "#00F0FF", "duty": "Area Patrol & Security"},
    }

    cols_b = st.columns(len(sim.robots))
    for idx, (r_id, r) in enumerate(sorted(sim.robots.items())):
        with cols_b[idx % len(cols_b)]:
            m = snapshot.fleet_metrics.get(r_id, {})
            health_val = m.get("health_score", {}).value or 100
            info = fleet_meta.get(r_id, {"name": f"Robot {r_id}", "type": "AMR", "color": "#00F0FF", "duty": "Standard"})
            status_color = "#10B981" if health_val >= 80 else "#F59E0B" if health_val >= 60 else "#EF4444"
            card_html = (
                f'<div class="industry-kpi" style="border-left-color: {info["color"]};">'
                f'<div style="display: flex; justify-content: space-between; align-items: center;">'
                f'<span style="font-family: \'Orbitron\', sans-serif; font-size: 13px; font-weight: 800; color: {info["color"]};">0{r_id} {info["name"]}</span>'
                f'<span style="font-size: 10px; font-weight: 800; color: {status_color}; background: rgba(16, 185, 129, 0.15); padding: 2px 6px; border-radius: 4px;">{r.state}</span>'
                f'</div>'
                f'<div style="font-size: 11px; color: #94A3B8; margin-top: 2px; font-weight: 600;">{info["type"]} &bull; {info["duty"]}</div>'
                f'<div style="margin: 8px 0; font-size: 22px; font-weight: 700; color: #FFFFFF; font-family: \'Rajdhani\', monospace;">'
                f'{health_val:.0f} <span style="font-size: 11px; color: #94A3B8;">/100 Health</span>'
                f'</div>'
                f'<div style="font-size: 12px; color: #CBD5E1; line-height: 1.6;">'
                f'🔋 Battery: <strong>{r.battery:.1f}%</strong><br>'
                f'📍 Position: <strong>{r.pos}</strong><br>'
                f'🎯 Target: <strong>{r.goal or "Docked"}</strong><br>'
                f'📦 Completed: <strong>{r.completed_tasks} tasks</strong><br>'
                f'📏 Travelled: <strong>{r.total_distance}m</strong>'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🔬 Detailed AMR Telemetry & Component Inspection")
    inspect_options = [f"0{r} — {fleet_meta.get(r, {}).get('name', 'Robot')} ({fleet_meta.get(r, {}).get('type', 'AMR')})" for r in sorted(sim.robots.keys())]
    sel_inspect = st.selectbox("Select Robot for Deep Hardware Inspection", inspect_options, key="fleet_inspect_sel")
    inspect_id = int(sel_inspect.split(" ")[0])
    if inspect_id in sim.robots:
        render_robot_inspector_drawer(sim.robots[inspect_id], inspect_id)
