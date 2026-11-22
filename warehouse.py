"""Warehouse environment grid and layout model."""

from typing import List, Tuple, Set, Optional
from obstacles import ObstacleManager


class Warehouse:
    """Represents a discrete grid-based warehouse floor with aisles, shelves, and stations."""

    def __init__(self, width: int = 15, height: int = 15, auto_layout: bool = True):
        if width <= 0 or height <= 0:
            raise ValueError(f"Grid width and height must be positive, got {width}x{height}")
        self.width = width
        self.height = height

        self.obstacles = ObstacleManager(width=self.width, height=self.height)
        self.charging_docks: List[Tuple[int, int]] = []
        self.packing_stations: List[Tuple[int, int]] = []
        self.picking_stations: List[Tuple[int, int]] = []

        if auto_layout and self.width >= 15 and self.height >= 15:
            self._init_standard_layout()

    def _init_standard_layout(self) -> None:
        """Configures standard navigable 15x15 warehouse zones."""
        # Top row: Charging docks
        self.charging_docks = [(1, 0), (4, 0), (7, 0), (10, 0), (13, 0)]

        # Bottom row: Packing & Dispatch stations
        self.packing_stations = [(2, 14), (6, 14), (10, 14), (12, 14)]

        # Left perimeter: Picking / Inbound stations
        self.picking_stations = [(0, 4), (0, 7), (0, 10)]

        # 3 Pods of shelves with 2-cell aisles between them
        shelf_x_blocks = [(2, 3), (6, 7), (10, 11)]
        shelf_y_blocks = [(3, 5), (8, 10)]

        for x_rng in shelf_x_blocks:
            for y_rng in shelf_y_blocks:
                self.obstacles.add_shelf_block(x_rng, y_rng)

    @property
    def shelves(self) -> Set[Tuple[int, int]]:
        """Access set of shelf positions."""
        return self.obstacles.shelves

    @property
    def dynamic_obstacles(self) -> Set[Tuple[int, int]]:
        """Access set of dynamic obstacle positions."""
        return self.obstacles.dynamic_obstacles

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if (x, y) is within grid dimensions."""
        return self.obstacles.in_bounds(x, y)

    def is_walkable(self, x: int, y: int) -> bool:
        """A cell is walkable if inside bounds and free of obstacles."""
        if not self.in_bounds(x, y):
            return False
        return not self.obstacles.is_blocked(x, y)

    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Returns 4-connected walkable neighbors."""
        if not self.in_bounds(x, y):
            raise ValueError(f"Cannot get neighbors for out-of-bounds cell ({x}, {y})")

        neighbors: List[Tuple[int, int]] = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def add_dynamic_obstacle(self, x: int, y: int) -> bool:
        """Place dynamic obstacle."""
        try:
            self.obstacles.add_dynamic_obstacle(x, y)
            return True
        except ValueError:
            return False

    def remove_dynamic_obstacle(self, x: int, y: int) -> bool:
        """Remove dynamic obstacle."""
        try:
            return self.obstacles.remove_dynamic_obstacle(x, y)
        except ValueError:
            return False

    def clear_dynamic_obstacles(self) -> None:
        """Clear all dynamic obstacles."""
        self.obstacles.clear_dynamic_obstacles()

    def get_accessible_shelf_locations(self) -> List[Tuple[int, int]]:
        """Returns list of walkable positions adjacent to shelves."""
        pick_spots = set()
        for sx, sy in self.shelves:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = sx + dx, sy + dy
                if self.is_walkable(nx, ny):
                    pick_spots.add((nx, ny))
        return sorted(list(pick_spots))
