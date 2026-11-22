"""Multi-Robot Conflict Detection Module for warehouse path planning.

Reuses TimeExpandedState and Action from Module 4 (core.state).
Detects:
1. Vertex collisions: two robots occupying the same cell at time t.
2. Edge-swap collisions: two robots exchanging positions at time t -> t+1.
3. Opposite-direction corridor conflicts: robots moving towards each other in narrow aisles.
4. Same-direction corridor conflicts: trailing robot rear-ending or entering unvacated corridor cells.
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Union, Set
from dataclasses import dataclass, field

from core.state import TimeExpandedState, Action, Trajectory
from warehouse import Warehouse


class ConflictType(str, Enum):
    """Types of multi-robot spatial-temporal conflicts."""
    VERTEX = "vertex"
    EDGE_SWAP = "edge"
    CORRIDOR_OPPOSITE = "corridor_opposite"
    CORRIDOR_SAME_DIRECTION = "corridor_same_direction"


@dataclass(frozen=True)
class ConflictReport:
    """Structured report detailing a detected multi-robot conflict."""
    conflict_type: ConflictType
    robot_a: int
    robot_b: int
    time_step: int
    location_a: Tuple[int, int]
    location_b: Tuple[int, int]
    next_location_a: Optional[Tuple[int, int]] = None
    next_location_b: Optional[Tuple[int, int]] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert conflict report to JSON/serializable dictionary."""
        return {
            "conflict_type": self.conflict_type.value,
            "robot_a": self.robot_a,
            "robot_b": self.robot_b,
            "time_step": self.time_step,
            "location_a": self.location_a,
            "location_b": self.location_b,
            "next_location_a": self.next_location_a,
            "next_location_b": self.next_location_b,
            "description": self.description,
        }

    def to_reservation_constraint(self) -> Dict[str, Any]:
        """
        Formats conflict for reservation table blocking in Module 6.
        Returns the vertex/edge constraint needed to prevent the collision.
        """
        if self.conflict_type in (ConflictType.VERTEX, ConflictType.CORRIDOR_SAME_DIRECTION):
            return {
                "constraint_type": "vertex",
                "pos": self.location_a,
                "time_step": self.time_step,
                "conflicting_robots": (self.robot_a, self.robot_b),
            }
        elif self.conflict_type in (ConflictType.EDGE_SWAP, ConflictType.CORRIDOR_OPPOSITE):
            return {
                "constraint_type": "edge",
                "u": self.location_a,
                "v": self.next_location_a,
                "time_step": self.time_step,
                "conflicting_robots": (self.robot_a, self.robot_b),
            }
        else:
            return {
                "constraint_type": "vertex",
                "pos": self.location_a,
                "time_step": self.time_step,
                "conflicting_robots": (self.robot_a, self.robot_b),
            }


class MultiRobotConflictDetector:
    """Exhaustive conflict detection engine across space and time."""

    def __init__(self, warehouse: Optional[Warehouse] = None):
        self.warehouse = warehouse

    @staticmethod
    def normalize_trajectory(
        path: Union[Trajectory, List[TimeExpandedState], List[Tuple[int, int]]],
        start_time: int = 0,
    ) -> List[TimeExpandedState]:
        """
        Normalizes any input path into a list of TimeExpandedState (x, y, t).
        Validates trajectory integrity and rejects invalid jumps or non-coordinates.
        """
        if not path:
            return []

        # Handle Trajectory instance
        if isinstance(path, Trajectory):
            return list(path.states)

        states: List[TimeExpandedState] = []
        for i, item in enumerate(path):
            if isinstance(item, TimeExpandedState):
                states.append(item)
            elif isinstance(item, (tuple, list)) and len(item) == 2:
                states.append(TimeExpandedState(int(item[0]), int(item[1]), start_time + i))
            elif isinstance(item, (tuple, list)) and len(item) == 3:
                states.append(TimeExpandedState(int(item[0]), int(item[1]), int(item[2])))
            else:
                raise TypeError(f"Invalid path item at index {i}: {item}. Expected (x, y) or TimeExpandedState.")

        # Validate temporal and spatial continuity
        for i in range(len(states) - 1):
            curr, nxt = states[i], states[i + 1]
            if nxt.t != curr.t + 1:
                raise ValueError(
                    f"Trajectory temporal discontinuity at index {i}: time jumps from {curr.t} to {nxt.t}"
                )
            dist = abs(nxt.x - curr.x) + abs(nxt.y - curr.y)
            if dist > 1:
                raise ValueError(
                    f"Trajectory spatial jump at index {i}: moved from ({curr.x}, {curr.y}) to ({nxt.x}, {nxt.y}) (Manhattan distance {dist} > 1)"
                )

        return states

    def is_corridor_cell(self, x: int, y: int) -> bool:
        """
        Identifies whether cell (x, y) is part of a narrow corridor
        (i.e., bounded on two opposing sides by shelves, walls, or grid boundaries).
        """
        if self.warehouse is None:
            return False
        if not self.warehouse.is_walkable(x, y):
            return False

        # Vertical corridor: blocked left (x-1) and right (x+1)
        left_blocked = not self.warehouse.is_walkable(x - 1, y)
        right_blocked = not self.warehouse.is_walkable(x + 1, y)
        if left_blocked and right_blocked:
            return True

        # Horizontal corridor: blocked top (y-1) and bottom (y+1)
        top_blocked = not self.warehouse.is_walkable(x, y - 1)
        bottom_blocked = not self.warehouse.is_walkable(x, y + 1)
        if top_blocked and bottom_blocked:
            return True

        return False

    def detect_conflicts(
        self,
        paths: Dict[int, Union[Trajectory, List[TimeExpandedState], List[Tuple[int, int]]]],
        start_times: Optional[Dict[int, int]] = None,
        park_at_goal: bool = True,
    ) -> List[ConflictReport]:
        """
        Exhaustively scans robot trajectories to detect:
        - Vertex collisions
        - Edge-swap collisions
        - Opposite-direction corridor conflicts
        - Same-direction corridor collisions
        """
        conflicts: List[ConflictReport] = []
        robot_ids = sorted(list(paths.keys()))
        if len(robot_ids) < 2:
            return conflicts

        if start_times is None:
            start_times = {r_id: 0 for r_id in robot_ids}

        # Normalize trajectories to TimeExpandedState
        normalized_paths: Dict[int, List[TimeExpandedState]] = {}
        for r_id in robot_ids:
            st = start_times.get(r_id, 0)
            normalized_paths[r_id] = self.normalize_trajectory(paths[r_id], start_time=st)

        # Build time-indexed position lookup: pos_at[robot_id][t] -> (x, y)
        pos_at: Dict[int, Dict[int, Tuple[int, int]]] = {r_id: {} for r_id in robot_ids}
        max_horizon = 0

        for r_id, states in normalized_paths.items():
            for s in states:
                pos_at[r_id][s.t] = s.pos
                if s.t > max_horizon:
                    max_horizon = s.t

        # If park_at_goal is True, extend final position across time horizon
        if park_at_goal:
            for r_id, states in normalized_paths.items():
                if states:
                    last_s = states[-1]
                    for t in range(last_s.t + 1, max_horizon + 1):
                        pos_at[r_id][t] = last_s.pos

        # Pairwise scan at each timestep
        for t in range(max_horizon + 1):
            for i in range(len(robot_ids)):
                r1 = robot_ids[i]
                p1_curr = pos_at[r1].get(t)
                p1_next = pos_at[r1].get(t + 1)
                p1_prev = pos_at[r1].get(t - 1)

                if p1_curr is None:
                    continue

                for j in range(i + 1, len(robot_ids)):
                    r2 = robot_ids[j]
                    p2_curr = pos_at[r2].get(t)
                    p2_next = pos_at[r2].get(t + 1)
                    p2_prev = pos_at[r2].get(t - 1)

                    if p2_curr is None:
                        continue

                    # 1. VERTEX / CORRIDOR-SAME-DIRECTION COLLISION at time t
                    if p1_curr == p2_curr:
                        is_corridor = self.is_corridor_cell(p1_curr[0], p1_curr[1])
                        # Check if both robots moved in same direction into this cell
                        same_direction = False
                        if p1_prev is not None and p2_prev is not None:
                            d1 = (p1_curr[0] - p1_prev[0], p1_curr[1] - p1_prev[1])
                            d2 = (p2_curr[0] - p2_prev[0], p2_curr[1] - p2_prev[1])
                            if d1 == d2 and d1 != (0, 0):
                                same_direction = True

                        if is_corridor and same_direction:
                            conflicts.append(ConflictReport(
                                conflict_type=ConflictType.CORRIDOR_SAME_DIRECTION,
                                robot_a=r1,
                                robot_b=r2,
                                time_step=t,
                                location_a=p1_curr,
                                location_b=p2_curr,
                                next_location_a=p1_next,
                                next_location_b=p2_next,
                                description=f"Corridor same-direction conflict: Robot {r1} and Robot {r2} collided at corridor cell {p1_curr} at t={t}",
                            ))
                        else:
                            conflicts.append(ConflictReport(
                                conflict_type=ConflictType.VERTEX,
                                robot_a=r1,
                                robot_b=r2,
                                time_step=t,
                                location_a=p1_curr,
                                location_b=p2_curr,
                                next_location_a=p1_next,
                                next_location_b=p2_next,
                                description=f"Vertex collision: Robot {r1} and Robot {r2} occupy cell {p1_curr} simultaneously at t={t}",
                            ))
                        continue

                    # 2. EDGE-SWAP / CORRIDOR-OPPOSITE COLLISION at time t -> t+1
                    if p1_next is not None and p2_next is not None:
                        if p1_curr == p2_next and p1_next == p2_curr and p1_curr != p1_next:
                            is_corridor = (
                                self.is_corridor_cell(p1_curr[0], p1_curr[1])
                                or self.is_corridor_cell(p1_next[0], p1_next[1])
                            )
                            c_type = ConflictType.CORRIDOR_OPPOSITE if is_corridor else ConflictType.EDGE_SWAP
                            desc = (
                                f"Corridor opposite-direction conflict: Robot {r1} moving {p1_curr}->{p1_next} "
                                f"swaps with Robot {r2} moving {p2_curr}->{p2_next} at t={t}"
                                if is_corridor
                                else f"Edge-swap collision: Robot {r1} moving {p1_curr}->{p1_next} "
                                     f"swaps with Robot {r2} moving {p2_curr}->{p2_next} at t={t}"
                            )
                            conflicts.append(ConflictReport(
                                conflict_type=c_type,
                                robot_a=r1,
                                robot_b=r2,
                                time_step=t,
                                location_a=p1_curr,
                                location_b=p2_curr,
                                next_location_a=p1_next,
                                next_location_b=p2_next,
                                description=desc,
                            ))

        return conflicts
