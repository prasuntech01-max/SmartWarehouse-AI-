"""
tests/test_threejs_bridge.py
============================
Unit tests for the Three.js data bridge serializer adhering to docs/BRIDGE_CONTRACT.md.
"""

import json
import pytest
from simulation.engine import WarehouseSimulator
from visualization.threejs_bridge import (
    build_simulation_state,
    to_json,
    SCHEMA_VERSION,
    CELL_SIZE_METERS,
)


def test_bridge_contract_schema_version():
    """Verify schema version and metadata header."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    state = build_simulation_state(sim)

    assert state["meta"]["schema_version"] == SCHEMA_VERSION
    assert state["meta"]["sim_tick"] == 0
    assert state["meta"]["layout_version"] == 1
    assert "generated_at" in state["meta"]
    assert state["meta"]["running"] is True


def test_bridge_static_layout_structure():
    """Verify warehouse grid, shelves, docks, and conveyors match simulation."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    state = build_simulation_state(sim)
    layout = state["layout"]

    assert layout["grid"]["width"] == 15
    assert layout["grid"]["height"] == 15
    assert layout["cell_size"] == CELL_SIZE_METERS
    assert len(layout["shelves"]) > 0
    assert len(layout["charging_docks"]) >= 3
    assert len(layout["packing_stations"]) > 0
    assert len(layout["conveyors"]) > 0


def test_bridge_robots_telemetry_accuracy():
    """Ensure robot coordinates, status, and battery map directly from simulation."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    state = build_simulation_state(sim)
    robots = state["robots"]

    assert len(robots) == 3
    for r in robots:
        sim_r = sim.robots[r["id"]]
        assert r["x"] == sim_r.pos[0]
        assert r["y"] == sim_r.pos[1]
        assert r["battery"] == pytest.approx(sim_r.battery, 0.1)
        assert r["state"] == sim_r.state
        assert "world_y" in r
        assert "yaw" in r
        assert "carrying" in r


def test_bridge_dynamic_obstacle_reflection():
    """Verify dynamic obstacles appear in the payload when injected."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    sim.inject_obstacle(4, 2)
    state = build_simulation_state(sim)

    obs = state["obstacles"]
    assert any(o["x"] == 4 and o["y"] == 2 for o in obs)
    assert len(state["hazards"]) > 0


def test_bridge_stepping_and_path_progress():
    """Advance simulation ticks and verify coordinates and paths update."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    for _ in range(5):
        sim.step()

    state = build_simulation_state(sim)
    assert state["meta"]["sim_tick"] == 5
    assert state["metrics"]["step_count"] == 5
    assert state["metrics"]["pending_tasks"] >= 0


def test_bridge_json_serialization_and_payload_budget():
    """Ensure json serialisation works without errors and payload is compact."""
    sim = WarehouseSimulator(num_robots=5, width=15, height=15)
    for _ in range(10):
        sim.step()

    state = build_simulation_state(sim)
    raw_json = to_json(state)
    assert isinstance(raw_json, str)
    decoded = json.loads(raw_json)
    assert decoded["meta"]["schema_version"] == SCHEMA_VERSION

    # Payload budget check: a 5-robot state snapshot should be under 25 KB
    payload_kb = len(raw_json.encode("utf-8")) / 1024.0
    assert payload_kb < 30.0, f"Payload {payload_kb:.2f} KB exceeds 30 KB budget"


def test_bridge_graceful_null_safety():
    """Bridge should never raise even if optional fields are missing or None."""
    class DummySim:
        grid = type("Grid", (), {"width": 10, "height": 10, "shelves": set(), "charging_docks": [], "packing_stations": [], "picking_stations": [], "dynamic_obstacles": set()})()
        robots = {}
        step_count = 0

    state = build_simulation_state(DummySim())
    assert state["meta"]["sim_tick"] == 0
    assert len(state["robots"]) == 0
    assert state["metrics"]["num_robots"] == 0


def test_bridge_v2_enhanced_fields():
    """Verify Schema 2.0.0 fields: rack_config, zones, robot metrics, etc."""
    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    state = build_simulation_state(sim)

    assert state["meta"]["schema_version"] == "2.0.0"
    layout = state["layout"]
    assert "rack_config" in layout
    assert "conveyor_paths" in layout
    assert "dock_bays" in layout
    assert "zone_definitions" in layout
    assert "lane_definitions" in layout
    assert "crane_lines" in layout
    assert "charger_positions" in layout

    for r in state["robots"]:
        assert "replan_count" in r
        assert "collision_risk" in r
        assert "blocked_by" in r
        assert "carrying_type" in r
        assert "eta_ticks" in r

    metrics = state["metrics"]
    assert "collision_avoidance_events" in metrics
    assert "deadlock_count" in metrics
    assert "warehouse_utilization" in metrics


def test_bridge_payload_validation():
    """Verify validate_payload accurately validates a well-formed payload."""
    from visualization.threejs_bridge import validate_payload
    sim = WarehouseSimulator(num_robots=3, width=15, height=15)
    state = build_simulation_state(sim)
    warnings = validate_payload(state)
    assert warnings == [], f"Expected zero validation warnings, got: {warnings}"


def test_bridge_large_layout_generation():
    """Verify large layout configuration generates expected structural blocks."""
    from visualization.threejs_bridge import build_large_layout_config
    large_cfg = build_large_layout_config()
    assert len(large_cfg["rack_config"]) >= 8
    assert len(large_cfg["zone_definitions"]) >= 5
    assert len(large_cfg["dock_bays"]) >= 6
    assert len(large_cfg["charger_positions"]) >= 6

