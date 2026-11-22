"""Module 10 — Comprehensive Test Suite.

Tests for:
  - DemandForecaster
  - ShelfOptimizer
  - CongestionPredictor
  - RobotHealthMonitor
  - FleetOptimizer
  - AIAnalyticsEngine
  - Integration with live simulation

All 101 existing tests must continue to pass alongside these.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Minimal stubs for unit tests (avoid importing heavy simulation stack)
# ---------------------------------------------------------------------------

@dataclass
class _StubTask:
    task_id: int
    shelf_loc: Tuple[int, int]
    pick_spot: Tuple[int, int]
    delivery_station: Tuple[int, int]
    status: str = 'COMPLETED'
    completed_at_step: Optional[int] = None
    priority: int = 2


@dataclass
class _StubRobot:
    robot_id: int
    pos: Tuple[int, int]
    state: str = 'IDLE'
    goal: Optional[Tuple[int, int]] = None
    path: List[Tuple[int, int]] = field(default_factory=list)
    path_index: int = 0
    battery: float = 100.0
    total_distance: int = 0
    completed_tasks: int = 0


class _StubGrid:
    shelves = {(2, 3), (2, 4), (6, 3), (6, 4), (10, 3), (10, 4)}
    packing_stations = [(2, 14), (6, 14), (10, 14)]
    width = 15
    height = 15


class _StubTaskManager:
    def get_completed_tasks(self):
        return []


# ===========================================================================
# DemandForecaster Tests
# ===========================================================================

class TestDemandForecaster:
    def _make_forecaster(self):
        from core.demand_forecasting import DemandForecaster
        return DemandForecaster()

    def test_empty_data_handling(self):
        f = self._make_forecaster()
        assert f.total_tasks_analysed == 0
        assert not f.data_sufficient
        assert f.get_top_shelves(5) == []
        assert f.get_demand_heatmap_data() == {}
        forecast = f.forecast_next_demand()
        assert forecast['preliminary'] is True
        assert forecast['predicted_tasks'] == 0.0

    def test_update_with_completed_tasks(self):
        f = self._make_forecaster()
        tasks = [
            _StubTask(task_id=1, shelf_loc=(2, 3), pick_spot=(2, 3), delivery_station=(2, 14), completed_at_step=5),
            _StubTask(task_id=2, shelf_loc=(2, 3), pick_spot=(2, 3), delivery_station=(6, 14), completed_at_step=10),
            _StubTask(task_id=3, shelf_loc=(6, 3), pick_spot=(6, 3), delivery_station=(2, 14), completed_at_step=15),
        ]
        f.update(tasks)
        assert f.total_tasks_analysed == 3
        assert f.data_sufficient is True

    def test_top_shelves_sorted_by_frequency(self):
        f = self._make_forecaster()
        tasks = [
            _StubTask(1, (2, 3), (2, 3), (2, 14), completed_at_step=5),
            _StubTask(2, (2, 3), (2, 3), (2, 14), completed_at_step=10),
            _StubTask(3, (2, 3), (2, 3), (2, 14), completed_at_step=15),
            _StubTask(4, (6, 3), (6, 3), (2, 14), completed_at_step=20),
        ]
        f.update(tasks)
        top = f.get_top_shelves(2)
        assert len(top) == 2
        # (2,3) appears 3 times, (6,3) once — (2,3) must be first
        assert top[0][0] == (2, 3)
        assert top[0][1] == 3
        assert top[1][0] == (6, 3)
        assert top[1][1] == 1

    def test_demand_heatmap_normalised(self):
        f = self._make_forecaster()
        tasks = [
            _StubTask(1, (2, 3), (2, 3), (2, 14), completed_at_step=5),
            _StubTask(2, (2, 3), (2, 3), (2, 14), completed_at_step=10),
            _StubTask(3, (6, 3), (6, 3), (2, 14), completed_at_step=15),
        ]
        f.update(tasks)
        heatmap = f.get_demand_heatmap_data()
        assert (2, 3) in heatmap
        assert heatmap[(2, 3)] == 1.0  # max frequency
        assert heatmap[(6, 3)] < 1.0

    def test_forecast_returns_valid_dict(self):
        f = self._make_forecaster()
        tasks = [
            _StubTask(i, (2, 3), (2, 3), (2, 14), completed_at_step=i * 5)
            for i in range(1, 8)
        ]
        f.update(tasks)
        forecast = f.forecast_next_demand(steps_ahead=10)
        assert 'predicted_tasks' in forecast
        assert 'confidence' in forecast
        assert 'preliminary' in forecast
        assert forecast['predicted_tasks'] >= 0.0
        assert forecast['confidence'] in ('low', 'medium', 'high')

    def test_demand_trend_returns_list(self):
        f = self._make_forecaster()
        tasks = [
            _StubTask(i, (2, 3), (2, 3), (2, 14), completed_at_step=i * 10)
            for i in range(1, 6)
        ]
        f.update(tasks)
        trend = f.get_demand_trend((2, 3), window=10)
        assert isinstance(trend, list)
        assert len(trend) >= 1

    def test_trend_missing_shelf_returns_empty(self):
        f = self._make_forecaster()
        f.update([_StubTask(1, (2, 3), (2, 3), (2, 14), completed_at_step=5)])
        trend = f.get_demand_trend((99, 99), window=5)
        assert trend == []

    def test_preliminary_label_below_threshold(self):
        f = self._make_forecaster()
        tasks = [
            _StubTask(1, (2, 3), (2, 3), (2, 14), completed_at_step=5),
            _StubTask(2, (2, 3), (2, 3), (2, 14), completed_at_step=10),
        ]
        f.update(tasks)  # Only 2 — below 3-task threshold
        assert not f.data_sufficient
        fc = f.forecast_next_demand()
        assert fc['preliminary'] is True


# ===========================================================================
# ShelfOptimizer Tests
# ===========================================================================

class TestShelfOptimizer:
    def _make_optimizer(self, heatmap=None):
        from core.shelf_optimizer import ShelfOptimizer
        grid = _StubGrid()
        tm = _StubTaskManager()
        return ShelfOptimizer(grid=grid, task_manager=tm, demand_heatmap=heatmap or {})

    def test_analyse_layout_returns_expected_keys(self):
        opt = self._make_optimizer()
        result = opt.analyse_current_layout()
        assert 'shelf_count' in result
        assert 'avg_shelf_to_station_dist' in result
        assert 'shelf_distances' in result
        assert result['shelf_count'] == len(_StubGrid.shelves)

    def test_avg_distance_positive(self):
        opt = self._make_optimizer()
        result = opt.analyse_current_layout()
        assert result['avg_shelf_to_station_dist'] > 0.0

    def test_recommendations_advisory_only(self):
        opt = self._make_optimizer(heatmap={(2, 3): 0.9})
        recs = opt.recommend_relocations(top_n=3)
        assert isinstance(recs, list)
        for r in recs:
            assert 'suggestion' in r
            assert 'shelf' in r
            assert 'score' in r

    def test_recommendations_sorted_by_score_desc(self):
        opt = self._make_optimizer(heatmap={(10, 3): 0.95, (2, 3): 0.1})
        recs = opt.recommend_relocations(top_n=5)
        scores = [r['score'] for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_distance_saving_estimate_valid(self):
        opt = self._make_optimizer()
        savings = opt.estimate_distance_saving()
        assert 'current_avg_dist' in savings
        assert 'estimated_improvement_pct' in savings
        assert 0.0 <= savings['estimated_improvement_pct'] <= 100.0

    def test_optimization_report_has_advisory_note(self):
        opt = self._make_optimizer()
        report = opt.get_optimization_report()
        assert 'advisory_note' in report
        assert 'advisory' in report['advisory_note'].lower()

    def test_empty_grid_no_crash(self):
        from core.shelf_optimizer import ShelfOptimizer
        grid = MagicMock()
        grid.shelves = set()
        grid.packing_stations = []
        opt = ShelfOptimizer(grid=grid, task_manager=_StubTaskManager())
        result = opt.analyse_current_layout()
        assert result['shelf_count'] == 0
        recs = opt.recommend_relocations()
        assert recs == []

    def test_apply_relocation_swap_between_shelves(self):
        from core.shelf_optimizer import ShelfOptimizer
        from warehouse import Warehouse
        wh = Warehouse(15, 15)
        opt = ShelfOptimizer(grid=wh, task_manager=_StubTaskManager(), demand_heatmap={(2, 3): 0.8, (2, 4): 0.1})
        ok, msg = opt.apply_relocation((2, 3), (2, 4))
        assert ok is True
        assert "Successfully swapped" in msg
        assert opt.demand_heatmap[(2, 3)] == 0.8 or opt.demand_heatmap[(2, 3)] == 0.1

    def test_apply_relocation_invalid_source_rejected(self):
        from core.shelf_optimizer import ShelfOptimizer
        from warehouse import Warehouse
        wh = Warehouse(15, 15)
        opt = ShelfOptimizer(grid=wh, task_manager=_StubTaskManager())
        ok, msg = opt.apply_relocation((0, 0), (2, 3))
        assert ok is False
        assert "not an existing shelf" in msg

    def test_apply_relocation_to_dock_rejected(self):
        from core.shelf_optimizer import ShelfOptimizer
        from warehouse import Warehouse
        wh = Warehouse(15, 15)
        opt = ShelfOptimizer(grid=wh, task_manager=_StubTaskManager())
        dock = wh.charging_docks[0]
        ok, msg = opt.apply_relocation((2, 3), dock)
        assert ok is False
        assert "reserved charging dock" in msg


# ===========================================================================
# CongestionPredictor Tests
# ===========================================================================

class TestCongestionPredictor:
    def _make_predictor(self):
        from core.congestion_predictor import CongestionPredictor
        return CongestionPredictor(grid=_StubGrid())

    def test_no_robots_returns_zero_score(self):
        pred = self._make_predictor()
        assert pred.get_congestion_score({}) == 0.0

    def test_heatmap_empty_when_no_paths(self):
        pred = self._make_predictor()
        robots = {1: _StubRobot(robot_id=1, pos=(1, 1), path=[], path_index=0)}
        hm = pred.get_congestion_heatmap(robots)
        assert hm == {}

    def test_heatmap_populated_with_active_path(self):
        pred = self._make_predictor()
        path = [(1, 1), (1, 2), (1, 3), (1, 4)]
        r = _StubRobot(robot_id=1, pos=(1, 1), state='MOVING_TO_PICK', path=path, path_index=0)
        hm = pred.get_congestion_heatmap({1: r})
        assert len(hm) == len(path)
        assert all(0.0 <= v <= 1.0 for v in hm.values())

    def test_max_score_is_one(self):
        pred = self._make_predictor()
        path = [(1, 1), (2, 1), (3, 1)]
        r1 = _StubRobot(robot_id=1, pos=(1, 1), state='MOVING_TO_PICK', path=path, path_index=0)
        r2 = _StubRobot(robot_id=2, pos=(1, 1), state='MOVING_TO_PICK', path=path, path_index=0)
        hm = pred.get_congestion_heatmap({1: r1, 2: r2})
        assert max(hm.values()) == 1.0

    def test_risk_zones_filtered_by_threshold(self):
        pred = self._make_predictor()
        path = [(5, 5), (5, 6)]
        r1 = _StubRobot(1, (5, 5), 'MOVING_TO_PICK', path=path, path_index=0)
        r2 = _StubRobot(2, (5, 5), 'MOVING_TO_PICK', path=path, path_index=0)
        r3 = _StubRobot(3, (5, 5), 'MOVING_TO_PICK', path=path, path_index=0)
        zones = pred.get_risk_zones({1: r1, 2: r2, 3: r3}, threshold=0.5)
        for z in zones:
            assert z['score'] >= 0.5

    def test_recommendations_non_empty_with_active_robots(self):
        pred = self._make_predictor()
        path = [(i, 5) for i in range(10)]
        robots = {i: _StubRobot(i, (i, 5), 'MOVING_TO_PICK', path=path, path_index=0) for i in range(1, 4)}
        recs = pred.get_recommendations(robots)
        assert len(recs) >= 1

    def test_no_active_robots_message(self):
        pred = self._make_predictor()
        robots = {1: _StubRobot(1, (1, 1), state='IDLE', path=[])}
        recs = pred.get_recommendations(robots)
        assert any('unavailable' in r.lower() or 'no active' in r.lower() for r in recs)


# ===========================================================================
# RobotHealthMonitor Tests
# ===========================================================================

class TestRobotHealthMonitor:
    def _make_monitor(self, robots):
        from core.predictive_maintenance import RobotHealthMonitor
        return RobotHealthMonitor(robots=robots, step_count=0)

    def test_full_battery_no_distance_max_health(self):
        r = _StubRobot(1, (1, 1), battery=100.0, total_distance=0, completed_tasks=0)
        monitor = self._make_monitor({1: r})
        score = monitor.compute_health_score(1)
        assert score == 100.0

    def test_low_battery_deducts_points(self):
        r = _StubRobot(1, (1, 1), battery=15.0, total_distance=0, completed_tasks=0)
        monitor = self._make_monitor({1: r})
        score = monitor.compute_health_score(1)
        assert score <= 80.0  # -20 for <20% battery

    def test_mid_battery_deducts_half(self):
        r = _StubRobot(1, (1, 1), battery=35.0, total_distance=0, completed_tasks=0)
        monitor = self._make_monitor({1: r})
        score = monitor.compute_health_score(1)
        assert 85.0 <= score <= 95.0  # -10 for <40% battery

    def test_high_distance_reduces_health(self):
        r = _StubRobot(1, (1, 1), battery=100.0, total_distance=600, completed_tasks=0)
        monitor = self._make_monitor({1: r})
        score = monitor.compute_health_score(1)
        assert score <= 70.0

    def test_many_tasks_reduces_health(self):
        r = _StubRobot(1, (1, 1), battery=100.0, total_distance=0, completed_tasks=10)
        monitor = self._make_monitor({1: r})
        score = monitor.compute_health_score(1)
        assert score <= 80.0

    def test_fleet_health_summary_all_robots(self):
        robots = {
            1: _StubRobot(1, (1, 1), battery=100.0, total_distance=0, completed_tasks=0),
            2: _StubRobot(2, (2, 2), battery=10.0, total_distance=500, completed_tasks=12),
        }
        monitor = self._make_monitor(robots)
        summary = monitor.get_fleet_health_summary()
        assert 1 in summary and 2 in summary
        assert summary[1]['score'] > summary[2]['score']

    def test_maintenance_priority_order(self):
        robots = {
            1: _StubRobot(1, (1, 1), battery=100.0, total_distance=0, completed_tasks=0),
            2: _StubRobot(2, (2, 2), battery=5.0, total_distance=800, completed_tasks=20),
            3: _StubRobot(3, (3, 3), battery=50.0, total_distance=100, completed_tasks=5),
        }
        monitor = self._make_monitor(robots)
        priority = monitor.get_maintenance_priority()
        # Robot 2 must be first (worst health)
        assert priority[0] == 2

    def test_nonexistent_robot_returns_zero(self):
        monitor = self._make_monitor({})
        assert monitor.compute_health_score(99) == 0.0

    def test_fleet_average_health_in_range(self):
        robots = {
            1: _StubRobot(1, (1, 1), battery=100.0, total_distance=0, completed_tasks=0),
            2: _StubRobot(2, (2, 2), battery=50.0, total_distance=200, completed_tasks=5),
        }
        monitor = self._make_monitor(robots)
        avg = monitor.get_fleet_average_health()
        assert 0.0 <= avg <= 100.0

    def test_critical_robots_identified(self):
        robots = {
            1: _StubRobot(1, (1, 1), battery=5.0, total_distance=800, completed_tasks=20),
            2: _StubRobot(2, (2, 2), battery=100.0, total_distance=0, completed_tasks=0),
        }
        monitor = self._make_monitor(robots)
        critical = monitor.get_critical_robots(threshold=50.0)
        assert 1 in critical
        assert 2 not in critical


# ===========================================================================
# FleetOptimizer Tests
# ===========================================================================

class TestFleetOptimizer:
    def _make_optimizer(self):
        from core.fleet_optimizer import FleetOptimizer
        from simulation.engine import WarehouseSimulator
        sim = WarehouseSimulator(num_robots=2, width=15, height=15, seed=42)
        return FleetOptimizer(sim=sim)

    def test_benchmark_returns_six_strategies(self):
        opt = self._make_optimizer()
        results = opt.benchmark_strategies(steps=5, seed=42)
        assert len(results) == 6
        for r in results:
            assert 'strategy' in r
            assert 'completed_tasks' in r
            assert 'gini_index' in r

    def test_benchmark_does_not_modify_live_sim(self):
        from simulation.engine import WarehouseSimulator
        from core.fleet_optimizer import FleetOptimizer
        sim = WarehouseSimulator(num_robots=2, width=15, height=15, seed=42)
        initial_step = sim.step_count
        opt = FleetOptimizer(sim=sim)
        opt.benchmark_strategies(steps=5)
        assert sim.step_count == initial_step  # Live sim must not advance

    def test_recommend_strategy_returns_valid_result(self):
        opt = self._make_optimizer()
        results = opt.benchmark_strategies(steps=5)
        rec = opt.recommend_strategy(results)
        assert 'recommended' in rec
        assert 'reason' in rec
        assert len(rec['reason']) > 0

    def test_efficiency_metrics_valid(self):
        opt = self._make_optimizer()
        metrics = opt.get_current_efficiency_metrics()
        assert 'utilization_pct' in metrics
        assert 'total_fleet_distance' in metrics
        assert metrics['total_fleet_distance'] >= 0

    def test_estimate_improvement_between_strategies(self):
        from core.task_assignment import AssignmentStrategy
        opt = self._make_optimizer()
        results = opt.benchmark_strategies(steps=10)
        improvement = opt.estimate_improvement(
            current_strategy=AssignmentStrategy.NEAREST_ROBOT.value,
            recommended_strategy=AssignmentStrategy.WEIGHTED_MULTI_CRITERIA.value,
            benchmark_data=results,
        )
        assert isinstance(improvement, float)


# ===========================================================================
# AIAnalyticsEngine Tests
# ===========================================================================

class TestAIAnalyticsEngine:
    def _make_engine(self):
        from simulation.engine import WarehouseSimulator
        from simulation.ai_analytics import AIAnalyticsEngine
        sim = WarehouseSimulator(num_robots=2, width=15, height=15, seed=42)
        return AIAnalyticsEngine(sim=sim), sim

    def test_engine_initialises_without_error(self):
        engine, sim = self._make_engine()
        assert engine is not None

    def test_full_analysis_runs_without_error(self):
        engine, sim = self._make_engine()
        result = engine.run_full_analysis()
        assert isinstance(result, dict)
        assert 'demand' in result
        assert 'congestion' in result
        assert 'health' in result

    def test_cache_invalidated_on_step_advance(self):
        engine, sim = self._make_engine()
        result1 = engine.run_full_analysis()
        step1 = result1['step']
        sim.step()  # Advance sim
        result2 = engine.run_full_analysis()
        step2 = result2['step']
        assert step2 == step1 + 1

    def test_summary_kpis_valid_types(self):
        engine, sim = self._make_engine()
        kpis = engine.get_summary_kpis()
        assert 'fleet_avg_health' in kpis
        assert 'congestion_score' in kpis
        assert 0.0 <= kpis['fleet_avg_health'] <= 100.0
        assert 0.0 <= kpis['congestion_score'] <= 100.0

    def test_all_recommendations_non_none(self):
        engine, sim = self._make_engine()
        recs = engine.get_all_recommendations()
        assert isinstance(recs, list)
        for r in recs:
            assert r.get('message') is not None

    def test_integration_full_sim_run_then_analysis(self):
        """Run 50 steps, then verify analytics provide non-trivial results."""
        from simulation.engine import WarehouseSimulator
        from simulation.ai_analytics import AIAnalyticsEngine

        sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
        for _ in range(50):
            sim.step()

        engine = AIAnalyticsEngine(sim=sim)
        result = engine.run_full_analysis()

        kpis = engine.get_summary_kpis()
        assert kpis['completed_tasks'] >= 0
        # Fleet health should still be non-zero for a fresh sim
        assert kpis['fleet_avg_health'] > 0.0

    def test_recommendations_aggregate_all_sources(self):
        """After running simulation, all_recommendations must have source annotations."""
        from simulation.engine import WarehouseSimulator
        from simulation.ai_analytics import AIAnalyticsEngine

        sim = WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)
        for _ in range(20):
            sim.step()

        engine = AIAnalyticsEngine(sim=sim)
        all_recs = engine.get_all_recommendations()
        sources = {r['source'] for r in all_recs}
        # Must have at least health and shelf recommendations
        assert any('Health' in s or 'Shelf' in s for s in sources)


# ===========================================================================
# 3D Digital Twin Module 10 Tests
# ===========================================================================

class TestWarehouse3DRendererModule10:
    def test_3d_renderer_camera_presets_and_theme(self):
        from warehouse import Warehouse
        from visualization.renderer_3d import Warehouse3DRenderer
        import plotly.graph_objects as go
        wh = Warehouse(15, 15)
        renderer = Warehouse3DRenderer(wh)

        for view in ['iso', 'top', 'front', 'side']:
            fig = renderer.render_3d(robots={}, step_count=0, camera_view=view, theme='dark')
            assert isinstance(fig, go.Figure)

    def test_3d_renderer_with_congestion_and_shelf_overlays(self):
        from warehouse import Warehouse
        from visualization.renderer_3d import Warehouse3DRenderer
        wh = Warehouse(15, 15)
        renderer = Warehouse3DRenderer(wh)

        c_heatmap = {(2, 2): 0.8, (3, 3): 0.4}
        recs = [{'shelf': (2, 3), 'target_swap': (2, 4)}]
        fig = renderer.render_3d(
            robots={},
            step_count=5,
            congestion_heatmap=c_heatmap,
            shelf_optimizations=recs,
            show_heatmaps=True,
        )
        trace_names = [t.name for t in fig.data if hasattr(t, 'name')]
        assert "Congestion Heatmap" in trace_names
        assert "Shelf Relocation Advisory" in trace_names

    def test_3d_renderer_selected_robot_highlight(self):
        from warehouse import Warehouse
        from visualization.renderer_3d import Warehouse3DRenderer
        from simulation.engine import RobotState
        wh = Warehouse(15, 15)
        renderer = Warehouse3DRenderer(wh)

        robots = {1: RobotState(robot_id=1, home_dock=(1, 0), pos=(1, 0))}
        fig = renderer.render_3d(
            robots=robots,
            step_count=0,
            selected_robot_id=1,
        )
        trace_names = [t.name for t in fig.data if hasattr(t, 'name')]
        assert "Selected Robot R1" in trace_names
