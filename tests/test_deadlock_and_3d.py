"""Comprehensive unit and integration tests for Module 7 (Deadlock Handling) and 3D Visualization."""

import pytest
import plotly.graph_objects as go
from warehouse import Warehouse
from core.reservation import ReservationTable
from core.state import TimeExpandedState, Action, Trajectory, TimeExpandedPlanner
from core.conflict import MultiRobotConflictDetector
from core.deadlock import (
    DeadlockHandler,
    WaitForGraph,
    DeadlockEvent,
)
from visualization.renderer_3d import Warehouse3DRenderer
from simulation.engine import RobotState, WarehouseSimulator


# ==========================================
# 1. WAIT-FOR GRAPH (WFG) & CYCLE DETECTION
# ==========================================
def test_wait_for_graph_empty_and_linear():
    wfg = WaitForGraph()
    assert wfg.has_cycle() is False
    assert wfg.find_cycles() == []

    # Linear chain: 1 -> 2 -> 3 (no cycle)
    wfg.add_edge(1, 2, target_cell=(1, 1), reason="occupied_cell")
    wfg.add_edge(2, 3, target_cell=(1, 2), reason="occupied_cell")
    assert wfg.has_cycle() is False
    assert wfg.find_cycles() == []


def test_wait_for_graph_2_robot_cycle():
    wfg = WaitForGraph()
    # 2 robots blocking each other: 1 -> 2 and 2 -> 1
    wfg.add_edge(1, 2, target_cell=(1, 1))
    wfg.add_edge(2, 1, target_cell=(1, 0))

    assert wfg.has_cycle() is True
    cycles = wfg.find_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {1, 2}


def test_wait_for_graph_3_robot_circular_wait():
    wfg = WaitForGraph()
    # Circular wait: 1 -> 2 -> 3 -> 1
    wfg.add_edge(1, 2, target_cell=(2, 2))
    wfg.add_edge(2, 3, target_cell=(2, 3))
    wfg.add_edge(3, 1, target_cell=(3, 2))

    assert wfg.has_cycle() is True
    cycles = wfg.find_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {1, 2, 3}


def test_wait_for_graph_building_from_live_states():
    wh = Warehouse(15, 15)
    table = ReservationTable()
    handler = DeadlockHandler(wh, table)

    # Robot 1 at (1, 0), wants to move to (1, 1)
    # Robot 2 at (1, 1), wants to move to (1, 0)
    robot_states = {
        1: {
            'pos': (1, 0),
            'goal': (1, 3),
            'path': [(1, 0), (1, 1), (1, 2), (1, 3)],
            'path_index': 0,
        },
        2: {
            'pos': (1, 1),
            'goal': (1, 0),
            'path': [(1, 1), (1, 0)],
            'path_index': 0,
        },
    }

    wfg = handler.build_wait_for_graph(robot_states, current_time=0)
    assert wfg.has_cycle() is True
    cycles = handler.detect_deadlocks(robot_states, current_time=0)
    assert len(cycles) == 1
    assert set(cycles[0]) == {1, 2}


# ==========================================
# 2. DEADLOCK RECOVERY STRATEGIES
# ==========================================
def test_deadlock_resolution_priority_elevation():
    wh = Warehouse(15, 15)
    table = ReservationTable()
    handler = DeadlockHandler(wh, table)

    # Robot 1 at (0, 1), wants to cross to (4, 1)
    # Robot 2 at (2, 0), wants to cross to (2, 2)
    # They contend at (2, 1)
    robot_states = {
        1: {'pos': (0, 1), 'goal': (4, 1), 'path': [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)], 'path_index': 0},
        2: {'pos': (2, 0), 'goal': (2, 2), 'path': [(2, 0), (2, 1), (2, 2)], 'path_index': 0},
    }

    success, new_paths, msg = handler.resolve_deadlock(
        cycle=[1, 2],
        robot_states=robot_states,
        current_time=0,
    )

    assert success is True
    assert 1 in new_paths and 2 in new_paths
    assert len(handler.event_log) == 1
    assert handler.event_log[0].success is True

    # Mathematical verification: 0 conflicts in resolved paths
    detector = MultiRobotConflictDetector(warehouse=wh)
    assert len(detector.detect_conflicts(new_paths)) == 0


def test_deadlock_resolution_evasive_yield_in_narrow_aisle():
    wh = Warehouse(7, 3, auto_layout=False)
    # 1-cell corridor at y=1
    for x in range(7):
        wh.obstacles.add_shelf(x, 0)
        wh.obstacles.add_shelf(x, 2)
    # Open turnout bay at (4, 0)
    wh.obstacles.remove_dynamic_obstacle(4, 0)
    wh.obstacles.shelves.remove((4, 0))

    table = ReservationTable()
    handler = DeadlockHandler(wh, table)

    # Robot 1 at (0, 1) wants to go to (6, 1)
    # Robot 2 at (6, 1) wants to go to (0, 1)
    robot_states = {
        1: {'pos': (0, 1), 'goal': (6, 1), 'path': [(0, 1), (1, 1), (2, 1)], 'path_index': 0},
        2: {'pos': (6, 1), 'goal': (0, 1), 'path': [(6, 1), (5, 1), (4, 1)], 'path_index': 0},
    }

    success, new_paths, msg = handler.resolve_deadlock(
        cycle=[1, 2],
        robot_states=robot_states,
        current_time=0,
    )

    assert success is True
    detector = MultiRobotConflictDetector(warehouse=wh)
    assert len(detector.detect_conflicts(new_paths)) == 0


def test_deadlock_event_logging():
    wh = Warehouse(15, 15)
    table = ReservationTable()
    handler = DeadlockHandler(wh, table)

    event = DeadlockEvent(
        event_id=1,
        timestamp=5,
        cycle=[1, 2],
        affected_robots=[1, 2],
        graph_edges={1: [2], 2: [1]},
        strategy_used="PRIORITY_ELEVATION",
        success=True,
        message="Cycle resolved",
        latency_ms=1.2,
    )
    d = event.to_dict()
    assert d["event_id"] == 1
    assert d["timestamp"] == 5
    assert d["cycle"] == [1, 2]
    assert d["strategy_used"] == "PRIORITY_ELEVATION"
    assert d["success"] is True


def test_repeated_deadlock_counter_tracking():
    wh = Warehouse(15, 15)
    table = ReservationTable()
    handler = DeadlockHandler(wh, table)

    robot_states = {
        1: {'pos': (0, 1), 'goal': (4, 1), 'path': [(0, 1), (1, 1)], 'path_index': 0},
        2: {'pos': (1, 1), 'goal': (0, 1), 'path': [(1, 1), (0, 1)], 'path_index': 0},
    }

    handler.resolve_deadlock(cycle=[1, 2], robot_states=robot_states, current_time=0)
    assert handler.robot_deadlock_counts[1] == 1
    assert handler.robot_deadlock_counts[2] == 1

    handler.resolve_deadlock(cycle=[1, 2], robot_states=robot_states, current_time=1)
    assert handler.robot_deadlock_counts[1] == 2
    assert handler.robot_deadlock_counts[2] == 2


# ==========================================
# 3. 3D VISUALIZATION TESTS
# ==========================================
def test_3d_renderer_empty_fleet():
    wh = Warehouse(15, 15)
    renderer_3d = Warehouse3DRenderer(wh)

    fig = renderer_3d.render_3d(robots={}, step_count=0)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 3  # Floor, gridlines, stations


def test_3d_renderer_running_simulation_and_deadlock_indicators():
    wh = Warehouse(15, 15)
    renderer_3d = Warehouse3DRenderer(wh)

    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    for _ in range(5):
        sim.step()

    # Render with deadlock warning active for robot 1 and 2
    fig = renderer_3d.render_3d(
        robots=sim.robots,
        step_count=sim.step_count,
        deadlock_cycles=[[1, 2]],
    )

    assert isinstance(fig, go.Figure)
    # Check that deadlock trace was created
    trace_names = [t.name for t in fig.data if hasattr(t, 'name')]
    assert "Deadlock Warning" in trace_names
    assert "Robot Fleet" in trace_names
    assert "Charging Docks" in trace_names
    assert "Packing Stations" in trace_names
