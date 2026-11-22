"""Sidebar navigation component for SmartWarehouse AI."""

import streamlit as st
from typing import Dict, Any
from .auth_helper import logout_user, login_user


NAV_SECTIONS = [
    ("📊 Executive Command Centre", "command_centre"),
    ("🌐 3D Digital Twin", "digital_twin"),
    ("🤖 Robot Fleet Telemetry", "robot_fleet"),
    ("🏭 Warehouse Operations", "operations"),
    ("🗺️ Path Planning & Space-Time", "path_planning"),
    ("📦 Task Management", "task_management"),
    ("📡 IoT Command Centre", "iot_centre"),
    ("🚨 Emergency Response", "emergency_response"),
    ("💡 AI Recommendations", "recommendations"),
    ("📈 Deep Analytics", "analytics"),
    ("🔬 Algorithm Benchmarking", "benchmarking"),
    ("📑 Reports & Exports", "reports"),
    ("🛡️ System Administration", "admin"),
    ("⚙️ Settings", "settings"),
]


def render_sidebar_navigation() -> str:
    """Renders the comprehensive role-aware sidebar navigation and returns selected view."""
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="font-size: 28px;">🤖</span>
                <div>
                    <h2 style="margin: 0; font-size: 18px; color: #00F0FF; font-weight: 700;">SmartWarehouse AI</h2>
                    <span style="font-size: 10px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em;">Enterprise Autonomous Platform</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Active User & Role Display
        username = st.session_state.get("username", "operator")
        role = st.session_state.get("user_role", "OPERATOR")
        role_color = "#EF4444" if role == "ADMIN" else "#00F0FF" if role == "OPERATOR" else "#94A3B8"

        st.markdown(
            f"""
            <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 8px 12px; margin-bottom: 14px;">
                <div style="font-size: 11px; color: #94A3B8;">AUTHENTICATED SESSION</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2px;">
                    <span style="font-size: 13px; font-weight: 600; color: #F8FAFC;">👤 {username}</span>
                    <span style="background: {role_color}; color: #0F172A; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px;">{role}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quick Role Switcher / Login Form for Viva Evaluation
        with st.expander("🔐 Switch User / Role", expanded=False):
            sel_role = st.selectbox("Switch Role Profile", ["OPERATOR", "ADMIN", "VIEWER"], index=["OPERATOR", "ADMIN", "VIEWER"].index(role))
            if sel_role != role:
                st.session_state.user_role = sel_role
                st.session_state.username = sel_role.lower()
                st.rerun()

            u_in = st.text_input("Username", key="nav_u_in")
            p_in = st.text_input("Password", type="password", key="nav_p_in")
            if st.button("Log In", key="nav_login_btn", use_container_width=True):
                ok, msg = login_user(u_in, p_in)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

            if st.button("Log Out (Guest Viewer)", key="nav_logout_btn", use_container_width=True):
                logout_user()
                st.rerun()

        st.divider()

        # Primary Navigation Radio
        nav_labels = [label for label, _ in NAV_SECTIONS]
        label_to_key = {label: key for label, key in NAV_SECTIONS}

        selected_label = st.radio(
            "Navigation Sections",
            options=nav_labels,
            index=0,
            label_visibility="collapsed",
        )
        selected_key = label_to_key[selected_label]

        st.divider()

        # Persistent Simulation Mode Notice (Rule 4)
        st.markdown(
            """
            <div style="font-size: 10px; color: #64748B; line-height: 1.4;">
                🟢 <strong>Simulation Mode Active</strong><br>
                All IoT telemetry, robot coordinates, and sensor streams are simulated for academic demonstration. No physical actuators connected.
            </div>
            """,
            unsafe_allow_html=True,
        )

        return selected_key
