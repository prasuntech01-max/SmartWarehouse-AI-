"""Dedicated 3D Digital Twin view with full layer controls and camera presets."""

import time
import streamlit as st
from typing import Any
from ui.components import render_section_header
from visualization.renderer_3d import Warehouse3DRenderer
from visualization.renderer import WarehouseRenderer


def render_digital_twin_page(sim: Any, ai_engine: Any) -> None:
    """Renders the comprehensive 3D Digital Twin with layer toggles and telemetry inspection."""
    render_section_header(
        "Interactive 3D Sensor Digital Twin",
        "High-fidelity digital-twin with cybernetic aesthetic, mission rays, dynamic replanning paths, and telemetry.",
        icon="🌐",
    )

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1, 1, 1, 1])
    with ctrl_col1:
        cam_choice = st.selectbox("Camera Preset", ["Isometric", "Top-Down", "Front", "Side"], index=0)
        cam_map = {"Isometric": "iso", "Top-Down": "top", "Front": "front", "Side": "side"}
    with ctrl_col2:
        theme_choice = st.selectbox("Lighting & Theme", ["Industrial Dark", "Clean Light"], index=0)
        thm = "dark" if "Dark" in theme_choice else "light"
    with ctrl_col3:
        fleet_opts = ["All Fleet"] + [f"Robot R{r}" for r in sorted(sim.robots.keys())]
        sel_bot_lbl = st.selectbox("Target Robot Focus", fleet_opts, index=0)
        sel_bot_id = int(sel_bot_lbl.replace("Robot R", "")) if "Robot R" in sel_bot_lbl else None
    with ctrl_col4:
        display_mode = st.radio("Render Engine", ["3D Plotly (WebGL)", "2D Matplotlib Fallback"], index=0, horizontal=True)

    with st.expander("🛠️ Layer Visibility & Overlay Controls", expanded=False):
        lcol1, lcol2, lcol3, lcol4 = st.columns(4)
        with lcol1:
            show_paths = st.checkbox("Planned Navigation Routes", value=True)
            show_trails = st.checkbox("Movement Trails (History)", value=True)
        with lcol2:
            show_beacons = st.checkbox("Task Beacons & Mission Rays", value=True)
            show_heatmaps = st.checkbox("Congestion Density Overlay", value=True)
        with lcol3:
            show_shelf_recs = st.checkbox("Shelf Relocation Badges", value=True)
            show_labels = st.checkbox("Station / Dock Labels", value=True)
        with lcol4:
            show_sensors = st.checkbox("IoT Sensor Discs", value=True)
            show_hazards = st.checkbox("Hazard Zones (Alert)", value=True)

    if "3D" in display_mode:
        t0 = time.perf_counter()
        renderer_3d = Warehouse3DRenderer(sim.grid)

        # Mock sample IoT sensor observations for twin visualization
        sample_sensors = [
            {"sensor_id": "temp_aisle1", "type": "Temperature", "value": 24.5, "unit": "°C", "status": "NORMAL", "coord": (3, 3)},
            {"sensor_id": "smoke_dock", "type": "Smoke", "value": 0.05, "unit": "ratio", "status": "NORMAL", "coord": (1, 1)},
            {"sensor_id": "gas_pack", "type": "Gas", "value": 0.02, "unit": "ratio", "status": "NORMAL", "coord": (13, 2)},
        ] if show_sensors else None

        # Sample hazard zones
        sample_hazards = [
            {"type": "OBSTACLE", "severity": "WARNING", "coord": obs}
            for obs in sim.grid.dynamic_obstacles
        ] if show_hazards and sim.grid.dynamic_obstacles else None

        c_heatmap = ai_engine.congestion_predictor.get_congestion_heatmap(sim.robots) if show_heatmaps else None
        s_recs = ai_engine.shelf_optimizer.recommend_relocations(top_n=3) if show_shelf_recs else None

        try:
            fig = renderer_3d.render_3d(
                robots=sim.robots,
                step_count=sim.step_count,
                height=680,
                camera_view=cam_map[cam_choice],
                theme=thm,
                congestion_heatmap=c_heatmap,
                shelf_optimizations=s_recs,
                selected_robot_id=sel_bot_id,
                sensors=sample_sensors,
                hazard_zones=sample_hazards,
                show_trails=show_trails,
                show_paths=show_paths,
                show_beacons=show_beacons,
                show_heatmaps=show_heatmaps,
                show_labels=show_labels,
                show_sensors=show_sensors,
                show_hazards=show_hazards,
            )
            t1 = time.perf_counter()
            build_ms = (t1 - t0) * 1000.0
            num_traces = len(fig.data)

            # Performance & Trace Budget Badge
            budget_color = "#10B981" if num_traces <= 40 else "#EF4444"
            st.markdown(
                f"""
                <div style="display: flex; gap: 16px; margin-bottom: 8px; font-size: 11px;">
                    <span style="color: #94A3B8;">Trace Budget: <strong style="color: {budget_color};">{num_traces} / 40 traces</strong></span>
                    <span style="color: #94A3B8;">Render Latency: <strong style="color: #38BDF8;">{build_ms:.1f} ms</strong></span>
                    <span style="color: #94A3B8;">Grid Dimensions: <strong style="color: #F8FAFC;">{sim.grid.width}×{sim.grid.height} ({sim.grid.width*sim.grid.height} cells)</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"3D WebGL render encountered an issue ({e}). Displaying 2D floorplan fallback.")
            renderer_2d = WarehouseRenderer(sim.grid)
            fig_2d = renderer_2d.render(sim.robots, sim.step_count)
            st.pyplot(fig_2d, use_container_width=True)
    else:
        renderer_2d = WarehouseRenderer(sim.grid)
        fig_2d = renderer_2d.render(sim.robots, sim.step_count)
        st.pyplot(fig_2d, use_container_width=True)
