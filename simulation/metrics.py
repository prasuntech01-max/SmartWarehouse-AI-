"""Performance metrics collector and analytics for the warehouse simulator."""

from typing import Dict, List, Optional, Any
import time
import math


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
        self.deadlock_events_count = 0
        self.robot_active_steps: Dict[int, int] = {}
        self.robot_idle_steps: Dict[int, int] = {}
        self.scaling_data: Dict[int, float] = {}  # robot_count -> avg planning cost

        # Module 8 metrics
        self.replan_attempts: int = 0
        self.replan_successes: int = 0
        self.replan_failures: int = 0
        self.replan_distance_added: Dict[int, float] = {}  # robot_id -> cumulative additional steps
        self.obstacle_events_count: int = 0
        self.replan_times_by_robot: Dict[int, List[float]] = {}

        # Module 9 Task & Fleet Optimization metrics
        self.completed_tasks_by_priority: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
        self.task_wait_times: List[int] = []         # steps waiting in queue before assignment
        self.task_transit_times: List[int] = []      # steps from assignment to delivery completion
        self.strategy_benchmark_cache: List[Dict[str, Any]] = []

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

    def record_task_completion(self, priority: int = 2, wait_steps: int = 0, transit_steps: int = 0) -> None:
        """Increment completed task counter and log priority/duration telemetry."""
        self.completed_tasks_count += 1
        p = int(priority)
        self.completed_tasks_by_priority[p] = self.completed_tasks_by_priority.get(p, 0) + 1
        if wait_steps > 0:
            self.task_wait_times.append(wait_steps)
        if transit_steps > 0:
            self.task_transit_times.append(transit_steps)

    def record_replan_event(self, latency_ms: float) -> None:
        """Record dynamic replanning overhead."""
        self.replan_events_count += 1
        self.replan_latencies_ms.append(latency_ms)

    def record_replan_attempt(
        self,
        robot_id: int,
        success: bool,
        path_delta: float = 0.0,
        latency_ms: float = 0.0,
    ) -> None:
        """Record fine-grained per-robot replanning attempt."""
        self.replan_attempts += 1
        if success:
            self.replan_successes += 1
        else:
            self.replan_failures += 1

        self.replan_distance_added[robot_id] = (
            self.replan_distance_added.get(robot_id, 0.0) + max(0.0, path_delta)
        )
        if robot_id not in self.replan_times_by_robot:
            self.replan_times_by_robot[robot_id] = []
        self.replan_times_by_robot[robot_id].append(latency_ms)

    def record_obstacle_event(self) -> None:
        """Record a dynamic obstacle appearance."""
        self.obstacle_events_count += 1

    @property
    def replan_success_rate(self) -> float:
        """Percentage of replanning attempts that successfully found a route."""
        if self.replan_attempts == 0:
            return 100.0
        return round((self.replan_successes / self.replan_attempts) * 100.0, 1)

    def record_deadlock_event(self) -> None:
        """Record deadlock detection and recovery event."""
        self.deadlock_events_count += 1

    def record_scaling_benchmark(self, num_robots: int, avg_cost: float) -> None:
        """Records planning cost scaling for given robot count."""
        self.scaling_data[num_robots] = avg_cost

    @staticmethod
    def calculate_workload_balance(robot_completed_counts: Dict[int, int]) -> Dict[str, float]:
        """
        Calculates workload distribution fairness metrics across fleet robots:
        mean, standard deviation, and Gini coefficient (0.0 = perfect equality).
        """
        if not robot_completed_counts:
            return {"mean": 0.0, "std_dev": 0.0, "gini": 0.0}

        vals = list(robot_completed_counts.values())
        n = len(vals)
        mean_val = sum(vals) / n
        variance = sum((x - mean_val) ** 2 for x in vals) / n
        std_dev = math.sqrt(variance)

        # Gini coefficient: sum of absolute differences / (2 * n * sum(vals))
        total_sum = sum(vals)
        if total_sum == 0:
            gini = 0.0
        else:
            diff_sum = sum(abs(xi - xj) for xi in vals for xj in vals)
            gini = diff_sum / (2.0 * n * total_sum)

        return {
            "mean": round(mean_val, 2),
            "std_dev": round(std_dev, 2),
            "gini": round(gini, 3),
        }

    def get_replan_analytics(self) -> Dict[str, Any]:
        """Provides detailed Module 8 replanning telemetry."""
        return {
            'replan_attempts': self.replan_attempts,
            'replan_successes': self.replan_successes,
            'replan_failures': self.replan_failures,
            'replan_success_rate': self.replan_success_rate,
            'obstacle_events_count': self.obstacle_events_count,
            'replan_distance_added': dict(self.replan_distance_added),
            'replan_times_by_robot': {str(k): list(v) for k, v in self.replan_times_by_robot.items()},
        }

    def get_task_analytics(self) -> Dict[str, Any]:
        """Provides detailed Module 9 task dispatching & completion analytics."""
        avg_wait = (sum(self.task_wait_times) / len(self.task_wait_times)) if self.task_wait_times else 0.0
        avg_transit = (sum(self.task_transit_times) / len(self.task_transit_times)) if self.task_transit_times else 0.0
        return {
            'completed_tasks_by_priority': dict(self.completed_tasks_by_priority),
            'avg_wait_steps': round(avg_wait, 1),
            'avg_transit_steps': round(avg_transit, 1),
            'total_completed': self.completed_tasks_count,
        }

    def get_summary(self) -> Dict[str, Any]:
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
            'deadlock_events': self.deadlock_events_count,
            'robot_utilization_percent': round(overall_utilization, 1),
            'scaling_data': self.scaling_data,
            'replan_success_rate': self.replan_success_rate,
            'obstacle_events': self.obstacle_events_count,
            'tasks_by_priority': self.completed_tasks_by_priority,
        }
