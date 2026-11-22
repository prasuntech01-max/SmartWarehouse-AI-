"""Unit tests for Phase 2: Multi-Agent Planning, Deadlock Resolution, Dynamic Replanning, and Task Management."""

import pytest
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner
from core.multi_agent import MultiAgentPlanner, Conflict
from core.deadlock import DeadlockHandler
from core.replanner import DynamicReplanner
from core.task_manager import TaskManager


def test_conflict_detection_synthetic():
    # 1. Test synthetic vertex collision
    paths_vertex = {
        1: [(0, 0), (1, 0), (2, 0)],
        2: [(2, 0), (1, 0), (0, 0)],
    }
    # Both are at (1, 0) at t=1
    conflicts_v = MultiAgentPlanner.detect_conflicts(paths_vertex)
    assert len(conflicts_v) >= 1
    assert any(c.conflict_type == 'vertex' and c.time_step == 1 for c in conflicts_v)

    # 2. Test synthetic edge swap collision
    paths_edge = {
        1: [(0, 0), (1, 0)],
        2: [(1, 0), (0, 0)],
    }
    conflicts_e = MultiAgentPlanner.detect_conflicts(paths_edge)
    assert len(conflicts_e) >= 1
    assert any(c.conflict_type == 'edge' and c.time_step == 0 for c in conflicts_e)


def test_multi_agent_prioritized_planning_no_conflicts():
    grid = WarehouseGrid(15, 15)
    ma_planner = MultiAgentPlanner(grid)

    # 3 robots crossing aisles
    agents = [
        {'id': 1, 'start': (1, 0), 'goal': (1, 14)},
        {'id': 2, 'start': (4, 14), 'goal': (4, 0)},
        {'id': 3, 'start': (0, 7), 'goal': (14, 7)},
    ]

    paths, success = ma_planner.plan_prioritized(agents, start_time=0)
    assert success is True
    assert len(paths) == 3

    # Mathematical verification: 0 conflicts
    conflicts = MultiAgentPlanner.detect_conflicts(paths)
    assert len(conflicts) == 0, f"Expected 0 conflicts, got: {conflicts}"


def test_fleet_scaling_5_robots_zero_conflicts():
    grid = WarehouseGrid(15, 15)
    ma_planner = MultiAgentPlanner(grid)

    agents = [
        {'id': 1, 'start': (1, 0), 'goal': (1, 14)},
        {'id': 2, 'start': (4, 0), 'goal': (4, 14)},
        {'id': 3, 'start': (7, 0), 'goal': (7, 14)},
        {'id': 4, 'start': (10, 0), 'goal': (10, 14)},
        {'id': 5, 'start': (13, 0), 'goal': (13, 14)},
    ]

    paths, success = ma_planner.plan_prioritized(agents, start_time=0)
    assert success is True
    assert len(paths) == 5

    conflicts = MultiAgentPlanner.detect_conflicts(paths)
    assert len(conflicts) == 0


def test_dynamic_replanning_on_obstacle():
    grid = WarehouseGrid(15, 15)
    res_table = ReservationTable()
    replanner = DynamicReplanner(grid, res_table)

    # Robot 1 plans a path from (1, 0) to (1, 4)
    original_path = [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)]
    res_table.reserve_path(original_path, robot_id=1, start_time=0)

    # At current_time = 1, obstacle is placed at (1, 3) which is in the future trajectory
    obstacle = (1, 3)
    current_time = 1
    robot_states = {
        1: {
            'pos': (1, 1),
            'goal': (1, 4),
            'path': original_path,
            'start_time': 0,
        }
    }

    updated_paths, latency_ms, affected = replanner.handle_obstacle_injection(
        obstacle=obstacle,
        current_time=current_time,
        robot_states=robot_states,
    )

    assert 1 in affected
    assert latency_ms >= 0.0
    assert 1 in updated_paths

    new_subpath = updated_paths[1]
    assert obstacle not in new_subpath
    assert new_subpath[-1] == (1, 4)


def test_task_manager():
    grid = WarehouseGrid(15, 15)
    tm = TaskManager(grid, seed=123)
    tm.populate_initial_tasks(5)

    assert tm.get_pending_count() == 5
    assert tm.get_completed_count() == 0

    assigned = tm.assign_next_task(robot_id=1, current_step=0)
    assert assigned is not None
    assert assigned.assigned_robot == 1
    assert assigned.status == 'PICKING_IN_TRANSIT'

    tm.complete_task(assigned.task_id, current_step=10)
    assert tm.get_completed_count() == 1
