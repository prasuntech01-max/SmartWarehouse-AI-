"""Comprehensive unit tests for Phase 1 modules: warehouse.py, obstacles.py, robot.py, and astar.py."""

import pytest
from obstacles import ObstacleManager, ObstacleType
from warehouse import Warehouse
from robot import Robot, RobotStatus
from astar import AStarPlanner, PathNotFoundError
from core.reservation import ReservationTable


# ==========================================
# 1. OBSTACLES.PY TESTS
# ==========================================
def test_obstacle_manager_init_and_validation():
    mgr = ObstacleManager(15, 15)
    assert mgr.width == 15
    assert mgr.height == 15
    assert mgr.in_bounds(0, 0) is True
    assert mgr.in_bounds(14, 14) is True
    assert mgr.in_bounds(15, 15) is False
    assert mgr.in_bounds(-1, 0) is False

    with pytest.raises(ValueError):
        ObstacleManager(0, 15)

    with pytest.raises(ValueError):
        ObstacleManager(15, -5)


def test_obstacle_manager_operations():
    mgr = ObstacleManager(15, 15)
    mgr.add_shelf(2, 2)
    assert mgr.is_blocked(2, 2) is True
    assert mgr.is_blocked(2, 3) is False

    # Block addition
    mgr.add_shelf_block((4, 5), (4, 5))
    assert mgr.is_blocked(4, 4) is True
    assert mgr.is_blocked(5, 5) is True

    # Dynamic obstacle
    mgr.add_dynamic_obstacle(6, 6)
    assert mgr.is_blocked(6, 6) is True
    assert (6, 6) in mgr.dynamic_obstacles

    # Dynamic obstacle on shelf must raise ValueError
    with pytest.raises(ValueError):
        mgr.add_dynamic_obstacle(2, 2)

    # Removal
    removed = mgr.remove_dynamic_obstacle(6, 6)
    assert removed is True
    assert mgr.is_blocked(6, 6) is False

    # Clear
    mgr.add_dynamic_obstacle(7, 7)
    mgr.clear_dynamic_obstacles()
    assert len(mgr.dynamic_obstacles) == 0


def test_obstacle_manager_error_handling():
    mgr = ObstacleManager(10, 10)
    with pytest.raises(ValueError):
        mgr.add_shelf(15, 5)
    with pytest.raises(ValueError):
        mgr.add_dynamic_obstacle(-1, 2)
    with pytest.raises(TypeError):
        mgr.add_shelf("2", 3)  # type: ignore


# ==========================================
# 2. WAREHOUSE.PY TESTS
# ==========================================
def test_warehouse_initialization_and_layout():
    wh = Warehouse(15, 15)
    assert wh.width == 15
    assert wh.height == 15
    assert len(wh.charging_docks) == 5
    assert len(wh.packing_stations) == 4
    assert len(wh.picking_stations) == 3
    assert len(wh.shelves) > 0

    # Docks and stations should be walkable
    for dock in wh.charging_docks:
        assert wh.is_walkable(dock[0], dock[1]) is True
    for pack in wh.packing_stations:
        assert wh.is_walkable(pack[0], pack[1]) is True

    # Shelves must not be walkable
    first_shelf = next(iter(wh.shelves))
    assert wh.is_walkable(first_shelf[0], first_shelf[1]) is False


def test_warehouse_neighbors_and_walkability():
    wh = Warehouse(15, 15)
    # Origin (0,0) neighbors: (0,1) and (1,0)
    nbrs = wh.get_neighbors(0, 0)
    assert (0, 1) in nbrs
    assert (1, 0) in nbrs
    assert len(nbrs) == 2

    # Accessible pick spots should be next to shelves
    picks = wh.get_accessible_shelf_locations()
    assert len(picks) > 0
    for px, py in picks:
        assert wh.is_walkable(px, py) is True

    # Error handling on get_neighbors for out of bounds
    with pytest.raises(ValueError):
        wh.get_neighbors(20, 20)


# ==========================================
# 3. ROBOT.PY TESTS
# ==========================================
def test_robot_lifecycle():
    bot = Robot(robot_id=1, start_pos=(1, 0), home_dock=(1, 0))
    assert bot.pos == (1, 0)
    assert bot.status == RobotStatus.IDLE
    assert bot.battery == 100.0

    # Set goal
    bot.set_goal((1, 3))
    assert bot.status == RobotStatus.WAITING
    assert bot.is_at_goal() is False

    # Set path
    path = [(1, 0), (1, 1), (1, 2), (1, 3)]
    bot.set_path(path)
    assert bot.status == RobotStatus.MOVING

    # Step through path
    p1 = bot.step()
    assert p1 == (1, 1)
    assert bot.pos == (1, 1)
    assert len(bot.trail) == 2

    bot.step()  # to (1, 2)
    bot.step()  # to (1, 3)
    assert bot.pos == (1, 3)
    assert bot.is_at_goal() is True
    assert bot.status == RobotStatus.COMPLETED

    # Reset
    bot.reset()
    assert bot.pos == (1, 0)
    assert bot.status == RobotStatus.IDLE
    assert bot.goal is None


def test_robot_error_handling():
    bot = Robot(robot_id=2, start_pos=(0, 0))
    with pytest.raises(ValueError):
        bot.set_path([])  # empty path

    with pytest.raises(ValueError):
        bot.set_path([(5, 5), (5, 6)])  # path doesn't start at bot.pos

    with pytest.raises(TypeError):
        bot.set_goal("invalid")  # type: ignore

    with pytest.raises(TypeError):
        Robot(robot_id=3, start_pos="bad")  # type: ignore


# ==========================================
# 4. ASTAR.PY TESTS
# ==========================================
def test_astar_2d_shortest_path():
    wh = Warehouse(15, 15)
    planner = AStarPlanner(wh)

    start = (1, 0)
    goal = (1, 2)
    path = planner.plan_2d(start, goal)

    assert path == [(1, 0), (1, 1), (1, 2)]


def test_astar_2d_shelf_obstacle_avoidance():
    wh = Warehouse(15, 15)
    planner = AStarPlanner(wh)

    # (2, 3) is a shelf. Plan from (2, 2) to (2, 6) across the shelf
    start = (1, 3)
    goal = (4, 3)
    path = planner.plan_2d(start, goal)

    assert path is not None
    assert path[0] == start
    assert path[-1] == goal
    # Path must not cross through any shelves
    for node in path:
        assert node not in wh.shelves


def test_astar_start_equals_goal():
    wh = Warehouse(15, 15)
    planner = AStarPlanner(wh)
    path = planner.plan_2d((0, 0), (0, 0))
    assert path == [(0, 0)]


def test_astar_spacetime_with_reservation_wait():
    wh = Warehouse(15, 15)
    res_table = ReservationTable()
    planner = AStarPlanner(wh, res_table)

    start = (1, 0)
    goal = (1, 2)

    # Cell (1, 1) is blocked at t=1 by robot 9
    res_table.reserve_vertex(1, 1, t=1, robot_id=9)

    # Space-time A* will wait or go around
    path = planner.plan_spacetime(start, goal, start_time=0, robot_id=1)
    assert path is not None
    assert path[0] == start
    assert path[-1] == goal
    assert path[1] != (1, 1)  # Robot 1 does not step on (1, 1) at t=1


def test_astar_error_handling():
    wh = Warehouse(15, 15)
    planner = AStarPlanner(wh)

    # 1. Out of bounds start
    with pytest.raises(ValueError, match="out of bounds"):
        planner.plan_2d((-1, 0), (1, 1))

    # 2. Out of bounds goal
    with pytest.raises(ValueError, match="out of bounds"):
        planner.plan_2d((0, 0), (20, 20))

    # 3. Blocked start (on a shelf)
    shelf = next(iter(wh.shelves))
    with pytest.raises(ValueError, match="blocked"):
        planner.plan_2d(shelf, (0, 0))

    # 4. Blocked goal (on a shelf)
    with pytest.raises(ValueError, match="blocked"):
        planner.plan_2d((0, 0), shelf)

    # 5. Type error
    with pytest.raises(TypeError):
        planner.plan_2d("0,0", (1, 1))  # type: ignore

    # 6. Unreachable goal (enclosed cell)
    # Create isolated 3x3 warehouse with walled-off center
    isolated_wh = Warehouse(3, 3)
    isolated_wh.obstacles.shelves.clear()
    for x in range(3):
        for y in range(3):
            if (x, y) != (0, 0) and (x, y) != (2, 2):
                isolated_wh.obstacles.add_shelf(x, y)

    iso_planner = AStarPlanner(isolated_wh)
    # When raise_on_failure is False, returns None
    assert iso_planner.plan_2d((0, 0), (2, 2), raise_on_failure=False) is None
    # When raise_on_failure is True, raises PathNotFoundError
    with pytest.raises(PathNotFoundError):
        iso_planner.plan_2d((0, 0), (2, 2), raise_on_failure=True)
