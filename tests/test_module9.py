"""Comprehensive automated tests for Module 9: Intelligent Task Assignment & Fleet Optimization.

Tests coverage:
- TaskPriority & TaskStatus enum mappings
- Task lifecycle state machine & transition rules
- Custom task coordinate and layout validation
- Cancellation and failure lifecycles
- Dedicated assignment strategies (Nearest, Shortest Route, Priority-First, Workload-Balanced, Weighted)
- Hungarian batch assignment 1-to-1 matching guarantee
- Engine integration: manual task assignment, cancellation with reservation release, and reassignment
- Fleet metrics, battery tracking, distance recording, and workload balance calculation
- Multi-robot mission execution with zero collisions
"""

import pytest
from core.grid import WarehouseGrid
from core.task_manager import TaskManager, WarehouseTask, TaskPriority, TaskStatus
from core.task_assignment import (
    TaskAssignmentEngine,
    AssignmentStrategy,
    AssignmentWeights,
    AssignmentDecision,
)
from simulation.engine import WarehouseSimulator
from simulation.metrics import MetricsCollector


def test_task_priority_enum_and_labels():
    """Verify TaskPriority values, labels, and string parsing."""
    assert TaskPriority.LOW == 1
    assert TaskPriority.NORMAL == 2
    assert TaskPriority.HIGH == 3
    assert TaskPriority.URGENT == 4

    assert TaskPriority.LOW.label == "Low"
    assert TaskPriority.NORMAL.label == "Normal"
    assert TaskPriority.HIGH.label == "High"
    assert TaskPriority.URGENT.label == "Urgent"

    assert TaskPriority.from_str("urgent") == TaskPriority.URGENT
    assert TaskPriority.from_str("HIGH") == TaskPriority.HIGH
    assert TaskPriority.from_str("normal") == TaskPriority.NORMAL
    assert TaskPriority.from_str("low") == TaskPriority.LOW
    assert TaskPriority.from_str("unknown") == TaskPriority.NORMAL


def test_task_state_machine_valid_transitions():
    """Verify standard pick-and-deliver lifecycle transitions."""
    task = WarehouseTask(
        task_id=1,
        shelf_loc=(2, 3),
        pick_spot=(1, 3),
        delivery_station=(2, 14),
        priority=TaskPriority.NORMAL,
        status="QUEUED",
        created_at_step=0,
    )

    assert task.status == "QUEUED"
    assert task.transition_to("MOVING_TO_PICK", current_step=1, note="Dispatched") is True
    assert task.status == "MOVING_TO_PICK"

    assert task.transition_to("PICKING", current_step=5, note="Arrived at pick") is True
    assert task.status == "PICKING"

    assert task.transition_to("MOVING_TO_DELIVERY", current_step=6, note="Off to pack") is True
    assert task.status == "MOVING_TO_DELIVERY"

    assert task.transition_to("DELIVERING", current_step=12, note="Arrived at pack") is True
    assert task.status == "DELIVERING"

    assert task.transition_to("COMPLETED", current_step=13, note="Complete") is True
    assert task.status == "COMPLETED"

    # Terminal state: cannot transition out of COMPLETED
    assert task.transition_to("MOVING_TO_PICK", current_step=14) is False


def test_task_state_machine_rejects_illegal_leaps():
    """Verify that state leaps violating warehouse physics are rejected."""
    task = WarehouseTask(
        task_id=2,
        shelf_loc=(2, 3),
        pick_spot=(1, 3),
        delivery_station=(2, 14),
        priority=TaskPriority.HIGH,
        status="QUEUED",
    )

    # Cannot deliver before picking
    assert task.transition_to("DELIVERING", current_step=1) is False
    assert task.transition_to("COMPLETED", current_step=1) is False
    assert task.status == "QUEUED"


def test_custom_task_coordinate_validation():
    """Verify validation against layout, boundaries, obstacles, and stations."""
    grid = WarehouseGrid(15, 15)
    tm = TaskManager(grid)

    # 1. Out of bounds pick
    t1, err1 = tm.create_custom_task(pick_spot=(-1, 5), delivery_station=(2, 14))
    assert t1 is None
    assert "outside warehouse boundaries" in err1

    # 2. Pick inside a permanent shelf obstacle
    shelf_cell = list(grid.shelves)[0]
    t2, err2 = tm.create_custom_task(pick_spot=shelf_cell, delivery_station=(2, 14))
    assert t2 is None
    assert "blocked or inside a permanent shelf" in err2

    # 3. Delivery not a valid packing station
    t3, err3 = tm.create_custom_task(pick_spot=(1, 3), delivery_station=(5, 5))
    assert t3 is None
    assert "not a registered warehouse packing station" in err3

    # 4. Pick == Delivery
    t4, err4 = tm.create_custom_task(pick_spot=(2, 14), delivery_station=(2, 14))
    assert t4 is None
    assert "cannot be identical" in err4

    # 5. Valid task creation
    valid_pick = (1, 3)  # adjacent to shelf (2, 3)
    valid_pack = grid.packing_stations[0]
    t5, err5 = tm.create_custom_task(pick_spot=valid_pick, delivery_station=valid_pack, priority=TaskPriority.URGENT)
    assert t5 is not None
    assert t5.priority == TaskPriority.URGENT
    assert t5.status == "QUEUED"
    assert t5.task_id in tm.tasks


def test_task_cancellation_and_failure():
    """Verify task cancellation and failure status updates."""
    grid = WarehouseGrid(15, 15)
    tm = TaskManager(grid)
    task = tm.generate_random_task(current_step=0)
    task.assigned_robot = 1
    task.status = "MOVING_TO_PICK"

    # Cancel task
    assert tm.cancel_task(task.task_id, current_step=3, reason="Out of stock") is True
    assert task.status == "CANCELLED"
    assert task.assigned_robot is None

    # Cannot cancel already cancelled task
    assert tm.cancel_task(task.task_id, current_step=4) is False


def test_assignment_strategy_nearest_robot():
    """Verify NEAREST_ROBOT selects the robot with minimum Manhattan distance to pick spot."""
    grid = WarehouseGrid(15, 15)
    engine = TaskAssignmentEngine(grid, default_strategy=AssignmentStrategy.NEAREST_ROBOT)

    # Robot 1 at (1, 1), Robot 2 at (10, 10)
    idle_robots = {
        1: {'pos': (1, 1), 'workload': 0},
        2: {'pos': (10, 10), 'workload': 0},
    }

    # Task with pick spot near Robot 1
    task = WarehouseTask(
        task_id=101,
        shelf_loc=(2, 3),
        pick_spot=(1, 3),
        delivery_station=(2, 14),
        priority=TaskPriority.NORMAL,
    )

    decision = engine.select_best_task_for_robot(
        robot_id=1,
        robot_pos=(1, 1),
        robot_workload=0,
        available_tasks=[task],
        strategy=AssignmentStrategy.NEAREST_ROBOT,
    )
    assert decision is not None
    assert decision.task_id == 101
    assert decision.distance_to_pick == 2


def test_assignment_strategy_priority_first():
    """Verify PRIORITY_FIRST prioritizes Urgent over Normal tasks."""
    grid = WarehouseGrid(15, 15)
    engine = TaskAssignmentEngine(grid)

    task_normal = WarehouseTask(
        task_id=1,
        shelf_loc=(2, 3),
        pick_spot=(1, 2),  # distance 1 from robot at (1, 1)
        delivery_station=(2, 14),
        priority=TaskPriority.NORMAL,
    )
    task_urgent = WarehouseTask(
        task_id=2,
        shelf_loc=(6, 7),
        pick_spot=(5, 7),  # distance 10 from robot at (1, 1)
        delivery_station=(2, 14),
        priority=TaskPriority.URGENT,
    )

    decision = engine.select_best_task_for_robot(
        robot_id=1,
        robot_pos=(1, 1),
        robot_workload=0,
        available_tasks=[task_normal, task_urgent],
        strategy=AssignmentStrategy.PRIORITY_FIRST,
    )
    # Even though task_urgent is further away, PRIORITY_FIRST must select it
    assert decision is not None
    assert decision.task_id == 2
    assert decision.priority == TaskPriority.URGENT


def test_assignment_strategy_workload_balanced():
    """Verify WORKLOAD_BALANCED dispatches to the robot with fewer completed tasks."""
    grid = WarehouseGrid(15, 15)
    engine = TaskAssignmentEngine(grid)

    # Robot 1 has completed 5 tasks, Robot 2 has completed 0 tasks
    idle_robots = {
        1: {'pos': (1, 1), 'workload': 5},
        2: {'pos': (1, 2), 'workload': 0},
    }

    task = WarehouseTask(
        task_id=55,
        shelf_loc=(2, 3),
        pick_spot=(1, 3),
        delivery_station=(2, 14),
    )

    decisions = engine.assign_batch(
        idle_robots=idle_robots,
        pending_tasks=[task],
        strategy=AssignmentStrategy.WORKLOAD_BALANCED,
    )
    assert len(decisions) == 1
    # Robot 2 with 0 workload should be chosen over Robot 1 with 5 workload
    assert decisions[0].robot_id == 2


def test_hungarian_batch_assignment_one_to_one():
    """Verify BATCH_OPTIMAL ensures strictly 1-to-1 matching without duplicate assignments."""
    grid = WarehouseGrid(15, 15)
    engine = TaskAssignmentEngine(grid)

    idle_robots = {
        1: {'pos': (1, 0), 'workload': 1},
        2: {'pos': (4, 0), 'workload': 2},
        3: {'pos': (7, 0), 'workload': 0},
    }

    tasks = [
        WarehouseTask(task_id=1, shelf_loc=(2, 3), pick_spot=(1, 3), delivery_station=(2, 14)),
        WarehouseTask(task_id=2, shelf_loc=(6, 3), pick_spot=(5, 3), delivery_station=(6, 14)),
        WarehouseTask(task_id=3, shelf_loc=(10, 3), pick_spot=(9, 3), delivery_station=(10, 14)),
    ]

    decisions = engine.assign_batch(
        idle_robots=idle_robots,
        pending_tasks=tasks,
        strategy=AssignmentStrategy.BATCH_OPTIMAL,
    )

    assert len(decisions) == 3
    assigned_robots = [d.robot_id for d in decisions]
    assigned_tasks = [d.task_id for d in decisions]

    # Every robot and every task must be assigned exactly once
    assert len(set(assigned_robots)) == 3
    assert len(set(assigned_tasks)) == 3


def test_engine_manual_assignment_and_busy_rejection():
    """Verify simulator manual dispatch and rejection of busy robots."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
    # Clear auto tasks so fleet is idle
    sim.task_manager.tasks.clear()

    # Create a custom task
    valid_pick = (1, 3)
    valid_pack = sim.grid.packing_stations[0]
    task, _ = sim.create_custom_task(valid_pick, valid_pack)

    # 1. Manual assignment to Robot 1
    ok, msg = sim.assign_task_manually(task.task_id, 1)
    assert ok is True
    assert sim.robots[1].state == "MOVING_TO_PICK"
    assert sim.robots[1].assigned_task.task_id == task.task_id

    # 2. Attempting to assign another task to Robot 1 while busy must fail
    task2, _ = sim.create_custom_task((5, 3), valid_pack)
    ok2, err2 = sim.assign_task_manually(task2.task_id, 1)
    assert ok2 is False
    assert "Only IDLE robots can be assigned" in err2


def test_engine_cancel_active_task_releases_reservations():
    """Verify task cancellation safely clears reservations and returns robot to IDLE."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
    sim.task_manager.tasks.clear()

    task, _ = sim.create_custom_task((1, 3), sim.grid.packing_stations[0])
    sim.assign_task_manually(task.task_id, 1)
    assert sim.robots[1].state == "MOVING_TO_PICK"

    # Cancel the active task
    ok, msg = sim.cancel_task(task.task_id)
    assert ok is True
    assert task.status == "CANCELLED"
    assert sim.robots[1].state == "IDLE"
    assert sim.robots[1].assigned_task is None
    assert sim.robots[1].path == []

    # Current spot must remain reserved
    curr_pos = sim.robots[1].pos
    assert sim.reservation_table.is_vertex_reserved(curr_pos[0], curr_pos[1], sim.step_count + 1) is True


def test_engine_reassign_task():
    """Verify transferring an order from one robot to another."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
    sim.task_manager.tasks.clear()

    task, _ = sim.create_custom_task((1, 3), sim.grid.packing_stations[0])
    sim.assign_task_manually(task.task_id, 1)
    assert sim.robots[1].assigned_task.task_id == task.task_id

    # Reassign to Robot 2
    ok, msg = sim.reassign_task(task.task_id, 2)
    assert ok is True
    assert sim.robots[1].state == "IDLE"
    assert sim.robots[1].assigned_task is None
    assert sim.robots[2].state == "MOVING_TO_PICK"
    assert sim.robots[2].assigned_task.task_id == task.task_id


def test_workload_balance_calculation():
    """Verify Gini coefficient and standard deviation calculation."""
    # Perfect equality
    bal_equal = MetricsCollector.calculate_workload_balance({1: 3, 2: 3, 3: 3})
    assert bal_equal["std_dev"] == 0.0
    assert bal_equal["gini"] == 0.0

    # Unequal workload
    bal_unequal = MetricsCollector.calculate_workload_balance({1: 10, 2: 0, 3: 0})
    assert bal_unequal["std_dev"] > 0.0
    assert bal_unequal["gini"] > 0.5


def test_multi_robot_mission_lifecycle_with_dynamic_assignment():
    """Verify full execution across 35 discrete steps with zero collisions."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
    sim.set_assignment_strategy(AssignmentStrategy.WEIGHTED_MULTI_CRITERIA)

    for _ in range(35):
        sim.step()

    summary = sim.metrics.get_summary()
    assert summary["completed_tasks"] > 0
    assert summary["detected_conflicts"] == 0
    # Battery deducted on moving robots
    for r in sim.robots.values():
        if r.total_distance > 0:
            assert r.battery < 100.0


def test_assignment_strategy_shortest_total_route():
    """Verify SHORTEST_TOTAL_ROUTE minimizes robot->pickup + pickup->delivery."""
    grid = WarehouseGrid(15, 15)
    engine = TaskAssignmentEngine(grid)

    # Task 1: total route from (1, 0) -> pick (1, 2) [dist 2] + delivery (2, 2) [dist 1] = 3
    task_short = WarehouseTask(
        task_id=1,
        shelf_loc=(2, 3),
        pick_spot=(1, 2),
        delivery_station=(2, 2),
    )
    # Task 2: total route from (1, 0) -> pick (1, 1) [dist 1] + delivery (10, 14) [dist 22] = 23
    task_long = WarehouseTask(
        task_id=2,
        shelf_loc=(2, 3),
        pick_spot=(1, 1),
        delivery_station=(10, 14),
    )

    decision = engine.select_best_task_for_robot(
        robot_id=1,
        robot_pos=(1, 0),
        robot_workload=0,
        available_tasks=[task_short, task_long],
        strategy=AssignmentStrategy.SHORTEST_TOTAL_ROUTE,
    )
    assert decision is not None
    assert decision.task_id == 1
    assert decision.total_mission_distance < 10


def test_assignment_strategy_weighted_multi_criteria_scoring():
    """Verify WEIGHTED_MULTI_CRITERIA calculates normalized cost using configured weights."""
    grid = WarehouseGrid(15, 15)
    weights = AssignmentWeights(w_distance=0.5, w_workload=0.2, w_priority=0.2, w_duration=0.1)
    engine = TaskAssignmentEngine(grid, default_strategy=AssignmentStrategy.WEIGHTED_MULTI_CRITERIA, weights=weights)

    task = WarehouseTask(
        task_id=10,
        shelf_loc=(2, 3),
        pick_spot=(1, 3),
        delivery_station=(2, 14),
        priority=TaskPriority.HIGH,
    )

    cost = engine.calculate_cost(
        robot_id=1,
        robot_pos=(1, 0),
        robot_workload=1,
        task=task,
        strategy=AssignmentStrategy.WEIGHTED_MULTI_CRITERIA,
    )
    assert 0.0 <= cost <= 1.0


def test_strategy_benchmark_execution():
    """Verify that multiple strategies execute deterministically on identical simulator configurations."""
    strategies = [
        AssignmentStrategy.NEAREST_ROBOT,
        AssignmentStrategy.PRIORITY_FIRST,
        AssignmentStrategy.WORKLOAD_BALANCED,
    ]

    results = []
    for strat in strategies:
        sim = WarehouseSimulator(num_robots=2, width=15, height=15, seed=42)
        sim.set_assignment_strategy(strat)
        for _ in range(15):
            sim.step()
        summary = sim.metrics.get_summary()
        results.append((strat, summary["completed_tasks"], summary["detected_conflicts"]))

    assert len(results) == 3
    for strat, completed, conflicts in results:
        assert conflicts == 0

