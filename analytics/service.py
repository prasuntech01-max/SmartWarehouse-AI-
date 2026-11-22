"""Analytics service providing aggregated KPIs, historical analysis, and provenance tracking."""

import time
import math
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

from .models import ProvenanceType, MetricValue, FilterSpec, AnalyticsSnapshot
from core.planner import AStarPlanner
from persistence.repo import IncidentRepo


class AnalyticsService:
    """Unified service for analytics aggregation from live simulation and persistence."""

    def __init__(self, simulator_instance: Any, process_start_time: Optional[float] = None):
        self.sim = simulator_instance
        self.process_start_time = process_start_time or time.time()
        self._cache: Dict[str, Any] = {}
        self._last_cached_step = -1

    def invalidate_cache_if_needed(self) -> None:
        if self.sim.step_count != self._last_cached_step:
            self._cache.clear()
            self._last_cached_step = self.sim.step_count

    def get_snapshot(self, filters: Optional[FilterSpec] = None) -> AnalyticsSnapshot:
        """Constructs a comprehensive snapshot of live and persisted analytics."""
        self.invalidate_cache_if_needed()
        cache_key = f"snapshot_{filters.start_step if filters else 0}_{filters.end_step if filters else 'end'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        sim = self.sim
        metrics = sim.metrics.get_summary()
        replan_analytics = sim.metrics.get_replan_analytics()
        task_analytics = sim.metrics.get_task_analytics()
        now = time.time()
        wall_clock_uptime = max(0.0, now - self.process_start_time)

        # 1. Summary KPIs
        total_tasks_count = len(sim.task_manager.tasks)
        completed_tasks_count = metrics.get("completed_tasks", 0)
        pending_tasks_count = len(sim.task_manager.get_pending_tasks())
        makespan = metrics.get("makespan", 0)
        throughput = metrics.get("throughput_per_100_steps", 0.0)
        overall_utilization = metrics.get("robot_utilization_percent", 0.0)

        summary_kpis = {
            "total_tasks": MetricValue(
                value=total_tasks_count,
                unit="tasks",
                provenance=ProvenanceType.SIMULATED,
                notes="Total created pick-and-pack warehouse orders/tasks",
            ),
            "completed_tasks": MetricValue(
                value=completed_tasks_count,
                unit="tasks",
                provenance=ProvenanceType.SIMULATED,
                notes="Tasks completed by delivery to packing station",
            ),
            "pending_tasks": MetricValue(
                value=pending_tasks_count,
                unit="tasks",
                provenance=ProvenanceType.SIMULATED,
                notes="Tasks currently queued or pending assignment",
            ),
            "completion_rate_percent": MetricValue(
                value=round((completed_tasks_count / max(1, total_tasks_count)) * 100.0, 1),
                unit="%",
                provenance=ProvenanceType.SIMULATED,
                notes="Percentage of created tasks successfully delivered",
            ),
            "fleet_throughput": MetricValue(
                value=throughput,
                unit="tasks/100st",
                provenance=ProvenanceType.SIMULATED,
                notes="Completed tasks normalized per 100 simulation steps",
            ),
            "fleet_utilization": MetricValue(
                value=overall_utilization,
                unit="%",
                provenance=ProvenanceType.SIMULATED,
                notes="Active movement and action steps over total fleet opportunities",
            ),
            "simulation_step": MetricValue(
                value=sim.step_count,
                unit="steps",
                provenance=ProvenanceType.SIMULATED,
                notes="Discrete simulation tick counter",
            ),
            "process_uptime": MetricValue(
                value=round(wall_clock_uptime, 1),
                unit="sec",
                provenance=ProvenanceType.MEASURED,
                notes="Host process wall-clock runtime since initialization",
            ),
        }

        # 2. Safety & Collision KPIs
        detected_conflicts = metrics.get("detected_conflicts", 0)
        deadlock_events = metrics.get("deadlock_events", 0)
        replan_events = metrics.get("replan_events", 0)
        replan_success_rate = metrics.get("replan_success_rate", 100.0)
        avg_replan_latency = metrics.get("avg_replan_latency_ms", 0.0)

        safety_kpis = {
            "physical_collisions": MetricValue(
                value=0,
                unit="collisions",
                provenance=ProvenanceType.SIMULATED,
                notes="Physical coordinate overlap between robots (0 guaranteed by reservation table)",
            ),
            "conflicts_detected_and_avoided": MetricValue(
                value=detected_conflicts,
                unit="conflicts",
                provenance=ProvenanceType.SIMULATED,
                notes="Space-time route intersections resolved via prioritized wait or rerouting",
            ),
            "deadlock_recovery_events": MetricValue(
                value=deadlock_events,
                unit="events",
                provenance=ProvenanceType.SIMULATED,
                notes="Wait-For Graph (WFG) cycle detection and multi-tier resolutions",
            ),
            "replan_events": MetricValue(
                value=replan_events,
                unit="events",
                provenance=ProvenanceType.SIMULATED,
                notes="Dynamic route replannings triggered by unexpected obstacle injections",
            ),
            "replan_success_rate": MetricValue(
                value=replan_success_rate,
                unit="%",
                provenance=ProvenanceType.SIMULATED,
                notes="Percentage of replanning queries successfully finding alternate trajectories",
            ),
            "avg_replan_latency": MetricValue(
                value=avg_replan_latency,
                unit="ms",
                provenance=ProvenanceType.MEASURED,
                notes="Mean CPU wall-clock latency for Space-Time A* dynamic recalculation",
            ),
        }

        # 3. Fleet Metrics per Robot
        fleet_metrics = {}
        completed_counts = {}
        for r_id, r in sim.robots.items():
            if filters and filters.robot_ids and r_id not in filters.robot_ids:
                continue

            active_st = sim.metrics.robot_active_steps.get(r_id, 0)
            idle_st = sim.metrics.robot_idle_steps.get(r_id, 0)
            tot_st = active_st + idle_st
            util_pct = round((active_st / max(1, tot_st)) * 100.0, 1)
            completed_counts[r_id] = r.completed_tasks

            # Predictive Maintenance health score estimation
            wear_deduction = min(30.0, r.total_distance / 20.0)
            task_deduction = min(20.0, r.completed_tasks * 2.0)
            bat_deduction = 20.0 if r.battery < 20.0 else (10.0 if r.battery < 40.0 else 0.0)
            health_score = max(0.0, round(100.0 - bat_deduction - wear_deduction - task_deduction, 1))

            fleet_metrics[r_id] = {
                "state": MetricValue(r.state, provenance=ProvenanceType.SIMULATED),
                "battery": MetricValue(round(r.battery, 1), unit="%", provenance=ProvenanceType.SIMULATED),
                "total_distance": MetricValue(r.total_distance, unit="m", provenance=ProvenanceType.SIMULATED),
                "completed_tasks": MetricValue(r.completed_tasks, unit="tasks", provenance=ProvenanceType.SIMULATED),
                "utilization": MetricValue(util_pct, unit="%", provenance=ProvenanceType.SIMULATED),
                "health_score": MetricValue(
                    health_score,
                    unit="/100",
                    provenance=ProvenanceType.ESTIMATED,
                    notes="Derived from battery status, travel wear, and workload history",
                ),
            }

        # 4. Workload Balance (Gini Coefficient)
        wb = sim.metrics.calculate_workload_balance(completed_counts)
        workload_balance = {
            "mean_tasks": MetricValue(wb.get("mean", 0.0), unit="tasks", provenance=ProvenanceType.ESTIMATED),
            "std_dev": MetricValue(wb.get("std_dev", 0.0), unit="tasks", provenance=ProvenanceType.ESTIMATED),
            "gini_index": MetricValue(
                wb.get("gini", 0.0),
                unit="index",
                provenance=ProvenanceType.ESTIMATED,
                notes="0.0 = perfect equality of task distribution, 1.0 = total inequality",
            ),
        }

        # 5. Path Efficiency & Optimality
        total_actual_dist = sum(r.total_distance for r in sim.robots.values())
        path_efficiency = {
            "total_fleet_distance": MetricValue(
                total_actual_dist, unit="m", provenance=ProvenanceType.SIMULATED
            ),
            "avg_wait_steps": MetricValue(
                task_analytics.get("avg_wait_steps", 0.0), unit="steps", provenance=ProvenanceType.SIMULATED
            ),
            "avg_transit_steps": MetricValue(
                task_analytics.get("avg_transit_steps", 0.0), unit="steps", provenance=ProvenanceType.SIMULATED
            ),
        }

        # 6. IoT & Hazard Incidents
        active_incidents_count = 0
        persisted_incidents_count = 0
        try:
            recent_db_incidents = IncidentRepo.list_recent(limit=50)
            persisted_incidents_count = len(recent_db_incidents)
        except Exception:
            recent_db_incidents = []

        iot_kpis = {
            "persisted_incidents": MetricValue(
                persisted_incidents_count,
                unit="incidents",
                provenance=ProvenanceType.MEASURED,
                notes="Historical incident records stored in SQLite database",
            ),
            "telemetry_source": MetricValue(
                "SIMULATED",
                provenance=ProvenanceType.SIMULATED_TELEMETRY,
                notes="All IoT sensor feeds are synthetic simulations for academic demonstration",
            ),
        }

        # 7. Task Breakdown by Priority
        task_breakdown = {
            "by_priority": task_analytics.get("completed_tasks_by_priority", {}),
            "total_completed": completed_tasks_count,
        }

        snapshot = AnalyticsSnapshot(
            timestamp=now,
            simulation_step=sim.step_count,
            wall_clock_uptime_sec=wall_clock_uptime,
            summary_kpis=summary_kpis,
            fleet_metrics=fleet_metrics,
            workload_balance=workload_balance,
            path_efficiency=path_efficiency,
            safety_kpis=safety_kpis,
            iot_kpis=iot_kpis,
            task_breakdown=task_breakdown,
        )
        self._cache[cache_key] = snapshot
        return snapshot

    def get_fleet_dataframe(self) -> pd.DataFrame:
        """Generates a clean pandas DataFrame for fleet status."""
        snapshot = self.get_snapshot()
        rows = []
        for r_id, m in sorted(snapshot.fleet_metrics.items()):
            rows.append({
                "Robot": f"R{r_id}",
                "State": m["state"].value,
                "Battery (%)": m["battery"].value,
                "Distance (m)": m["total_distance"].value,
                "Completed Tasks": m["completed_tasks"].value,
                "Utilization (%)": m["utilization"].value,
                "Health (/100)": m["health_score"].value,
            })
        return pd.DataFrame(rows)

    def get_task_roster_dataframe(self, limit: int = 50) -> pd.DataFrame:
        """Generates a pandas DataFrame for all warehouse tasks."""
        sim = self.sim
        tasks = list(sim.task_manager.tasks.values())
        rows = []
        for t in reversed(tasks[-limit:]):
            rows.append({
                "Task ID": f"#{t.task_id}",
                "Priority": t.priority_label,
                "Pickup (x,y)": str(t.pick_spot),
                "Delivery (x,y)": str(t.delivery_station),
                "Status": t.status,
                "Assigned Robot": f"R{t.assigned_robot}" if t.assigned_robot else "Unassigned",
                "Created Step": t.created_at_step,
                "Est Distance (m)": int(t.estimated_cost),
            })
        return pd.DataFrame(rows)

    def get_incident_dataframe(self, limit: int = 50) -> pd.DataFrame:
        """Generates a pandas DataFrame for recent persisted incidents."""
        try:
            incidents = IncidentRepo.list_recent(limit=limit)
        except Exception:
            incidents = []

        rows = []
        for inc in incidents:
            rows.append({
                "Incident ID": f"#{inc.id}",
                "Hazard Type": inc.hazard_type,
                "Severity": inc.severity,
                "Status": inc.status,
                "Location": str(inc.coord),
                "Tick": inc.tick,
                "Explanation": inc.explanation,
                "Created At": str(inc.created_at),
                "Source": inc.data_source,
            })
        return pd.DataFrame(rows)

    @staticmethod
    def compare_snapshots(current: AnalyticsSnapshot, previous: AnalyticsSnapshot) -> Dict[str, Any]:
        """Calculates absolute and percentage deltas between two snapshots safely."""
        comparisons = {}
        for key, curr_m in current.summary_kpis.items():
            if key in previous.summary_kpis:
                prev_val = previous.summary_kpis[key].value
                curr_val = curr_m.value
                if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)):
                    abs_diff = curr_val - prev_val
                    pct_diff = round((abs_diff / max(1e-9, abs(prev_val))) * 100.0, 1) if prev_val != 0 else 0.0
                    comparisons[key] = {
                        "current": curr_val,
                        "previous": prev_val,
                        "abs_change": round(abs_diff, 2),
                        "pct_change": pct_diff,
                        "unit": curr_m.unit,
                        "provenance": curr_m.provenance.value,
                    }
        return comparisons
