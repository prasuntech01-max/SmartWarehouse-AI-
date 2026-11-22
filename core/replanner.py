"""Dynamic replanning upon unexpected mid-route obstacle occurrences."""

import time
from typing import Dict, List, Tuple, Optional, Set
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner


class DynamicReplanner:
    def __init__(self, grid: WarehouseGrid, reservation_table: ReservationTable):
        self.grid = grid
        self.reservation_table = reservation_table
        self.planner = SpaceTimeAStarPlanner(grid, reservation_table)

    def handle_obstacle_injection(
        self,
        obstacle: Tuple[int, int],
        current_time: int,
        robot_states: Dict[int, Dict[str, any]],
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
            # Keep past reservations, but clear from current_time onwards
            self._clear_future_reservations(r_id, current_time)

        # Replan each affected robot in priority order
        updated_paths: Dict[int, List[Tuple[int, int]]] = {}

        for r_id in affected_robots:
            state = robot_states[r_id]
            curr_pos = state['pos']
            goal = state['goal']

            new_subpath = self.planner.plan(
                start=curr_pos,
                goal=goal,
                start_time=current_time,
                robot_id=r_id,
            )

            if new_subpath is not None:
                updated_paths[r_id] = new_subpath
                self.reservation_table.reserve_path(
                    new_subpath,
                    robot_id=r_id,
                    start_time=current_time,
                )
            else:
                # Fallback: wait in place for current step
                updated_paths[r_id] = [curr_pos]

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return updated_paths, latency_ms, affected_robots

    def _clear_future_reservations(self, robot_id: int, from_time: int) -> None:
        """Removes reservations for a robot starting from a specified timestep."""
        v_to_del = [
            (x, y, t)
            for (x, y, t), r in self.reservation_table.vertex_reservations.items()
            if r == robot_id and t >= from_time
        ]
        for k in v_to_del:
            del self.reservation_table.vertex_reservations[k]

        e_to_del = [
            (u, v, t)
            for (u, v, t), r in self.reservation_table.edge_reservations.items()
            if r == robot_id and t >= from_time
        ]
        for k in e_to_del:
            del self.reservation_table.edge_reservations[k]
