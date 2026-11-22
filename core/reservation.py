"""Space-Time Reservation Table for multi-robot collision avoidance.

Guarantees:
1. Time-indexed vertex reservations (x, y, t).
2. Directed edge reservations ((u, v), t) preventing head-on and swap collisions.
3. Destination parking reservations: holds destination cell safely after arrival.
4. Atomic updates, safe release, and transaction rollback snapshots.
"""

from __future__ import annotations
from typing import Dict, Tuple, List, Optional, Set, Any, Union, TYPE_CHECKING
import copy

if TYPE_CHECKING:
    from core.state import TimeExpandedState, Trajectory


class ReservationTable:
    def __init__(self, max_horizon: int = 250):
        self.max_horizon = max_horizon
        # vertex_reservations: (x, y, t) -> robot_id
        self.vertex_reservations: Dict[Tuple[int, int, int], int] = {}
        # edge_reservations: ((u_x, u_y), (v_x, v_y), t) -> robot_id
        self.edge_reservations: Dict[Tuple[Tuple[int, int], Tuple[int, int], int], int] = {}
        # robot_paths: robot_id -> List[(x, y, t)]
        self.robot_paths: Dict[int, List[Tuple[int, int, int]]] = {}

    def is_vertex_reserved(self, x: int, y: int, t: int, ignore_robot: Optional[int] = None) -> bool:
        """Check if cell (x, y) is occupied at time t by another robot."""
        res = self.vertex_reservations.get((x, y, t))
        if res is not None and res != ignore_robot:
            return True
        return False

    def get_vertex_reservation(self, x: int, y: int, t: int) -> Optional[int]:
        """Returns the robot_id holding reservation at (x, y, t), or None."""
        return self.vertex_reservations.get((x, y, t))

    def is_edge_reserved(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        ignore_robot: Optional[int] = None,
    ) -> bool:
        """
        Check if traversing u -> v at time t causes an edge swap collision.
        An edge conflict occurs if another robot is traversing v -> u (opposite swap)
        or u -> v (same directed edge traversal) at the exact same timestep t.
        """
        # Opposite direction traversal (head-on swap collision)
        res_opposite = self.edge_reservations.get((v, u, t))
        if res_opposite is not None and res_opposite != ignore_robot:
            return True
        # Same directed edge conflict
        res_same = self.edge_reservations.get((u, v, t))
        if res_same is not None and res_same != ignore_robot:
            return True
        return False

    def get_edge_reservation(self, u: Tuple[int, int], v: Tuple[int, int], t: int) -> Optional[int]:
        """Returns the robot_id holding edge reservation (u -> v, t), or None."""
        return self.edge_reservations.get((u, v, t))

    def is_action_valid(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        ignore_robot: Optional[int] = None,
    ) -> bool:
        """Returns True if moving from u at t to v at t+1 is free of vertex and edge conflicts."""
        # 1. Target vertex at t + 1 must be free
        if self.is_vertex_reserved(v[0], v[1], t + 1, ignore_robot=ignore_robot):
            return False
        # 2. Edge traversal u -> v at t must be free of opposing/duplicate traversals
        if u != v and self.is_edge_reserved(u, v, t, ignore_robot=ignore_robot):
            return False
        return True

    def reserve_vertex(self, x: int, y: int, t: int, robot_id: int) -> None:
        """Directly reserve a vertex (x, y) at time t for robot_id."""
        self.vertex_reservations[(x, y, t)] = robot_id

    def release_vertex(self, x: int, y: int, t: int, robot_id: Optional[int] = None) -> bool:
        """
        Safely releases a vertex reservation.
        If robot_id is provided, only releases if currently held by that robot.
        """
        key = (x, y, t)
        if key in self.vertex_reservations:
            if robot_id is None or self.vertex_reservations[key] == robot_id:
                del self.vertex_reservations[key]
                return True
        return False

    def reserve_edge(self, u: Tuple[int, int], v: Tuple[int, int], t: int, robot_id: int) -> None:
        """Directly reserve an edge traversal u -> v at time t for robot_id."""
        self.edge_reservations[(u, v, t)] = robot_id

    def release_edge(self, u: Tuple[int, int], v: Tuple[int, int], t: int, robot_id: Optional[int] = None) -> bool:
        """
        Safely releases an edge reservation.
        If robot_id is provided, only releases if currently held by that robot.
        """
        key = (u, v, t)
        if key in self.edge_reservations:
            if robot_id is None or self.edge_reservations[key] == robot_id:
                del self.edge_reservations[key]
                return True
        return False

    def reserve_path(
        self,
        path: Union[Trajectory, List[TimeExpandedState], List[Tuple[int, int]]],
        robot_id: int,
        start_time: int = 0,
        stay_at_goal_until: Optional[int] = None,
    ) -> None:
        """
        Reserves space-time vertices and edges along the path.
        If stay_at_goal_until is set, reserves the final position up to that timestep.
        """
        # Clear previous reservations for this robot
        self.clear_robot_reservations(robot_id)

        # Normalize coordinates
        coords: List[Tuple[int, int]] = []
        if hasattr(path, "coords"):
            coords = path.coords
            start_t = path.states[0].t if hasattr(path, "states") and path.states else start_time
        elif path and hasattr(path[0], "pos"):
            coords = [s.pos for s in path]
            start_t = path[0].t
        else:
            coords = [p for p in path]  # type: ignore
            start_t = start_time

        recorded_path: List[Tuple[int, int, int]] = []
        n = len(coords)
        for i in range(n):
            t = start_t + i
            pos = coords[i]
            self.vertex_reservations[(pos[0], pos[1], t)] = robot_id
            recorded_path.append((pos[0], pos[1], t))

            if i < n - 1:
                next_pos = coords[i + 1]
                if pos != next_pos:
                    self.edge_reservations[(pos, next_pos, t)] = robot_id

        # Reserve parking/staying at goal
        if n > 0:
            final_pos = coords[-1]
            end_t = start_t + n - 1
            horizon = stay_at_goal_until if stay_at_goal_until is not None else min(end_t + 25, self.max_horizon)
            for t in range(end_t + 1, horizon + 1):
                self.vertex_reservations[(final_pos[0], final_pos[1], t)] = robot_id
                recorded_path.append((final_pos[0], final_pos[1], t))

        self.robot_paths[robot_id] = recorded_path

    def release_future_reservations(self, robot_id: int, from_time: int) -> int:
        """
        Safely removes all vertex and edge reservations for robot_id from from_time onwards.
        Preserves past reservations to maintain historic conflict avoidance.
        """
        count = 0
        v_keys = [k for k, v in self.vertex_reservations.items() if v == robot_id and k[2] >= from_time]
        for k in v_keys:
            del self.vertex_reservations[k]
            count += 1

        e_keys = [k for k, v in self.edge_reservations.items() if v == robot_id and k[2] >= from_time]
        for k in e_keys:
            del self.edge_reservations[k]
            count += 1

        # Truncate robot_path
        if robot_id in self.robot_paths:
            self.robot_paths[robot_id] = [p for p in self.robot_paths[robot_id] if p[2] < from_time]

        return count

    def clear_robot_reservations(self, robot_id: int) -> None:
        """Removes all vertex and edge reservations for a specific robot."""
        v_keys = [k for k, v in self.vertex_reservations.items() if v == robot_id]
        for k in v_keys:
            del self.vertex_reservations[k]

        e_keys = [k for k, v in self.edge_reservations.items() if v == robot_id]
        for k in e_keys:
            del self.edge_reservations[k]

        if robot_id in self.robot_paths:
            del self.robot_paths[robot_id]

    def clear(self) -> None:
        """Clears all reservations."""
        self.vertex_reservations.clear()
        self.edge_reservations.clear()
        self.robot_paths.clear()

    def snapshot(self) -> Dict[str, Any]:
        """Creates a snapshot for transactional rollback."""
        return {
            "vertex_reservations": dict(self.vertex_reservations),
            "edge_reservations": dict(self.edge_reservations),
            "robot_paths": {r: list(p) for r, p in self.robot_paths.items()},
        }

    def restore(self, snap: Dict[str, Any]) -> None:
        """Restores state from a snapshot."""
        self.vertex_reservations = dict(snap["vertex_reservations"])
        self.edge_reservations = dict(snap["edge_reservations"])
        self.robot_paths = {r: list(p) for r, p in snap["robot_paths"].items()}

    def get_robot_position_at(self, robot_id: int, t: int) -> Optional[Tuple[int, int]]:
        """Return position of robot at time t if known."""
        path = self.robot_paths.get(robot_id)
        if not path:
            return None
        for x, y, pt in path:
            if pt == t:
                return (x, y)
        if path and t >= path[-1][2]:
            return (path[-1][0], path[-1][1])
        return None
