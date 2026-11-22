"""Comprehensive unit tests for Module 6: Reservation Table and Priority Planning."""

import pytest
from warehouse import Warehouse
from core.reservation import ReservationTable
from core.state import TimeExpandedState, Action, Trajectory, TimeExpandedPlanner
from core.conflict import MultiRobotConflictDetector, ConflictType
from core.priority import (
    PriorityScheme,
    PriorityManager,
    PriorityPlanner,
)


# ==========================================
# 1. TIME-INDEXED VERTEX RESERVATIONS
# ==========================================
def test_vertex_reservation_lifecycle():
    table = ReservationTable()

    # Initially free
    assert table.is_vertex_reserved(2, 2, t=5) is False
    assert table.get_vertex_reservation(2, 2, t=5) is None

    # Reserve for robot 1
    table.reserve_vertex(2, 2, t=5, robot_id=1)
    assert table.is_vertex_reserved(2, 2, t=5) is True
    assert table.is_vertex_reserved(2, 2, t=5, ignore_robot=1) is False
    assert table.is_vertex_reserved(2, 2, t=5, ignore_robot=2) is True
    assert table.get_vertex_reservation(2, 2, t=5) == 1

    # Safe release with wrong robot ID fails
    released = table.release_vertex(2, 2, t=5, robot_id=99)
    assert released is False
    assert table.is_vertex_reserved(2, 2, t=5) is True

    # Safe release with matching robot ID succeeds
    released = table.release_vertex(2, 2, t=5, robot_id=1)
    assert released is True
    assert table.is_vertex_reserved(2, 2, t=5) is False


# ==========================================
# 2. DIRECTED EDGE RESERVATIONS
# ==========================================
def test_edge_reservation_lifecycle_and_swap_prevention():
    table = ReservationTable()

    u = (1, 1)
    v = (1, 2)
    t = 3

    assert table.is_edge_reserved(u, v, t) is False
    assert table.get_edge_reservation(u, v, t) is None

    # Robot 1 reserves u -> v at t=3
    table.reserve_edge(u, v, t, robot_id=1)
    assert table.get_edge_reservation(u, v, t) == 1

    # Same edge traversal by another robot is blocked
    assert table.is_edge_reserved(u, v, t, ignore_robot=2) is True
    # Opposite direction traversal (v -> u at t=3) is blocked to prevent head-on swap
    assert table.is_edge_reserved(v, u, t, ignore_robot=2) is True

    # Safe release
    assert table.release_edge(u, v, t, robot_id=2) is False
    assert table.release_edge(u, v, t, robot_id=1) is True
    assert table.is_edge_reserved(u, v, t) is False
    assert table.is_edge_reserved(v, u, t) is False


# ==========================================
# 3. SAFE RESERVATION RELEASE, UPDATES & ROLLBACK
# ==========================================
def test_future_reservation_release_and_snapshot():
    table = ReservationTable()

    # Path for Robot 1: t=0..(1,0), t=1..(1,1), t=2..(1,2), t=3..(1,3)
    path = [(1, 0), (1, 1), (1, 2), (1, 3)]
    table.reserve_path(path, robot_id=1, start_time=0)

    assert table.is_vertex_reserved(1, 0, t=0) is True
    assert table.is_vertex_reserved(1, 2, t=2) is True
    assert table.is_vertex_reserved(1, 3, t=3) is True

    # Take snapshot
    snap = table.snapshot()

    # Release future reservations from t=2 onwards
    count = table.release_future_reservations(robot_id=1, from_time=2)
    assert count > 0

    # Past reservations remain
    assert table.is_vertex_reserved(1, 0, t=0) is True
    assert table.is_vertex_reserved(1, 1, t=1) is True
    # Future reservations released
    assert table.is_vertex_reserved(1, 2, t=2) is False
    assert table.is_vertex_reserved(1, 3, t=3) is False

    # Restore from snapshot
    table.restore(snap)
    assert table.is_vertex_reserved(1, 2, t=2) is True
    assert table.is_vertex_reserved(1, 3, t=3) is True


# ==========================================
# 4. ROBOT PRIORITY MANAGEMENT
# ==========================================
def test_priority_manager_schemes():
    mgr = PriorityManager([3, 1, 2])
    assert mgr.get_rank(3) == 0
    assert mgr.get_rank(1) == 1
    assert mgr.get_rank(2) == 2

    agents = [
        {'id': 1, 'start': (0, 0), 'goal': (1, 1)},  # dist = 2
        {'id': 2, 'start': (0, 0), 'goal': (5, 5)},  # dist = 10
        {'id': 3, 'start': (0, 0), 'goal': (2, 2)},  # dist = 4
    ]

    # Manual ordering
    sorted_manual = mgr.sort_robots(agents, scheme=PriorityScheme.MANUAL)
    assert [a['id'] for a in sorted_manual] == [3, 1, 2]

    # ID ascending
    sorted_id = mgr.sort_robots(agents, scheme=PriorityScheme.ID_ASCENDING)
    assert [a['id'] for a in sorted_id] == [1, 2, 3]

    # Longest path first
    sorted_lpf = mgr.sort_robots(agents, scheme=PriorityScheme.LONGEST_PATH_FIRST)
    assert [a['id'] for a in sorted_lpf] == [2, 3, 1]

    # Priority inversion
    mgr.invert_priority(3, 1)
    assert mgr.priority_list == [1, 3, 2]

    # Elevate to top
    mgr.elevate_to_top(2)
    assert mgr.priority_list == [2, 1, 3]


# ==========================================
# 5. SEQUENTIAL MULTI-ROBOT PATH PLANNING
# ==========================================
def test_priority_planning_intersecting_paths():
    wh = Warehouse(15, 15)
    table = ReservationTable()
    planner = PriorityPlanner(warehouse=wh, reservation_table=table)

    # Robot 1 crosses horizontally along aisle y=1: (0, 1) -> (4, 1)
    # Robot 2 crosses vertically along aisle x=2:   (2, 0) -> (2, 2)
    # Both would collide at (2, 1) at t=2 without space-time reservations!
    agents = [
        {'id': 1, 'start': (0, 1), 'goal': (4, 1)},
        {'id': 2, 'start': (2, 0), 'goal': (2, 2)},
    ]

    # Robot 1 has priority over Robot 2
    paths, success, conflicts = planner.plan_sequential(agents, priorities=[1, 2])
    assert success is True
    assert len(conflicts) == 0

    p1 = paths[1]
    p2 = paths[2]

    # Robot 1 takes direct 5-step path
    assert len(p1) == 5

    # Verify no collisions between trajectories at any timestep
    detector = MultiRobotConflictDetector(warehouse=wh)
    assert len(detector.detect_conflicts(paths)) == 0


def test_priority_ordering_determines_who_waits():
    wh = Warehouse(15, 15)
    table = ReservationTable()
    planner = PriorityPlanner(warehouse=wh, reservation_table=table)

    agents = [
        {'id': 1, 'start': (0, 1), 'goal': (4, 1)},
        {'id': 2, 'start': (2, 0), 'goal': (2, 2)},
    ]

    # Test 1: Priority [1, 2] -> Robot 1 takes direct optimal path
    paths1, _, _ = planner.plan_sequential(agents, priorities=[1, 2])
    len_r1_first = len(paths1[1])
    len_r2_second = len(paths1[2])

    # Test 2: Inverted priority [2, 1] -> Robot 2 takes direct path, Robot 1 accommodates
    paths2, _, _ = planner.plan_sequential(agents, priorities=[2, 1])
    len_r2_first = len(paths2[2])
    len_r1_second = len(paths2[1])

    assert len_r1_first <= len_r1_second
    assert len_r2_first <= len_r2_second


def test_head_on_swap_prevention_in_aisle():
    wh = Warehouse(7, 3, auto_layout=False)
    # 1-cell corridor at y=1
    for x in range(7):
        wh.obstacles.add_shelf(x, 0)
        wh.obstacles.add_shelf(x, 2)
    # Turnout/bay at (4, 0) allows Robot 2 to step aside at t=2 while Robot 1 passes
    wh.obstacles.remove_dynamic_obstacle(4, 0)
    wh.obstacles.shelves.remove((4, 0))

    table = ReservationTable()
    planner = PriorityPlanner(warehouse=wh, reservation_table=table)

    # Robot 1: (0, 1) -> (6, 1)
    # Robot 2: (6, 1) -> (0, 1)
    agents = [
        {'id': 1, 'start': (0, 1), 'goal': (6, 1)},
        {'id': 2, 'start': (6, 1), 'goal': (0, 1)},
    ]

    paths, success, conflicts = planner.plan_sequential(agents, priorities=[1, 2])
    assert success is True
    assert len(conflicts) == 0

    detector = MultiRobotConflictDetector(warehouse=wh)
    assert len(detector.detect_conflicts(paths)) == 0


# ==========================================
# 6. WAITING AND REPLANNING
# ==========================================
def test_replan_robot_with_atomic_reservation_update():
    wh = Warehouse(15, 15)
    table = ReservationTable()
    planner = PriorityPlanner(warehouse=wh, reservation_table=table)

    agents = [
        {'id': 1, 'start': (1, 0), 'goal': (1, 8)},
        {'id': 2, 'start': (4, 0), 'goal': (4, 8)},
    ]
    paths, success, _ = planner.plan_sequential(agents, priorities=[1, 2])
    assert success is True

    # At t=2, Robot 1 is at (1, 2). Replan Robot 1 to head to (10, 2)
    new_traj = planner.replan_robot(
        robot_id=1,
        current_pos=(1, 2),
        goal=(10, 2),
        current_time=2,
    )

    assert new_traj is not None
    assert new_traj[0] == (1, 2)
    assert new_traj[-1] == (10, 2)
    assert table.is_vertex_reserved(10, 2, t=2 + len(new_traj) - 1) is True


def test_replan_robot_failure_rolls_back_safely():
    wh = Warehouse(5, 5, auto_layout=False)
    table = ReservationTable()
    planner = PriorityPlanner(warehouse=wh, reservation_table=table)

    # Walled off cell at (4, 4)
    for x in range(5):
        for y in range(5):
            if (x, y) not in ((0, 0), (1, 0), (0, 1)):
                wh.obstacles.add_shelf(x, y)

    agents = [{'id': 1, 'start': (0, 0), 'goal': (1, 0)}]
    paths, success, _ = planner.plan_sequential(agents)
    assert success is True

    snap_before = table.snapshot()

    # Replan to unreachable destination (4, 4)
    failed_replan = planner.replan_robot(
        robot_id=1,
        current_pos=(0, 0),
        goal=(4, 4),
        current_time=1,
    )

    assert failed_replan is None
    # Verify reservation table was rolled back and preserved
    assert table.vertex_reservations == snap_before["vertex_reservations"]
