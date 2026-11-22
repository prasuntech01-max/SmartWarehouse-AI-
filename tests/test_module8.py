"""Comprehensive tests for Module 8: Dynamic Replanning & Obstacle Management.

Covers:
- Dynamic obstacle event lifecycle & path intersection detection
- Atomic dynamic replanning with reservation updates
- Safe waiting and rollback upon blocked conditions
- Replan telemetry and metric tracking
- Collision-free multi-robot execution post-replan
- Accurate conflict detection with park_at_goal=False for active paths
- Protection of stationary, idle, and docked robots
- Deterministic evaluation demo execution
"""

import pytest
from core.grid import WarehouseGrid
from core.obstacle_manager import DynamicObstacleManager, ObstacleEvent
from core.reservation import ReservationTable
from core.replanner import DynamicReplanner, ReplanEvent
from core.conflict import MultiRobotConflictDetector, ConflictType
from core.multi_agent import MultiAgentPlanner
from simulation.engine import WarehouseSimulator
from simulation.metrics import MetricsCollector
from simulation.demo import DemoScenario, DemoResult


def test_obstacle_event_creation_and_history():
    """Verify obstacle event tracking and history logging."""
    dom = DynamicObstacleManager()
    assert dom.active_count == 0
    assert dom.total_events == 0

    ev1 = dom.add_obstacle((3, 4), current_time=10, reason="test_spill")
    assert ev1.obstacle_id == 1
    assert ev1.pos == (3, 4)
    assert ev1.activated_at == 10
    assert ev1.status == 'active'
    assert ev1.removed_at is None
    assert dom.active_count == 1
    assert dom.total_events == 1

    ev2 = dom.add_obstacle((5, 6), current_time=12, reason="forklift_stop")
    assert ev2.obstacle_id == 2
    assert dom.active_count == 2
    assert dom.total_events == 2

    history = dom.get_history()
    assert len(history) == 2
    assert history[0].obstacle_id == 1
    assert history[1].obstacle_id == 2


def test_obstacle_removal_by_id_and_coords():
    """Verify obstacle deactivation by ID and by coordinates."""
    dom = DynamicObstacleManager()
    ev1 = dom.add_obstacle((2, 3), current_time=5)
    ev2 = dom.add_obstacle((4, 5), current_time=6)

    # Remove by ID
    assert dom.remove_obstacle(ev1.obstacle_id, current_time=15) is True
    assert dom.active_count == 1
    assert ev1.status == 'removed'
    assert ev1.removed_at == 15
    assert (2, 3) not in dom.get_active_positions()

    # Remove by coordinate
    assert dom.remove_obstacle_at((4, 5), current_time=20) is True
    assert dom.active_count == 0
    assert ev2.status == 'removed'
    assert ev2.removed_at == 20

    # Removing non-existent obstacle returns False
    assert dom.remove_obstacle(999, current_time=25) is False
    assert dom.remove_obstacle_at((9, 9), current_time=25) is False


def test_path_intersection_detection():
    """Verify detection of dynamic obstacles intersecting robot planned paths."""
    dom = DynamicObstacleManager()
    ev1 = dom.add_obstacle((2, 2), current_time=0)
    ev2 = dom.add_obstacle((8, 8), current_time=0)

    # Robot 1 path passes through (2, 2)
    path_r1 = [(0, 2), (1, 2), (2, 2), (3, 2), (4, 2)]
    # Robot 2 path avoids all obstacles
    path_r2 = [(0, 0), (1, 0), (2, 0), (3, 0)]

    intersections = dom.detect_path_intersections({1: path_r1, 2: path_r2})
    assert 1 in intersections
    assert len(intersections[1]) == 1
    assert intersections[1][0].pos == (2, 2)
    assert 2 not in intersections


def test_multiple_robots_affected_by_single_obstacle():
    """Verify that multiple robots planning to cross the same cell are all detected."""
    dom = DynamicObstacleManager()
    dom.add_obstacle((5, 5), current_time=10)

    path1 = [(5, 2), (5, 3), (5, 4), (5, 5), (5, 6)]
    path2 = [(2, 5), (3, 5), (4, 5), (5, 5), (6, 5)]

    intersections = dom.detect_path_intersections({1: path1, 2: path2})
    assert 1 in intersections
    assert 2 in intersections


def test_replanner_single_robot_success():
    """Verify that replanner successfully routes around an unexpected obstacle."""
    grid = WarehouseGrid(15, 15)
    rt = ReservationTable()
    replanner = DynamicReplanner(grid, rt)

    start = (1, 1)
    goal = (1, 5)
    # Block direct path at (1, 3)
    grid.add_dynamic_obstacle(1, 3)

    new_path, latency, success = replanner.replan_single_robot(
        robot_id=1,
        curr_pos=start,
        goal=goal,
        current_time=0,
        old_path_len=5,
    )

    assert success is True
    assert new_path is not None
    assert (1, 3) not in new_path
    assert new_path[0] == start
    assert new_path[-1] == goal
    assert len(replanner.replan_history) == 1
    assert replanner.replan_history[0].success is True


def test_replanner_blocked_safe_waiting():
    """Verify that a robot completely trapped/blocked falls back to safe waiting."""
    grid = WarehouseGrid(5, 5, auto_layout=False)
    rt = ReservationTable()
    replanner = DynamicReplanner(grid, rt)

    curr_pos = (1, 1)
    goal = (3, 3)

    # Trap robot completely
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        grid.add_dynamic_obstacle(curr_pos[0] + dx, curr_pos[1] + dy)

    fallback_path, latency, success = replanner.replan_single_robot(
        robot_id=1,
        curr_pos=curr_pos,
        goal=goal,
        current_time=5,
        old_path_len=4,
    )

    assert success is False
    assert fallback_path == [curr_pos]
    # Check that stationary spot is reserved in reservation table
    assert rt.is_vertex_reserved(curr_pos[0], curr_pos[1], 6) is True
    assert replanner.replan_history[-1].success is False


def test_metrics_replan_attempt_and_success_rate():
    """Verify MetricsCollector Module 8 telemetry."""
    mc = MetricsCollector()
    assert mc.replan_success_rate == 100.0

    mc.record_replan_attempt(robot_id=1, success=True, path_delta=2.0, latency_ms=1.5)
    mc.record_replan_attempt(robot_id=2, success=True, path_delta=0.0, latency_ms=2.0)
    mc.record_replan_attempt(robot_id=3, success=False, path_delta=0.0, latency_ms=3.0)

    assert mc.replan_attempts == 3
    assert mc.replan_successes == 2
    assert mc.replan_failures == 1
    assert mc.replan_success_rate == 66.7
    assert mc.replan_distance_added[1] == 2.0

    analytics = mc.get_replan_analytics()
    assert 'replan_attempts' in analytics
    assert 'replan_success_rate' in analytics
    assert analytics['replan_attempts'] == 3


def test_engine_dynamic_obstacle_injection_and_metrics():
    """Verify simulator dynamic obstacle injection updates obstacle manager and metrics."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
    # Warmup 3 steps
    for _ in range(3):
        sim.step()

    # Find a free walkable cell not occupied by a robot or active goal
    robot_positions = {r.pos for r in sim.robots.values()}
    robot_goals = {r.goal for r in sim.robots.values() if r.goal is not None}
    test_x, test_y = 5, 5
    while (test_x, test_y) in robot_positions or (test_x, test_y) in sim.grid.shelves or (test_x, test_y) in robot_goals:
        test_x += 1

    success, msg = sim.inject_obstacle(test_x, test_y)
    assert success is True
    assert (test_x, test_y) in sim.grid.dynamic_obstacles
    assert sim.obstacle_manager.active_count >= 1
    assert sim.metrics.obstacle_events_count == 1

    # Clear obstacles
    sim.clear_dynamic_obstacles()
    assert len(sim.grid.dynamic_obstacles) == 0
    assert sim.obstacle_manager.active_count == 0


def test_conflict_check_park_at_goal_false_eliminates_station_false_positives():
    """
    Verify that park_at_goal=False prevents false positives when multiple robots
    visit the same delivery station at separate disjoint timesteps.
    """
    wh = WarehouseGrid(15, 15)
    detector = MultiRobotConflictDetector(warehouse=wh)

    # Robot 1 arrives at (2, 14) at t=4
    p1 = [(2, 10), (2, 11), (2, 12), (2, 13), (2, 14)]
    # Robot 2 arrives at (2, 14) at t=10 (6 steps after Robot 1 left)
    p2 = [(5, 14), (4, 14), (3, 14), (2, 14)]
    start_times = {1: 0, 2: 7}  # R2 starts at t=7, arrives at (2, 14) at t=10

    # With park_at_goal=True: R1's arrival at t=4 is extended to t=10, causing conflict
    c_true = detector.detect_conflicts({1: p1, 2: p2}, start_times=start_times, park_at_goal=True)
    assert len(c_true) >= 1

    # With park_at_goal=False: accurately recognizes that R1 is not at (2, 14) at t=10
    c_false = detector.detect_conflicts({1: p1, 2: p2}, start_times=start_times, park_at_goal=False)
    assert len(c_false) == 0


def test_conflict_check_preserves_genuine_collisions_with_park_at_goal_false():
    """Verify that genuine vertex and edge-swap collisions are detected with park_at_goal=False."""
    wh = WarehouseGrid(15, 15)
    detector = MultiRobotConflictDetector(warehouse=wh)

    # Genuine Vertex Collision at (2, 2) at t=2
    p1 = [(0, 2), (1, 2), (2, 2), (3, 2)]
    p2 = [(2, 0), (2, 1), (2, 2), (2, 3)]
    c_vert = detector.detect_conflicts({1: p1, 2: p2}, park_at_goal=False)
    assert len(c_vert) == 1
    assert c_vert[0].conflict_type == ConflictType.VERTEX
    assert c_vert[0].location_a == (2, 2)
    assert c_vert[0].time_step == 2

    # Genuine Edge-Swap Collision at t=1 -> t=2
    p3 = [(1, 0), (2, 0), (3, 0)]
    p4 = [(4, 0), (3, 0), (2, 0)]
    c_swap = detector.detect_conflicts({3: p3, 4: p4}, park_at_goal=False)
    assert len(c_swap) == 1
    assert c_swap[0].conflict_type == ConflictType.EDGE_SWAP


def test_stationary_idle_docked_robot_protection():
    """Verify that idle and parked robots maintain vertex reservations preventing collisions."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
    # Clear tasks so robots remain stationary and idle at charging docks
    sim.task_manager.tasks.clear()

    dock_r1 = sim.robots[1].pos
    # Verify Robot 1's dock is reserved at step 0
    assert sim.reservation_table.is_vertex_reserved(dock_r1[0], dock_r1[1], 0) is True

    # Advance one step while idle
    sim.step()
    assert sim.step_count == 1

    # All 3 idle robots must have their stationary docks reserved at current time step
    for r_id, r in sim.robots.items():
        assert r.state == 'IDLE'
        assert sim.reservation_table.is_vertex_reserved(r.pos[0], r.pos[1], sim.step_count) is True


def test_collision_free_after_replanning():
    """Verify multi-robot execution remains collision-free after mid-route obstacle injection."""
    sim = WarehouseSimulator(num_robots=4, width=15, height=15, seed=42)

    # Run 5 steps
    for _ in range(5):
        sim.step()

    # Inject obstacle in an aisle
    sim.inject_obstacle(5, 7)

    # Run 30 steps post-injection
    for _ in range(30):
        sim.step()

    # Verify zero physical collisions occurred
    summary = sim.metrics.get_summary()
    assert summary['detected_conflicts'] == 0


def test_deterministic_demo_scenario():
    """Verify that the DemoScenario runs end-to-end and successfully alters planned routes."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
    result = DemoScenario.run_dynamic_obstacle_demo(sim, steps_before=5, steps_after=15)

    assert isinstance(result, DemoResult)
    assert result.success is True
    assert result.obstacle_pos is not None
    assert result.replan_latency_ms >= 0.0
    assert result.steps_after_obstacle > result.steps_before_obstacle
    # Old paths and new paths were recorded
    assert len(result.old_paths) > 0
    assert len(result.new_paths) > 0
