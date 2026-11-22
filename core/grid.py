"""Warehouse grid representation with shelves, stations, docks, and dynamic obstacles."""

from typing import Set, Tuple, List, Optional


class WarehouseGrid:
    def __init__(self, width: int = 15, height: int = 15):
        self.width = width
        self.height = height
        self.shelves: Set[Tuple[int, int]] = set()
        self.picking_stations: List[Tuple[int, int]] = []
        self.packing_stations: List[Tuple[int, int]] = []
        self.charging_docks: List[Tuple[int, int]] = []
        self.dynamic_obstacles: Set[Tuple[int, int]] = set()
        self._init_standard_layout()

    def _init_standard_layout(self) -> None:
        """Initializes a standard navigable 15x15 layout with shelves and aisles."""
        # Charging docks along top row (y = 0)
        self.charging_docks = [(1, 0), (4, 0), (7, 0), (10, 0), (13, 0)]

        # Packing / Dispatch stations along bottom row (y = 14)
        self.packing_stations = [(2, 14), (6, 14), (10, 14), (12, 14)]

        # Picking / Intake stations along left edge (x = 0)
        self.picking_stations = [(0, 4), (0, 7), (0, 10)]

        # Shelf pods in blocks of 2x3 to leave generous aisles
        # Shelf columns: (2, 3), (6, 7), (10, 11)
        # Shelf rows: [3, 4, 5] and [8, 9, 10]
        shelf_x_ranges = [(2, 3), (6, 7), (10, 11)]
        shelf_y_ranges = [(3, 5), (8, 10)]

        for x_start, x_end in shelf_x_ranges:
            for y_start, y_end in shelf_y_ranges:
                for x in range(x_start, x_end + 1):
                    for y in range(y_start, y_end + 1):
                        self.shelves.add((x, y))

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates lie within warehouse bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        """Cell is walkable if inside grid, not a static shelf, and not a dynamic obstacle."""
        if not self.in_bounds(x, y):
            return False
        if (x, y) in self.shelves:
            return False
        if (x, y) in self.dynamic_obstacles:
            return False
        return True

    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Returns valid adjacent walkable neighbor coordinates."""
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def add_dynamic_obstacle(self, x: int, y: int) -> bool:
        """Add dynamic obstacle if valid and walkable."""
        if self.in_bounds(x, y) and (x, y) not in self.shelves:
            self.dynamic_obstacles.add((x, y))
            return True
        return False

    def remove_dynamic_obstacle(self, x: int, y: int) -> bool:
        """Remove dynamic obstacle."""
        if (x, y) in self.dynamic_obstacles:
            self.dynamic_obstacles.remove((x, y))
            return True
        return False

    def clear_dynamic_obstacles(self) -> None:
        """Clear all dynamic obstacles."""
        self.dynamic_obstacles.clear()

    def get_accessible_shelf_locations(self) -> List[Tuple[int, int]]:
        """Returns walkable cells directly adjacent to shelves where robots can pick items."""
        pick_spots = set()
        for sx, sy in self.shelves:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = sx + dx, sy + dy
                if self.is_walkable(nx, ny):
                    pick_spots.add((nx, ny))
        return sorted(list(pick_spots))
