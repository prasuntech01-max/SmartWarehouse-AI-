"""SmartWarehouse AI — Interactive Streamlit Dashboard (Module 10).

Autonomous warehouse robot simulator featuring:
- Time-Expanded State Space & Space-Time A* Planning
- Reservation Tables for Vertex & Edge-Swap Collision Avoidance
- Wait-For Graph (WFG) Deadlock Detection & Multi-Tier Recovery
- Dynamic Obstacle Management with Event History
- Intelligent Multi-Strategy Task Assignment (Nearest, Shortest, Priority, Workload, Weighted, Hungarian)
- Real-Time Fleet Workload & Battery Optimization
- Interactive Task Management Operations Center (Create, Cancel, Reassign)
- Professional 3D Digital Twin with Mission Beacons, Camera Controls & Rays
- AI-Powered Intelligence: Demand Forecasting, Congestion Prediction, Predictive Maintenance,
  Smart Shelf Optimization, Fleet Strategy Benchmarking (Module 10)
"""

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import time

from simulation.engine import WarehouseSimulator
from simulation.demo import DemoScenario
from simulation.ai_analytics import AIAnalyticsEngine
from visualization.renderer import WarehouseRenderer, ROBOT_COLORS
from visualization.renderer_3d import Warehouse3DRenderer
from visualization.ai_dashboard import (
    render_demand_forecast_chart,
    render_top_shelves_chart,
    render_congestion_heatmap_3d,
    render_fleet_health_dashboard,
    render_strategy_comparison,
    render_shelf_optimization_3d,
    render_maintenance_priority,
)
from core.multi_agent import MultiAgentPlanner
from core.task_manager import TaskPriority
from core.task_assignment import AssignmentStrategy
from simulation.metrics import MetricsCollector

# Streamlit Page Configuration
st.set_page_config(
    page_title="SmartWarehouse AI — AI Intelligence & Digital Twin (Module 10)",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Industrial Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #0F172A;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #00F0FF;
        color: #F8FAFC;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-critical { background-color: #EF4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-high { background-color: #F59E0B; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-normal { background-color: #0284C7; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .priority-urgent { color: #EF4444; font-weight: bold; }
    .priority-high { color: #F59E0B; font-weight: bold; }
    .priority-normal { color: #0284C7; font-weight: bold; }
    .priority-low { color: #94A3B8; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def get_simulator() -> WarehouseSimulator:
    """Retrieve or initialize simulator in session state."""
    if 'sim' not in st.session_state:
        st.session_state.num_robots = 3
        st.session_state.paused = False
        st.session_state.batch_size = 5
        st.session_state.demo_result = None
        st.session_state.last_message = "Simulator initialized with 3 robots on 15x15 grid — Module 10 ready."
        st.session_state.sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    return st.session_state.sim


def get_analytics_engine(sim_instance: WarehouseSimulator) -> AIAnalyticsEngine:
    """Retrieve or create AI analytics engine bound to current simulator."""
    if 'ai_engine' not in st.session_state or st.session_state.get('ai_sim_id') != id(sim_instance):
        st.session_state.ai_engine = AIAnalyticsEngine(sim_instance)
        st.session_state.ai_sim_id = id(sim_instance)
    else:
        st.session_state.ai_engine.sim = sim_instance
    return st.session_state.ai_engine


sim = get_simulator()
ai_engine = get_analytics_engine(sim)
renderer_2d = WarehouseRenderer(sim.grid)
renderer_3d = Warehouse3DRenderer(sim.grid)

# ===================== SIDEBAR CONTROLS =====================
with st.sidebar:
    st.title("🤖 Control Centre")
    st.caption("SmartWarehouse AI — Industrial Fleet & AI Controls")

    # Display & Visual Settings
    st.subheader("🖥 Visualization Settings")
    view_mode = st.radio(
        "Display Mode",
        ["3D Digital Twin (Plotly)", "2D Floorplan (Matplotlib)"],
        index=0,
    )

    if "3D" in view_mode:
        col_cam, col_thm = st.columns(2)
        with col_cam:
            camera_preset = st.selectbox(
                "Camera Preset",
                options=["Isometric", "Top-Down", "Front", "Side"],
                index=0,
            )
            camera_map = {"Isometric": "iso", "Top-Down": "top", "Front": "front", "Side": "side"}
            selected_cam = camera_map[camera_preset]
        with col_thm:
            theme_choice = st.selectbox(
                "3D Theme",
                options=["Industrial Dark", "Clean Light"],
                index=0,
            )
            theme_val = "dark" if "Dark" in theme_choice else "light"

        with st.expander("🛠 3D Layer Overlays", expanded=False):
            show_heatmaps = st.checkbox("Congestion Heatmap", value=True)
            show_shelf_recs = st.checkbox("Shelf Relocation Badges", value=True)
            show_paths = st.checkbox("Robot Navigation Paths", value=True)
            show_trails = st.checkbox("Movement Trails", value=True)
            show_beacons = st.checkbox("Task Beacons & Rays", value=True)
            show_labels = st.checkbox("Station / Dock Labels", value=True)

        fleet_options = ["All Fleet"] + [f"Robot R{r_id}" for r_id in sorted(sim.robots.keys())]
        selected_robot_label = st.selectbox("Highlight Robot Focus", options=fleet_options, index=0)
        selected_robot_id = int(selected_robot_label.replace("Robot R", "")) if "Robot R" in selected_robot_label else None
    else:
        selected_cam = "iso"
        theme_val = "light"
        show_heatmaps = False
        show_shelf_recs = False
        show_paths = True
        show_trails = True
        show_beacons = True
        show_labels = True
        selected_robot_id = None

    st.divider()

    # Fleet size selector
    selected_robots = st.slider(
        "Robot Fleet Size",
        min_value=1,
        max_value=5,
        value=st.session_state.num_robots,
        help="Configurable fleet size (1 to 5 robots). Default is 3.",
    )

    if selected_robots != st.session_state.num_robots:
        st.session_state.num_robots = selected_robots
        sim.reset(num_robots=selected_robots)
        ai_engine = get_analytics_engine(sim)
        renderer_2d = WarehouseRenderer(sim.grid)
        renderer_3d = Warehouse3DRenderer(sim.grid)
        st.session_state.demo_result = None
        st.session_state.last_message = f"Fleet reconfigured to {selected_robots} robots."
        st.rerun()

    st.divider()
    st.subheader("🎯 Dispatch Strategy")
    strategy_options = {
        "Weighted Multi-Criteria": AssignmentStrategy.WEIGHTED_MULTI_CRITERIA,
        "Priority-First Dispatch": AssignmentStrategy.PRIORITY_FIRST,
        "Workload-Balanced Allocation": AssignmentStrategy.WORKLOAD_BALANCED,
        "Nearest Available Robot": AssignmentStrategy.NEAREST_ROBOT,
        "Shortest Total Route": AssignmentStrategy.SHORTEST_TOTAL_ROUTE,
        "Hungarian Batch Optimizer": AssignmentStrategy.BATCH_OPTIMAL,
    }

    current_strat_label = [k for k, v in strategy_options.items() if v == sim.assignment_strategy][0]
    selected_strat_label = st.selectbox(
        "Strategy Policy",
        options=list(strategy_options.keys()),
        index=list(strategy_options.keys()).index(current_strat_label),
        help="Algorithm used by simulator to match orders to robots.",
    )
    if strategy_options[selected_strat_label] != sim.assignment_strategy:
        sim.set_assignment_strategy(strategy_options[selected_strat_label])
        st.session_state.last_message = f"Assignment strategy switched to: {selected_strat_label}."
        st.rerun()

    st.divider()
    st.subheader("⏱ Execution Controls")

    is_paused = st.session_state.get('paused', False)
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("⏸ Pause", use_container_width=True, disabled=is_paused):
            st.session_state.paused = True
            st.rerun()
    with col_p2:
        if st.button("▶ Resume", use_container_width=True, disabled=not is_paused):
            st.session_state.paused = False
            st.rerun()

    batch_size = st.select_slider(
        "Step Batch Size",
        options=[1, 5, 10, 20],
        value=st.session_state.get('batch_size', 5),
    )
    st.session_state.batch_size = batch_size

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶ Step +1", use_container_width=True, disabled=is_paused):
            sim.step()
            st.rerun()
    with col_btn2:
        if st.button(f"⏩ Run ×{batch_size}", use_container_width=True, disabled=is_paused):
            for _ in range(batch_size):
                sim.step()
            st.rerun()

    col_btn3, col_btn4 = st.columns(2)
    with col_btn3:
        if st.button("🔄 Reset", use_container_width=True):
            sim.reset(num_robots=st.session_state.num_robots)
            ai_engine = get_analytics_engine(sim)
            st.session_state.demo_result = None
            st.session_state.paused = False
            st.session_state.last_message = "Simulation reset to initial state."
            st.rerun()
    with col_btn4:
        if st.button("⚡ Run 50", use_container_width=True, disabled=is_paused):
            for _ in range(50):
                sim.step()
            st.rerun()

    st.divider()
    st.subheader("🚨 Dynamic Obstacles")
    col_ox, col_oy = st.columns(2)
    with col_ox:
        obs_x = st.number_input("Obstacle X", min_value=0, max_value=14, value=4)
    with col_oy:
        obs_y = st.number_input("Obstacle Y", min_value=0, max_value=14, value=2)

    if st.button("🚨 Inject Obstacle", use_container_width=True):
        success, msg = sim.inject_obstacle(int(obs_x), int(obs_y))
        st.session_state.last_message = msg
        st.rerun()

    if st.button("🧹 Clear Obstacles", use_container_width=True):
        sim.clear_dynamic_obstacles()
        st.session_state.last_message = "All dynamic obstacles cleared."
        st.rerun()

    st.divider()
    st.subheader("🎬 Viva & Evaluation Demo")
    if st.button("🎬 Run Replanning Demo", use_container_width=True):
        with st.spinner("Executing dynamic replanning demonstration..."):
            demo_res = DemoScenario.run_dynamic_obstacle_demo(sim)
            st.session_state.demo_result = demo_res
            st.session_state.last_message = f"Demo complete: {demo_res.message}"
        st.rerun()


# ===================== MAIN HEADER & KPIS =====================
st.title("SmartWarehouse AI — Autonomous Fleet & Predictive Intelligence")
st.caption("Module 10: AI-Powered Digital Twin, Predictive Analytics, Demand Forecasting, Congestion Prevention & Maintenance")

if st.session_state.get('last_message'):
    st.info(st.session_state.last_message)

# Extended KPI Metrics
metrics = sim.metrics.get_summary()
analytics = sim.metrics.get_replan_analytics()
kpis_ai = ai_engine.get_summary_kpis()

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
with kpi1:
    st.metric("Makespan (Steps)", metrics['makespan'])
with kpi2:
    st.metric("Tasks Completed", metrics['completed_tasks'])
with kpi3:
    st.metric("Fleet Throughput", f"{metrics['throughput_per_100_steps']}/100st")
with kpi4:
    st.metric("Replan Success", f"{analytics['replan_success_rate']}%", f"{analytics['replan_attempts']} attempts")
with kpi5:
    health_delta = "Nominal" if kpis_ai['fleet_avg_health'] >= 80 else "Caution" if kpis_ai['fleet_avg_health'] >= 60 else "Urgent"
    st.metric("Fleet Avg Health", f"{kpis_ai['fleet_avg_health']}%", health_delta)
with kpi6:
    c_status = "Clear" if kpis_ai['congestion_score'] < 30 else "Moderate" if kpis_ai['congestion_score'] < 60 else "Heavy"
    st.metric("Congestion Index", f"{kpis_ai['congestion_score']}/100", c_status)

# Expandable Demo Scenario Results
if st.session_state.get('demo_result'):
    dr = st.session_state.demo_result
    with st.expander("🎬 Dynamic Replanning Demo Results", expanded=True):
        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1:
            st.metric("Obstacle Location", str(dr.obstacle_pos))
        with dc2:
            st.metric("Affected Robots", len(dr.affected_robots), f"IDs: {dr.affected_robots}")
        with dc3:
            st.metric("Replan Latency", f"{dr.replan_latency_ms:.2f} ms")
        with dc4:
            st.metric("Steps After Replan", dr.steps_after_obstacle - dr.steps_before_obstacle)
        st.success(f"Outcome: {dr.message}")

# Collect current deadlock cycles if any
active_states_dl: dict = {}
for r_id, r in sim.robots.items():
    if r.path and r.goal is not None:
        active_states_dl[r_id] = {
            'pos': r.pos,
            'goal': r.goal,
            'path': r.path,
            'path_index': r.path_index,
            'is_waiting': (r.pos == r.path[r.path_index] if r.path_index < len(r.path) else True),
        }
current_cycles = (
    sim.deadlock_handler.detect_deadlocks(active_states_dl, sim.step_count)
    if len(active_states_dl) >= 2
    else []
)

# ===================== MAIN APPLICATION TABS =====================
tab_ai, tab_map, tab_demand, tab_shelf, tab_congestion, tab_maintenance, tab_fleet, tab_ops = st.tabs([
    "🧠 AI Command Centre",
    "🗺 3D Digital Twin",
    "📈 Demand Forecasting",
    "🏭 Shelf Optimization",
    "🌡 Congestion Intelligence",
    "🤖 Predictive Maintenance",
    "🔬 Fleet Optimization",
    "📋 Operations & Logs",
])

# ----------------- TAB 1: AI COMMAND CENTRE -----------------
with tab_ai:
    st.subheader("🧠 Warehouse Intelligence Command Centre")
    st.markdown("Centralized AI coordination across demand forecasting, layout optimization, congestion mitigation, and health telemetry.")

    col_btn_ai1, col_btn_ai2, col_btn_ai3 = st.columns([1, 1, 2])
    with col_btn_ai1:
        if st.button("⚡ Run Full AI Analysis", use_container_width=True):
            with st.spinner("Executing full multi-engine warehouse analysis..."):
                ai_engine.refresh()
                st.session_state.last_message = f"AI Analysis refreshed at simulation step {sim.step_count}."
            st.rerun()
    with col_btn_ai2:
        if st.button("🔄 Reset Telemetry", use_container_width=True):
            ai_engine.refresh()
            st.session_state.last_message = "AI telemetry cache synchronized."
            st.rerun()

    full_analysis = ai_engine.run_full_analysis()

    # Strategic AI Summary Cards
    c_sc1, c_sc2, c_sc3, c_sc4 = st.columns(4)
    with c_sc1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🤖 Fleet Health Status</h4>
            <h2>{kpis_ai['fleet_avg_health']}%</h2>
            <p>Active Robots: {len(sim.robots)} | Monitored: 100%</p>
        </div>
        """, unsafe_allow_html=True)
    with c_sc2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🌡 Congestion Risk</h4>
            <h2>{kpis_ai['congestion_score']}/100</h2>
            <p>Risk Zones: {len(full_analysis['congestion'].get('risk_zones', []))} cells</p>
        </div>
        """, unsafe_allow_html=True)
    with c_sc3:
        st.markdown(f"""
        <div class="metric-card">
            <h4>📈 Predicted Demand (Next 10 St)</h4>
            <h2>{kpis_ai['predicted_next_tasks']:.1f} orders</h2>
            <p>Confidence: {kpis_ai['forecast_confidence'].upper()} {'(Preliminary)' if kpis_ai['preliminary_data'] else ''}</p>
        </div>
        """, unsafe_allow_html=True)
    with c_sc4:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🏭 Layout Efficiency</h4>
            <h2>{full_analysis['shelf_optimization']['savings_estimate'].get('estimated_improvement_pct', 0.0)}%</h2>
            <p>Potential Travel Saving ({kpis_ai['shelf_recommendations_count']} recommendations)</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💡 Prioritized Autonomous Recommendations")
    all_recs = ai_engine.get_all_recommendations()

    if all_recs:
        for rec in all_recs[:8]:
            pri = rec['priority']
            badge_class = "badge-critical" if pri == "CRITICAL" else "badge-high" if pri == "HIGH" else "badge-normal"
            st.markdown(
                f"<span class='{badge_class}'>{pri}</span> **[{rec['source']}]** {rec['message']}",
                unsafe_allow_html=True,
            )
    else:
        st.info("All warehouse parameters operating within optimal tolerances. Advance simulation to generate telemetry.")


# ----------------- TAB 2: INTERACTIVE 3D DIGITAL TWIN -----------------
with tab_map:
    col_map, col_details = st.columns([1.6, 1.0])

    with col_map:
        if "3D" in view_mode:
            st.subheader(f"3D Digital Twin — {camera_preset} View ({theme_choice})")
            st.caption("Rotate (left drag), Pan (right drag), Zoom (scroll). Active mission rays, obstacle alerts, and telemetry.")

            c_heatmap_data = ai_engine.congestion_predictor.get_congestion_heatmap(sim.robots) if show_heatmaps else None
            s_recs_data = ai_engine.shelf_optimizer.recommend_relocations(top_n=3) if show_shelf_recs else None

            fig_3d = renderer_3d.render_3d(
                robots=sim.robots,
                step_count=sim.step_count,
                deadlock_cycles=current_cycles,
                height=650,
                camera_view=selected_cam,
                theme=theme_val,
                congestion_heatmap=c_heatmap_data,
                shelf_optimizations=s_recs_data,
                selected_robot_id=selected_robot_id,
                show_trails=show_trails,
                show_paths=show_paths,
                show_beacons=show_beacons,
                show_heatmaps=show_heatmaps,
                show_labels=show_labels,
            )
            st.plotly_chart(fig_3d, use_container_width=True)
        else:
            st.subheader("2D Warehouse Floorplan (Matplotlib)")
            fig_2d = renderer_2d.render(sim.robots, sim.step_count)
            st.pyplot(fig_2d, use_container_width=True)
            plt.close(fig_2d)

    with col_details:
        st.subheader("Fleet Telemetry & Status")
        robot_records = []
        health_summary = ai_engine.health_monitor.get_fleet_health_summary()

        for r_id, r in sorted(sim.robots.items()):
            t_label = f"#{r.assigned_task.task_id} ({r.assigned_task.priority_label})" if r.assigned_task else "-"
            h_info = health_summary.get(r_id, {})
            robot_records.append({
                "Robot": f"R{r_id}",
                "Pos": str(r.pos),
                "State": r.state,
                "Task": t_label,
                "Battery": f"{r.battery:.1f}%",
                "Health": f"{h_info.get('score', 100):.0f}%",
                "Distance": f"{r.total_distance}m",
            })

        df_robots = pd.DataFrame(robot_records)
        st.dataframe(df_robots, use_container_width=True, hide_index=True)

        st.subheader("Space-Time Verification")
        active_paths = {r_id: r.path[r.path_index:] for r_id, r in sim.robots.items() if r.path}
        live_conflicts = MultiAgentPlanner.detect_conflicts(
            active_paths,
            warehouse=sim.grid,
            park_at_goal=False,
        )
        if not live_conflicts:
            st.success("✅ **Space-Time Verification**: 0 Vertex & 0 Edge Conflicts detected across all active horizons.")
        else:
            st.warning(f"⚠️ {len(live_conflicts)} potential conflict(s) detected in remaining horizons.")

        st.divider()
        st.subheader("🛡️ Wait-For Graph (WFG) Status")
        if current_cycles:
            st.warning(f"⚠️ **Active Circular Wait Detected**: Cycles {current_cycles}. Recovery pipeline active.")
        else:
            st.success("✅ **Wait-For Graph Status**: Acyclic (No circular wait conditions).")

        dl_events = sim.deadlock_handler.event_log
        if dl_events:
            event_data = [e.to_dict() for e in reversed(dl_events[-5:])]
            df_dl = pd.DataFrame(event_data)
            st.dataframe(
                df_dl[["timestamp", "cycle", "strategy_used", "success", "latency_ms"]],
                use_container_width=True,
                hide_index=True,
            )


# ----------------- TAB 3: DEMAND FORECASTING -----------------
with tab_demand:
    st.subheader("📈 AI Warehouse Demand Forecasting")
    st.markdown("Analyses order completion patterns using Exponentially Weighted Moving Averages (EWMA) to forecast future item picking demand.")

    col_df_btn, col_df_info = st.columns([1, 3])
    with col_df_btn:
        if st.button("🔮 Generate Demand Forecast", use_container_width=True):
            completed = sim.task_manager.get_completed_tasks()
            ai_engine.demand_forecaster.update(completed)
            st.session_state.last_message = f"Demand forecast generated from {len(completed)} completed tasks."
            st.rerun()
    with col_df_info:
        fc = ai_engine.demand_forecaster.forecast_next_demand(steps_ahead=10)
        label_note = "(Preliminary — requires ≥ 3 completed tasks)" if fc['preliminary'] else "(High Confidence)"
        st.caption(f"Forecast Horizon: 10 simulation steps. Model: EWMA (α=0.3). {label_note}")

    col_d1, col_d2 = st.columns([1.2, 1.0])
    with col_d1:
        fig_demand = render_demand_forecast_chart(ai_engine.demand_forecaster)
        st.plotly_chart(fig_demand, use_container_width=True)
    with col_d2:
        fig_top_shelves = render_top_shelves_chart(ai_engine.demand_forecaster, n=8)
        st.plotly_chart(fig_top_shelves, use_container_width=True)

    st.divider()
    st.markdown("#### 📦 Historical Completed Order Log")
    completed_tasks = sim.task_manager.get_completed_tasks()
    if completed_tasks:
        c_table = [{
            "Task ID": f"#{t.task_id}",
            "Shelf Location": str(t.shelf_loc),
            "Pick Spot": str(t.pick_spot),
            "Delivery Station": str(t.delivery_station),
            "Priority": t.priority_label,
            "Completed Step": t.completed_at_step,
        } for t in reversed(completed_tasks[-15:])]
        st.dataframe(pd.DataFrame(c_table), use_container_width=True, hide_index=True)
    else:
        st.info("No completed tasks yet. Advance the simulation to collect order data.")


# ----------------- TAB 4: SMART SHELF OPTIMIZATION -----------------
with tab_shelf:
    st.subheader("🏭 Intelligent Warehouse Shelf Optimization")
    st.markdown("Calculates Manhattan distances from shelves to packing stations weighted by historical picking demand, identifying relocation swaps to minimize total fleet travel.")

    col_sh_btn, col_sh_kpi = st.columns([1, 2])
    with col_sh_btn:
        if st.button("⚡ Optimize Shelf Locations", use_container_width=True):
            ai_engine.shelf_optimizer.demand_heatmap = ai_engine.demand_forecaster.get_demand_heatmap_data()
            st.session_state.last_message = "Shelf optimization report regenerated."
            st.rerun()

    opt_report = ai_engine.shelf_optimizer.get_optimization_report()
    layout_data = opt_report['layout_analysis']
    savings_data = opt_report['savings_estimate']

    with col_sh_kpi:
        st.caption(f"Current Avg Distance: {layout_data.get('avg_shelf_to_station_dist', 0)} cells | Estimated Improvement: {savings_data.get('estimated_improvement_pct', 0)}%")

    col_s1, col_s2 = st.columns([1.3, 1.0])
    with col_s1:
        fig_shelf_3d = render_shelf_optimization_3d(ai_engine.shelf_optimizer, sim.grid)
        st.plotly_chart(fig_shelf_3d, use_container_width=True)
    with col_s2:
        st.markdown("#### 🔄 Relocation Recommendations")
        recs = opt_report['recommendations']
        if recs:
            rec_rows = []
            for r in recs:
                rec_rows.append({
                    "Shelf": str(r['shelf']),
                    "Distance": f"{r['dist_to_station']}m",
                    "Score": r['score'],
                    "Target Swap": str(r.get('target_swap', '(2,3)')),
                })
            st.dataframe(pd.DataFrame(rec_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Layout nominal. No relocation required.")

        st.divider()
        st.markdown("#### ✅ Apply Approved Relocation")
        st.caption("Select a proposed swap and apply layout changes to the active simulation.")

        if recs:
            swap_options = {i: f"Swap {r['shelf']} ↔ {r.get('target_swap', '(2,3)')}" for i, r in enumerate(recs)}
            sel_swap_idx = st.selectbox("Choose Proposal", options=list(swap_options.keys()), format_func=lambda i: swap_options[i])
            if st.button("✅ Apply Approved Relocation", use_container_width=True):
                chosen = recs[sel_swap_idx]
                ok, msg = ai_engine.shelf_optimizer.apply_relocation(chosen['shelf'], chosen.get('target_swap', (2, 3)))
                st.session_state.last_message = msg
                st.rerun()


# ----------------- TAB 5: CONGESTION INTELLIGENCE -----------------
with tab_congestion:
    st.subheader("🌡 Warehouse Congestion Intelligence & Heatmap")
    st.markdown("Analyses active robot path projections and reservation-table horizons to detect traffic bottlenecks before deadlocks occur.")

    if st.button("🔍 Scan Warehouse Congestion", use_container_width=True):
        ai_engine.congestion_predictor.compute_cell_traffic(sim.robots)
        st.session_state.last_message = "Warehouse traffic density recalculated."
        st.rerun()

    c_rep = ai_engine.congestion_predictor.get_full_report(sim.robots)

    col_cg1, col_cg2 = st.columns([1.3, 1.0])
    with col_cg1:
        fig_cong_3d = render_congestion_heatmap_3d(ai_engine.congestion_predictor, sim.grid, sim.robots)
        st.plotly_chart(fig_cong_3d, use_container_width=True)
    with col_cg2:
        st.markdown(f"#### 🚨 Congestion Risk Index: **{c_rep['congestion_score']}/100**")
        risk_zones = c_rep.get('risk_zones', [])
        if risk_zones:
            rz_rows = [{
                "Cell": str(z['cell']),
                "Risk Score": f"{z['score']:.2f}",
                "Severity": z['severity_label'],
            } for z in risk_zones[:8]]
            st.dataframe(pd.DataFrame(rz_rows), use_container_width=True, hide_index=True)
        else:
            st.success("✅ No critical traffic bottlenecks detected along active routes.")

        st.markdown("#### 🛣 Dynamic Routing Advisory")
        for rec in c_rep.get('recommendations', []):
            st.markdown(f"- {rec}")


# ----------------- TAB 6: PREDICTIVE MAINTENANCE -----------------
with tab_maintenance:
    st.subheader("🤖 Predictive Robot Maintenance & Telemetry")
    st.markdown("Simulated battery level, mechanical wear (distance travelled), and workload fatigue are monitored to project maintenance urgency.")
    st.caption("ℹ️ *Note: Telemetry metrics are derived from digital-twin simulation state for university demonstration.*")

    if st.button("🔧 Analyze Robot Health", use_container_width=True):
        ai_engine.health_monitor.robots = sim.robots
        st.session_state.last_message = "Robot fleet diagnostics refreshed."
        st.rerun()

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        fig_health = render_fleet_health_dashboard(ai_engine.health_monitor)
        st.plotly_chart(fig_health, use_container_width=True)
    with col_m2:
        fig_maint_pri = render_maintenance_priority(ai_engine.health_monitor)
        st.plotly_chart(fig_maint_pri, use_container_width=True)

    st.divider()
    st.markdown("#### 🩺 Per-Robot Diagnostic Telemetry")
    h_summary = ai_engine.health_monitor.get_fleet_health_summary()
    cols_bots = st.columns(len(h_summary)) if h_summary else [st.container()]

    for idx, (r_id, h_data) in enumerate(sorted(h_summary.items())):
        with cols_bots[idx % len(cols_bots)]:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Robot R{r_id} — {h_data['status']}</h4>
                <h3>Score: {h_data['score']:.0f}/100</h3>
                <p>🔋 Battery: {h_data['battery']}%</p>
                <p>📍 Distance: {h_data['distance']}m</p>
                <p>📦 Completed: {h_data['completed_tasks']} tasks</p>
            </div>
            """, unsafe_allow_html=True)
            for r_item in h_data.get('recommendations', [])[:2]:
                st.caption(f"• {r_item}")


# ----------------- TAB 7: FLEET STRATEGY OPTIMIZATION -----------------
with tab_fleet:
    st.subheader("🔬 AI Fleet Strategy Benchmark & Optimization")
    st.markdown("Empirically evaluates all 6 dispatch algorithms on identical simulation scenarios to determine the optimal strategy for the current workload.")

    if st.button("🚀 Run Multi-Strategy Comparative Benchmark (40 steps)", use_container_width=True):
        with st.spinner("Benchmarking all 6 assignment strategies under identical conditions..."):
            bench_results = ai_engine.fleet_optimizer.benchmark_strategies(steps=40, seed=42)
            st.session_state.bench_data = bench_results
            st.session_state.last_message = "Multi-strategy benchmark completed."
        st.rerun()

    bench_data = st.session_state.get('bench_data')
    if bench_data:
        col_f1, col_f2 = st.columns([1.2, 1.0])
        with col_f1:
            st.markdown("#### 📊 Benchmark Performance Results")
            df_b = pd.DataFrame(bench_data)
            st.dataframe(
                df_b[["strategy_label", "completed_tasks", "total_distance", "utilization_pct", "gini_index", "runtime_ms"]],
                use_container_width=True,
                hide_index=True,
            )
        with col_f2:
            fig_cmp = render_strategy_comparison(bench_data)
            st.plotly_chart(fig_cmp, use_container_width=True)

        st.divider()
        rec_strat = ai_engine.fleet_optimizer.recommend_strategy(bench_data)
        st.success(f"🏆 **AI Recommended Strategy**: **{rec_strat['recommended_label']}** (Score: {rec_strat['combined_score']:.2f})")
        st.markdown(f"**Rationale**: {rec_strat['reason']}")
    else:
        st.info("Click 'Run Multi-Strategy Comparative Benchmark' to execute deterministic benchmarking across all 6 strategies.")


# ----------------- TAB 8: OPERATIONS & LOGS -----------------
with tab_ops:
    st.subheader("📦 Task Operations, Dispatch & Audit Trail")

    col_op1, col_op2 = st.columns(2)
    with col_op1:
        st.markdown("#### ➕ Create New Custom Order")
        accessible_picks = sorted(sim.grid.get_accessible_shelf_locations())
        packing_stations = sorted(sim.grid.packing_stations)

        c1, c2, c3 = st.columns(3)
        with c1:
            pick_choice = st.selectbox(
                "Pickup Location",
                options=accessible_picks,
                format_func=lambda c: f"Shelf ({c[0]}, {c[1]})",
                index=0 if accessible_picks else 0,
            )
        with c2:
            delivery_choice = st.selectbox(
                "Delivery Station",
                options=packing_stations,
                format_func=lambda c: f"Packing ({c[0]}, {c[1]})",
                index=0 if packing_stations else 0,
            )
        with c3:
            priority_choice = st.selectbox(
                "Priority Tier",
                options=[TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.URGENT],
                format_func=lambda p: f"{TaskPriority(p).label} ({p.value})",
                index=1,
            )

        if st.button("🚀 Register & Enqueue Order", use_container_width=True):
            new_task, msg = sim.create_custom_task(
                pick_spot=pick_choice,
                delivery_station=delivery_choice,
                priority=priority_choice.value,
            )
            st.session_state.last_message = msg
            st.rerun()

    with col_op2:
        st.markdown("#### 🎯 Manual Dispatch Controls")
        pending_tasks = sim.task_manager.get_pending_tasks()
        idle_robot_ids = [r_id for r_id, r in sim.robots.items() if r.state == 'IDLE']

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            task_options = {t.task_id: f"#{t.task_id} ({t.priority_label}) -> Pick {t.pick_spot}" for t in pending_tasks}
            selected_task_id = st.selectbox(
                "Pending Order",
                options=list(task_options.keys()) if task_options else [None],
                format_func=lambda tid: task_options.get(tid, "None") if tid else "None",
            )
        with m_col2:
            selected_robot_id_man = st.selectbox(
                "Idle Robot Target",
                options=idle_robot_ids if idle_robot_ids else [None],
                format_func=lambda r: f"Robot R{r}" if r else "None",
            )

        if st.button("👉 Manually Dispatch", use_container_width=True, disabled=not (selected_task_id and selected_robot_id_man)):
            ok, msg = sim.assign_task_manually(selected_task_id, selected_robot_id_man)
            st.session_state.last_message = msg
            st.rerun()

        # Cancellation
        active_or_pending = [t.task_id for t in sim.task_manager.tasks.values() if t.status not in ('COMPLETED', 'CANCELLED', 'FAILED')]
        can_col1, can_col2 = st.columns([2, 1])
        with can_col1:
            cancel_tid = st.selectbox(
                "Cancel Active Order",
                options=active_or_pending if active_or_pending else [None],
                format_func=lambda tid: f"Task #{tid} [{sim.task_manager.tasks[tid].status}]" if tid else "None",
            )
        with can_col2:
            st.write("")
            st.write("")
            if st.button("❌ Cancel", use_container_width=True, disabled=cancel_tid is None):
                ok, msg = sim.cancel_task(cancel_tid)
                st.session_state.last_message = msg
                st.rerun()

    st.divider()
    st.markdown("#### 📋 Warehouse Order Roster")
    all_tasks = list(sim.task_manager.tasks.values())
    if all_tasks:
        task_table = [{
            "Task ID": f"#{t.task_id}",
            "Priority": t.priority_label,
            "Pickup": str(t.pick_spot),
            "Delivery": str(t.delivery_station),
            "Status": t.status,
            "Robot": f"R{t.assigned_robot}" if t.assigned_robot else "Unassigned",
            "Created Step": t.created_at_step,
            "Distance": f"{int(t.estimated_cost)}m",
        } for t in reversed(all_tasks[-25:])]
        st.dataframe(pd.DataFrame(task_table), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 📜 Audit Logs")
    l_tab1, l_tab2, l_tab3 = st.tabs(["AI Assignments", "Replanning Events", "Obstacle Events"])
    with l_tab1:
        decisions = sim.assignment_engine.history
        if decisions:
            st.dataframe(pd.DataFrame([d.to_dict() for d in reversed(decisions[-25:])]), use_container_width=True, hide_index=True)
        else:
            st.info("No dispatch decisions logged yet.")
    with l_tab2:
        replan_history = sim.replanner.replan_history
        if replan_history:
            st.dataframe(pd.DataFrame([e.to_dict() for e in reversed(replan_history[-25:])]), use_container_width=True, hide_index=True)
        else:
            st.caption("No replanning events recorded.")
    with l_tab3:
        obs_history = sim.obstacle_manager.get_history()
        if obs_history:
            st.dataframe(pd.DataFrame([e.to_dict() for e in reversed(obs_history[-20:])]), use_container_width=True, hide_index=True)
        else:
            st.caption("No dynamic obstacles recorded.")
