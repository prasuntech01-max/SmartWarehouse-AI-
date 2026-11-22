"""Multi-Agent Prioritized Planning and Collision Detection."""

from typing import Dict, List, Tuple, Optional, NamedTuple
import time
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner


class Conflict(NamedTuple):
    conflict_type: str  # 'vertex' or 'edge'
    robot_a: int
    robot_b: int
    time_step: int
    location_a: Tuple[int, int]
    location_b: Tuple[int, int]


class MultiAgentPlanner:
    def __init__(self, grid: WarehouseGrid):
        self.grid = grid
        self.reservation_table = ReservationTable()
        self.planner = SpaceTimeAStarPlanner(grid, self.reservation_table)

    @staticmethod
    def detect_conflicts(paths: Dict[int, List[Tuple[int, int]]], start_times: Optional[Dict[int, int]] = None) -> List[Conflict]:
        """
        Exhaustively scans a dictionary of robot paths to detect any vertex or edge collisions.
        Returns a list of all detected conflicts.
        """
        conflicts: List[Conflict] = []
        robot_ids = list(paths.keys())
        if not robot_ids:
            return conflicts

        if start_times is None:
            start_times = {r_id: 0 for r_id in robot_ids}

        # Determine overall time horizon
        max_t = 0
        expanded_paths: Dict[int, Dict[int, Tuple[int, int]]] = {}

        for r_id in robot_ids:
            r_path = paths[r_id]
            st = start_times[r_id]
            expanded: Dict[int, Tuple[int, int]] = {}
            for i, pos in enumerate(r_path):
                expanded[st + i] = pos
            if r_path:
                end_t = st + len(r_path) - 1
                if end_t > max_t:
                    max_t = end_t
            expanded_paths[r_id] = expanded

        # Check at each time step
        for t in range(max_t + 1):
            for i in range(len(robot_ids)):
                r1 = robot_ids[i]
                p1_curr = expanded_paths[r1].get(t)
                p1_next = expanded_paths[r1].get(t + 1)

                if p1_curr is None:
                    continue

                for j in range(i + 1, len(robot_ids)):
                    r2 = robot_ids[j]
                    p2_curr = expanded_paths[r2].get(t)
                    p2_next = expanded_paths[r2].get(t + 1)

                    if p2_curr is None:
                        continue

                    # 1. Vertex Conflict at time t
                    if p1_curr == p2_curr:
                        conflicts.append(Conflict(
                            conflict_type='vertex',
                            robot_a=r1,
                            robot_b=r2,
                            time_step=t,
                            location_a=p1_curr,
                            location_b=p2_curr,
                        ))

                    # 2. Edge/Swap Conflict at time t -> t+1
                    if p1_next is not None and p2_next is not None:
                        if p1_curr == p2_next and p1_next == p2_curr and p1_curr != p1_next:
                            conflicts.append(Conflict(
                                conflict_type='edge',
                                robot_a=r1,
                                robot_b=r2,
                                time_step=t,
                                location_a=p1_curr,
                                location_b=p2_curr,
                            ))

        return conflicts

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
