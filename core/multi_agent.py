"""Multi-Agent Prioritized Planning and Collision Detection."""

from typing import Dict, List, Tuple, Optional, Any
import time
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner
from core.conflict import MultiRobotConflictDetector, ConflictReport, ConflictType

# Backward-compatibility alias
Conflict = ConflictReport

__all__ = [
    "MultiAgentPlanner",
    "Conflict",
    "ConflictReport",
    "ConflictType",
    "MultiRobotConflictDetector",
]


class MultiAgentPlanner:
    def __init__(self, grid: WarehouseGrid):
        self.grid = grid
        self.reservation_table = ReservationTable()
        self.planner = SpaceTimeAStarPlanner(grid, self.reservation_table)
        self.detector = MultiRobotConflictDetector(warehouse=grid)

    @staticmethod
    def detect_conflicts(
        paths: Dict[int, Any],
        start_times: Optional[Dict[int, int]] = None,
        warehouse: Optional[WarehouseGrid] = None,
    ) -> List[ConflictReport]:
        """
        Exhaustively scans a dictionary of robot paths to detect any vertex or edge collisions.
        Returns a list of all detected conflicts.
        """
        detector = MultiRobotConflictDetector(warehouse=warehouse)
        return detector.detect_conflicts(paths, start_times=start_times)

    def plan_prioritized(
        self,
        agents: List[Dict[str, any]],
        start_time: int = 0,
        priorities: Optional[List[int]] = None,
    ) -> Tuple[Dict[int, List[Tuple[int, int]]], bool]:
        """
        Computes collision-free paths for multiple agents using Prioritized Space-Time A*.
        
        agents: List of dicts with keys: 'id', 'start', 'goal'
        Returns:
            paths: Dict of robot_id -> path
            success: True if all robots found a valid collision-free path
        """
        self.reservation_table.clear()
        paths: Dict[int, List[Tuple[int, int]]] = {}

        # Default ordering: given priority list or sequential
        if priorities is None:
            ordered_agents = agents
        else:
            p_map = {r_id: idx for idx, r_id in enumerate(priorities)}
            ordered_agents = sorted(agents, key=lambda a: p_map.get(a['id'], 999))

        all_success = True
        for agent in ordered_agents:
            r_id = agent['id']
            start = agent['start']
            goal = agent['goal']

            # Plan trajectory respecting reservations made by higher-priority agents
            path = self.planner.plan(
                start=start,
                goal=goal,
                start_time=start_time,
                robot_id=r_id,
            )

            if path is None:
                all_success = False
                paths[r_id] = [start]  # Hold start as fallback
            else:
                paths[r_id] = path
                self.reservation_table.reserve_path(path, robot_id=r_id, start_time=start_time)

        return paths, all_success
