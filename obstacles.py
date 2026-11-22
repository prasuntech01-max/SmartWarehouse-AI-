"""Obstacle management for warehouse environments.

Supports static obstacles (shelves, structural barriers) and dynamic obstacles (unexpected blockages).
"""

from enum import Enum
from typing import Set, Tuple, List, Optional


class ObstacleType(Enum):
    SHELF = "shelf"
    STATIC_WALL = "static_wall"
    DYNAMIC = "dynamic"


class ObstacleManager:
    """Manages static and dynamic obstacles with bounds checking and collision validation."""

    def __init__(self, width: int = 15, height: int = 15):
        if width <= 0 or height <= 0:
            raise ValueError(f"Grid dimensions must be positive integers, got {width}x{height}")
        self.width = width
        self.height = height
        self.shelves: Set[Tuple[int, int]] = set()
        self.static_walls: Set[Tuple[int, int]] = set()
        self.dynamic_obstacles: Set[Tuple[int, int]] = set()

    def in_bounds(self, x: int, y: int) -> bool:
        """Validate whether coordinate lies within grid boundaries."""
        return 0 <= x < self.width and 0 <= y < self.height

    def _validate_coords(self, x: int, y: int) -> None:
        """Helper to assert coordinate validity."""
        if not (isinstance(x, int) and isinstance(y, int)):
            raise TypeError(f"Coordinates must be integers, got ({type(x).__name__}, {type(y).__name__})")
        if not self.in_bounds(x, y):
            raise ValueError(f"Coordinate ({x}, {y}) is out of bounds for {self.width}x{self.height} grid")

    def add_shelf(self, x: int, y: int) -> None:
        """Add a static shelf obstacle at (x, y)."""
        self._validate_coords(x, y)
        self.shelves.add((x, y))

    def add_shelf_block(self, x_range: Tuple[int, int], y_range: Tuple[int, int]) -> None:
        """Add a rectangular block of shelves."""
        x_start, x_end = x_range
        y_start, y_end = y_range
        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                self.add_shelf(x, y)

    def add_dynamic_obstacle(self, x: int, y: int) -> None:
        """Add a dynamic obstacle at runtime."""
        self._validate_coords(x, y)
        if (x, y) in self.shelves:
            raise ValueError(f"Cannot place dynamic obstacle at ({x}, {y}): cell is already a permanent shelf")
        self.dynamic_obstacles.add((x, y))

    def remove_dynamic_obstacle(self, x: int, y: int) -> bool:
        """Remove a dynamic obstacle. Returns True if removed, False if not present."""
        self._validate_coords(x, y)
        if (x, y) in self.dynamic_obstacles:
            self.dynamic_obstacles.remove((x, y))
            return True
        return False

    def clear_dynamic_obstacles(self) -> None:
        """Remove all dynamic obstacles."""
        self.dynamic_obstacles.clear()

    def is_blocked(self, x: int, y: int) -> bool:
        """Returns True if the cell is blocked by any static or dynamic obstacle, or out of bounds."""
        if not self.in_bounds(x, y):
            return True
        return (
            (x, y) in self.shelves
            or (x, y) in self.static_walls
            or (x, y) in self.dynamic_obstacles
        )

    def get_all_blocked(self) -> Set[Tuple[int, int]]:
        """Return the union of all blocked cells."""
        return self.shelves | self.static_walls | self.dynamic_obstacles
