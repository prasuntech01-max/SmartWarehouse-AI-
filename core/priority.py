"""Priority Management and Sequential Multi-Robot Path Planning.

Integrates:
- Module 4 (core.state): TimeExpandedPlanner and Trajectory
- Module 5 (core.conflict): MultiRobotConflictDetector and ConflictReport
- Module 6 (core.reservation): ReservationTable
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Union
import copy
from warehouse import Warehouse
from core.reservation import ReservationTable
from core.state import TimeExpandedPlanner, Trajectory, Action, TimeExpandedState
from core.conflict import MultiRobotConflictDetector, ConflictReport


class PriorityScheme(str, Enum):
    """Strategies for ordering multi-robot planning priority."""
    MANUAL = "manual"
    ID_ASCENDING = "id_ascending"
    LONGEST_PATH_FIRST = "longest_path_first"
    SHORTEST_PATH_FIRST = "shortest_path_first"


class PriorityManager:
    """Manages robot priorities, dynamic reordering, and priority inversions."""

    def __init__(self, priorities: Optional[List[int]] = None):
        self._priority_list: List[int] = list(priorities) if priorities is not None else []

    @property
    def priority_list(self) -> List[int]:
        return list(self._priority_list)

    def set_priorities(self, priorities: List[int]) -> None:
        """Sets explicit priority order (first element = highest priority)."""
        self._priority_list = list(priorities)

    def get_rank(self, robot_id: int) -> int:
        """Returns priority rank (0 is highest). Lower index = higher priority."""
        if robot_id in self._priority_list:
            return self._priority_list.index(robot_id)
        return 999999

    def sort_robots(
        self,
        agents: List[Dict[str, Any]],
        scheme: PriorityScheme = PriorityScheme.MANUAL,
    ) -> List[Dict[str, Any]]:
        """
        Sorts agent definitions according to selected priority scheme.
        Agents format: [{'id': int, 'start': (x,y), 'goal': (x,y)}, ...]
        """
        if scheme == PriorityScheme.MANUAL:
            if not self._priority_list:
                return list(agents)
            p_map = {r_id: idx for idx, r_id in enumerate(self._priority_list)}
            return sorted(agents, key=lambda a: p_map.get(a['id'], 999999))

        elif scheme == PriorityScheme.ID_ASCENDING:
            return sorted(agents, key=lambda a: a['id'])

        elif scheme == PriorityScheme.LONGEST_PATH_FIRST:
            # Longest Manhattan distance first
            def dist(a):
                s, g = a['start'], a['goal']
                return abs(s[0] - g[0]) + abs(s[1] - g[1])
            return sorted(agents, key=dist, reverse=True)

        elif scheme == PriorityScheme.SHORTEST_PATH_FIRST:
            def dist(a):
                s, g = a['start'], a['goal']
                return abs(s[0] - g[0]) + abs(s[1] - g[1])
            return sorted(agents, key=dist)

        return list(agents)

    def invert_priority(self, robot_a: int, robot_b: int) -> List[int]:
        """Swaps priority ranks between two robots to resolve deadlocks."""
        if robot_a in self._priority_list and robot_b in self._priority_list:
            idx_a = self._priority_list.index(robot_a)
            idx_b = self._priority_list.index(robot_b)
            self._priority_list[idx_a], self._priority_list[idx_b] = (
                self._priority_list[idx_b],
                self._priority_list[idx_a],
            )
        return self.priority_list

    def elevate_to_top(self, robot_id: int) -> List[int]:
        """Promotes a robot to highest priority rank."""
        if robot_id in self._priority_list:
            self._priority_list.remove(robot_id)
        self._priority_list.insert(0, robot_id)
        return self.priority_list


class PriorityPlanner:
    """Sequential Multi-Robot Path Planner utilizing Reservation Tables and Priority Management."""

    def __init__(
        self,
        warehouse: Warehouse,
        reservation_table: Optional[ReservationTable] = None,
    ):
        self.warehouse = warehouse
        self.reservation_table = reservation_table or ReservationTable()
        self.planner = TimeExpandedPlanner(self.warehouse, self.reservation_table)
        self.detector = MultiRobotConflictDetector(warehouse=self.warehouse)
        self.priority_manager = PriorityManager()

    def plan_sequential(
        self,
        agents: List[Dict[str, Any]],
        start_time: int = 0,
        priorities: Optional[List[int]] = None,
        scheme: PriorityScheme = PriorityScheme.MANUAL,
        clear_table: bool = True,
    ) -> Tuple[Dict[int, Trajectory], bool, List[ConflictReport]]:
        """
        Sequentially plans paths for all agents in priority order:
        - Higher priority robots plan first and reserve space-time cells/edges.
        - Lower priority robots plan around reserved cells, automatically waiting or detouring.
        - Validates resulting fleet trajectories using MultiRobotConflictDetector.
        
        Returns:
            (paths, success, conflicts)
        """
        if clear_table:
            self.reservation_table.clear()

        if priorities is not None:
            self.priority_manager.set_priorities(priorities)
        else:
            self.priority_manager.set_priorities([a['id'] for a in agents])

        ordered_agents = self.priority_manager.sort_robots(agents, scheme=scheme)

        paths: Dict[int, Trajectory] = {}
        all_succeeded = True

        for agent in ordered_agents:
            r_id = agent['id']
            start = agent['start']
            goal = agent['goal']
            st = agent.get('start_time', start_time)

            traj = self.planner.plan(
                start=start,
                goal=goal,
                start_time=st,
                robot_id=r_id,
            )

            if traj is None:
                all_succeeded = False
                # Fallback: stationary trajectory holding start position
                fallback_state = TimeExpandedState(start[0], start[1], st)
                traj = Trajectory([fallback_state], [])
                paths[r_id] = traj
                self.reservation_table.reserve_vertex(start[0], start[1], st, robot_id=r_id)
            else:
                paths[r_id] = traj
                self.reservation_table.reserve_path(traj, robot_id=r_id, start_time=st)

        # Formal verification via Module 5
        conflicts = self.detector.detect_conflicts(paths)

        return paths, all_succeeded, conflicts

    def replan_robot(
        self,
        robot_id: int,
        current_pos: Tuple[int, int],
        goal: Tuple[int, int],
        current_time: int,
        hold_at_goal: int = 5,
    ) -> Optional[Trajectory]:
        """
        Safely replans a single robot's path from current_pos to goal starting at current_time:
        - Takes an atomic reservation snapshot for rollback protection.
        - Releases future reservations for this robot.
        - Replans respecting all other robots' existing reservations.
        - Commits new reservations upon success, or rolls back upon failure.
        """
        snapshot = self.reservation_table.snapshot()

        # Release future reservations for this robot
        self.reservation_table.release_future_reservations(robot_id, from_time=current_time)

        try:
            new_traj = self.planner.plan(
                start=current_pos,
                goal=goal,
                start_time=current_time,
                robot_id=robot_id,
                hold_at_goal=hold_at_goal,
            )
        except (ValueError, TypeError):
            self.reservation_table.restore(snapshot)
            return None

        if new_traj is not None:
            # Commit new reservations
            self.reservation_table.reserve_path(
                new_traj,
                robot_id=robot_id,
                start_time=current_time,
            )
            return new_traj
        else:
            # Rollback to snapshot
            self.reservation_table.restore(snapshot)
            return None
