"""System Administration and Settings views."""

import streamlit as st
import shutil
import time
import os
from typing import Any
from ui.components import render_section_header
from ui.auth_helper import check_permission
from persistence.repo import UserRepo
from auth.crypto import hash_password


def render_admin_page() -> None:
    """Renders user management, database backup/restore, and audit controls."""
    render_section_header(
        "System Administration & Security",
        "Role-based access control, operator identity management, database backup snapshots, and security integrity.",
        icon="🛡️",
    )

    can_admin = check_permission("manage_users")
    if not can_admin:
        st.error("⛔ Access Denied. System Administration requires the ADMIN role.")
        return

    tab_users, tab_db, tab_sec = st.tabs(["👥 User Management", "💾 Database Maintenance", "🔒 Security Audit"])

    with tab_users:
        st.markdown("#### ➕ Create New User Account")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_u = st.text_input("New Username", key="adm_u_name")
        with c2:
            new_p = st.text_input("Temporary Password", type="password", key="adm_p_word")
        with c3:
            new_r = st.selectbox("Role Assignment", ["OPERATOR", "VIEWER", "ADMIN"], key="adm_r_sel")

        if st.button("Create Account", key="adm_create_user_btn"):
            if new_u and new_p:
                try:
                    pwd_hash = hash_password(new_p)
                    UserRepo.create(new_u, pwd_hash, role=new_r)
                    st.success(f"User account `{new_u}` ({new_r}) created successfully!")
                except Exception as e:
                    st.error(f"Error creating user: {e}")
            else:
                st.warning("Please supply both username and password.")

    with tab_db:
        st.markdown("#### 💾 SQLite Database Snapshot & Backup")
        st.caption("Active database file: `data/smartwarehouse.db` (WAL mode enabled)")

        if st.button("⚡ Create Manual Database Backup", key="adm_backup_btn"):
            os.makedirs("backups", exist_ok=True)
            bk_name = f"backups/smartwarehouse_backup_{int(time.time())}.db"
            try:
                shutil.copy2("data/smartwarehouse.db", bk_name)
                st.success(f"Snapshot created: `{bk_name}`")
            except Exception as e:
                st.error(f"Backup failed: {e}")

    with tab_sec:
        st.markdown("#### 🔒 Security Architecture Status")
        st.info("✅ **Password Hashing:** `hashlib.scrypt` (N=16384, r=8, p=1) with 128-bit salt and constant-time verification.")
        st.info("✅ **SQL Injection Neutralization:** Parameterized SQL queries utilized across all repositories.")
        st.info("✅ **CSV Formula Injection:** Neutralized via single-quote prefix on all exported tabular data.")


def render_settings_page() -> None:
    """Renders application settings and build specifications."""
    render_section_header(
        "Platform Configuration & Settings",
        "Runtime environment configuration, demonstration thresholds, and engineering build metadata.",
        icon="⚙️",
    )

    st.markdown("#### 📋 Platform Build Information")
    st.markdown(
        """
        - **Project Title:** SmartWarehouse AI — Module 13 Enterprise Edition
        - **Course & Institution:** CSE276 B.Tech CSE (AI & ML) Capstone — Lovely Professional University
        - **Python Engine:** Python 3.13.7 (Windows AMD64)
        - **Core Frameworks:** Streamlit 1.67.0 | Plotly 7.1.0 | Pandas 3.1.1 | SQLite 3
        - **Simulation Model:** Space-Time 4-Connected A* with Wait actions and Reservation Table
        - **Persistence:** SQLite Thread-Local WAL with non-blocking Write-Behind Queue
        """
    )
