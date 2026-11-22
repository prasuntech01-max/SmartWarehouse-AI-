"""SmartWarehouse AI — Interactive Streamlit Dashboard (Module 9).

Autonomous warehouse robot simulator featuring:
- Time-Expanded State Space & Space-Time A* Planning
- Reservation Tables for Vertex & Edge-Swap Collision Avoidance
- Wait-For Graph (WFG) Deadlock Detection & Multi-Tier Recovery
- Dynamic Obstacle Management with Event History
- Intelligent Multi-Strategy Task Assignment (Nearest, Shortest, Priority, Workload, Weighted, Hungarian)
- Real-Time Fleet Workload & Battery Optimization
- Interactive Task Management Operations Center (Create, Cancel, Reassign)
- Professional 3D Digital Twin with Mission Beacons & Rays
- Advanced Strategy Benchmarks & Analytics
"""

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import time

from simulation.engine import WarehouseSimulator
from simulation.demo import DemoScenario
from visualization.renderer import WarehouseRenderer, ROBOT_COLORS
from visualization.renderer_3d import Warehouse3DRenderer
from core.multi_agent import MultiAgentPlanner
from core.task_manager import TaskPriority
from core.task_assignment import AssignmentStrategy

# Streamlit Page Configuration
st.set_page_config(
    page_title="SmartWarehouse AI — Autonomous Fleet & Task Optimization (Module 9)",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Industrial Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #F8F9FA;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #0284C7;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
    }
    .priority-urgent { color: #E74C3C; font-weight: bold; }
    .priority-high { color: #E67E22; font-weight: bold; }
    .priority-normal { color: #3498DB; font-weight: bold; }
    .priority-low { color: #95A5A6; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def get_simulator() -> WarehouseSimulator:
    """Retrieve or initialize simulator in session state."""
    if 'sim' not in st.session_state:
        st.session_state.num_robots = 3
        st.session_state.paused = False
        st.session_state.batch_size = 5
        st.session_state.demo_result = None
        st.session_state.last_message = "Simulator initialized with 3 robots on 15x15 grid — Module 9 ready."
        st.session_state.sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    return st.session_state.sim


sim = get_simulator()
renderer_2d = WarehouseRenderer(sim.grid)
renderer_3d = Warehouse3DRenderer(sim.grid)

# ===================== SIDEBAR CONTROLS =====================
with st.sidebar:
    st.title("🤖 Fleet & Simulation Control")
    st.markdown("Configure warehouse parameters, dispatch policies, and execution.")

    # Visualization Mode Toggle
    view_mode = st.radio(
        "Display Mode",
        ["3D Digital Twin (Plotly)", "2D Floorplan (Matplotlib)"],
        index=0,
        help="Switch between interactive 3D perspective and 2D floorplan view.",
    )

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
        renderer_2d = WarehouseRenderer(sim.grid)
        renderer_3d = Warehouse3DRenderer(sim.grid)
        st.session_state.demo_result = None
        st.session_state.last_message = f"Fleet reconfigured to {selected_robots} robots."
        st.rerun()

    st.divider()
    st.subheader("🎯 AI Task Assignment Strategy")
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
        "Dispatch Strategy",
        options=list(strategy_options.keys()),
        index=list(strategy_options.keys()).index(current_strat_label),
        help="Algorithm used by the simulator to match pending orders to available robots.",
    )
    if strategy_options[selected_strat_label] != sim.assignment_strategy:
        sim.set_assignment_strategy(strategy_options[selected_strat_label])
        st.session_state.last_message = f"Task assignment policy switched to: {selected_strat_label}."
        st.rerun()

    st.divider()
    st.subheader("Execution Controls")

    # Pause / Resume Control
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

    # Batch step speed selector
    batch_size = st.select_slider(
        "Step Batch Size",
        options=[1, 5, 10, 20],
        value=st.session_state.get('batch_size', 5),
        help="Number of discrete timesteps advanced per batch run.",
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
    st.subheader("Dynamic Obstacle Injection")
    st.caption("Place unexpected obstacles mid-route to trigger Space-Time replanning.")

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
    st.caption("Deterministic: resets to 3 robots, injects an obstacle on an active route, and demonstrates dynamic replanning.")
    if st.button("🎬 Run Replanning Demo", use_container_width=True):
        with st.spinner("Executing dynamic replanning demonstration..."):
            demo_res = DemoScenario.run_dynamic_obstacle_demo(sim)
            st.session_state.demo_result = demo_res
            st.session_state.last_message = f"Demo complete: {demo_res.message}"
        st.rerun()


# ===================== MAIN CONTENT =====================
st.title("SmartWarehouse AI — Autonomous Fleet & Task Optimization (Module 9)")

if st.session_state.get('last_message'):
    st.info(st.session_state.last_message)

# Extended KPI Metric Row
metrics = sim.metrics.get_summary()
analytics = sim.metrics.get_replan_analytics()
task_an = sim.metrics.get_task_analytics()

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
with kpi1:
    st.metric("Makespan (Steps)", metrics['makespan'])
with kpi2:
    st.metric("Tasks Completed", metrics['completed_tasks'])
with kpi3:
    st.metric("Throughput", f"{metrics['throughput_per_100_steps']} / 100 steps")
with kpi4:
    st.metric("Replan Success", f"{analytics['replan_success_rate']}%", f"{analytics['replan_attempts']} attempts")
with kpi5:
    st.metric("Pending Orders", sim.task_manager.get_pending_count(), f"Active: {len(sim.task_manager.get_active_tasks())}")
with kpi6:
    st.metric("Dispatch Strategy", sim.assignment_strategy.value[:14] + "..")

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

# Main Tabs (Module 9 Structure)
tab_map, tab_tasks, tab_analytics, tab_logs = st.tabs([
    "🗺 Live Warehouse 3D",
    "📋 Task Operations Center",
    "📊 Performance & Strategy Analytics",
    "📜 System & Audit Logs",
])

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

# ----------------- TAB 1: LIVE 3D WAREHOUSE & FLEET -----------------
with tab_map:
    col_map, col_details = st.columns([1.55, 1.0])

    with col_map:
        if "3D" in view_mode:
            st.subheader("3D Interactive Digital Twin (Plotly)")
            st.caption("Rotate (left drag), Pan (right drag), Zoom (scroll). Shows active task beacons & mission rays.")
            fig_3d = renderer_3d.render_3d(sim.robots, sim.step_count, deadlock_cycles=current_cycles, height=620)
            st.plotly_chart(fig_3d, use_container_width=True)
        else:
            st.subheader("2D Warehouse Floorplan (Matplotlib)")
            fig_2d = renderer_2d.render(sim.robots, sim.step_count)
            st.pyplot(fig_2d, use_container_width=True)
            plt.close(fig_2d)

    with col_details:
        st.subheader("Fleet Telemetry & Status")

        robot_records = []
        for r_id, r in sorted(sim.robots.items()):
            t_label = f"#{r.assigned_task.task_id} ({r.assigned_task.priority_label})" if r.assigned_task else "-"
            robot_records.append({
                "Robot": f"R{r_id}",
                "Position": str(r.pos),
                "State": r.state,
                "Assigned Task": t_label,
                "Battery": f"{r.battery:.1f}%",
                "Tasks Done": r.completed_tasks,
                "Travelled": f"{r.total_distance}m",
            })

        df_robots = pd.DataFrame(robot_records)
        st.dataframe(df_robots, use_container_width=True, hide_index=True)

        st.subheader("Task Queue Summary")
        st.markdown(f"- **Queued Orders**: {len(sim.task_manager.get_pending_tasks())}")
        st.markdown(f"- **Active In-Transit**: {len(sim.task_manager.get_active_tasks())}")
        st.markdown(f"- **Completed Orders**: {sim.task_manager.get_completed_count()}")
        st.markdown(f"- **Fleet Utilization**: {metrics['robot_utilization_percent']}%")

        st.divider()
        st.subheader("Space-Time Conflict Check")
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

        # Deadlock telemetry section
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


# ----------------- TAB 2: TASK OPERATIONS CENTER (MODULE 9) -----------------
with tab_tasks:
    st.subheader("📦 Task Operations & Dispatch Center")
    st.markdown("Create custom warehouse orders, manually assign tasks, or manage order cancellations.")

    col_t_create, col_t_actions = st.columns([1.2, 1.0])

    with col_t_create:
        st.markdown("#### ➕ Create New Custom Order")
        accessible_picks = sorted(sim.grid.get_accessible_shelf_locations())
        packing_stations = sorted(sim.grid.packing_stations)

        c1, c2, c3 = st.columns(3)
        with c1:
            pick_choice = st.selectbox(
                "Pickup Location (X, Y)",
                options=accessible_picks,
                format_func=lambda c: f"Shelf Pick ({c[0]}, {c[1]})",
                index=0 if accessible_picks else 0,
            )
        with c2:
            delivery_choice = st.selectbox(
                "Delivery Station (X, Y)",
                options=packing_stations,
                format_func=lambda c: f"Packing Station ({c[0]}, {c[1]})",
                index=0 if packing_stations else 0,
            )
        with c3:
            priority_choice = st.selectbox(
                "Order Priority",
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

    with col_t_actions:
        st.markdown("#### 🎯 Manual Dispatch & Task Controls")
        pending_tasks = sim.task_manager.get_pending_tasks()
        idle_robot_ids = [r_id for r_id, r in sim.robots.items() if r.state == 'IDLE']

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            task_options = {t.task_id: f"#{t.task_id} ({t.priority_label}) -> Pick {t.pick_spot}" for t in pending_tasks}
            selected_task_id = st.selectbox(
                "Select Pending Task",
                options=list(task_options.keys()) if task_options else [None],
                format_func=lambda tid: task_options.get(tid, "No pending tasks") if tid else "None",
            )
        with m_col2:
            selected_robot_id = st.selectbox(
                "Select Idle Robot",
                options=idle_robot_ids if idle_robot_ids else [None],
                format_func=lambda r: f"Robot R{r}" if r else "No idle robots",
            )

        if st.button("👉 Manually Assign Robot", use_container_width=True, disabled=not (selected_task_id and selected_robot_id)):
            ok, msg = sim.assign_task_manually(selected_task_id, selected_robot_id)
            st.session_state.last_message = msg
            st.rerun()

        # Cancellation section
        active_or_pending = [t.task_id for t in sim.task_manager.tasks.values() if t.status not in ('COMPLETED', 'CANCELLED', 'FAILED')]
        can_col1, can_col2 = st.columns([2, 1])
        with can_col1:
            cancel_tid = st.selectbox(
                "Cancel Active/Pending Task",
                options=active_or_pending if active_or_pending else [None],
                format_func=lambda tid: f"Task #{tid} [{sim.task_manager.tasks[tid].status}]" if tid else "None",
            )
        with can_col2:
            st.write("")
            st.write("")
            if st.button("❌ Cancel Task", use_container_width=True, disabled=cancel_tid is None):
                ok, msg = sim.cancel_task(cancel_tid)
                st.session_state.last_message = msg
                st.rerun()

    st.divider()
    st.markdown("#### 📋 Warehouse Order Roster")
    all_tasks = list(sim.task_manager.tasks.values())
    if all_tasks:
        task_table = []
        for t in reversed(all_tasks[-30:]):
            task_table.append({
                "Task ID": f"#{t.task_id}",
                "Priority": t.priority_label,
                "Pickup Location": str(t.pick_spot),
                "Delivery Station": str(t.delivery_station),
                "Status": t.status,
                "Assigned Robot": f"R{t.assigned_robot}" if t.assigned_robot else "Unassigned",
                "Created Step": t.created_at_step,
                "Est. Distance": f"{int(t.estimated_cost)}m",
            })
        st.dataframe(pd.DataFrame(task_table), use_container_width=True, hide_index=True)
    else:
        st.info("No orders currently registered.")


# ----------------- TAB 3: ADVANCED ANALYTICS & STRATEGY BENCHMARK -----------------
with tab_analytics:
    st.subheader("📊 Performance & Multi-Strategy Optimization Analytics")

    an_row1_c1, an_row1_c2 = st.columns(2)

    with an_row1_c1:
        # 1. Robot Workload & Travelled Distance Balance Chart
        robot_ids_sorted = sorted(sim.robots.keys())
        completed_vals = [sim.robots[r].completed_tasks for r in robot_ids_sorted]
        dist_vals = [sim.robots[r].total_distance for r in robot_ids_sorted]
        robot_labels = [f"Robot R{r}" for r in robot_ids_sorted]

        fig_workload = go.Figure(data=[
            go.Bar(name='Completed Tasks', x=robot_labels, y=completed_vals, marker_color='#0284C7'),
            go.Bar(name='Distance (m)', x=robot_labels, y=dist_vals, marker_color='#93C5FD'),
        ])
        fig_workload.update_layout(
            barmode='group',
            title='<b>Fleet Workload Balance</b> (Completed Tasks & Distance Travelled)',
            xaxis_title='Robot',
            yaxis_title='Count / Distance',
            height=300,
            margin=dict(t=40, b=30, l=40, r=20),
            legend=dict(orientation='h', y=-0.25),
        )
        st.plotly_chart(fig_workload, use_container_width=True)

    with an_row1_c2:
        # 2. Priority Distribution of Completed Tasks Donut Chart
        p_counts = task_an['completed_tasks_by_priority']
        p_labels = ["Low", "Normal", "High", "Urgent"]
        p_vals = [p_counts.get(1, 0), p_counts.get(2, 0), p_counts.get(3, 0), p_counts.get(4, 0)]
        p_colors = ['#95A5A6', '#3498DB', '#E67E22', '#E74C3C']

        if sum(p_vals) > 0:
            fig_pie = go.Figure(data=[go.Pie(
                labels=p_labels,
                values=p_vals,
                hole=0.45,
                marker=dict(colors=p_colors),
            )])
            fig_pie.update_layout(
                title='<b>Completed Orders by Priority Tier</b>',
                height=300,
                margin=dict(t=40, b=20, l=20, r=20),
                legend=dict(orientation='h', y=-0.2),
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            fig_empty = go.Figure()
            fig_empty.add_annotation(text="No tasks completed yet.<br>Advance simulation to view priority distribution.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig_empty.update_layout(title='<b>Completed Orders by Priority Tier</b>', height=300)
            st.plotly_chart(fig_empty, use_container_width=True)

    # 3. Strategy Benchmark Comparison Runner
    st.divider()
    st.subheader("🔬 AI Task Assignment Strategy Benchmark")
    st.caption("Empirically executes all 5 dispatch algorithms on identical 3-robot fleets with identical warehouse orders.")

    if st.button("🚀 Run Multi-Strategy Comparative Benchmark", use_container_width=True):
        with st.spinner("Benchmarking dispatch algorithms under identical conditions..."):
            strategies_to_test = [
                AssignmentStrategy.NEAREST_ROBOT,
                AssignmentStrategy.SHORTEST_TOTAL_ROUTE,
                AssignmentStrategy.PRIORITY_FIRST,
                AssignmentStrategy.WORKLOAD_BALANCED,
                AssignmentStrategy.WEIGHTED_MULTI_CRITERIA,
                AssignmentStrategy.BATCH_OPTIMAL,
            ]
            benchmark_rows = []

            for strat in strategies_to_test:
                b_sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
                b_sim.set_assignment_strategy(strat)
                t_bench0 = time.perf_counter()
                for _ in range(40):
                    b_sim.step()
                elapsed_ms = (time.perf_counter() - t_bench0) * 1000.0
                summary = b_sim.metrics.get_summary()

                robot_counts = {r_id: r.completed_tasks for r_id, r in b_sim.robots.items()}
                balance = MetricsCollector.calculate_workload_balance(robot_counts)

                benchmark_rows.append({
                    "Strategy": strat.label,
                    "Completed Tasks": summary['completed_tasks'],
                    "Total Steps": summary['total_robot_steps'],
                    "Workload StdDev": balance['std_dev'],
                    "Gini Index": balance['gini'],
                    "Runtime (ms)": round(elapsed_ms, 2),
                    "Collisions": summary['detected_conflicts'],
                })

            df_bench_strat = pd.DataFrame(benchmark_rows)

            bc1, bc2 = st.columns([1.2, 1.0])
            with bc1:
                st.dataframe(df_bench_strat, use_container_width=True, hide_index=True)
            with bc2:
                fig_strat_bar = go.Figure(data=[
                    go.Bar(
                        x=df_bench_strat["Strategy"],
                        y=df_bench_strat["Completed Tasks"],
                        marker_color='#0284C7',
                    )
                ])
                fig_strat_bar.update_layout(
                    title='<b>Throughput Comparison Across Strategies</b> (40 Steps)',
                    xaxis_title='Strategy',
                    yaxis_title='Completed Tasks',
                    height=280,
                    margin=dict(t=40, b=60, l=40, r=20),
                )
                st.plotly_chart(fig_strat_bar, use_container_width=True)


# ----------------- TAB 4: SYSTEM & AUDIT LOGS -----------------
with tab_logs:
    st.subheader("📜 System Operations & Assignment Audit Trail")

    st.markdown("#### 🎯 AI Assignment Decisions History")
    decisions = sim.assignment_engine.history
    if decisions:
        dec_records = [d.to_dict() for d in reversed(decisions[-30:])]
        st.dataframe(pd.DataFrame(dec_records), use_container_width=True, hide_index=True)
        st.caption(f"Total AI allocation decisions logged: {len(decisions)}")
    else:
        st.info("No AI assignment decisions logged yet. Advance the simulation to trigger dispatching.")

    st.divider()
    st.markdown("#### 📋 Dynamic Replanning Event Log (Module 8)")
    replan_history = sim.replanner.replan_history
    if replan_history:
        r_records = [e.to_dict() for e in reversed(replan_history[-30:])]
        st.dataframe(pd.DataFrame(r_records), use_container_width=True, hide_index=True)
    else:
        st.caption("No replanning events recorded in this run.")

    st.divider()
    st.markdown("#### 🚧 Dynamic Obstacle Event History (Module 8)")
    obs_history = sim.obstacle_manager.get_history()
    if obs_history:
        o_records = [e.to_dict() for e in reversed(obs_history[-20:])]
        st.dataframe(pd.DataFrame(o_records), use_container_width=True, hide_index=True)
    else:
        st.caption("No obstacle events recorded.")
