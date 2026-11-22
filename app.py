"""SmartWarehouse AI — Interactive Streamlit Dashboard.

An autonomous warehouse robot simulator demonstrating:
- Space-Time A* Path Planning
- Vertex & Edge-Swap Collision Avoidance via Reservation Tables
- Deadlock Detection and Dynamic Replanning
- Task Assignment & Fleet Scalability Analysis (1 to 5 robots)
"""

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import time
from simulation.engine import WarehouseSimulator
from visualization.renderer import WarehouseRenderer, ROBOT_COLORS
from core.multi_agent import MultiAgentPlanner

# Streamlit Page Configuration
st.set_page_config(
    page_title="SmartWarehouse AI — Robot Fleet Simulator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #F8F9FA;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #1E88E5;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def get_simulator() -> WarehouseSimulator:
    """Retrieve or initialize simulator in session state."""
    if 'sim' not in st.session_state:
        st.session_state.num_robots = 3
        st.session_state.sim = WarehouseSimulator(num_robots=3, width=15, height=15)
        st.session_state.auto_play = False
        st.session_state.last_message = "Simulator initialized with 3 robots on 15x15 grid."
    return st.session_state.sim


sim = get_simulator()
renderer = WarehouseRenderer(sim.grid)

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.title("🤖 Fleet Control")
    st.markdown("Configure warehouse parameters and simulation controls.")

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
        st.session_state.last_message = f"Fleet reconfigured to {selected_robots} robots."
        st.rerun()

    st.divider()
    st.subheader("Simulation Controls")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("▶ Step +1", use_container_width=True):
            sim.step()
            st.rerun()
    with col_btn2:
        if st.button("⏩ Step +5", use_container_width=True):
            for _ in range(5):
                sim.step()
            st.rerun()

    col_btn3, col_btn4 = st.columns(2)
    with col_btn3:
        if st.button("🔄 Reset", use_container_width=True):
            sim.reset(num_robots=st.session_state.num_robots)
            st.session_state.last_message = "Simulation reset to initial state."
            st.rerun()

    with col_btn4:
        # Run 20 steps benchmark batch
        if st.button("⚡ Run 20", use_container_width=True):
            for _ in range(20):
                sim.step()
            st.rerun()

    st.divider()
    st.subheader("Dynamic Obstacle Injection")
    st.caption("Place unexpected obstacles mid-route to trigger dynamic Space-Time replanning.")

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
        sim.grid.clear_dynamic_obstacles()
        st.session_state.last_message = "All dynamic obstacles cleared."
        st.rerun()


# ----------------- MAIN CONTENT AREA -----------------
st.title("SmartWarehouse AI — Autonomous Robot Fleet Simulator")

if st.session_state.get('last_message'):
    st.info(st.session_state.last_message)

# KPI Metric Row
metrics = sim.metrics.get_summary()

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("Makespan (Steps)", metrics['makespan'])
with kpi2:
    st.metric("Tasks Completed", metrics['completed_tasks'])
with kpi3:
    st.metric("Throughput", f"{metrics['throughput_per_100_steps']} / 100 steps")
with kpi4:
    st.metric("Collision Rate", f"{metrics['collision_rate_percent']}%", delta="0 Conflicts", delta_color="normal")
with kpi5:
    st.metric("Replans Triggered", metrics['replan_events'], f"Avg {metrics['avg_replan_latency_ms']} ms")

# Warehouse Map & Robot Status Columns
col_map, col_details = st.columns([1.5, 1.0])

with col_map:
    st.subheader("Warehouse Floorplan (15x15 Grid)")
    fig = renderer.render(sim.robots, sim.step_count)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with col_details:
    st.subheader("Fleet Telemetry & Status")

    # Robot Table
    robot_records = []
    for r_id, r in sorted(sim.robots.items()):
        robot_records.append({
            "Robot": f"R{r_id}",
            "Position": str(r.pos),
            "State": r.state,
            "Target Goal": str(r.goal) if r.goal else "None",
            "Path Remaining": max(0, len(r.path) - r.path_index - 1) if r.path else 0,
            "Task ID": r.assigned_task.task_id if r.assigned_task else "-",
        })

    df_robots = pd.DataFrame(robot_records)
    st.dataframe(df_robots, use_container_width=True, hide_index=True)

    st.subheader("Mission & Tasks Queue")
    st.markdown(f"- **Queued / Active Tasks**: {sim.task_manager.get_pending_count()}")
    st.markdown(f"- **Completed Tasks**: {sim.task_manager.get_completed_count()}")
    st.markdown(f"- **Fleet Utilization**: {metrics['robot_utilization_percent']}%")

    st.divider()
    st.subheader("Multi-Robot Conflict Check")
    # Verify current live paths across all active robots
    active_paths = {r_id: r.path[r.path_index:] for r_id, r in sim.robots.items() if r.path}
    live_conflicts = MultiAgentPlanner.detect_conflicts(active_paths)
    if not live_conflicts:
        st.success("✅ **Space-Time Verification**: 0 Vertex & 0 Edge Conflicts detected across all planned horizons.")
    else:
        st.error(f"⚠️ {len(live_conflicts)} conflicts detected.")


# ----------------- SCALABILITY & PERFORMANCE ANALYSIS -----------------
st.divider()
st.subheader("📈 Multi-Robot Planning Cost & Scalability Benchmark")
st.caption("Investigate how planning cost and task makespan grow as the number of robots increases from 1 to 5.")

if st.button("📊 Run Scalability Benchmark (1 to 5 Robots)"):
    with st.spinner("Executing benchmark across fleet sizes (1 to 5 robots)..."):
        benchmark_results = []
        for fleet_size in range(1, 6):
            bench_sim = WarehouseSimulator(num_robots=fleet_size, width=15, height=15, seed=42)
            t_start = time.perf_counter()
            for _ in range(30):
                bench_sim.step()
            bench_time_ms = (time.perf_counter() - t_start) * 1000.0
            bench_summary = bench_sim.metrics.get_summary()

            benchmark_results.append({
                "Robots": fleet_size,
                "Tasks Completed": bench_summary['completed_tasks'],
                "Total Steps": bench_summary['total_robot_steps'],
                "Execution Time (ms)": round(bench_time_ms, 2),
                "Collision Count": bench_summary['detected_conflicts'],
            })

        df_bench = pd.DataFrame(benchmark_results)

        b_col1, b_col2 = st.columns([1, 1.2])
        with b_col1:
            st.dataframe(df_bench, use_container_width=True, hide_index=True)

        with b_col2:
            fig_b, ax_b = plt.subplots(figsize=(6, 3.2), dpi=100)
            ax_b.plot(df_bench["Robots"], df_bench["Execution Time (ms)"], marker='o', color='#1E88E5', linewidth=2, label="Planning Runtime (ms)")
            ax_b.set_xlabel("Number of Robots")
            ax_b.set_ylabel("30-Step Runtime (ms)")
            ax_b.set_title("Fleet Scalability: Planning Overhead vs. Fleet Size")
            ax_b.set_xticks(range(1, 6))
            ax_b.grid(True, linestyle='--', alpha=0.5)
            ax_b.legend()
            plt.tight_layout()
            st.pyplot(fig_b, use_container_width=True)
            plt.close(fig_b)
