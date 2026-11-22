"""Deep Analytics, Demand Forecasting, and Layout Optimization view."""

import streamlit as st
import pandas as pd
from typing import Any
from ui.components import render_section_header, render_kpi_card
from analytics.service import AnalyticsService
from visualization.ai_dashboard import (
    render_demand_forecast_chart,
    render_top_shelves_chart,
    render_congestion_heatmap_3d,
    render_shelf_optimization_3d,
)


def render_analytics_page(sim: Any, ai_engine: Any, analytics_service: AnalyticsService) -> None:
    """Renders demand forecasting, layout optimization, and traffic density analytics."""
    render_section_header(
        "Warehouse Deep Analytics & Predictive Intelligence",
        "Empirical demand prediction using EWMA models, demand-weighted shelf relocation optimization, and traffic heatmaps.",
        icon="📈",
    )

    tab_fc, tab_opt, tab_cong = st.tabs(["📦 Demand Forecasting", "🏭 Shelf Optimization", "🌡 Traffic & Congestion"])

    with tab_fc:
        st.markdown("#### 📈 Exponentially Weighted Moving Average (EWMA) Demand Forecast")
        col_btn, col_cap = st.columns([1, 3])
        with col_btn:
            if st.button("🔮 Refresh Demand Forecast", key="an_refresh_fc", use_container_width=True):
                completed = sim.task_manager.get_completed_tasks()
                ai_engine.demand_forecaster.update(completed)
                st.success(f"Forecast updated from {len(completed)} completed task(s).")
                st.rerun()

        col_d1, col_d2 = st.columns([1.3, 1.0])
        with col_d1:
            fig_fc = render_demand_forecast_chart(ai_engine.demand_forecaster)
            st.plotly_chart(fig_fc, use_container_width=True)
        with col_d2:
            fig_top = render_top_shelves_chart(ai_engine.demand_forecaster, n=8)
            st.plotly_chart(fig_top, use_container_width=True)

    with tab_opt:
        st.markdown("#### 🔄 Demand-Weighted Storage Layout Optimization")
        opt_report = ai_engine.shelf_optimizer.get_optimization_report()
        layout_data = opt_report['layout_analysis']
        savings = opt_report['savings_estimate']

        k1, k2, k3 = st.columns(3)
        with k1:
            render_kpi_card("Current Mean Distance", f"{layout_data.get('avg_shelf_to_station_dist', 0)} cells", "", provenance="ESTIMATED")
        with k2:
            render_kpi_card("Potential Improvement", f"{savings.get('estimated_improvement_pct', 0)}%", "", provenance="ESTIMATED")
        with k3:
            render_kpi_card("Proposals", len(opt_report.get('recommendations', [])), "swaps", provenance="ESTIMATED")

        col_s1, col_s2 = st.columns([1.3, 1.0])
        with col_s1:
            fig_sh = render_shelf_optimization_3d(ai_engine.shelf_optimizer, sim.grid)
            st.plotly_chart(fig_sh, use_container_width=True)
        with col_s2:
            st.markdown("##### Recommended Swaps")
            recs = opt_report.get('recommendations', [])
            if recs:
                st.dataframe(pd.DataFrame(recs), use_container_width=True, hide_index=True)
            else:
                st.info("Current rack layout operates at optimal throughput.")

    with tab_cong:
        st.markdown("#### 🚨 Active Route Congestion & Bottleneck Analysis")
        c_rep = ai_engine.congestion_predictor.get_full_report(sim.robots)
        col_c1, col_c2 = st.columns([1.3, 1.0])
        with col_c1:
            fig_cong = render_congestion_heatmap_3d(ai_engine.congestion_predictor, sim.grid, sim.robots)
            st.plotly_chart(fig_cong, use_container_width=True)
        with col_c2:
            render_kpi_card("Congestion Risk Score", f"{c_rep['congestion_score']}/100", "", provenance="SIMULATED")
            st.markdown("##### High-Density Corridor Cells")
            rz = c_rep.get('risk_zones', [])
            if rz:
                st.dataframe(pd.DataFrame(rz[:8]), use_container_width=True, hide_index=True)
            else:
                st.success("✅ No critical traffic bottlenecks along planned trajectories.")
