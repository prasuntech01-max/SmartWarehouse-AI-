"""Space-Time A* planner (aliased to astar.AStarPlanner to avoid duplicate code)."""

from astar import AStarPlanner


class SpaceTimeAStarPlanner(AStarPlanner):
    """SpaceTimeAStarPlanner subclass aliasing AStarPlanner for backward compatibility."""

    def __init__(self, grid, reservation_table=None):
        super().__init__(warehouse=grid, reservation_table=reservation_table)
