"""Data models for the benchmarking framework."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class BenchmarkConfig:
    """Configuration for an empirical benchmark run."""
    benchmark_type: str = "PLANNER_COMPARISON"  # PLANNER_COMPARISON, FLEET_SCALING, DISPATCH_STRATEGIES
    algorithms: List[str] = field(default_factory=lambda: ["A*_2D_Static", "SpaceTime_A*_Reservation"])
    num_robots: int = 3
    grid_size: int = 15
    obstacle_density: float = 0.10
    num_trials: int = 3                          # Default 3 trials (configurable 1 to 10)
    seed: int = 42


@dataclass
class TrialResult:
    """Metrics from an individual benchmark trial."""
    algorithm_name: str
    scenario_seed: int
    num_robots: int
    grid_size: str
    obstacle_density: float
    execution_time_ms: float
    memory_peak_kb: float
    path_length: int
    optimal_path_length: int
    optimality_ratio: float
    conflicts_detected: int
    replan_count: int
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm_name": self.algorithm_name,
            "scenario_seed": self.scenario_seed,
            "num_robots": self.num_robots,
            "grid_size": self.grid_size,
            "obstacle_density": self.obstacle_density,
            "execution_time_ms": round(self.execution_time_ms, 3),
            "memory_peak_kb": round(self.memory_peak_kb, 2),
            "path_length": self.path_length,
            "optimal_path_length": self.optimal_path_length,
            "optimality_ratio": round(self.optimality_ratio, 3),
            "conflicts_detected": self.conflicts_detected,
            "replan_count": self.replan_count,
            "success": self.success,
        }


@dataclass
class BenchmarkSummary:
    """Statistical summary across multiple trials for an algorithm."""
    algorithm_name: str
    total_trials: int
    success_rate: float
    mean_time_ms: float
    median_time_ms: float
    std_dev_time_ms: float
    min_time_ms: float
    max_time_ms: float
    mean_memory_kb: float
    mean_path_length: float
    mean_optimality_ratio: float


@dataclass
class BenchmarkRun:
    """Complete record of a benchmark run containing raw trials and aggregate summaries."""
    run_id: str
    benchmark_name: str
    config: BenchmarkConfig
    environment: Dict[str, Any]
    trials: List[TrialResult]
    summaries: Dict[str, BenchmarkSummary]
    winning_algorithm: str
    limitations: str
    executed_by: str = "OPERATOR"
    timestamp: str = ""
