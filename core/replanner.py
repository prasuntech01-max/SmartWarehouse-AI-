"""Dynamic replanning upon unexpected mid-route obstacle occurrences."""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Tuple, Optional, Set, Any
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner


@dataclass
class ReplanEvent:
    """Detailed record of an individual robot replanning action."""
    robot_id: int
    reason: str
    success: bool
    old_path_len: int
    new_path_len: int
    latency_ms: float
    timestamp: int

    @property
    def path_delta(self) -> int:
        """Step count difference between newly planned and previous path."""
        return self.new_path_len - self.old_path_len

    def to_dict(self) -> Dict[str, Any]:
        """Convert replan event to dictionary."""
        return {
            'robot_id': self.robot_id,
            'reason': self.reason,
            'success': self.success,
            'old_path_len': self.old_path_len,
            'new_path_len': self.new_path_len,
            'path_delta': self.path_delta,
            'latency_ms': round(self.latency_ms, 3),
            'timestamp': self.timestamp,
        }


class DynamicReplanner:
    """
    Intelligent dynamic replanner handling runtime obstacles, atomic reservation updates,
    and safe waiting fallbacks with complete telemetry history.
    """

    def __init__(self, grid: WarehouseGrid, reservation_table: ReservationTable):
        self.grid = grid
        self.reservation_table = reservation_table
        self.planner = SpaceTimeAStarPlanner(grid, reservation_table)
        self.replan_history: List[ReplanEvent] = []

    def replan_single_robot(
        self,
        robot_id: int,
        curr_pos: Tuple[int, int],
        goal: Tuple[int, int],
        current_time: int,
        old_path_len: int = 0,
        reason: str = "dynamic_obstacle",
    ) -> Tuple[Optional[List[Tuple[int, int]]], float, bool]:
        """
        Atomically replans a path for a single robot while protecting existing reservations.

        Returns:
            (new_path, latency_ms, success)
        """
        t0 = time.perf_counter()
        snapshot = self.reservation_table.snapshot()

        # Release future reservations for this robot starting at current_time
        self._clear_future_reservations(robot_id, current_time)

        # Plan alternate route
        try:
            new_path = self.planner.plan(
                start=curr_pos,
                goal=goal,
                start_time=current_time,
                robot_id=robot_id,
            )
        except Exception:
            new_path = None

        latency_ms = (time.perf_counter() - t0) * 1000.0

        if new_path is not None:
            # Commit new trajectory reservation
            self.reservation_table.reserve_path(
                new_path,
                robot_id=robot_id,
                start_time=current_time,
            )
            event = ReplanEvent(
                robot_id=robot_id,
                reason=reason,
                success=True,
                old_path_len=old_path_len,
                new_path_len=len(new_path),
                latency_ms=latency_ms,
                timestamp=current_time,
            )
            self.replan_history.append(event)
            return new_path, latency_ms, True
        else:
            # Rollback to snapshot or fallback to safe waiting in place
            self.reservation_table.restore(snapshot)
            # Re-reserve current stationary vertex to prevent other robots from entering
            self.reservation_table.reserve_vertex(
                curr_pos[0], curr_pos[1], current_time + 1, robot_id=robot_id
            )
            event = ReplanEvent(
                robot_id=robot_id,
                reason=f"{reason}_failed_waiting",
                success=False,
                old_path_len=old_path_len,
                new_path_len=1,
                latency_ms=latency_ms,
                timestamp=current_time,
            )
            self.replan_history.append(event)
            return [curr_pos], latency_ms, False

    def handle_obstacle_injection(
        self,
        obstacle: Tuple[int, int],
        current_time: int,
        robot_states: Dict[int, Dict[str, Any]],
    ) -> Tuple[Dict[int, List[Tuple[int, int]]], float, List[int]]:
        """
        Dynamically replans trajectories for robots affected by sudden obstacle appearance.

        Args:
            obstacle: (x, y) coordinates of injected obstacle
            current_time: Current simulation timestep
            robot_states: Dict of robot_id -> {'pos': (x, y), 'goal': (x, y), 'path': [(x, y)...], 'start_time': int}

        Returns:
            updated_paths: Dict of robot_id -> remaining path from current_time onwards
            latency_ms: Milliseconds taken to replan
            affected_robot_ids: List of robot IDs that required replanning
        """
        t0 = time.perf_counter()
        affected_robots: List[int] = []

        # Add obstacle to grid
        self.grid.add_dynamic_obstacle(obstacle[0], obstacle[1])

        # Identify which robots are affected
        for r_id, state in robot_states.items():
            path = state['path']
            st = state.get('start_time', 0)

            # Check if any future node on robot's trajectory collides with the obstacle
            is_affected = False
            for i, node in enumerate(path):
                t_node = st + i
                if t_node >= current_time and node == obstacle:
                    is_affected = True
                    break

            if is_affected:
                affected_robots.append(r_id)

        # Clear future reservations for affected robots
        for r_id in affected_robots:
            self._clear_future_reservations(r_id, current_time)

        # Replan each affected robot in priority order
        updated_paths: Dict[int, List[Tuple[int, int]]] = {}

        for r_id in affected_robots:
            state = robot_states[r_id]
            curr_pos = state['pos']
            goal = state['goal']
            old_len = len(state.get('path', []))

            t_sub0 = time.perf_counter()
            try:
                new_subpath = self.planner.plan(
                    start=curr_pos,
                    goal=goal,
                    start_time=current_time,
                    robot_id=r_id,
                )
            except Exception:
                new_subpath = None
            sub_latency_ms = (time.perf_counter() - t_sub0) * 1000.0

            if new_subpath is not None:
                updated_paths[r_id] = new_subpath
                self.reservation_table.reserve_path(
                    new_subpath,
                    robot_id=r_id,
                    start_time=current_time,
                )
                self.replan_history.append(ReplanEvent(
                    robot_id=r_id,
                    reason="obstacle_injection",
                    success=True,
                    old_path_len=old_len,
                    new_path_len=len(new_subpath),
                    latency_ms=sub_latency_ms,
                    timestamp=current_time,
                ))
            else:
                # Safe fallback: wait in place for current step
                updated_paths[r_id] = [curr_pos]
                self.reservation_table.reserve_vertex(
                    curr_pos[0], curr_pos[1], current_time + 1, robot_id=r_id
                )
                self.replan_history.append(ReplanEvent(
                    robot_id=r_id,
                    reason="obstacle_injection_blocked",
                    success=False,
                    old_path_len=old_len,
                    new_path_len=1,
                    latency_ms=sub_latency_ms,
                    timestamp=current_time,
                ))

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return updated_paths, latency_ms, affected_robots

    def _clear_future_reservations(self, robot_id: int, from_time: int) -> None:
        """Removes reservations for a robot starting from a specified timestep."""
        self.reservation_table.release_future_reservations(robot_id, from_time=from_time)
