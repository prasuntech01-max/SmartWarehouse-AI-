"""Path Planning, Space-Time A*, and Deadlock Recovery view."""

import streamlit as st
import pandas as pd
from typing import Any
from ui.components import render_section_header, render_kpi_card
from core.multi_agent import MultiAgentPlanner


def render_path_planning_page(sim: Any, analytics_service: Any) -> None:
    """Renders space-time path reservation analytics, deadlock logs, and dynamic replanning metrics."""
    render_section_header(
        "Path Planning & Space-Time Verification",
        "Deterministic Space-Time A* searching in (x, y, t) state space, reservation tables, and collision avoidance verification.",
        icon="🗺️",
    )

    snapshot = analytics_service.get_snapshot()
    safety = snapshot.safety_kpis

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("Physical Collisions", safety["physical_collisions"].value, "collisions", provenance=safety["physical_collisions"].provenance)
    with col2:
        render_kpi_card("Conflicts Resolved", safety["conflicts_detected_and_avoided"].value, "conflicts", provenance=safety["conflicts_detected_and_avoided"].provenance)
    with col3:
        render_kpi_card("Replan Success Rate", f"{safety['replan_success_rate'].value}%", "", provenance=safety["replan_success_rate"].provenance)
    with col4:
        render_kpi_card("Avg Replan Latency", safety["avg_replan_latency"].value, "ms", provenance=safety["avg_replan_latency"].provenance)

    st.divider()

    # Active Horizon Verification
    active_paths = {r_id: r.path[r.path_index:] for r_id, r in sim.robots.items() if r.path}
    live_conflicts = MultiAgentPlanner.detect_conflicts(
        active_paths,
        warehouse=sim.grid,
        park_at_goal=False,
    )

    col_v1, col_v2 = st.columns([1.2, 1.0])
    with col_v1:
        st.markdown("#### 🛡️ Space-Time Conflict Verifier")
        if not live_conflicts:
            st.success("✅ **0 Vertex & 0 Edge Conflicts** detected across all active future horizons.")
            st.caption("Active reservation table guarantees no overlapping coordinates at any shared time step.")
        else:
            st.warning(f"⚠️ {len(live_conflicts)} potential conflict(s) detected.")

        st.markdown("#### 📜 Deadlock Recovery Event History")
        dl_events = sim.deadlock_handler.event_log
        if dl_events:
            df_dl = pd.DataFrame([e.to_dict() for e in reversed(dl_events[-15:])])
            st.dataframe(df_dl, use_container_width=True, hide_index=True)
        else:
            st.info("No deadlock cycles have occurred. Wait-For Graph (WFG) is currently acyclic.")

    with col_v2:
        st.markdown("#### ⚡ Dynamic Obstacle Replan Log")
        replan_history = sim.replanner.replan_history
        if replan_history:
            df_rep = pd.DataFrame([e.to_dict() for e in reversed(replan_history[-15:])])
            st.dataframe(df_rep, use_container_width=True, hide_index=True)
        else:
            st.info("No dynamic obstacle replannings recorded yet.")
