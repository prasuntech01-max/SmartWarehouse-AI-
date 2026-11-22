"""Space-Time A* Planner for warehouse robot path planning."""

import heapq
import time
from typing import List, Tuple, Optional, Dict
from core.grid import WarehouseGrid
from core.reservation import ReservationTable


class SpaceTimeAStarPlanner:
    def __init__(self, grid: WarehouseGrid, reservation_table: Optional[ReservationTable] = None):
        self.grid = grid
        self.reservation_table = reservation_table or ReservationTable()

    def manhattan_distance(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """Admissible Manhattan distance heuristic."""
        return abs(x1 - x2) + abs(y1 - y2)

    def plan(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        start_time: int = 0,
        robot_id: int = 0,
        max_time: int = 200,
        hold_at_goal: int = 5,
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Plans a collision-free space-time trajectory from start to goal.
        
        Args:
            start: (x, y) start coordinate
            goal: (x, y) destination coordinate
            start_time: Current simulation time step
            robot_id: ID of the robot planning the route
            max_time: Maximum allowable time horizon before aborting search
            hold_at_goal: Number of timesteps the goal must remain free after arrival
            
        Returns:
            List of (x, y) coordinates from start_time to arrival, or None if no valid path exists.
        """
        start_clock = time.perf_counter()

        if not self.grid.is_walkable(start[0], start[1]):
            return None
        if not self.grid.is_walkable(goal[0], goal[1]):
            return None

        # Priority queue stores: (f_score, h_score, (x, y, t))
        open_set: List[Tuple[float, int, Tuple[int, int, int]]] = []
        h_start = self.manhattan_distance(start[0], start[1], goal[0], goal[1])
        heapq.heappush(open_set, (float(h_start), h_start, (start[0], start[1], start_time)))

        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
        g_score: Dict[Tuple[int, int, int], int] = {(start[0], start[1], start_time): 0}
        closed_set = set()

        nodes_expanded = 0

        while open_set:
            current_f, current_h, current_state = heapq.heappop(open_set)
            cx, cy, ct = current_state

            if current_state in closed_set:
                continue
            closed_set.add(current_state)
            nodes_expanded += 1

            # Goal test: reached goal coordinate
            if (cx, cy) == goal:
                # Ensure the goal position is safe from conflicts for hold_at_goal steps
                goal_safe = True
                for delta_t in range(1, hold_at_goal + 1):
                    if self.reservation_table.is_vertex_reserved(goal[0], goal[1], ct + delta_t, ignore_robot=robot_id):
                        goal_safe = False
                        break
                if goal_safe:
                    # Reconstruct path
                    path: List[Tuple[int, int]] = []
                    curr: Optional[Tuple[int, int, int]] = current_state
                    while curr is not None:
                        path.append((curr[0], curr[1]))
                        curr = came_from.get(curr)
                    path.reverse()
                    return path

            if ct >= start_time + max_time:
                continue

            current_g = g_score[current_state]

            # Possible actions: Move to 4-connected neighbors, or Wait in place
            neighbors = self.grid.get_neighbors(cx, cy)
            candidates = neighbors + [(cx, cy)]  # (cx, cy) represents Wait action

            for nx, ny in candidates:
                next_t = ct + 1
                next_state = (nx, ny, next_t)

                if next_state in closed_set:
                    continue

                # Collision check using reservation table
                if not self.reservation_table.is_action_valid(
                    u=(cx, cy),
                    v=(nx, ny),
                    t=ct,
                    ignore_robot=robot_id,
                ):
                    continue

                # Tentative g_score: step cost is 1
                tentative_g = current_g + 1

                if next_state not in g_score or tentative_g < g_score[next_state]:
                    came_from[next_state] = current_state
                    g_score[next_state] = tentative_g
                    h = self.manhattan_distance(nx, ny, goal[0], goal[1])
                    # Slight tie-breaker to prefer moving over waiting when f is equal
                    wait_penalty = 0.001 if (nx, ny) == (cx, cy) else 0.0
                    f = tentative_g + h + wait_penalty
                    heapq.heappush(open_set, (f, h, next_state))

        return None
