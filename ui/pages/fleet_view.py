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

    cols_b = st.columns(len(sim.robots))
    for idx, (r_id, r) in enumerate(sorted(sim.robots.items())):
        with cols_b[idx % len(cols_b)]:
            m = snapshot.fleet_metrics.get(r_id, {})
            health_val = m.get("health_score", {}).value or 100
            status_color = "#10B981" if health_val >= 80 else "#F59E0B" if health_val >= 60 else "#EF4444"
            st.markdown(
                f"""
                <div class="industry-kpi" style="border-left-color: {status_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 14px; font-weight: 700;">Robot R{r_id}</span>
                        <span style="font-size: 10px; font-weight: 800; color: {status_color};">{r.state}</span>
                    </div>
                    <div style="margin: 8px 0; font-size: 20px; font-weight: 700; color: {status_color};">
                        {health_val:.0f} <span style="font-size: 11px; color: #94A3B8;">/100 Health</span>
                    </div>
                    <div style="font-size: 12px; color: #CBD5E1; line-height: 1.6;">
                        🔋 Battery: <strong>{r.battery:.1f}%</strong><br>
                        📍 Position: <strong>{r.pos}</strong><br>
                        🎯 Target: <strong>{r.goal or 'Docked'}</strong><br>
                        📦 Completed: <strong>{r.completed_tasks} tasks</strong><br>
                        📏 Travelled: <strong>{r.total_distance}m</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown("#### 🔬 Detailed AMR Telemetry & Component Inspection")
    sel_inspect = st.selectbox("Select Robot for Deep Hardware Inspection", [f"Robot R{r}" for r in sorted(sim.robots.keys())], key="fleet_inspect_sel")
    inspect_id = int(sel_inspect.replace("Robot R", ""))
    if inspect_id in sim.robots:
        render_robot_inspector_drawer(sim.robots[inspect_id], inspect_id)
