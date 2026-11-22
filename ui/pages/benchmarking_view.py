"""Empirical Benchmarking Framework view for algorithm comparisons."""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Any
from ui.components import render_section_header
from ui.auth_helper import check_permission
from benchmarks.runner import BenchmarkRunner
from benchmarks.models import BenchmarkConfig
from persistence.repo import BenchmarkRepo


def render_benchmarking_page() -> None:
    """Renders the empirical benchmarking suite for pathfinding and dispatch algorithms."""
    render_section_header(
        "Scientific Algorithm Benchmarking Suite",
        "Deterministic, isolated performance comparisons across pathfinding planners and multi-robot dispatch strategies.",
        icon="🔬",
    )

    can_benchmark = check_permission("run_benchmarks")
    if not can_benchmark:
        st.warning("🔒 Executing benchmark suites requires OPERATOR or ADMIN role. VIEWERS may review stored historical results.")

    st.markdown("#### ⚙️ Configure Benchmark Parameters")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        bench_type = st.selectbox(
            "Benchmark Scenario",
            ["PLANNER_COMPARISON", "DISPATCH_STRATEGIES", "FLEET_SCALING"],
            format_func=lambda s: s.replace("_", " ").title(),
            index=0,
        )
    with col2:
        num_trials = st.slider("Number of Trials", min_value=1, max_value=10, value=3, help="Default is 3 trials for fast statistical significance.")
    with col3:
        num_bots = st.slider("Fleet Size", min_value=1, max_value=5, value=3)
    with col4:
        seed_val = st.number_input("Scenario Seed", min_value=1, max_value=9999, value=42)

    if st.button("🚀 Run Empirical Benchmark Suite", key="btn_run_bench", disabled=not can_benchmark, use_container_width=True):
        with st.spinner("Executing isolated benchmark trials (warm-up discarded, tracemalloc active)..."):
            runner = BenchmarkRunner()
            cfg = BenchmarkConfig(
                benchmark_type=bench_type,
                num_trials=num_trials,
                num_robots=num_bots,
                seed=int(seed_val),
            )
            run_result = runner.run_benchmark(cfg, persist=True)
            st.session_state["latest_bench_run"] = run_result
            st.success(f"Benchmark run `{run_result.run_id}` completed successfully!")

    # Display Latest Results if available
    latest_run = st.session_state.get("latest_bench_run")
    if latest_run:
        st.divider()
        st.markdown(f"### 📊 Benchmark Results — Run `{latest_run.run_id}`")
        st.success(f"🏆 **Winning Algorithm:** **{latest_run.winning_algorithm}** (Evaluated on {len(latest_run.trials)} total trials)")

        summary_rows = []
        for name, s in latest_run.summaries.items():
            summary_rows.append({
                "Algorithm": name,
                "Trials": s.total_trials,
                "Success (%)": f"{s.success_rate}%",
                "Mean Time (ms)": s.mean_time_ms,
                "Median (ms)": s.median_time_ms,
                "Std Dev (ms)": s.std_dev_time_ms,
                "Peak Heap (KB)": s.mean_memory_kb,
                "Mean Path (m)": s.mean_path_length,
                "Optimality Ratio": s.mean_optimality_ratio,
            })

        df_sum = pd.DataFrame(summary_rows)
        st.dataframe(df_sum, use_container_width=True, hide_index=True)

        # Plotly Comparison Chart
        fig_bar = px.bar(
            df_sum,
            x="Algorithm",
            y="Mean Time (ms)",
            error_y="Std Dev (ms)",
            color="Algorithm",
            title="Algorithm Execution Time Comparison (Lower is Faster)",
            template="plotly_dark",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.caption(f"ℹ️ *Scientific Rigor Note: {latest_run.limitations}*")

    # Stored Historical Runs
    st.divider()
    st.markdown("#### 📜 Persisted Benchmark Runs (SQLite)")
    try:
        past_runs = BenchmarkRepo.list_runs(limit=10)
        if past_runs:
            history_rows = [{
                "Run ID": r["run_id"],
                "Benchmark": r["benchmark_name"],
                "Trials": r["total_trials"],
                "Executed By": r["executed_by"],
                "Timestamp": str(r["created_at"]),
            } for r in past_runs]
            st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No prior benchmark runs stored in database.")
    except Exception:
        st.info("No historical benchmark database records found.")
