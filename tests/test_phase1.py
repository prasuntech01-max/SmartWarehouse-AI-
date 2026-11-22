"""Unit tests for Phase 1: Grid, Reservation Table, and Space-Time A* Planner."""

import pytest
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner


def test_grid_initialization():
    grid = WarehouseGrid(width=15, height=15)
    assert grid.width == 15
    assert grid.height == 15
    assert len(grid.shelves) > 0
    assert len(grid.charging_docks) == 5
    assert len(grid.packing_stations) == 4
    assert len(grid.picking_stations) == 3

    # Charging dock should be walkable
    assert grid.is_walkable(1, 0) is True
    # Shelf should not be walkable
    first_shelf = next(iter(grid.shelves))
    assert grid.is_walkable(first_shelf[0], first_shelf[1]) is False


def test_dynamic_obstacle():
    grid = WarehouseGrid(15, 15)
    assert grid.is_walkable(1, 1) is True
    grid.add_dynamic_obstacle(1, 1)
    assert grid.is_walkable(1, 1) is False
    grid.remove_dynamic_obstacle(1, 1)
    assert grid.is_walkable(1, 1) is True


def test_single_robot_astar():
    grid = WarehouseGrid(15, 15)
    res_table = ReservationTable()
    planner = SpaceTimeAStarPlanner(grid, res_table)

    start = (1, 0)
    goal = (1, 2)
    path = planner.plan(start=start, goal=goal, start_time=0, robot_id=1)

    assert path is not None
    assert path[0] == start
    assert path[-1] == goal
    assert len(path) == 3  # (1,0) -> (1,1) -> (1,2)


def test_vertex_collision_avoidance_via_wait():
    grid = WarehouseGrid(15, 15)
    res_table = ReservationTable()
    planner = SpaceTimeAStarPlanner(grid, res_table)

    start = (1, 0)
    goal = (1, 2)

    # Robot 99 occupies (1, 1) at t=1
    res_table.reserve_vertex(1, 1, t=1, robot_id=99)

    path = planner.plan(start=start, goal=goal, start_time=0, robot_id=1)
    assert path is not None
    assert path[0] == start
    assert path[-1] == goal

    # Verify Robot 1 does not step on (1, 1) at t=1
    assert path[1] != (1, 1)


def test_edge_swap_collision_avoidance():
    grid = WarehouseGrid(15, 15)
    res_table = ReservationTable()
    planner = SpaceTimeAStarPlanner(grid, res_table)

    # Robot 2 is moving (1, 1) -> (1, 0) at t=0
    res_table.reserve_edge((1, 1), (1, 0), t=0, robot_id=2)
    res_table.reserve_vertex(1, 0, t=1, robot_id=2)

    # Robot 1 wants to move (1, 0) -> (1, 1) starting at t=0
    # Moving directly into (1, 1) at t=0 would cause a head-on swap collision!
    path = planner.plan(start=(1, 0), goal=(1, 2), start_time=0, robot_id=1)
    assert path is not None
    # Robot 1 cannot step into (1, 1) at t=1
    assert path[1] != (1, 1)
