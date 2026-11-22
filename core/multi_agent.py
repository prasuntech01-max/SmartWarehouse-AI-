"""Multi-Agent Prioritized Planning and Collision Detection."""

from typing import Dict, List, Tuple, Optional, Any
import time
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner
from core.conflict import MultiRobotConflictDetector, ConflictReport, ConflictType
from core.priority import PriorityPlanner, PriorityManager, PriorityScheme

# Backward-compatibility alias
Conflict = ConflictReport

__all__ = [
    "MultiAgentPlanner",
    "Conflict",
    "ConflictReport",
    "ConflictType",
    "MultiRobotConflictDetector",
    "PriorityPlanner",
    "PriorityManager",
    "PriorityScheme",
]


class MultiAgentPlanner:
    def __init__(self, grid: WarehouseGrid):
        self.grid = grid
        self.reservation_table = ReservationTable()
        self.planner = SpaceTimeAStarPlanner(grid, self.reservation_table)
        self.detector = MultiRobotConflictDetector(warehouse=grid)
        self.priority_planner = PriorityPlanner(warehouse=grid, reservation_table=self.reservation_table)

    @staticmethod
    def detect_conflicts(
        paths: Dict[int, Any],
        start_times: Optional[Dict[int, int]] = None,
        warehouse: Optional[WarehouseGrid] = None,
        park_at_goal: bool = True,
    ) -> List[ConflictReport]:
        """
        Exhaustively scans a dictionary of robot paths to detect any vertex or edge collisions.
        Returns a list of all detected conflicts.
        """
        detector = MultiRobotConflictDetector(warehouse=warehouse)
        return detector.detect_conflicts(paths, start_times=start_times, park_at_goal=park_at_goal)

    def plan_prioritized(
        self,
        agents: List[Dict[str, any]],
        start_time: int = 0,
        priorities: Optional[List[int]] = None,
    ) -> Tuple[Dict[int, Any], bool]:
        """
        Computes collision-free paths for multiple agents using Prioritized Space-Time A*.
        
        agents: List of dicts with keys: 'id', 'start', 'goal'
        Returns:
            paths: Dict of robot_id -> path / trajectory
            success: True if all robots found a valid collision-free path
        """
        paths, all_success, _ = self.priority_planner.plan_sequential(
            agents=agents,
            start_time=start_time,
            priorities=priorities,
            clear_table=True,
        )
        return paths, all_success
