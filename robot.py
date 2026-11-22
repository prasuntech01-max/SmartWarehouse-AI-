"""Autonomous Mobile Robot (AMR) entity for the warehouse."""

from enum import Enum
from typing import Tuple, List, Optional, Any


class RobotStatus(Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class Robot:
    """Represents an autonomous warehouse robot navigating the grid."""

    def __init__(
        self,
        robot_id: int,
        start_pos: Tuple[int, int],
        home_dock: Optional[Tuple[int, int]] = None,
        battery: float = 100.0,
    ):
        if not (isinstance(start_pos, (tuple, list)) and len(start_pos) == 2):
            raise TypeError("start_pos must be a coordinate tuple (x, y)")
        self.robot_id = robot_id
        self.pos: Tuple[int, int] = (int(start_pos[0]), int(start_pos[1]))
        self.home_dock: Tuple[int, int] = home_dock if home_dock is not None else self.pos
        self.battery: float = max(0.0, min(100.0, battery))

        self.goal: Optional[Tuple[int, int]] = None
        self.path: List[Tuple[int, int]] = []
        self.path_index: int = 0
        self.status: RobotStatus = RobotStatus.IDLE
        self.trail: List[Tuple[int, int]] = [self.pos]
        self.assigned_task: Optional[Any] = None

    def set_goal(self, goal: Tuple[int, int]) -> None:
        """Assign destination goal coordinate."""
        if not (isinstance(goal, (tuple, list)) and len(goal) == 2):
            raise TypeError("goal must be a coordinate tuple (x, y)")
        self.goal = (int(goal[0]), int(goal[1]))
        if self.pos == self.goal:
            self.status = RobotStatus.COMPLETED
        else:
            self.status = RobotStatus.WAITING

    def set_path(self, path: List[Tuple[int, int]]) -> None:
        """Assign planned trajectory."""
        if not path:
            raise ValueError("Path cannot be empty")
        if path[0] != self.pos:
            raise ValueError(f"Path must start at robot current position {self.pos}, got {path[0]}")
        self.path = list(path)
        self.path_index = 0
        if len(self.path) > 1:
            self.status = RobotStatus.MOVING
        else:
            self.status = RobotStatus.IDLE

    def step(self) -> Tuple[int, int]:
        """
        Advance one step along current path.
        Returns the new position.
        """
        if self.path and self.path_index < len(self.path) - 1:
            self.path_index += 1
            next_pos = self.path[self.path_index]
            self.pos = next_pos
            self.trail.append(self.pos)
            if len(self.trail) > 10:
                self.trail.pop(0)

            # Deduct battery slightly on movement
            self.battery = max(0.0, self.battery - 0.1)

            if self.is_at_goal():
                self.status = RobotStatus.COMPLETED
            else:
                self.status = RobotStatus.MOVING
        else:
            if self.is_at_goal():
                self.status = RobotStatus.COMPLETED
            else:
                self.status = RobotStatus.IDLE

        return self.pos

    def is_at_goal(self) -> bool:
        """Checks if current position matches goal."""
        return self.goal is not None and self.pos == self.goal

    def reset(self, pos: Optional[Tuple[int, int]] = None) -> None:
        """Reset robot to home dock or specified position."""
        target_pos = pos if pos is not None else self.home_dock
        self.pos = target_pos
        self.goal = None
        self.path = []
        self.path_index = 0
        self.status = RobotStatus.IDLE
        self.trail = [self.pos]
        self.assigned_task = None
