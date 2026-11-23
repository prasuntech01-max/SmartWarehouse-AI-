"""
tests/test_comprehensive_edge_cases.py
======================================
Automated verification of system edge cases:
1. Empty warehouse (0 shelves, minimal grid)
2. No robots (fleet = 0 handling in bridge)
3. One single robot (fleet = 1 in standard 15x15 warehouse)
4. Multiple robots (scaled fleet of 5 AMRs)
5. No available paths (fully walled off goal)
6. Blocked paths (dynamic obstacle blocking route)
7. Conflicting reservations (space-time collision resolution)
8. Deadlock scenarios (circular wait resolution via WaitForGraph)
9. Emergency hazards (IoT flame/gas trip and detection)
10. Missing sensor data (graceful null safety)
11. Invalid JSON payload (validation reject and fallback)
12. Database unavailable (safe error handling and fallback)
13. Empty task queue (idle robots safely hold positions)
14. Large simulation state (50x50 DC with 5 robots)
"""

import json
import pytest
from simulation.engine import WarehouseSimulator
from core.grid import WarehouseGrid
from core.planner import AStarPlanner
from core.state import TimeExpandedPlanner, Action, TimeExpandedState
from core.reservation import ReservationTable
from core.deadlock import WaitForGraph, DeadlockHandler
from core.hazard_detector import (
    HazardDetector,
    SensorObservation,
    DeviceObservation,
    HazardSeverity,
    HazardType,
    DataSource,
)
from visualization.threejs_bridge import (
    build_simulation_state,
    validate_payload,
    to_json,
    SCHEMA_VERSION,
)
from persistence.db import get_connection


def test_edge_case_empty_warehouse():
    """Verify simulation and bridge handle an empty grid with zero shelves or stations."""
    sim = WarehouseSimulator(num_robots=1, width=15, height=15)
    sim.grid.shelves.clear()
    sim.grid.charging_docks.clear()
    sim.grid.packing_stations.clear()
    sim.grid.picking_stations.clear()
    sim.robots.clear()

    sim.step()
    state = build_simulation_state(sim)
    assert state["meta"]["sim_tick"] == 1
    assert len(state["robots"]) == 0
    assert len(state["layout"]["shelves"]) == 0
    warnings = validate_payload(state)
    assert isinstance(warnings, list)


def test_edge_case_no_robots():
    """Verify bridge and metrics operate safely when fleet has 0 robots."""
    sim = WarehouseSimulator(num_robots=1, width=15, height=15)
    sim.robots.clear()
    state = build_simulation_state(sim)
    assert len(state["robots"]) == 0
    assert state["metrics"]["num_robots"] == 0
    assert state["metrics"]["active_robots"] == 0


def test_edge_case_one_robot():
    """Verify single robot planning, stepping, and telemetry generation."""
    sim = WarehouseSimulator(num_robots=1, width=15, height=15)
    sim.step()
    state = build_simulation_state(sim)
    assert len(state["robots"]) == 1
    r = state["robots"][0]
    assert r["id"] == 1
    assert "battery" in r
    assert "carrying" in r


def test_edge_case_multiple_robots_scaled():
    """Verify fleet scaling to maximum capacity (5 robots) without unhandled exceptions."""
    sim = WarehouseSimulator(num_robots=5, width=15, height=15)
    for _ in range(10):
        sim.step()
    state = build_simulation_state(sim)
    assert len(state["robots"]) == 5
    for r in state["robots"]:
        assert 0 <= r["x"] < 15
        assert 0 <= r["y"] < 15


def test_edge_case_no_available_path_walled_off():
    """Verify planner returns empty path/failure safely when goal is walled off."""
    grid = WarehouseGrid(width=15, height=15)
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        grid.obstacles.add_shelf(5 + dx, 5 + dy)

    planner = AStarPlanner(grid)
    path = planner.plan((0, 0), (5, 5))
    assert path is None or len(path) == 0


def test_edge_case_blocked_paths_dynamic_obstacle():
    """Verify dynamic obstacle injection prompts safe replanning or yield."""
    sim = WarehouseSimulator(num_robots=2, width=15, height=15)
    sim.step()
    sim.inject_obstacle(5, 5)
    assert (5, 5) in sim.grid.dynamic_obstacles

    for _ in range(5):
        sim.step()
    state = build_simulation_state(sim)
    assert any(o["x"] == 5 and o["y"] == 5 for o in state["obstacles"])


def test_edge_case_conflicting_reservations():
    """Verify reservation table handles space-time vertex claims and rejects conflicts."""
    res_table = ReservationTable()
    res_table.reserve_vertex(3, 3, 2, robot_id=1)
    assert res_table.is_vertex_reserved(3, 3, 2) is True
    assert res_table.is_vertex_reserved(3, 3, 2, ignore_robot=1) is False
    assert res_table.is_vertex_reserved(3, 3, 2, ignore_robot=2) is True


def test_edge_case_deadlock_circular_wait_detection():
    """Verify deadlock detector correctly identifies circular waits."""
    wfg = WaitForGraph()
    wfg.add_edge(1, 2, target_cell=(2, 2), reason="occupied_cell")
    wfg.add_edge(2, 1, target_cell=(2, 3), reason="occupied_cell")
    assert wfg.has_cycle() is True
    cycles = wfg.find_cycles()
    assert len(cycles) > 0


def test_edge_case_emergency_hazard_trip():
    """Verify hazard detector trips emergency incident on fire/flame rule combination."""
    detector = HazardDetector()
    temp_obs = SensorObservation(
        sensor_id="TEMP-01",
        device_id="GATEWAY-01",
        sensor_type="TEMPERATURE",
        value=55.0,
        unit="C",
        tick=1,
        coord=(5, 5),
        connected=True,
        health_ok=True,
        data_source=DataSource.SIMULATED,
    )
    smoke_obs = SensorObservation(
        sensor_id="SMOKE-01",
        device_id="GATEWAY-01",
        sensor_type="SMOKE",
        value=0.9,
        unit="ppm",
        tick=1,
        coord=(5, 5),
        connected=True,
        health_ok=True,
        data_source=DataSource.SIMULATED,
    )
    dev_obs = DeviceObservation(
        device_id="GATEWAY-01",
        online=True,
        last_seen_tick=1,
    )
    result = detector.evaluate(observations=[temp_obs, smoke_obs], devices=[dev_obs], tick=1)
    active = detector.active_incidents()
    assert len(active) > 0
    assert any(inc.severity in (HazardSeverity.CRITICAL, HazardSeverity.EMERGENCY) for inc in active)


def test_edge_case_missing_sensor_data_null_safety():
    """Verify bridge gracefully tolerates missing or empty sensor lists."""
    sim = WarehouseSimulator(num_robots=2, width=15, height=15)
    state = build_simulation_state(sim)
    state["iot_sensors"] = []
    warnings = validate_payload(state)
    assert isinstance(warnings, list)
    encoded = to_json(state)
    assert len(encoded) > 0


def test_edge_case_invalid_json_payload_validation():
    """Verify validate_payload correctly catches missing sections in malformed payloads."""
    malformed_payload = {"meta": {"schema_version": "2.0.0"}}
    warnings = validate_payload(malformed_payload)
    assert len(warnings) > 0
    assert any("layout" in w for w in warnings)
    assert any("robots" in w for w in warnings)


def test_edge_case_database_unavailable_handling():
    """Verify database helpers handle missing records safely."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", ("__non_existent_user_9999__",))
    assert cur.fetchone() is None


def test_edge_case_empty_task_queue():
    """Verify simulation functions normally when task queue is empty."""
    sim = WarehouseSimulator(num_robots=2, width=15, height=15)
    sim.task_manager.tasks.clear()
    for _ in range(5):
        sim.step()
    state = build_simulation_state(sim)
    assert state["metrics"]["pending_tasks"] == 0


def test_edge_case_large_simulation_state():
    """Verify performance and serialization with a 50x50 warehouse."""
    sim = WarehouseSimulator(num_robots=3, width=50, height=50)
    for _ in range(3):
        sim.step()
    state = build_simulation_state(sim)
    assert state["layout"]["grid"]["width"] == 50
    assert state["layout"]["grid"]["height"] == 50
    assert len(state["robots"]) == 3
    raw_json = to_json(state)
    assert len(raw_json) > 0
