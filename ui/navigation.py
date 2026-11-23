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
        # 3D Metallic Brand Logo for Sidebar
        st.markdown(
            """
            <div style="background: linear-gradient(180deg, #090e1a 0%, #0d1527 100%);
                        border: 1px solid rgba(0, 240, 255, 0.25);
                        border-radius: 10px;
                        padding: 12px;
                        margin-bottom: 12px;
                        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 32px; height: 32px; border-radius: 6px; background: #0f172a; border: 1.5px solid #00f0ff; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 10px rgba(0, 240, 255, 0.4);">
                        <span style="font-family: 'Orbitron', monospace; font-size: 13px; font-weight: 900; color: #00f0ff;">AI</span>
                    </div>
                    <div>
                        <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;">
                            SmartWarehouse <span style="color: #d946ef; font-style: italic;">AI</span>
                        </div>
                        <div style="font-family: 'Rajdhani', sans-serif; font-size: 9px; color: #38bdf8; letter-spacing: 1.2px; text-transform: uppercase; font-weight: 700;">
                            Operations &amp; Robotics Platform
                        </div>
                    </div>
                </div>
                <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(0, 240, 255, 0.15); font-family: 'Rajdhani', sans-serif; font-size: 9px; color: #94a3b8; letter-spacing: 1.5px; text-transform: uppercase; text-align: center; font-weight: 600;">
                    AUTONOMOUS &bull; INTELLIGENT &bull; OPTIMIZED
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Active User & Role Display
        username = st.session_state.get("username", "admin")
        role = st.session_state.get("user_role", "ADMIN")
        role_color = "#EF4444" if role == "ADMIN" else "#00F0FF" if role == "OPERATOR" else "#94A3B8"

        st.markdown(
            f"""
            <div style="background: #090e1a; border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px;">
                <div style="font-size: 10px; color: #64748B; font-family: 'Rajdhani', sans-serif; font-weight: 700; letter-spacing: 0.8px;">CLEARANCE IDENTITY</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <span style="font-size: 13px; font-weight: 700; color: #F8FAFC;">👤 {username}</span>
                    <span style="background: {role_color}; color: #090e1a; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;">{role}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quick Role Switcher / Login Form
        with st.expander("🔐 Security Role Switcher", expanded=False):
            sel_role = st.selectbox("Switch Active Role", ["ADMIN", "OPERATOR", "VIEWER"], index=["ADMIN", "OPERATOR", "VIEWER"].index(role) if role in ["ADMIN", "OPERATOR", "VIEWER"] else 0)
            if sel_role != role:
                st.session_state.user_role = sel_role
                st.session_state.username = sel_role.lower()
                st.rerun()
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
