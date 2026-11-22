"""Performance metrics collector and analytics for the warehouse simulator."""

from typing import Dict, List, Optional
import time


class MetricsCollector:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.simulation_step = 0
        self.total_robot_steps = 0
        self.completed_tasks_count = 0
        self.detected_conflicts_count = 0
        self.replan_events_count = 0
        self.replan_latencies_ms: List[float] = []
        self.robot_active_steps: Dict[int, int] = {}
        self.robot_idle_steps: Dict[int, int] = {}
        self.scaling_data: Dict[int, float] = {}  # robot_count -> avg planning cost

    def record_step(
        self,
        step: int,
        robot_statuses: Dict[int, str],
        conflicts_count: int,
    ) -> None:
        """Update step-level statistics."""
        self.simulation_step = step
        self.detected_conflicts_count += conflicts_count

        for r_id, status in robot_statuses.items():
            if status in ('IDLE', 'DOCKED'):
                self.robot_idle_steps[r_id] = self.robot_idle_steps.get(r_id, 0) + 1
            else:
                self.robot_active_steps[r_id] = self.robot_active_steps.get(r_id, 0) + 1
                self.total_robot_steps += 1

    def record_task_completion(self) -> None:
        """Increment completed task counter."""
        self.completed_tasks_count += 1

    def record_replan_event(self, latency_ms: float) -> None:
        """Record dynamic replanning overhead."""
        self.replan_events_count += 1
        self.replan_latencies_ms.append(latency_ms)

    def record_scaling_benchmark(self, num_robots: int, avg_cost: float) -> None:
        """Records planning cost scaling for given robot count."""
        self.scaling_data[num_robots] = avg_cost

    def get_summary(self) -> Dict[str, any]:
        """Calculates comprehensive KPIs."""
        makespan = self.simulation_step
        throughput = (self.completed_tasks_count / max(1, makespan)) * 100.0  # tasks per 100 steps
        avg_latency = (
            sum(self.replan_latencies_ms) / len(self.replan_latencies_ms)
            if self.replan_latencies_ms
            else 0.0
        )
        total_tracked_steps = sum(self.robot_active_steps.values()) + sum(self.robot_idle_steps.values())
        overall_utilization = (
            (sum(self.robot_active_steps.values()) / max(1, total_tracked_steps)) * 100.0
            if total_tracked_steps > 0
            else 0.0
        )

        return {
            'makespan': makespan,
            'total_robot_steps': self.total_robot_steps,
            'completed_tasks': self.completed_tasks_count,
            'throughput_per_100_steps': round(throughput, 2),
            'detected_conflicts': self.detected_conflicts_count,
            'collision_rate_percent': 0.0 if self.detected_conflicts_count == 0 else round((self.detected_conflicts_count / max(1, self.total_robot_steps)) * 100, 2),
            'replan_events': self.replan_events_count,
            'avg_replan_latency_ms': round(avg_latency, 2),
            'robot_utilization_percent': round(overall_utilization, 1),
            'scaling_data': self.scaling_data,
        }
