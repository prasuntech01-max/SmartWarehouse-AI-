"""Dedicated 3D Digital Twin view — Three.js premium scene + Plotly fallback.

The Three.js scene is embedded as a full-height HTML component that communicates
with the Python simulation via window.updateSimulation(json_state).  The Plotly
renderer is preserved as an optional fallback if WebGL is unavailable.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from ui.components import render_section_header
from ui.sound_panel import get_sound_settings, render_sound_control_panel
from visualization.renderer_3d import Warehouse3DRenderer
from visualization.renderer import WarehouseRenderer
from visualization.threejs_bridge import build_simulation_state


# ─── Path to the built Three.js bundle ───────────────────────────────────────
_FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "threejs_digital_twin", "dist",
)
_BUNDLE_JS  = os.path.join(_FRONTEND_DIR, "bundle.js")
_INDEX_HTML = os.path.join(_FRONTEND_DIR, "index.html")

_THREEJS_AVAILABLE = os.path.isfile(_BUNDLE_JS) and os.path.getsize(_BUNDLE_JS) > 1000


import re

def _load_threejs_html() -> str:
    """Read the built index.html and cleanly inline the bundle for Streamlit components."""
    with open(_INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    with open(_BUNDLE_JS, "r", encoding="utf-8") as f:
        js = f.read()

    # Remove any external script tags referencing bundle.js (minified or unminified)
    html = re.sub(r'<script[^>]*src=[\'"]?bundle\.js[\'"]?[^>]*></script>', '', html, flags=re.IGNORECASE)

    # Safely inline the JavaScript bundle right before </body>
    inlined_script = f'<script type="text/javascript">\n{js}\n</script>'
    if "</body>" in html:
        html = html.replace("</body>", f"{inlined_script}\n</body>")
    else:
        html += inlined_script
    return html


def _get_uptime_start() -> float:
    return st.session_state.get("_app_start_time", time.time())


# ─── Render the Three.js twin ─────────────────────────────────────────────────

def _render_threejs(sim: Any, ai_engine: Any,
                    show_paths: bool, show_sensors: bool,
                    show_hazards: bool, height_px: int) -> None:
    """Inject Three.js scene and push live simulation data into it."""

    if not _THREEJS_AVAILABLE:
        st.warning(
            "⚠️ Three.js bundle not found at `frontend/threejs_digital_twin/dist/bundle.js`. "
            "Run `npm run build` inside `frontend/threejs_digital_twin/` to generate it.",
            icon="🔧",
        )
        return

    # Sample IoT sensor observations (use real iot module if available)
    sample_sensors = None
    if show_sensors:
        sample_sensors = [
            {"sensor_id": "temp_aisle1", "type": "Temperature",
             "value": 24.5, "unit": "°C", "status": "NORMAL", "coord": [3, 3]},
            {"sensor_id": "smoke_dock",  "type": "Smoke",
             "value": 0.05, "unit": "ratio", "status": "NORMAL", "coord": [1, 1]},
            {"sensor_id": "gas_pack",    "type": "Gas",
             "value": 0.02, "unit": "ratio", "status": "NORMAL", "coord": [13, 2]},
        ]

    # Hazard zones (from actual dynamic obstacles)
    hazard_zones = None
    if show_hazards and sim.grid.dynamic_obstacles:
        hazard_zones = [
            {"type": "OBSTACLE", "severity": "WARNING", "coord": list(obs)}
            for obs in sim.grid.dynamic_obstacles
        ]

    # Build the JSON state from real simulation data
    state = build_simulation_state(
        sim=sim,
        sensors=sample_sensors if show_sensors else [],
        hazards=hazard_zones,
        uptime_start=_get_uptime_start(),
        sound_settings=get_sound_settings(),
    )
    state_json = json.dumps(state, separators=(',', ':'))

    # Load and inline the Three.js HTML
    try:
        html_content = _load_threejs_html()
    except Exception as exc:
        st.error(f"Failed to load Three.js bundle: {exc}")
        return

    # Inject the initialisation call after the bundle loads
    injection = f"""
<script>
(function waitForScene() {{
  if (typeof window.updateSimulation === 'function') {{
    window.updateSimulation({state_json});
  }} else {{
    setTimeout(waitForScene, 80);
  }}
}})();
</script>
"""
    full_html = html_content + injection

    components.html(full_html, height=height_px, scrolling=False)


# ─── Main page renderer ───────────────────────────────────────────────────────

def render_digital_twin_page(sim: Any, ai_engine: Any) -> None:
    """Renders the comprehensive 3D Digital Twin with Three.js scene."""

    render_section_header(
        "Interactive 3D Sensor Digital Twin",
        "Premium industrial warehouse digital twin — real Python simulation data, "
        "detailed AMR models, pallet racks, conveyors, and live telemetry.",
        icon="🌐",
    )

    # ── Top controls ─────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1, 1, 1, 1])

    with ctrl1:
        display_mode = st.radio(
            "Render Engine",
            ["3D Three.js (WebGL)", "3D Plotly (WebGL)", "2D Matplotlib Fallback"],
            index=0,
            horizontal=True,
        )
    with ctrl2:
        height_choice = st.selectbox("Viewport Height", ["680px", "800px", "560px"], index=0)
        height_px = int(height_choice.replace("px", ""))
    with ctrl3:
        fleet_opts = ["All Fleet"] + [f"Robot R{r}" for r in sorted(sim.robots.keys())]
        sel_bot_lbl = st.selectbox("Target Robot Focus", fleet_opts, index=0)
        sel_bot_id  = int(sel_bot_lbl.replace("Robot R", "")) if "Robot R" in sel_bot_lbl else None
    with ctrl4:
        cam_choice = st.selectbox("Camera Preset", ["Isometric", "Top-Down", "Front", "Side"], index=0)
        cam_map = {"Isometric": "iso", "Top-Down": "top", "Front": "front", "Side": "side"}

    # ── Layer toggles ─────────────────────────────────────────────────────────
    with st.expander("🛠️ Layer Visibility & Overlay Controls", expanded=False):
        lcol1, lcol2, lcol3, lcol4 = st.columns(4)
        with lcol1:
            show_paths   = st.checkbox("Planned Navigation Routes", value=True)
            show_trails  = st.checkbox("Movement Trails (History)",  value=True)
        with lcol2:
            show_beacons  = st.checkbox("Task Beacons & Mission Rays", value=True)
            show_heatmaps = st.checkbox("Congestion Density Overlay",  value=True)
        with lcol3:
            show_shelf_recs = st.checkbox("Shelf Relocation Badges", value=True)
            show_labels     = st.checkbox("Station / Dock Labels",   value=True)
        with lcol4:
            show_sensors = st.checkbox("IoT Sensor Discs",   value=True)
            show_hazards = st.checkbox("Hazard Zones (Alert)", value=True)

    with st.expander("🔊 Futuristic Sound Control Panel", expanded=False):
        render_sound_control_panel(key_prefix="dt_snd")

    # ── Render selection ──────────────────────────────────────────────────────
    if "Three.js" in display_mode:
        # ── Three.js premium scene ────────────────────────────────────────────
        # Quick metrics bar above the canvas
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        total_done = sum(r.completed_tasks for r in sim.robots.values())
        avg_bat    = (sum(r.battery for r in sim.robots.values()) / max(len(sim.robots), 1))
        throughput = round(total_done / max(sim.step_count, 1) * 100, 1)

        m_col1.metric("Step",        sim.step_count)
        m_col2.metric("Active Robots", len(sim.robots))
        m_col3.metric("Tasks Done",  total_done)
        m_col4.metric("Throughput",  f"{throughput}/100 steps")
        m_col5.metric("Avg Battery", f"{avg_bat:.1f}%")

        if not _THREEJS_AVAILABLE:
            st.info(
                "**Three.js bundle not built yet.** To build it, open a terminal and run:\n\n"
                "```\ncd frontend/threejs_digital_twin\nnpm run build\n```\n\n"
                "The scene will appear here after the build completes and you reload the page.",
                icon="🔧",
            )
        else:
            _render_threejs(
                sim=sim,
                ai_engine=ai_engine,
                show_paths=show_paths,
                show_sensors=show_sensors,
                show_hazards=show_hazards,
                height_px=height_px,
            )

    elif "Plotly" in display_mode:
        # ── Existing Plotly renderer (kept intact) ────────────────────────────
        t0 = time.perf_counter()
        renderer_3d = Warehouse3DRenderer(sim.grid)

        sample_sensors_plotly = [
            {"sensor_id": "temp_aisle1", "type": "Temperature", "value": 24.5,
             "unit": "°C", "status": "NORMAL", "coord": (3, 3)},
            {"sensor_id": "smoke_dock",  "type": "Smoke",        "value": 0.05,
             "unit": "ratio", "status": "NORMAL", "coord": (1, 1)},
            {"sensor_id": "gas_pack",    "type": "Gas",           "value": 0.02,
             "unit": "ratio", "status": "NORMAL", "coord": (13, 2)},
        ] if show_sensors else None

        sample_hazards_plotly = [
            {"type": "OBSTACLE", "severity": "WARNING", "coord": obs}
            for obs in sim.grid.dynamic_obstacles
        ] if show_hazards and sim.grid.dynamic_obstacles else None

        c_heatmap = ai_engine.congestion_predictor.get_congestion_heatmap(sim.robots) if show_heatmaps else None
        s_recs    = ai_engine.shelf_optimizer.recommend_relocations(top_n=3) if show_shelf_recs else None

        try:
            fig = renderer_3d.render_3d(
                robots=sim.robots,
                step_count=sim.step_count,
                height=height_px,
                camera_view=cam_map[cam_choice],
                theme="dark",
                congestion_heatmap=c_heatmap,
                shelf_optimizations=s_recs,
                selected_robot_id=sel_bot_id,
                sensors=sample_sensors_plotly,
                hazard_zones=sample_hazards_plotly,
                show_trails=show_trails,
                show_paths=show_paths,
                show_beacons=show_beacons,
                show_heatmaps=show_heatmaps,
                show_labels=show_labels,
                show_sensors=show_sensors,
                show_hazards=show_hazards,
            )
            t1 = time.perf_counter()
            build_ms  = (t1 - t0) * 1000.0
            num_traces = len(fig.data)
            budget_color = "#10B981" if num_traces <= 40 else "#EF4444"

            st.markdown(
                f"""
                <div style="display:flex;gap:16px;margin-bottom:8px;font-size:11px;">
                  <span style="color:#94A3B8;">Trace Budget:
                    <strong style="color:{budget_color};">{num_traces} / 40 traces</strong></span>
                  <span style="color:#94A3B8;">Render Latency:
                    <strong style="color:#38BDF8;">{build_ms:.1f} ms</strong></span>
                  <span style="color:#94A3B8;">Grid:
                    <strong style="color:#F8FAFC;">{sim.grid.width}×{sim.grid.height}</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig, use_container_width=True)

        except Exception as exc:
            st.error(f"3D Plotly render issue ({exc}). Switching to 2D fallback.")
            renderer_2d = WarehouseRenderer(sim.grid)
            st.pyplot(renderer_2d.render(sim.robots, sim.step_count), use_container_width=True)

    else:
        # ── 2D Matplotlib fallback ────────────────────────────────────────────
        renderer_2d = WarehouseRenderer(sim.grid)
        st.pyplot(renderer_2d.render(sim.robots, sim.step_count), use_container_width=True)
