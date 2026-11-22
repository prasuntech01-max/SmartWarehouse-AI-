"""Space-Time Reservation Table for multi-robot collision avoidance.

Guarantees:
1. Vertex Collision Prevention: No two robots occupy cell (x, y) at time t.
2. Edge/Swap Collision Prevention: No two robots traverse edge (u, v) and (v, u) concurrently at time t.
3. Goal Reservation: When a robot finishes its path, it safely reserves its destination.
"""

from typing import Dict, Tuple, List, Optional, Set


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

    def is_edge_reserved(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        ignore_robot: Optional[int] = None,
    ) -> bool:
        """
        Check if traversing u -> v at time t causes an edge swap collision.
        Edge collision occurs if another robot is traversing v -> u at time t.
        """
        # Opposite direction traversal
        res_opposite = self.edge_reservations.get((v, u, t))
        if res_opposite is not None and res_opposite != ignore_robot:
            return True
        # Same directed edge conflict (two robots trying to step into same target along same vector)
        res_same = self.edge_reservations.get((u, v, t))
        if res_same is not None and res_same != ignore_robot:
            return True
        return False

    def is_action_valid(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        ignore_robot: Optional[int] = None,
    ) -> bool:
        """Returns True if moving from u at t to v at t+1 is free of vertex and edge conflicts."""
        # Check target vertex at t + 1
        if self.is_vertex_reserved(v[0], v[1], t + 1, ignore_robot=ignore_robot):
            return False
        # Check edge conflict
        if u != v and self.is_edge_reserved(u, v, t, ignore_robot=ignore_robot):
            return False
        return True

    def reserve_vertex(self, x: int, y: int, t: int, robot_id: int) -> None:
        """Directly reserve a vertex (x, y) at time t for robot_id."""
        self.vertex_reservations[(x, y, t)] = robot_id

    def reserve_edge(self, u: Tuple[int, int], v: Tuple[int, int], t: int, robot_id: int) -> None:
        """Directly reserve an edge traversal u -> v at time t for robot_id."""
        self.edge_reservations[(u, v, t)] = robot_id

    def reserve_path(
        self,
        path: List[Tuple[int, int]],
        robot_id: int,
        start_time: int = 0,
        stay_at_goal_until: Optional[int] = None,
    ) -> None:
        """
        Reserves space-time vertices and edges along the path.
        If stay_at_goal_until is set, reserves the final position up to that time step.
        """
        # Clear previous reservations for this robot
        self.clear_robot_reservations(robot_id)

        recorded_path: List[Tuple[int, int, int]] = []
        n = len(path)
        for i in range(n):
            t = start_time + i
            pos = path[i]
            self.vertex_reservations[(pos[0], pos[1], t)] = robot_id
            recorded_path.append((pos[0], pos[1], t))

            if i < n - 1:
                next_pos = path[i + 1]
                self.edge_reservations[(pos, next_pos, t)] = robot_id

        # Reserve parking/staying at goal
        if n > 0:
            final_pos = path[-1]
            end_t = start_time + n - 1
            horizon = stay_at_goal_until if stay_at_goal_until is not None else min(end_t + 25, self.max_horizon)
            for t in range(end_t + 1, horizon + 1):
                self.vertex_reservations[(final_pos[0], final_pos[1], t)] = robot_id
                recorded_path.append((final_pos[0], final_pos[1], t))

        self.robot_paths[robot_id] = recorded_path

    def clear_robot_reservations(self, robot_id: int) -> None:
        """Removes all vertex and edge reservations for a specific robot."""
        # Remove from vertex reservations
        v_keys = [k for k, v in self.vertex_reservations.items() if v == robot_id]
        for k in v_keys:
            del self.vertex_reservations[k]

        # Remove from edge reservations
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

    def get_robot_position_at(self, robot_id: int, t: int) -> Optional[Tuple[int, int]]:
        """Return position of robot at time t if known."""
        path = self.robot_paths.get(robot_id)
        if not path:
            return None
        for x, y, pt in path:
            if pt == t:
                return (x, y)
        # If past the path end, return final position
        if path and t >= path[-1][2]:
            return (path[-1][0], path[-1][1])
        return None
