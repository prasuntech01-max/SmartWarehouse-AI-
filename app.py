"""SmartWarehouse AI — Enterprise Industrial Command Centre & 3D Digital Twin (Module 13).

Autonomous warehouse robot simulator and intelligence platform featuring:
- Time-Expanded State Space & Space-Time A* Planning
- Reservation Tables for Vertex & Edge-Swap Collision Avoidance
- Wait-For Graph (WFG) Deadlock Detection & Multi-Tier Recovery
- Dynamic Obstacle Management with Instant Replanning
- Intelligent Multi-Strategy Task Assignment (Nearest, Shortest, Priority, Workload, Weighted, Hungarian)
- Real-Time Fleet Telemetry, Battery & Predictive Maintenance
- Industrial IoT Command Centre & Deterministic Hazard Detection
- Explainable AI Advisory Recommendations with Measurable Evidence
- Scientific Empirical Benchmarking Suite (Isolated trials, tracemalloc, time.perf_counter)
- Audit-Grade Executive Reporting & Multi-Format Exports (HTML Print-to-PDF, CSV, ZIP)
- High-Fidelity 3D Sensor Digital Twin with Layer Overlays & Camera Presets
- Role-Based Access Control (ADMIN, OPERATOR, VIEWER) & SQLite Persistence
"""

import time
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go

from simulation.engine import WarehouseSimulator
from simulation.demo import DemoScenario
from simulation.ai_analytics import AIAnalyticsEngine
from visualization.renderer import WarehouseRenderer
from visualization.renderer_3d import Warehouse3DRenderer

# Module 13 Extensions
from analytics.service import AnalyticsService
from recommendations.engine import RecommendationEngine
from ui.theme import inject_custom_theme
from ui.navigation import render_sidebar_navigation
from ui.auth_helper import init_auth_session, check_permission
from ui.branding import render_enterprise_header

from ui.pages.command_centre import render_command_centre_view
from ui.pages.digital_twin_view import render_digital_twin_page
from ui.pages.fleet_view import render_fleet_page
from ui.pages.operations_view import render_operations_page
from ui.pages.path_planning_view import render_path_planning_page
from ui.pages.iot_emergency_views import render_iot_page, render_emergency_page
from ui.pages.recommendations_view import render_recommendations_page
from ui.pages.analytics_view import render_analytics_page
from ui.pages.benchmarking_view import render_benchmarking_page
from ui.pages.reports_view import render_reports_page
from ui.pages.admin_settings_views import render_admin_page, render_settings_page

# Streamlit Page Configuration
st.set_page_config(
    page_title="SmartWarehouse AI — Industrial Command Centre",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Record application start time for process uptime calculation
if "_app_start_time" not in st.session_state:
    st.session_state["_app_start_time"] = time.time()

# Inject Design System & Initialize Auth
inject_custom_theme()
init_auth_session()


def get_simulator() -> WarehouseSimulator:
    """Retrieve or initialize simulator in session state."""
    if 'sim' not in st.session_state:
        st.session_state.num_robots = 5
        st.session_state.paused = False
        st.session_state.batch_size = 5
        st.session_state.demo_result = None
        st.session_state.last_message = "Simulator initialized with 5 autonomous robots on 15x15 grid — TITAN-X, ATLAS, VORTEX, NOVA, SPECTRE active."
        st.session_state.sim = WarehouseSimulator(num_robots=5, width=15, height=15)
    return st.session_state.sim


def get_analytics_engine(sim_instance: WarehouseSimulator) -> AIAnalyticsEngine:
    """Retrieve or create AI analytics engine bound to current simulator."""
    if 'ai_engine' not in st.session_state or st.session_state.get('ai_sim_id') != id(sim_instance):
        st.session_state.ai_engine = AIAnalyticsEngine(sim_instance)
        st.session_state.ai_sim_id = id(sim_instance)
    else:
        st.session_state.ai_engine.sim = sim_instance
    return st.session_state.ai_engine


def get_analytics_service(sim_instance: WarehouseSimulator) -> AnalyticsService:
    """Retrieve or initialize AnalyticsService."""
    if 'analytics_service' not in st.session_state or st.session_state.get('analytics_sim_id') != id(sim_instance):
        start_time = st.session_state.get('_app_start_time', time.time())
        st.session_state.analytics_service = AnalyticsService(sim_instance, process_start_time=start_time)
        st.session_state.analytics_sim_id = id(sim_instance)
    else:
        st.session_state.analytics_service.sim = sim_instance
    return st.session_state.analytics_service


def get_recommendation_engine(analytics_svc: AnalyticsService) -> RecommendationEngine:
    """Retrieve or initialize RecommendationEngine."""
    if 'rec_engine' not in st.session_state:
        st.session_state.rec_engine = RecommendationEngine(analytics_svc)
    else:
        st.session_state.rec_engine.analytics_service = analytics_svc
    return st.session_state.rec_engine


# Instantiate singletons
sim = get_simulator()
ai_engine = get_analytics_engine(sim)
analytics_service = get_analytics_service(sim)
rec_engine = get_recommendation_engine(analytics_service)

# Render Sidebar Navigation
selected_view = render_sidebar_navigation()

# Render Enterprise Top Header (Product Branding, Live Clock, System Status, User Pill)
render_enterprise_header()

# Route to active view
if selected_view == "command_centre":
    render_command_centre_view(sim, ai_engine, analytics_service, rec_engine)
elif selected_view == "digital_twin":
    render_digital_twin_page(sim, ai_engine)
elif selected_view == "robot_fleet":
    render_fleet_page(sim, ai_engine, analytics_service)
elif selected_view == "operations":
    render_operations_page(sim, analytics_service)
elif selected_view == "path_planning":
    render_path_planning_page(sim, analytics_service)
elif selected_view == "task_management":
    render_operations_page(sim, analytics_service)
elif selected_view == "iot_centre":
    render_iot_page(sim)
elif selected_view == "emergency_response":
    render_emergency_page(sim, analytics_service)
elif selected_view == "recommendations":
    render_recommendations_page(rec_engine)
elif selected_view == "analytics":
    render_analytics_page(sim, ai_engine, analytics_service)
elif selected_view == "benchmarking":
    render_benchmarking_page()
elif selected_view == "reports":
    render_reports_page(analytics_service)
elif selected_view == "admin":
    render_admin_page()
elif selected_view == "settings":
    render_settings_page()
else:
    render_command_centre_view(sim, ai_engine, analytics_service, rec_engine)
