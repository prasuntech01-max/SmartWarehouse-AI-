"""Comprehensive unit tests for Phase 2, Module 5: Multi-Robot Conflict Detection."""

import pytest
from warehouse import Warehouse
from core.state import TimeExpandedState, Action, Trajectory, TimeExpandedPlanner
from core.conflict import (
    ConflictType,
    ConflictReport,
    MultiRobotConflictDetector,
)


# ==========================================
# 1. VERTEX COLLISION TESTS
# ==========================================
def test_vertex_collision_detection_basic():
    detector = MultiRobotConflictDetector()

    # Robot 1: (0,0) -> (1,0) -> (2,0)
    # Robot 2: (2,0) -> (1,0) -> (0,0)
    # Both at (1,0) at t=1
    paths = {
        1: [(0, 0), (1, 0), (2, 0)],
        2: [(2, 0), (1, 0), (0, 0)],
    }

    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) == 1
    c = conflicts[0]

    assert c.conflict_type == ConflictType.VERTEX
    assert c.time_step == 1
    assert c.location_a == (1, 0)
    assert c.location_b == (1, 0)
    assert set([c.robot_a, c.robot_b]) == {1, 2}
    assert "Vertex collision" in c.description


def test_vertex_collision_at_start():
    detector = MultiRobotConflictDetector()
    # Both start at same location at t=0
    paths = {
        1: [(5, 5), (5, 6)],
        2: [(5, 5), (6, 5)],
    }
    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.VERTEX
    assert conflicts[0].time_step == 0
    assert conflicts[0].location_a == (5, 5)


def test_vertex_collision_with_parked_robot():
    detector = MultiRobotConflictDetector()

    # Robot 1 stops at (3, 3) at t=1 and parks there
    # Robot 2 arrives at (3, 3) at t=3
    paths = {
        1: [(3, 2), (3, 3)],
        2: [(1, 3), (2, 3), (3, 3), (4, 3)],
    }

    # With park_at_goal=True (default), Robot 2 colliding into parked Robot 1 must be caught
    conflicts = detector.detect_conflicts(paths, park_at_goal=True)
    assert len(conflicts) >= 1
    v_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.VERTEX and c.time_step == 2]
    assert len(v_conflicts) == 1
    assert v_conflicts[0].location_a == (3, 3)


# ==========================================
# 2. EDGE-SWAP COLLISION TESTS
# ==========================================
def test_edge_swap_collision_detection():
    detector = MultiRobotConflictDetector()

    # Robot 1 moves (0, 0) -> (1, 0) at t=0
    # Robot 2 moves (1, 0) -> (0, 0) at t=0
    paths = {
        1: [(0, 0), (1, 0)],
        2: [(1, 0), (0, 0)],
    }

    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) == 1
    c = conflicts[0]

    assert c.conflict_type == ConflictType.EDGE_SWAP
    assert c.time_step == 0
    assert c.location_a == (0, 0)
    assert c.next_location_a == (1, 0)
    assert c.location_b == (1, 0)
    assert c.next_location_b == (0, 0)
    assert "Edge-swap collision" in c.description


# ==========================================
# 3. CORRIDOR CONFLICT TESTS
# ==========================================
def test_corridor_opposite_direction_conflict():
    wh = Warehouse(5, 3, auto_layout=False)
    # Block top (y=0) and bottom (y=2) to form a narrow aisle at y=1
    for x in range(5):
        wh.obstacles.add_shelf(x, 0)
        wh.obstacles.add_shelf(x, 2)

    detector = MultiRobotConflictDetector(warehouse=wh)
    assert detector.is_corridor_cell(2, 1) is True

    # Robot 1 moving (1, 1) -> (2, 1)
    # Robot 2 moving (2, 1) -> (1, 1)
    paths = {
        1: [(1, 1), (2, 1)],
        2: [(2, 1), (1, 1)],
    }

    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.conflict_type == ConflictType.CORRIDOR_OPPOSITE
    assert c.time_step == 0


def test_corridor_same_direction_converging_conflict():
    wh = Warehouse(5, 5, auto_layout=False)
    # Aisle along x=2 from y=0 to y=4 (flanked by shelves at x=1 and x=3)
    for y in range(5):
        wh.obstacles.add_shelf(1, y)
        wh.obstacles.add_shelf(3, y)

    detector = MultiRobotConflictDetector(warehouse=wh)
    assert detector.is_corridor_cell(2, 2) is True

    # Both robots move in the SAME direction (southward) along corridor into cell (2, 2) at t=2
    # Robot 1: (2, 0) -> (2, 1) -> (2, 2)
    # Robot 2: (2, 0) -> (2, 1) -> (2, 2)
    paths = {
        1: [(2, 0), (2, 1), (2, 2)],
        2: [(2, 0), (2, 1), (2, 2)],
    }

    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) >= 1
    same_dir_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.CORRIDOR_SAME_DIRECTION]
    assert len(same_dir_conflicts) >= 1
    c = same_dir_conflicts[0]
    assert c.time_step in (1, 2)
    assert c.location_a[0] == 2


# ==========================================
# 4. COLLISION-FREE SCENARIOS
# ==========================================
def test_collision_free_parallel_paths():
    detector = MultiRobotConflictDetector()

    # Robot 1 and 2 move along parallel tracks with no overlap
    paths = {
        1: [(0, 0), (1, 0), (2, 0), (3, 0)],
        2: [(0, 1), (1, 1), (2, 1), (3, 1)],
    }

    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) == 0


def test_collision_free_crossing_at_different_timesteps():
    detector = MultiRobotConflictDetector()

    # Robot 1 crosses (1, 1) at t=1
    # Robot 2 crosses (1, 1) at t=3
    paths = {
        1: [(0, 1), (1, 1), (2, 1), (3, 1)],
        2: [(1, -1), (1, 0), (1, 0), (1, 1), (1, 2)],
    }

    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) == 0


def test_collision_free_safe_following():
    detector = MultiRobotConflictDetector()

    # Robot 2 follows Robot 1 maintaining 1-step buffer
    paths = {
        1: [(1, 0), (2, 0), (3, 0), (4, 0)],
        2: [(0, 0), (1, 0), (2, 0), (3, 0)],
    }

    conflicts = detector.detect_conflicts(paths)
    assert len(conflicts) == 0


# ==========================================
# 5. REUSING MODULE 4's TRAJECTORY & TIMEEXPANDEDSTATE
# ==========================================
def test_conflict_detection_with_trajectories():
    wh = Warehouse(15, 15)
    planner = TimeExpandedPlanner(wh)
    detector = MultiRobotConflictDetector(warehouse=wh)

    # Generate two colliding paths using TimeExpandedPlanner
    traj1 = planner.plan(start=(1, 0), goal=(1, 4), start_time=0)
    traj2 = planner.plan(start=(1, 4), goal=(1, 0), start_time=0)

    assert isinstance(traj1, Trajectory)
    assert isinstance(traj2, Trajectory)

    # Pass Trajectory objects directly to conflict detector
    conflicts = detector.detect_conflicts({1: traj1, 2: traj2})
    assert len(conflicts) >= 1
    assert any(c.conflict_type in (ConflictType.VERTEX, ConflictType.EDGE_SWAP, ConflictType.CORRIDOR_OPPOSITE) for c in conflicts)


# ==========================================
# 6. STRUCTURED CONFLICT REPORTS (MODULE 6 PREP)
# ==========================================
def test_structured_conflict_report_and_reservation_constraints():
    report = ConflictReport(
        conflict_type=ConflictType.VERTEX,
        robot_a=1,
        robot_b=2,
        time_step=4,
        location_a=(3, 5),
        location_b=(3, 5),
        description="Test vertex collision",
    )

    d = report.to_dict()
    assert d["conflict_type"] == "vertex"
    assert d["robot_a"] == 1
    assert d["robot_b"] == 2
    assert d["time_step"] == 4
    assert d["location_a"] == (3, 5)

    constraint = report.to_reservation_constraint()
    assert constraint["constraint_type"] == "vertex"
    assert constraint["pos"] == (3, 5)
    assert constraint["time_step"] == 4
    assert constraint["conflicting_robots"] == (1, 2)

    # Edge conflict constraint
    edge_report = ConflictReport(
        conflict_type=ConflictType.EDGE_SWAP,
        robot_a=3,
        robot_b=4,
        time_step=2,
        location_a=(1, 1),
        location_b=(1, 2),
        next_location_a=(1, 2),
        next_location_b=(1, 1),
    )
    edge_constraint = edge_report.to_reservation_constraint()
    assert edge_constraint["constraint_type"] == "edge"
    assert edge_constraint["u"] == (1, 1)
    assert edge_constraint["v"] == (1, 2)
    assert edge_constraint["time_step"] == 2


# ==========================================
# 7. INVALID TRAJECTORIES & EDGE CASES
# ==========================================
def test_invalid_trajectories_and_edge_cases():
    detector = MultiRobotConflictDetector()

    # 1. Empty fleet
    assert detector.detect_conflicts({}) == []

    # 2. Single robot
    assert detector.detect_conflicts({1: [(0, 0), (0, 1)]}) == []

    # 3. Spatial jump (teleportation) must raise ValueError
    with pytest.raises(ValueError, match="spatial jump"):
        detector.detect_conflicts({
            1: [(0, 0), (0, 5)],  # jumps 5 cells in 1 step!
            2: [(0, 0), (0, 1)],
        })

    # 4. Temporal jump must raise ValueError
    states_bad_time = [
        TimeExpandedState(0, 0, 0),
        TimeExpandedState(0, 1, 3),  # time jumps from 0 to 3!
    ]
    with pytest.raises(ValueError, match="temporal discontinuity"):
        detector.detect_conflicts({
            1: states_bad_time,
            2: [(0, 0), (0, 1)],
        })

    # 5. Invalid item type must raise TypeError
    with pytest.raises(TypeError):
        detector.detect_conflicts({
            1: ["invalid"],  # type: ignore
            2: [(0, 0), (0, 1)],
        })
