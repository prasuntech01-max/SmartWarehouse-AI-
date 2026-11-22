"""Genuine A* and Space-Time A* pathfinding implementation for warehouse robots."""

import heapq
import time
from typing import List, Tuple, Optional, Dict, Any
from warehouse import Warehouse
from core.reservation import ReservationTable
from core.state import Action, TimeExpandedState, Trajectory, TimeExpandedPlanner


class PathNotFoundError(Exception):
    """Raised when no valid obstacle-free path can be found between start and goal."""
    pass


class AStarPlanner:
    """A* Pathfinding supporting both static 2D grid searches and Space-Time reservation planning."""

    def __init__(
        self,
        warehouse: Optional[Warehouse] = None,
        reservation_table: Optional[ReservationTable] = None,
        grid: Optional[Warehouse] = None,
    ):
        wh = warehouse if warehouse is not None else grid
        if wh is None:
            raise ValueError("A valid Warehouse or WarehouseGrid instance must be provided")
        self.warehouse = wh
        self.grid = wh  # alias for grid-based calls
        self.reservation_table = reservation_table

    @staticmethod
    def manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
        """Admissible Manhattan distance heuristic."""
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _validate_endpoints(self, start: Tuple[int, int], goal: Tuple[int, int]) -> None:
        """Assert that start and goal are valid, in bounds, and walkable."""
        if not (isinstance(start, (tuple, list)) and len(start) == 2):
            raise TypeError(f"Start must be a coordinate tuple (x, y), got {start}")
        if not (isinstance(goal, (tuple, list)) and len(goal) == 2):
            raise TypeError(f"Goal must be a coordinate tuple (x, y), got {goal}")

        sx, sy = int(start[0]), int(start[1])
        gx, gy = int(goal[0]), int(goal[1])

        if not self.warehouse.in_bounds(sx, sy):
            raise ValueError(f"Start coordinate ({sx}, {sy}) is out of bounds for {self.warehouse.width}x{self.warehouse.height}")
        if not self.warehouse.in_bounds(gx, gy):
            raise ValueError(f"Goal coordinate ({gx}, {gy}) is out of bounds for {self.warehouse.width}x{self.warehouse.height}")

        if not self.warehouse.is_walkable(sx, sy):
            raise ValueError(f"Start coordinate ({sx}, {sy}) is blocked by an obstacle")
        if not self.warehouse.is_walkable(gx, gy):
            raise ValueError(f"Goal coordinate ({gx}, {gy}) is blocked by an obstacle")

    def plan_2d(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        raise_on_failure: bool = False,
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Classic static 2D A* pathfinding.
        Returns the shortest obstacle-avoiding path from start to goal.
        """
        self._validate_endpoints(start, goal)
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))

        if start == goal:
            return [start]

        # Priority queue stores: (f_score, h_score, (x, y))
        open_set: List[Tuple[float, int, Tuple[int, int]]] = []
        h_start = self.manhattan_distance(start, goal)
        heapq.heappush(open_set, (float(h_start), h_start, start))

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], int] = {start: 0}
        closed_set = set()

        while open_set:
            current_f, current_h, current = heapq.heappop(open_set)

            if current in closed_set:
                continue
            closed_set.add(current)

            if current == goal:
                # Reconstruct path
                path = []
                curr: Optional[Tuple[int, int]] = goal
                while curr is not None:
                    path.append(curr)
                    curr = came_from.get(curr)
                path.reverse()
                return path

            for neighbor in self.warehouse.get_neighbors(current[0], current[1]):
                if neighbor in closed_set:
                    continue

                tentative_g = g_score[current] + 1
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = self.manhattan_distance(neighbor, goal)
                    f = tentative_g + h
                    heapq.heappush(open_set, (float(f), h, neighbor))

        if raise_on_failure:
            raise PathNotFoundError(f"No valid path exists between {start} and {goal}")
        return None

    def plan_spacetime(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        start_time: int = 0,
        robot_id: int = 0,
        max_time: int = 200,
        hold_at_goal: int = 5,
        raise_on_failure: bool = False,
    ) -> Optional[Trajectory]:
        """
        Space-Time A* searching in (x, y, t) state-space.
        Supports 4-connected moves plus Wait actions, avoiding dynamic collisions
        via the reservation table.
        """
        self._validate_endpoints(start, goal)
        if self.reservation_table is None:
            # Fallback to standard 2D A* if no reservation table is provided
            return self.plan_2d(start, goal, raise_on_failure=raise_on_failure)

        te_planner = TimeExpandedPlanner(self.warehouse, self.reservation_table)
        return te_planner.plan(
            start=start,
            goal=goal,
            start_time=start_time,
            robot_id=robot_id,
            max_horizon=max_time,
            hold_at_goal=hold_at_goal,
            raise_on_failure=raise_on_failure,
        )

    def plan(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        start_time: int = 0,
        robot_id: int = 0,
        max_time: int = 200,
        hold_at_goal: int = 5,
        raise_on_failure: bool = False,
    ) -> Optional[List[Tuple[int, int]]]:
        """Unified planning API compatible with both single-agent and multi-agent systems."""
        if self.reservation_table is not None:
            return self.plan_spacetime(
                start=start,
                goal=goal,
                start_time=start_time,
                robot_id=robot_id,
                max_time=max_time,
                hold_at_goal=hold_at_goal,
                raise_on_failure=raise_on_failure,
            )
        else:
            return self.plan_2d(
                start=start,
                goal=goal,
                raise_on_failure=raise_on_failure,
            )


# Canonical alias for space-time planner
SpaceTimeAStarPlanner = AStarPlanner

__all__ = [
    "AStarPlanner",
    "SpaceTimeAStarPlanner",
    "PathNotFoundError",
    "Action",
    "TimeExpandedState",
    "Trajectory",
    "TimeExpandedPlanner",
]
