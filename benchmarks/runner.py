"""Empirical benchmark execution engine for path planning and task dispatching algorithms."""

import time
import tracemalloc
import random
import uuid
import math
import platform
import sys
import copy
from typing import List, Dict, Any, Tuple

from .models import BenchmarkConfig, TrialResult, BenchmarkSummary, BenchmarkRun
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import AStarPlanner
from core.state import TimeExpandedPlanner
from core.multi_agent import MultiAgentPlanner
from core.task_assignment import TaskAssignmentEngine, AssignmentStrategy
from core.task_manager import TaskManager
from persistence.repo import BenchmarkRepo


class BenchmarkRunner:
    """Executes deterministic, isolated benchmarks across pathfinding and dispatch algorithms."""

    LIMITATIONS_NOTE = (
        "Measurements reflect synthetic grid scenarios executed in Python 3.13 on the host CPU. "
        "Timings are subject to OS background scheduling jitter. Memory peaks reflect Python heap "
        "allocations via tracemalloc, not total OS process RSS."
    )

    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        return {
            "python_version": sys.version.split()[0],
            "os_platform": platform.platform(),
            "cpu_architecture": platform.machine(),
            "processor": platform.processor(),
        }

    @staticmethod
    def _calculate_stats(values: List[float]) -> Tuple[float, float, float, float, float]:
        if not values:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        n = len(values)
        mean_v = sum(values) / n
        sorted_v = sorted(values)
        median_v = sorted_v[n // 2] if n % 2 != 0 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0
        var_v = sum((x - mean_v) ** 2 for x in values) / max(1, n - 1) if n > 1 else 0.0
        std_v = math.sqrt(var_v)
        return round(mean_v, 3), round(median_v, 3), round(std_v, 3), round(min(values), 3), round(max(values), 3)

    def run_benchmark(
        self,
        config: BenchmarkConfig,
        executed_by: str = "OPERATOR",
        persist: bool = True,
    ) -> BenchmarkRun:
        """Executes the requested benchmark configuration and persists results."""
        run_id = f"BNCH-{uuid.uuid4().hex[:8].upper()}"
        env_info = self.get_environment_info()
        trials: List[TrialResult] = []

        # Warm-up run to discard cold cache / JIT effects
        self._warmup_planner()

        num_trials = min(max(1, config.num_trials), 10)

        if config.benchmark_type == "PLANNER_COMPARISON":
            trials = self._benchmark_planners(config, num_trials)
        elif config.benchmark_type == "DISPATCH_STRATEGIES":
            trials = self._benchmark_dispatch_strategies(config, num_trials)
        else:  # FLEET_SCALING
            trials = self._benchmark_fleet_scaling(config, num_trials)

        # Compute summaries per algorithm
        algo_groups: Dict[str, List[TrialResult]] = {}
        for t in trials:
            algo_groups.setdefault(t.algorithm_name, []).append(t)

        summaries: Dict[str, BenchmarkSummary] = {}
        winning_algo = ""
        best_score = float("inf")

        for algo, res_list in algo_groups.items():
            times = [r.execution_time_ms for r in res_list]
            mems = [r.memory_peak_kb for r in res_list]
            paths = [r.path_length for r in res_list if r.path_length > 0]
            ratios = [r.optimality_ratio for r in res_list if r.optimality_ratio > 0]
            successes = [1 for r in res_list if r.success]

            mean_t, med_t, std_t, min_t, max_t = self._calculate_stats(times)
            mean_mem, _, _, _, _ = self._calculate_stats(mems)
            mean_p, _, _, _, _ = self._calculate_stats([float(p) for p in paths])
            mean_ratio, _, _, _, _ = self._calculate_stats(ratios)

            succ_rate = round((len(successes) / max(1, len(res_list))) * 100.0, 1)

            summaries[algo] = BenchmarkSummary(
                algorithm_name=algo,
                total_trials=len(res_list),
                success_rate=succ_rate,
                mean_time_ms=mean_t,
                median_time_ms=med_t,
                std_dev_time_ms=std_t,
                min_time_ms=min_t,
                max_time_ms=max_t,
                mean_memory_kb=mean_mem,
                mean_path_length=mean_p,
                mean_optimality_ratio=mean_ratio,
            )

            # Determine winner (composite score of execution time and path optimality)
            score = mean_t * (mean_ratio if mean_ratio > 0 else 1.0)
            if score < best_score and succ_rate >= 100.0:
                best_score = score
                winning_algo = algo

        if not winning_algo and summaries:
            winning_algo = list(summaries.keys())[0]

        bench_run = BenchmarkRun(
            run_id=run_id,
            benchmark_name=config.benchmark_type.replace("_", " ").title(),
            config=config,
            environment=env_info,
            trials=trials,
            summaries=summaries,
            winning_algorithm=winning_algo,
            limitations=self.LIMITATIONS_NOTE,
            executed_by=executed_by,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        # Persist to database if enabled
        if persist:
            try:
                BenchmarkRepo.save_run(
                    run_id=run_id,
                    benchmark_name=bench_run.benchmark_name,
                    parameters={
                        "benchmark_type": config.benchmark_type,
                        "num_robots": config.num_robots,
                        "grid_size": f"{config.grid_size}x{config.grid_size}",
                        "obstacle_density": config.obstacle_density,
                        "num_trials": config.num_trials,
                        "seed": config.seed,
                    },
                    environment=env_info,
                    total_trials=len(trials),
                    executed_by=executed_by,
                    trials=[t.to_dict() for t in trials],
                )
            except Exception:
                pass

        return bench_run

    def _warmup_planner(self) -> None:
        """Executes a silent mock planning query to warm Python caches."""
        grid = WarehouseGrid(width=15, height=15)
        planner = AStarPlanner(warehouse=grid)
        try:
            planner.plan_2d((0, 0), (14, 14))
        except Exception:
            pass

    def _generate_synthetic_scenario(
        self, width: int, height: int, density: float, seed: int
    ) -> Tuple[WarehouseGrid, Tuple[int, int], Tuple[int, int]]:
        """Constructs an isolated warehouse grid with seeded obstacles and verified walkable endpoints."""
        grid = WarehouseGrid(width=width, height=height)
        rng = random.Random(seed)

        # Inject additional obstacles up to density
        target_obstacles = int(width * height * density)
        injected = 0
        attempts = 0
        while injected < target_obstacles and attempts < 200:
            attempts += 1
            x = rng.randint(0, width - 1)
            y = rng.randint(0, height - 1)
            if (x, y) not in grid.shelves and (x, y) not in grid.charging_docks and (x, y) not in grid.packing_stations:
                grid.add_dynamic_obstacle(x, y)
                injected += 1

        # Select valid start and goal
        walkable = [
            (x, y)
            for x in range(width)
            for y in range(height)
            if grid.is_walkable(x, y)
        ]
        start = walkable[0] if walkable else (0, 0)
        goal = walkable[-1] if len(walkable) > 1 else (width - 1, height - 1)
        return grid, start, goal

    def _benchmark_planners(self, config: BenchmarkConfig, num_trials: int) -> List[TrialResult]:
        """Evaluates 2D Static A* vs Space-Time Reservation A* on identical isolated scenarios."""
        results = []
        for trial_idx in range(num_trials):
            scenario_seed = config.seed + trial_idx * 17
            grid, start, goal = self._generate_synthetic_scenario(
                config.grid_size, config.grid_size, config.obstacle_density, scenario_seed
            )

            # Baseline 2D A* Shortest Path
            planner_2d = AStarPlanner(warehouse=grid)
            optimal_path = planner_2d.plan_2d(start, goal) or []
            optimal_len = len(optimal_path)

            # Algorithm 1: Static 2D A*
            tracemalloc.start()
            t0 = time.perf_counter()
            path_2d = planner_2d.plan_2d(start, goal)
            t1 = time.perf_counter()
            _, peak_mem_2d = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            len_2d = len(path_2d) if path_2d else 0
            results.append(
                TrialResult(
                    algorithm_name="A*_2D_Static",
                    scenario_seed=scenario_seed,
                    num_robots=1,
                    grid_size=f"{config.grid_size}x{config.grid_size}",
                    obstacle_density=config.obstacle_density,
                    execution_time_ms=(t1 - t0) * 1000.0,
                    memory_peak_kb=peak_mem_2d / 1024.0,
                    path_length=len_2d,
                    optimal_path_length=optimal_len,
                    optimality_ratio=round(len_2d / max(1, optimal_len), 3),
                    conflicts_detected=0,
                    replan_count=0,
                    success=(path_2d is not None and len(path_2d) > 0),
                )
            )

            # Algorithm 2: Space-Time A* with Reservation Constraints
            res_table = ReservationTable()
            # Place artificial reservation in middle of path to measure detour handling
            if len(optimal_path) > 4:
                mid_pt = optimal_path[len(optimal_path) // 2]
                res_table.reserve_vertex(mid_pt[0], mid_pt[1], t=len(optimal_path) // 2, robot_id=99)

            st_planner = TimeExpandedPlanner(grid, res_table)
            tracemalloc.start()
            t2 = time.perf_counter()
            path_st = st_planner.plan(start=start, goal=goal, start_time=0, robot_id=1)
            t3 = time.perf_counter()
            _, peak_mem_st = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            len_st = len(path_st) if path_st else 0
            results.append(
                TrialResult(
                    algorithm_name="SpaceTime_A*_Reservation",
                    scenario_seed=scenario_seed,
                    num_robots=1,
                    grid_size=f"{config.grid_size}x{config.grid_size}",
                    obstacle_density=config.obstacle_density,
                    execution_time_ms=(t3 - t2) * 1000.0,
                    memory_peak_kb=peak_mem_st / 1024.0,
                    path_length=len_st,
                    optimal_path_length=optimal_len,
                    optimality_ratio=round(len_st / max(1, optimal_len), 3),
                    conflicts_detected=1 if len(optimal_path) > 4 else 0,
                    replan_count=0,
                    success=(path_st is not None and len(path_st) > 0),
                )
            )

        return results

    def _benchmark_dispatch_strategies(self, config: BenchmarkConfig, num_trials: int) -> List[TrialResult]:
        """Evaluates all task assignment strategies on identical simulated workloads."""
        strategies = [
            ("Nearest_Robot", AssignmentStrategy.NEAREST_ROBOT),
            ("Shortest_Route", AssignmentStrategy.SHORTEST_TOTAL_ROUTE),
            ("Priority_First", AssignmentStrategy.PRIORITY_FIRST),
            ("Workload_Balanced", AssignmentStrategy.WORKLOAD_BALANCED),
            ("Weighted_MultiCriteria", AssignmentStrategy.WEIGHTED_MULTI_CRITERIA),
            ("Hungarian_Batch", AssignmentStrategy.BATCH_OPTIMAL),
        ]
        results = []

        for trial_idx in range(num_trials):
            scenario_seed = config.seed + trial_idx * 23
            grid = WarehouseGrid(width=config.grid_size, height=config.grid_size)
            task_mgr = TaskManager(grid, seed=scenario_seed)
            task_mgr.populate_initial_tasks(count=12, current_step=0)
            pending = task_mgr.get_pending_tasks()

            idle_robots = {
                r_id: {"pos": grid.charging_docks[r_id - 1], "workload": r_id * 2}
                for r_id in range(1, config.num_robots + 1)
            }

            for strat_label, strat_enum in strategies:
                engine = TaskAssignmentEngine(grid, default_strategy=strat_enum)
                tracemalloc.start()
                t0 = time.perf_counter()
                decisions = engine.assign_batch(
                    idle_robots=idle_robots,
                    pending_tasks=pending,
                    strategy=strat_enum,
                    current_step=0,
                )
                t1 = time.perf_counter()
                _, peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                results.append(
                    TrialResult(
                        algorithm_name=strat_label,
                        scenario_seed=scenario_seed,
                        num_robots=config.num_robots,
                        grid_size=f"{config.grid_size}x{config.grid_size}",
                        obstacle_density=config.obstacle_density,
                        execution_time_ms=(t1 - t0) * 1000.0,
                        memory_peak_kb=peak_mem / 1024.0,
                        path_length=len(decisions),
                        optimal_path_length=len(decisions),
                        optimality_ratio=1.0,
                        conflicts_detected=0,
                        replan_count=0,
                        success=(len(decisions) > 0),
                    )
                )

        return results

    def _benchmark_fleet_scaling(self, config: BenchmarkConfig, num_trials: int) -> List[TrialResult]:
        """Evaluates Multi-Agent Prioritized Planning scaling across 1 to 5 robots."""
        results = []
        fleet_counts = [1, 2, 3, 4, 5]

        for trial_idx in range(num_trials):
            scenario_seed = config.seed + trial_idx * 31
            grid = WarehouseGrid(width=config.grid_size, height=config.grid_size)
            ma_planner = MultiAgentPlanner(grid)

            for count in fleet_counts:
                agent_starts = [grid.charging_docks[i] for i in range(count)]
                agent_goals = [grid.packing_stations[i % len(grid.packing_stations)] for i in range(count)]

                tracemalloc.start()
                t0 = time.perf_counter()
                paths = ma_planner.plan_prioritized(starts=agent_starts, goals=agent_goals)
                t1 = time.perf_counter()
                _, peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                conflicts = ma_planner.detect_conflicts(paths)
                total_len = sum(len(p) for p in paths.values()) if paths else 0

                results.append(
                    TrialResult(
                        algorithm_name=f"Prioritized_Fleet_{count}_Robots",
                        scenario_seed=scenario_seed,
                        num_robots=count,
                        grid_size=f"{config.grid_size}x{config.grid_size}",
                        obstacle_density=config.obstacle_density,
                        execution_time_ms=(t1 - t0) * 1000.0,
                        memory_peak_kb=peak_mem / 1024.0,
                        path_length=total_len,
                        optimal_path_length=total_len,
                        optimality_ratio=1.0,
                        conflicts_detected=len(conflicts),
                        replan_count=0,
                        success=(len(paths) == count and len(conflicts) == 0),
                    )
                )

        return results
