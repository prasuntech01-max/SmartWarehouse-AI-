"""Module 10 — Predictive Robot Maintenance Health Monitor.

Computes a simulated health score for each robot based on battery level,
cumulative travel distance, and task completion load.

NOTE: All metrics are simulated telemetry derived from the digital-twin
simulation state — not real hardware sensor data.
"""

from typing import Dict, List, Any, Tuple


# Health tier thresholds
HEALTH_TIERS = [
    (80, 'Excellent', '#27AE60'),
    (60, 'Good',      '#3498DB'),
    (40, 'Warning',   '#E67E22'),
    (0,  'Critical',  '#E74C3C'),
]

# Maximum deductions from each factor
_MAX_BATTERY_DEDUCT = 20    # up to 20 pts for low battery
_MAX_DISTANCE_DEDUCT = 30   # up to 30 pts for high distance
_MAX_TASK_DEDUCT = 20       # up to 20 pts for high task count


def _health_tier(score: float) -> Tuple[str, str]:
    """Return (status_label, hex_colour) for a 0-100 health score."""
    for threshold, label, colour in HEALTH_TIERS:
        if score >= threshold:
            return label, colour
    return 'Critical', '#E74C3C'


class RobotHealthMonitor:
    """Monitors and reports per-robot health scores.

    Health Score Formula (documented, deterministic):
      Start at 100.
      Deduct 20 if battery < 20%.
      Deduct 10 if battery < 40% (instead of 20).
      Deduct min(30, total_distance / 20) for wear from travel.
      Deduct min(20, completed_tasks * 2) for task workload fatigue.

    Parameters
    ----------
    robots : dict
        Live {robot_id: RobotState} from WarehouseSimulator.
    step_count : int
        Current simulation step.
    """

    def __init__(self, robots: Dict[int, Any], step_count: int = 0) -> None:
        self.robots = robots
        self.step_count = step_count

    def compute_health_score(self, robot_id: int) -> float:
        """Compute health score 0-100 for robot_id.

        Returns 0.0 if robot_id does not exist.
        """
        robot = self.robots.get(robot_id)
        if robot is None:
            return 0.0

        score = 100.0
        battery = getattr(robot, 'battery', 100.0)
        distance = getattr(robot, 'total_distance', 0)
        tasks_done = getattr(robot, 'completed_tasks', 0)

        # Battery deduction
        if battery < 20.0:
            score -= _MAX_BATTERY_DEDUCT       # -20
        elif battery < 40.0:
            score -= _MAX_BATTERY_DEDUCT // 2  # -10

        # Distance wear deduction
        dist_deduct = min(_MAX_DISTANCE_DEDUCT, distance / 20.0)
        score -= dist_deduct

        # Task workload deduction
        task_deduct = min(_MAX_TASK_DEDUCT, tasks_done * 2.0)
        score -= task_deduct

        return max(0.0, round(score, 1))

    def get_fleet_health_summary(self) -> Dict[int, Dict[str, Any]]:
        """Compute health summary for every robot in the fleet.

        Returns
        -------
        {robot_id: {'score', 'status', 'colour', 'battery', 'distance',
                    'completed_tasks', 'recommendations'}}
        """
        summary = {}
        for r_id, robot in self.robots.items():
            score = self.compute_health_score(r_id)
            status, colour = _health_tier(score)
            recs = self.get_recommendations(r_id)
            summary[r_id] = {
                'score': score,
                'status': status,
                'colour': colour,
                'battery': round(getattr(robot, 'battery', 100.0), 1),
                'distance': getattr(robot, 'total_distance', 0),
                'completed_tasks': getattr(robot, 'completed_tasks', 0),
                'recommendations': recs,
            }
        return summary

    def get_maintenance_priority(self) -> List[int]:
        """Returns robot IDs sorted by urgency (lowest health first)."""
        scores = {r_id: self.compute_health_score(r_id) for r_id in self.robots}
        return sorted(scores.keys(), key=lambda r: scores[r])

    def get_recommendations(self, robot_id: int) -> List[str]:
        """Return context-sensitive maintenance action items for a robot."""
        robot = self.robots.get(robot_id)
        if robot is None:
            return [f"Robot R{robot_id} not found."]

        score = self.compute_health_score(robot_id)
        battery = getattr(robot, 'battery', 100.0)
        distance = getattr(robot, 'total_distance', 0)
        tasks = getattr(robot, 'completed_tasks', 0)
        recs = []

        if battery < 20.0:
            recs.append(
                f"CRITICAL: Battery at {battery:.1f}%. Return R{robot_id} to charging dock immediately."
            )
        elif battery < 40.0:
            recs.append(
                f"WARNING: Battery at {battery:.1f}%. Schedule charging for R{robot_id} soon."
            )

        if distance > 400:
            recs.append(
                f"R{robot_id} has travelled {distance}m — schedule simulated wheel-mechanism inspection."
            )
        elif distance > 200:
            recs.append(
                f"R{robot_id} has covered {distance}m — monitor drive components."
            )

        if tasks > 15:
            recs.append(
                f"R{robot_id} completed {tasks} tasks — high utilisation, consider redistributing workload."
            )

        if score < 40:
            recs.append(
                f"CRITICAL HEALTH ({score}/100): Recommend taking R{robot_id} offline for maintenance cycle."
            )
        elif score < 60:
            recs.append(
                f"HEALTH WARNING ({score}/100): R{robot_id} efficiency may be degraded — monitor closely."
            )

        if not recs:
            recs.append(
                f"R{robot_id} health nominal ({score}/100). No immediate action required."
            )

        return recs

    def get_fleet_average_health(self) -> float:
        """Fleet-wide mean health score 0-100."""
        if not self.robots:
            return 100.0
        scores = [self.compute_health_score(r_id) for r_id in self.robots]
        return round(sum(scores) / len(scores), 1)

    def get_critical_robots(self, threshold: float = 40.0) -> List[int]:
        """Return robot IDs with health score below threshold."""
        return [
            r_id for r_id in self.robots
            if self.compute_health_score(r_id) < threshold
        ]
