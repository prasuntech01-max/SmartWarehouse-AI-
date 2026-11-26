"""Warehouse Task Operations and Manual Dispatching view."""

import streamlit as st
from typing import Any
from ui.components import render_section_header
from ui.auth_helper import check_permission
from core.task_manager import TaskPriority
from persistence.repo import WarehouseOpsRepo, AuditLogRepo


def render_operations_page(sim: Any, analytics_service: Any) -> None:
    """Renders task creation, manual dispatch, order cancellation, and roster inspection."""
    render_section_header(
        "Warehouse Operations & Dispatching",
        "Interactive order creation, autonomous strategy configuration, manual dispatch overrides, and active order roster.",
        icon="🏭",
    )

    can_operate = check_permission("manage_tasks")
    if not can_operate:
        st.warning("🔒 Order creation and dispatch overrides require OPERATOR or ADMIN role.")

    col_op1, col_op2 = st.columns(2)
    with col_op1:
        st.markdown("#### ➕ Create New Custom Pick & Pack Order")
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

        if st.button("🚀 Register & Enqueue Order", key="op_create_task", disabled=not can_operate, use_container_width=True):
            new_task, msg = sim.create_custom_task(
                pick_spot=pick_choice,
                delivery_station=delivery_choice,
                priority=priority_choice.value,
            )
            if new_task is not None:
                WarehouseOpsRepo.upsert_task(new_task)
                AuditLogRepo.log(
                    actor=st.session_state.get("username", "system"),
                    action="TASK_CREATED",
                    target=f"task:{new_task.task_id}",
                    status="SUCCESS",
                    details=f"pick={pick_choice}, drop={delivery_choice}, priority={priority_choice.value}",
                )
            st.success(msg)
            analytics_service.invalidate_cache_if_needed()
            st.rerun()

    with col_op2:
        st.markdown("#### 🎯 Manual Dispatch & Cancellation")
        pending_tasks = sim.task_manager.get_pending_tasks()
        idle_robot_ids = [r_id for r_id, r in sim.robots.items() if r.state == 'IDLE']

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            task_options = {t.task_id: f"#{t.task_id} ({t.priority_label}) -> Pick {t.pick_spot}" for t in pending_tasks}
            selected_task_id = st.selectbox(
                "Pending Order",
                options=list(task_options.keys()) if task_options else [None],
                format_func=lambda tid: task_options.get(tid, "No pending tasks") if tid else "No pending tasks",
            )
        with m_col2:
            selected_robot_id_man = st.selectbox(
                "Target Robot",
                options=idle_robot_ids if idle_robot_ids else [None],
                format_func=lambda r: f"Robot R{r}" if r else "No idle robots",
            )

        if st.button("👉 Manually Dispatch", key="op_man_dispatch", disabled=not (can_operate and selected_task_id and selected_robot_id_man), use_container_width=True):
            ok, msg = sim.assign_task_manually(selected_task_id, selected_robot_id_man)
            if ok:
                task_obj = sim.task_manager.tasks.get(selected_task_id)
                if task_obj is not None:
                    WarehouseOpsRepo.upsert_task(task_obj)
                AuditLogRepo.log(
                    actor=st.session_state.get("username", "system"),
                    action="TASK_DISPATCHED",
                    target=f"task:{selected_task_id}",
                    status="SUCCESS",
                    details=f"robot=R{selected_robot_id_man}",
                )
                st.success(msg)
            else:
                st.error(msg)
            analytics_service.invalidate_cache_if_needed()
            st.rerun()

        # Cancellation
        active_or_pending = [t.task_id for t in sim.task_manager.tasks.values() if t.status not in ('COMPLETED', 'CANCELLED', 'FAILED')]
        can_col1, can_col2 = st.columns([2, 1])
        with can_col1:
            cancel_tid = st.selectbox(
                "Cancel Active Order",
                options=active_or_pending if active_or_pending else [None],
                format_func=lambda tid: f"Task #{tid} [{sim.task_manager.tasks[tid].status}]" if tid else "None active",
            )
        with can_col2:
            st.write("")
            st.write("")
            if st.button("❌ Cancel", key="op_cancel_btn", disabled=not (can_operate and cancel_tid is not None), use_container_width=True):
                ok, msg = sim.cancel_task(cancel_tid)
                if ok:
                    task_obj = sim.task_manager.tasks.get(cancel_tid)
                    if task_obj is not None:
                        WarehouseOpsRepo.upsert_task(task_obj)
                    AuditLogRepo.log(
                        actor=st.session_state.get("username", "system"),
                        action="TASK_CANCELLED",
                        target=f"task:{cancel_tid}",
                        status="SUCCESS",
                        details="Cancelled via Operations UI",
                    )
                st.warning(msg)
                analytics_service.invalidate_cache_if_needed()
                st.rerun()

    st.divider()
    st.markdown("#### 📋 Warehouse Order Lifecycle Roster")
    df_tasks = analytics_service.get_task_roster_dataframe(limit=50)
    st.dataframe(df_tasks, use_container_width=True, hide_index=True)
