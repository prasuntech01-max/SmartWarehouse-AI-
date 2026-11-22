"""Unit tests for the Explainable Recommendation Engine (Module 13 Stage 5)."""

import pytest
from simulation.engine import WarehouseSimulator
from analytics.service import AnalyticsService
from recommendations.engine import RecommendationEngine
from recommendations.models import RecommendationPriority


@pytest.fixture
def sim():
    return WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)


@pytest.fixture
def engine(sim):
    analytics = AnalyticsService(sim)
    return RecommendationEngine(analytics)


def test_battery_depletion_rule_triggers(sim, engine):
    # Set robot 1 battery low
    sim.robots[1].battery = 18.0
    engine.analytics_service.invalidate_cache_if_needed()
    recs = engine.evaluate_all()
    bat_recs = [r for r in recs if r.rule_id == "REC-BATTERY-DEPLETION-RISK"]
    assert len(bat_recs) == 1
    assert "Robot R1" in bat_recs[0].title
    assert bat_recs[0].priority in (RecommendationPriority.HIGH, RecommendationPriority.CRITICAL)
    assert len(bat_recs[0].evidence) >= 1


def test_predictive_maintenance_rule_triggers(sim, engine):
    # High distance and task count decreases health score below 50
    sim.robots[2].total_distance = 600
    sim.robots[2].completed_tasks = 20
    engine.analytics_service.invalidate_cache_if_needed()
    recs = engine.evaluate_all()
    maint_recs = [r for r in recs if r.rule_id == "REC-PREVENTIVE-MAINTENANCE"]
    assert len(maint_recs) == 1
    assert "Robot R2" in maint_recs[0].title
    assert maint_recs[0].priority == RecommendationPriority.HIGH


def test_congestion_rule_triggers(sim, engine):
    sim.metrics.detected_conflicts_count = 5
    sim.metrics.replan_events_count = 4
    engine.analytics_service.invalidate_cache_if_needed()
    recs = engine.evaluate_all()
    cong_recs = [r for r in recs if r.rule_id == "REC-CONGESTION-BOTTLENECK"]
    assert len(cong_recs) == 1


def test_priority_sorting(sim, engine):
    sim.robots[1].battery = 10.0  # CRITICAL
    sim.metrics.detected_conflicts_count = 5  # MEDIUM
    engine.analytics_service.invalidate_cache_if_needed()
    recs = engine.evaluate_all()
    assert len(recs) >= 2
    assert recs[0].priority == RecommendationPriority.CRITICAL


def test_recommendations_are_advisory(sim, engine):
    initial_pos = {r_id: r.pos for r_id, r in sim.robots.items()}
    recs = engine.evaluate_all()
    for r in recs:
        assert r.is_advisory is True
    # Assert robot state did not change
    for r_id, r in sim.robots.items():
        assert r.pos == initial_pos[r_id]
