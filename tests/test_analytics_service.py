"""Unit and integration tests for the Analytics Service (Module 13 Stage 2)."""

import pytest
import time
from simulation.engine import WarehouseSimulator
from analytics.service import AnalyticsService
from analytics.models import ProvenanceType, FilterSpec


@pytest.fixture
def sim():
    return WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)


@pytest.fixture
def analytics_service(sim):
    return AnalyticsService(sim, process_start_time=time.time() - 100.0)


def test_analytics_snapshot_structure(analytics_service):
    snapshot = analytics_service.get_snapshot()
    assert snapshot.simulation_step == 0
    assert snapshot.wall_clock_uptime_sec >= 100.0
    assert "completed_tasks" in snapshot.summary_kpis
    assert "fleet_throughput" in snapshot.summary_kpis
    assert "fleet_utilization" in snapshot.summary_kpis
    assert len(snapshot.fleet_metrics) == 3


def test_metric_provenance_labels(analytics_service):
    snapshot = analytics_service.get_snapshot()
    for name, metric in snapshot.summary_kpis.items():
        assert isinstance(metric.provenance, ProvenanceType)
        assert metric.provenance.value in ("MEASURED", "SIMULATED", "SIMULATED-TELEMETRY", "ESTIMATED")

    assert snapshot.safety_kpis["physical_collisions"].value == 0
    assert snapshot.safety_kpis["physical_collisions"].provenance == ProvenanceType.SIMULATED
    assert snapshot.summary_kpis["process_uptime"].provenance == ProvenanceType.MEASURED


def test_fleet_dataframe_generation(analytics_service):
    df = analytics_service.get_fleet_dataframe()
    assert len(df) == 3
    assert "Robot" in df.columns
    assert "Battery (%)" in df.columns
    assert "Utilization (%)" in df.columns
    assert "Health (/100)" in df.columns


def test_snapshot_comparison(analytics_service, sim):
    snap1 = analytics_service.get_snapshot()
    sim.step()
    analytics_service.invalidate_cache_if_needed()
    snap2 = analytics_service.get_snapshot()
    comp = AnalyticsService.compare_snapshots(snap2, snap1)
    assert "simulation_step" in comp
    assert comp["simulation_step"]["abs_change"] == 1


def test_robot_filter(analytics_service):
    spec = FilterSpec(robot_ids=[1])
    filtered_snap = analytics_service.get_snapshot(filters=spec)
    assert len(filtered_snap.fleet_metrics) == 1
    assert 1 in filtered_snap.fleet_metrics
