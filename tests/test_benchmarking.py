"""Unit and integration tests for the Benchmarking framework (Module 13 Stage 4)."""

import pytest
from simulation.engine import WarehouseSimulator
from benchmarks.runner import BenchmarkRunner
from benchmarks.models import BenchmarkConfig
from persistence.repo import BenchmarkRepo


@pytest.fixture
def sim():
    return WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)


def test_stats_calculation():
    vals = [10.0, 20.0, 30.0]
    mean, med, std, min_v, max_v = BenchmarkRunner._calculate_stats(vals)
    assert mean == 20.0
    assert med == 20.0
    assert min_v == 10.0
    assert max_v == 30.0
    assert std > 0


def test_benchmark_isolation(sim):
    # Verify live simulation state is unchanged before and after benchmark
    initial_step = sim.step_count
    initial_res_count = len(sim.reservation_table.vertex_reservations)

    runner = BenchmarkRunner()
    cfg = BenchmarkConfig(benchmark_type="PLANNER_COMPARISON", num_trials=1, seed=123)
    run_result = runner.run_benchmark(cfg, persist=False)

    assert run_result.run_id.startswith("BNCH-")
    assert sim.step_count == initial_step
    assert len(sim.reservation_table.vertex_reservations) == initial_res_count


def test_planner_benchmark_execution():
    runner = BenchmarkRunner()
    cfg = BenchmarkConfig(benchmark_type="PLANNER_COMPARISON", num_trials=2, seed=42)
    run_result = runner.run_benchmark(cfg, persist=True)

    assert len(run_result.trials) == 4  # 2 algorithms * 2 trials
    assert "A*_2D_Static" in run_result.summaries
    assert "SpaceTime_A*_Reservation" in run_result.summaries
    assert run_result.winning_algorithm != ""

    # Verify database persistence
    saved = BenchmarkRepo.get_run(run_result.run_id)
    assert saved is not None
    assert saved["run_id"] == run_result.run_id
    trials_db = BenchmarkRepo.get_trials(run_result.run_id)
    assert len(trials_db) == 4


def test_dispatch_strategies_benchmark():
    runner = BenchmarkRunner()
    cfg = BenchmarkConfig(benchmark_type="DISPATCH_STRATEGIES", num_trials=1, seed=42)
    run_result = runner.run_benchmark(cfg, persist=False)

    assert len(run_result.summaries) == 6
    assert "Nearest_Robot" in run_result.summaries
    assert "Hungarian_Batch" in run_result.summaries
