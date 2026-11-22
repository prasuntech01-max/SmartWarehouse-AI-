"""Deadlock detection and resolution mechanisms for multi-robot navigation."""

from typing import Dict, List, Tuple, Optional
import copy
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner


class DeadlockHandler:
    def __init__(self, grid: WarehouseGrid, planner: SpaceTimeAStarPlanner):
        self.grid = grid
        self.planner = planner

    def resolve_deadlock(
        self,
        agents: List[Dict[str, any]],
        start_time: int = 0,
        failed_robot_id: Optional[int] = None,
    ) -> Tuple[Dict[int, List[Tuple[int, int]]], bool]:
        """
        Attempts to resolve deadlocks using multi-tiered strategies:
        Strategy 1: Priority Inversion (reverse planning order so blocked robot plans first).
        Strategy 2: Staggered Departure (lower priority robot delays start by waiting in place).
        Strategy 3: Yield to open cell (move lower priority robot to adjacent open bay).
        """
        # Strategy 1: Prioritize the failed robot
        if failed_robot_id is not None:
            reordered_agents = [a for a in agents if a['id'] == failed_robot_id] + \
                               [a for a in agents if a['id'] != failed_robot_id]
            paths, success = self._try_plan_sequence(reordered_agents, start_time)
            if success:
                return paths, True

        # Strategy 2: Reverse priority order completely
        reversed_agents = list(reversed(agents))
        paths, success = self._try_plan_sequence(reversed_agents, start_time)
        if success:
            return paths, True

        # Strategy 3: Delay/staggered wait for lower priority agents
        for delay in [2, 4, 6]:
            res = self._try_staggered_starts(agents, start_time, delay)
            if res[1]:
                return res

        # Strategy 4: Yielding to open bay/neighbor
        return self._try_evasive_yield(agents, start_time)

    def _try_plan_sequence(
        self,
        agents: List[Dict[str, any]],
        start_time: int,
    ) -> Tuple[Dict[int, List[Tuple[int, int]]], bool]:
        """Runs standard prioritized planning on given agent order."""
        table = ReservationTable()
        planner = SpaceTimeAStarPlanner(self.grid, table)
        paths: Dict[int, List[Tuple[int, int]]] = {}

        for a in agents:
            r_id = a['id']
            path = planner.plan(a['start'], a['goal'], start_time=start_time, robot_id=r_id)
            if path is None:
                return {}, False
            paths[r_id] = path
            table.reserve_path(path, robot_id=r_id, start_time=start_time)

        return paths, True

    def _try_staggered_starts(
        self,
        agents: List[Dict[str, any]],
        start_time: int,
        wait_steps: int,
    ) -> Tuple[Dict[int, List[Tuple[int, int]]], bool]:
        """Higher priority moves immediately; lower priority waits in place before moving."""
        table = ReservationTable()
        planner = SpaceTimeAStarPlanner(self.grid, table)
        paths: Dict[int, List[Tuple[int, int]]] = {}

        for i, a in enumerate(agents):
            r_id = a['id']
            agent_delay = i * wait_steps
            actual_start_time = start_time + agent_delay

            # Initial wait path while parked at start
            prefix = [a['start']] * agent_delay

            # Temporarily reserve the start position during wait
            for dt in range(agent_delay):
                table.reserve_vertex(a['start'][0], a['start'][1], start_time + dt, robot_id=r_id)

            path = planner.plan(a['start'], a['goal'], start_time=actual_start_time, robot_id=r_id)
            if path is None:
                return {}, False

            full_path = prefix + path
            paths[r_id] = full_path
            table.reserve_path(full_path, robot_id=r_id, start_time=start_time)

        return paths, True

    def _try_evasive_yield(
        self,
        agents: List[Dict[str, any]],
        start_time: int,
    ) -> Tuple[Dict[int, List[Tuple[int, int]]], bool]:
        """
        If an agent is trapped, find an open neighbor cell to yield to before heading to goal.
        """
        if not agents:
            return {}, False

        primary = agents[0]
        secondary = agents[1] if len(agents) > 1 else None

        if secondary is None:
            return {}, False

        # Plan primary first
        table = ReservationTable()
        planner = SpaceTimeAStarPlanner(self.grid, table)
        p_path = planner.plan(primary['start'], primary['goal'], start_time=start_time, robot_id=primary['id'])
        if p_path is None:
            return {}, False

        table.reserve_path(p_path, robot_id=primary['id'], start_time=start_time)

        # For secondary, test yielding to adjacent walkable cells not in primary's path
        primary_cells = set(p_path)
        sec_neighbors = self.grid.get_neighbors(secondary['start'][0], secondary['start'][1])
        yield_candidates = [n for n in sec_neighbors if n not in primary_cells]

        for y_spot in yield_candidates:
            # Plan secondary: start -> yield_spot -> wait 3 steps -> goal
            path1 = planner.plan(secondary['start'], y_spot, start_time=start_time, robot_id=secondary['id'])
            if path1 is not None:
                t_yield = start_time + len(path1) - 1
                wait_len = 3
                wait_segment = [y_spot] * wait_len
                t_resume = t_yield + wait_len

                # Temporarily reserve
                for dt in range(len(path1)):
                    table.reserve_vertex(path1[dt][0], path1[dt][1], start_time + dt, robot_id=secondary['id'])
                for dt in range(wait_len):
                    table.reserve_vertex(y_spot[0], y_spot[1], t_yield + 1 + dt, robot_id=secondary['id'])

                path2 = planner.plan(y_spot, secondary['goal'], start_time=t_resume, robot_id=secondary['id'])
                if path2 is not None:
                    full_sec_path = path1 + wait_segment[1:] + path2[1:]
                    table.reserve_path(full_sec_path, robot_id=secondary['id'], start_time=start_time)
                    return {primary['id']: p_path, secondary['id']: full_sec_path}, True

        return {}, False
