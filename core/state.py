"""Time-Expanded State Space and Action models for multi-robot path planning.

Defines:
- Action: Up, Down, Left, Right, Wait
- TimeExpandedState: (x, y, t) state with formal transition validation
- Trajectory: Time-indexed trajectory containing states, coordinates, and actions
- TimeExpandedPlanner: Space-time A* planner in (x, y, t) state space
"""

from enum import Enum
from typing import Tuple, List, Optional, Dict, Set, Iterator
from dataclasses import dataclass, field
import heapq
import time

from warehouse import Warehouse
from core.reservation import ReservationTable


class Action(Enum):
    """Discrete navigation actions available to warehouse robots."""
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    WAIT = (0, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @classmethod
    def from_delta(cls, dx: int, dy: int) -> "Action":
        """Get Action enum corresponding to a coordinate delta."""
        for action in cls:
            if action.value == (dx, dy):
                return action
        raise ValueError(f"Invalid movement delta ({dx}, {dy}); diagonal or multi-step transitions are prohibited")


@dataclass(frozen=True, slots=True)
class TimeExpandedState:
    """State in the time-expanded space-time graph: (x, y, t)."""
    x: int
    y: int
    t: int

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.x, self.y)

    @property
    def as_tuple(self) -> Tuple[int, int, int]:
        return (self.x, self.y, self.t)

    def transition(self, action: Action) -> "TimeExpandedState":
        """Apply an action to produce the next state at time t + 1."""
        return TimeExpandedState(
            x=self.x + action.dx,
            y=self.y + action.dy,
            t=self.t + 1,
        )

    def is_valid_successor(self, next_state: "TimeExpandedState") -> bool:
        """
        Validates transition rules:
        1. Time must increment strictly by 1 (t -> t + 1).
        2. Movement must be Manhattan distance <= 1 (no diagonals or teleportation).
        """
        if next_state.t != self.t + 1:
            return False
        dist = abs(next_state.x - self.x) + abs(next_state.y - self.y)
        return dist <= 1


class Trajectory:
    """
    Time-indexed trajectory result providing dual interface:
    - Acts as a list of (x, y) coordinates for backward compatibility.
    - Exposes states (x, y, t), actions taken, and makespan.
    """

    def __init__(self, states: List[TimeExpandedState], actions: Optional[List[Action]] = None):
        self.states = list(states)
        self.coords = [s.pos for s in self.states]
        if actions is None:
            self.actions: List[Action] = []
            for i in range(len(self.states) - 1):
                dx = self.states[i + 1].x - self.states[i].x
                dy = self.states[i + 1].y - self.states[i].y
                self.actions.append(Action.from_delta(dx, dy))
        else:
            self.actions = list(actions)

    def __len__(self) -> int:
        return len(self.coords)

    def __getitem__(self, index):
        return self.coords[index]

    def __iter__(self) -> Iterator[Tuple[int, int]]:
        return iter(self.coords)

    def __eq__(self, other) -> bool:
        if isinstance(other, Trajectory):
            return self.coords == other.coords
        if isinstance(other, (list, tuple)):
            return self.coords == list(other)
        return False

    def __repr__(self) -> str:
        return f"Trajectory(length={len(self.coords)}, start={self.coords[0] if self.coords else None}, end={self.coords[-1] if self.coords else None})"

    @property
    def makespan(self) -> int:
        """Total elapsed timesteps of this trajectory."""
        return len(self.states) - 1 if self.states else 0

    @property
    def wait_count(self) -> int:
        """Number of Wait actions performed along trajectory."""
        return sum(1 for a in self.actions if a == Action.WAIT)


class TimeExpandedPlanner:
    """A* Planner operating across time-expanded state space (x, y, t)."""

    def __init__(self, warehouse: Warehouse, reservation_table: Optional[ReservationTable] = None):
        if warehouse is None:
            raise ValueError("Warehouse instance must be provided")
        self.warehouse = warehouse
        self.reservation_table = reservation_table

    @staticmethod
    def manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
        """Admissible Manhattan distance heuristic."""
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _validate_endpoints(self, start: Tuple[int, int], goal: Tuple[int, int], start_time: int) -> None:
        """Validates start, goal, and initial time parameters."""
        if start_time < 0:
            raise ValueError(f"start_time cannot be negative, got {start_time}")
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

    def get_valid_transitions(
        self,
        current_state: TimeExpandedState,
        robot_id: int = 0,
    ) -> List[Tuple[Action, TimeExpandedState]]:
        """
        Generates all valid (Action, TimeExpandedState) transitions from current state:
        - Evaluates Up, Down, Left, Right, Wait
        - Checks grid boundary
        - Checks static obstacles (shelves) and dynamic obstacles
        - Checks time-indexed reservation constraints (vertex & edge-swap)
        """
        valid_transitions: List[Tuple[Action, TimeExpandedState]] = []

        for action in Action:
            next_state = current_state.transition(action)
            nx, ny, nt = next_state.x, next_state.y, next_state.t

            # 1. Boundary check
            if not self.warehouse.in_bounds(nx, ny):
                continue

            # 2. Obstacle check (shelves & dynamic obstacles)
            if not self.warehouse.is_walkable(nx, ny):
                continue

            # 3. Reservation table conflict check
            if self.reservation_table is not None:
                if not self.reservation_table.is_action_valid(
                    u=(current_state.x, current_state.y),
                    v=(nx, ny),
                    t=current_state.t,
                    ignore_robot=robot_id,
                ):
                    continue

            valid_transitions.append((action, next_state))

        return valid_transitions

    def plan(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        start_time: int = 0,
        robot_id: int = 0,
        max_horizon: int = 200,
        hold_at_goal: int = 5,
        raise_on_failure: bool = False,
    ) -> Optional[Trajectory]:
        """
        Finds the optimal collision-free time-expanded trajectory from start to goal.
        """
        self._validate_endpoints(start, goal, start_time)
        start_pos = (int(start[0]), int(start[1]))
        goal_pos = (int(goal[0]), int(goal[1]))

        initial_state = TimeExpandedState(start_pos[0], start_pos[1], start_time)

        if start_pos == goal_pos:
            return Trajectory([initial_state], [])

        # Priority queue stores: (f_score, h_score, state_id, TimeExpandedState)
        open_set: List[Tuple[float, int, int, TimeExpandedState]] = []
        h_start = self.manhattan_distance(start_pos, goal_pos)
        counter = 0
        heapq.heappush(open_set, (float(h_start), h_start, counter, initial_state))

        came_from: Dict[TimeExpandedState, Tuple[TimeExpandedState, Action]] = {}
        g_score: Dict[TimeExpandedState, int] = {initial_state: 0}
        closed_set: Set[TimeExpandedState] = set()

        while open_set:
            _, _, _, current_state = heapq.heappop(open_set)

            if current_state in closed_set:
                continue
            closed_set.add(current_state)

            # Reached spatial goal
            if current_state.pos == goal_pos:
                # Goal safety check: cell must remain free of incoming collisions for hold_at_goal steps
                safe_at_goal = True
                if self.reservation_table is not None:
                    for dt in range(1, hold_at_goal + 1):
                        if self.reservation_table.is_vertex_reserved(
                            goal_pos[0], goal_pos[1], current_state.t + dt, ignore_robot=robot_id
                        ):
                            safe_at_goal = False
                            break

                if safe_at_goal:
                    # Reconstruct path and actions
                    states: List[TimeExpandedState] = []
                    actions: List[Action] = []
                    curr = current_state
                    while curr in came_from:
                        prev_state, action = came_from[curr]
                        states.append(curr)
                        actions.append(action)
                        curr = prev_state
                    states.append(initial_state)
                    states.reverse()
                    actions.reverse()
                    return Trajectory(states, actions)

            # Horizon cutoff
            if current_state.t >= start_time + max_horizon:
                continue

            current_g = g_score[current_state]

            for action, next_state in self.get_valid_transitions(current_state, robot_id=robot_id):
                if next_state in closed_set:
                    continue

                # Transition step cost = 1
                tentative_g = current_g + 1

                if next_state not in g_score or tentative_g < g_score[next_state]:
                    came_from[next_state] = (current_state, action)
                    g_score[next_state] = tentative_g
                    h = self.manhattan_distance(next_state.pos, goal_pos)
                    # Tie-breaker: prefer forward motion over wait if costs are tied
                    wait_penalty = 0.001 if action == Action.WAIT else 0.0
                    f = tentative_g + h + wait_penalty
                    counter += 1
                    heapq.heappush(open_set, (float(f), h, counter, next_state))

        if raise_on_failure:
            from astar import PathNotFoundError
            raise PathNotFoundError(
                f"No time-expanded path found from {start_pos} to {goal_pos} within horizon {max_horizon}"
            )
        return None
