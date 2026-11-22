# -*- coding: utf-8 -*-
"""Tests for the HazardDetector implementation (Module 11 – Phase 2)."""

import pytest
from core.hazard_detector import (
    HazardDetector,
    HazardConfig,
    HazardType,
    HazardSeverity,
    IncidentStatus,
    SensorObservation,
    DeviceObservation,
    DataSource,
)

# Helper to create a sensor observation
def make_obs(
    sensor_id: str,
    device_id: str,
    sensor_type: str,
    value: float,
    tick: int,
    coord=(0, 0),
    connected=True,
    health_ok=True,
    data_source=DataSource.SIMULATED,
) -> SensorObservation:
    return SensorObservation(
        sensor_id=sensor_id,
        device_id=device_id,
        sensor_type=sensor_type,
        value=value,
        unit="unit",
        tick=tick,
        coord=coord,
        connected=connected,
        health_ok=health_ok,
        data_source=data_source,
    )

# Helper to create a device observation
def make_dev(device_id: str, online: bool, last_seen_tick: int) -> DeviceObservation:
    return DeviceObservation(device_id=device_id, online=online, last_seen_tick=last_seen_tick)

@pytest.fixture
def detector():
    # Use default config (demo thresholds) for simplicity
    return HazardDetector()

def test_normal_readings_do_not_create_incident(detector):
    obs = [
        make_obs("temp1", "dev1", "TEMPERATURE", 25.0, tick=1, coord=(1, 1)),
        make_obs("smoke1", "dev1", "SMOKE", 0.1, tick=1, coord=(1, 1)),
    ]
    devs = [make_dev("dev1", online=True, last_seen_tick=1)]
    result = detector.evaluate(obs, devs, tick=1)
    assert result.new == []
    assert detector.active_incidents() == []

def test_warning_severity_creates_incident(detector):
    # Temperature crossing warning threshold (30.0) -> 35.0 gives WARNING
    obs = [make_obs("temp1", "dev1", "TEMPERATURE", 35.0, tick=1, coord=(2, 2))]
    devs = [make_dev("dev1", True, 1)]
    # Need consecutive count: default critical_confirm=3, but warning still creates incident when severity != NORMAL
    # The detector treats any abnormal (severity!=NORMAL) with counters; for warning, count must reach critical_confirm as well.
    # So we feed three ticks to trigger.
    for t in range(1, 4):
        result = detector.evaluate(obs, devs, tick=t)
    # After 3 ticks, incident should exist with WARNING severity
    incs = detector.active_incidents()
    assert len(incs) == 1
    inc = incs[0]
    assert inc.hazard_type == HazardType.EXCESSIVE_TEMPERATURE
    assert inc.severity == HazardSeverity.WARNING
    assert inc.status == IncidentStatus.ACTIVE

def test_critical_severity_and_confirmation(detector):
    # Temperature above critical threshold (40.0) -> 42.0
    obs = [make_obs("temp1", "dev1", "TEMPERATURE", 42.0, tick=1, coord=(3, 3))]
    devs = [make_dev("dev1", True, 1)]
    # Need 3 consecutive abnormal readings (critical_confirm default=3)
    for t in range(1, 4):
        detector.evaluate(obs, devs, tick=t)
    inc = detector.active_incidents()[0]
    assert inc.severity == HazardSeverity.CRITICAL
    assert inc.hazard_type == HazardType.EXCESSIVE_TEMPERATURE

def test_emergency_confirmation_single_tick(detector):
    # Value above emergency threshold (45.0) -> 46.0
    obs = [make_obs("temp1", "dev1", "TEMPERATURE", 46.0, tick=1, coord=(4, 4))]
    devs = [make_dev("dev1", True, 1)]
    # emergency_confirm = 1, should create immediately
    result = detector.evaluate(obs, devs, tick=1)
    inc = detector.active_incidents()[0]
    assert inc.severity == HazardSeverity.EMERGENCY
    assert inc.hazard_type == HazardType.EXCESSIVE_TEMPERATURE
    # No need for further ticks

def test_fire_rule_combination(detector):
    cfg = HazardConfig(sole_sensor_override=False)
    detector = HazardDetector(config=cfg)
    # Provide temperature and smoke readings within radius and time window
    temp_obs = make_obs("temp1", "dev1", "TEMPERATURE", 50.0, tick=1, coord=(5, 5))
    smoke_obs = make_obs("smoke1", "dev1", "SMOKE", 0.9, tick=1, coord=(6, 5))  # Manhattan distance 1
    devs = [make_dev("dev1", True, 1)]
    detector.evaluate([temp_obs, smoke_obs], devs, tick=1)
    # Fire incident should be created
    fire_incs = [i for i in detector.active_incidents() if i.hazard_type == HazardType.FIRE]
    assert len(fire_incs) == 1
    fire = fire_incs[0]
    assert fire.severity == HazardSeverity.EMERGENCY
    assert fire.status == IncidentStatus.ACTIVE

def test_device_offline_creates_disconnection_incident(detector):
    # Device goes offline after heartbeat
    dev_obs = [make_dev("dev1", online=False, last_seen_tick=5)]
    result = detector.evaluate([], dev_obs, tick=10)
    # Should create a DEVICE_DISCONNECTION incident
    incs = [i for i in detector.active_incidents() if i.hazard_type == HazardType.DEVICE_DISCONNECTION]
    assert len(incs) == 1
    inc = incs[0]
    assert inc.device_id == "dev1"
    assert inc.severity == HazardSeverity.WARNING

def test_idempotent_evaluation(detector):
    obs = [make_obs("temp1", "dev1", "TEMPERATURE", 46.0, tick=1, coord=(7, 7))]
    devs = [make_dev("dev1", True, 1)]
    first = detector.evaluate(obs, devs, tick=5)
    second = detector.evaluate(obs, devs, tick=5)  # duplicate tick
    assert second.summary == "No change (duplicate tick)"
    # No new incidents added on second call
    assert len(second.new) == 0
    assert len(second.updated) == 0

def test_import_guard_no_forbidden_modules(detector):
    # Ensure hazard_detector does not import simulation related modules.
    import inspect, sys
    src = inspect.getsource(sys.modules["core.hazard_detector"])
    forbidden = ["simulation", "planner", "reservation"]
    for f in forbidden:
        assert f not in src, f"Forbidden import {f} found in hazard_detector"
