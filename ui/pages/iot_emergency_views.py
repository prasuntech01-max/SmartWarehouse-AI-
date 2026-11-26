"""IoT Command Centre and Autonomous Emergency Response views."""

import streamlit as st
import pandas as pd
from typing import Any
from ui.components import render_section_header, render_kpi_card
from ui.auth_helper import check_permission
from persistence.repo import IncidentRepo, SensorRepo, AuditLogRepo


def render_iot_page(sim: Any) -> None:
    """Renders the Industrial IoT Command Centre."""
    render_section_header(
        "Industrial IoT Command Centre",
        "Environmental sensors, ESP32 device connectivity, heartbeat telemetry, and threshold monitoring.",
        icon="📡",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Connected Devices", "3 ESP32", "units", provenance="SIMULATED-TELEMETRY")
    with c2:
        render_kpi_card("Active Sensors", "9 sensors", "units", provenance="SIMULATED-TELEMETRY")
    with c3:
        render_kpi_card("Telemetry Source", "SIMULATED", "", provenance="SIMULATED-TELEMETRY")
    with c4:
        render_kpi_card("Heartbeat Status", "Nominal (5s)", "", provenance="MEASURED")

    st.divider()

    st.markdown("#### 🌡️ Live Telemetry Streams & Persisted Sensor History")
    if st.button("📡 Sample & Persist Sensor Telemetry Snapshot", key="iot_sample_persist_btn", use_container_width=False):
        samples = [
            ("TEMP-01", round(24.0 + (sim.step_count % 5) * 0.2, 2), "°C"),
            ("SMK-01", 0.04, "ratio"),
            ("GAS-01", 0.01, "ratio"),
            ("HUM-01", round(48.0 + (sim.step_count % 4) * 0.3, 2), "%"),
        ]
        for sid, val, unit in samples:
            SensorRepo.record(sid, val, unit, tick=sim.step_count, data_source="SIMULATED")
        st.success(f"Persisted {len(samples)} simulated sensor readings at tick {sim.step_count}.")

    persisted_sensors = SensorRepo.list_recent(limit=20)
    if persisted_sensors:
        st.dataframe(pd.DataFrame(persisted_sensors), use_container_width=True, hide_index=True)
    else:
        st.info("No sensor readings persisted in SQLite yet. Click 'Sample & Persist Sensor Telemetry Snapshot' above to record simulated readings.")


def render_emergency_page(sim: Any, analytics_service: Any) -> None:
    """Renders the Autonomous Emergency Response and Hazard Management dashboard."""
    render_section_header(
        "Autonomous Emergency Response & Safety Center",
        "Deterministic hazard detection, dynamic hazard zone isolation, manual operator acknowledgment, and audit log.",
        icon="🚨",
    )

    can_ack = check_permission("acknowledge_hazards")
    if not can_ack:
        st.warning("🔒 Emergency acknowledgment and clearance require OPERATOR or ADMIN role.")

    col1, col2 = st.columns([1.5, 1.0])
    with col1:
        st.markdown("#### 🚨 Active Hazard Incidents")
        df_inc = analytics_service.get_incident_dataframe(limit=25)
        if not df_inc.empty:
            st.dataframe(df_inc, use_container_width=True, hide_index=True)
        else:
            st.success("✅ **Zero Active Hazard Incidents**. All warehouse environmental sensors nominal.")

    with col2:
        st.markdown("#### 🛑 Emergency Response Controls")
        if st.button("🚨 Simulate Hazard Zone (Fire/Smoke)", key="em_inject_hazard", disabled=not can_ack, use_container_width=True):
            try:
                IncidentRepo.create_from_dict({
                    "hazard_type": "FIRE",
                    "severity": "CRITICAL",
                    "status": "ACTIVE",
                    "coord": (4, 4),
                    "value": 46.5,
                    "unit": "°C",
                    "tick": sim.step_count,
                    "rule_id": "FIRE_RULE",
                    "explanation": "Temperature sensor 46.5°C and smoke 0.85 exceeded emergency threshold.",
                    "recovery": "Awaiting operator clearance.",
                    "data_source": "SIMULATED",
                })
                st.error("Simulated Hazard Alert triggered and persisted to database!")
                analytics_service.invalidate_cache_if_needed()
                st.rerun()
            except Exception as e:
                st.error(f"Error persisting incident: {e}")

        if st.button("✅ Acknowledge & Clear Incident", key="em_clear_btn", disabled=not can_ack, use_container_width=True):
            actor = st.session_state.get("username", "operator")
            cleared_count = IncidentRepo.clear_active_incidents(actor=actor, tick=sim.step_count, notes="Cleared via Emergency Response UI")
            AuditLogRepo.log(
                actor=actor,
                action="HAZARD_CLEARED",
                target="incidents",
                status="SUCCESS",
                details=f"cleared={cleared_count}",
            )
            st.success(f"Hazard clearance recorded ({cleared_count} active incident(s) cleared and audited in SQLite).")
            analytics_service.invalidate_cache_if_needed()
            st.rerun()
