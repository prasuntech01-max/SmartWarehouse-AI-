"""Module 10 — Fleet Route & Strategy Optimizer.

Benchmarks all 6 task-assignment strategies on identical deterministic
simulation copies and recommends the best strategy for the current scenario.
Never modifies the live simulation.
"""

import time
from typing import Dict, List, Any, Optional


class FleetOptimizer:
    """Benchmarks assignment strategies and recommends the optimal one.

    Parameters
    ----------
    sim : WarehouseSimulator
        Reference to the live simulator (read-only — never mutated).
    """

    def __init__(self, sim: Any) -> None:
        self.sim = sim
        self._benchmark_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_step: int = -1

    def benchmark_strategies(
        self,
        steps: int = 30,
        seed: int = 42,
    ) -> List[Dict[str, Any]]:
        """Run all 6 strategies on identical isolated sim copies.

        Never modifies self.sim. Returns a list of result dicts.
        """
        from simulation.engine import WarehouseSimulator
        from core.task_assignment import AssignmentStrategy
        from simulation.metrics import MetricsCollector

        strategies = [
            AssignmentStrategy.NEAREST_ROBOT,
            AssignmentStrategy.SHORTEST_TOTAL_ROUTE,
            AssignmentStrategy.PRIORITY_FIRST,
            AssignmentStrategy.WORKLOAD_BALANCED,
            AssignmentStrategy.WEIGHTED_MULTI_CRITERIA,
            AssignmentStrategy.BATCH_OPTIMAL,
        ]

        results = []
        for strat in strategies:
            b_sim = WarehouseSimulator(
                num_robots=self.sim.num_robots,
                width=self.sim.width,
                height=self.sim.height,
                seed=seed,
            )
            b_sim.set_assignment_strategy(strat)

            t0 = time.perf_counter()
            for _ in range(steps):
                b_sim.step()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            summary = b_sim.metrics.get_summary()
            robot_counts = {r_id: r.completed_tasks for r_id, r in b_sim.robots.items()}
            balance = MetricsCollector.calculate_workload_balance(robot_counts)
            total_dist = sum(r.total_distance for r in b_sim.robots.values())
            utilization = summary.get('robot_utilization_percent', 0.0)

            results.append({
                'strategy': strat.value,
                'strategy_label': getattr(strat, 'label', strat.value),
                'completed_tasks': summary['completed_tasks'],
                'total_distance': total_dist,
                'utilization_pct': utilization,
                'gini_index': balance['gini'],
                'workload_std_dev': balance['std_dev'],
                'runtime_ms': round(elapsed_ms, 2),
                'detected_conflicts': summary['detected_conflicts'],
            })

        self._benchmark_cache = results
        self._cache_step = getattr(self.sim, 'step_count', 0)
        return results

    def get_current_efficiency_metrics(self) -> Dict[str, Any]:
        """Returns current live simulation efficiency metrics."""
        summary = self.sim.metrics.get_summary()
        robots = self.sim.robots

        total_dist = sum(r.total_distance for r in robots.values())
        avg_dist = round(total_dist / max(len(robots), 1), 1)
        utilization = summary.get('robot_utilization_percent', 0.0)
        completed = summary.get('completed_tasks', 0)
        steps = max(summary.get('makespan', 1), 1)
        throughput = round((completed / steps) * 100.0, 2)

        active = sum(
            1 for r in robots.values()
            if getattr(r, 'state', 'IDLE') not in ('IDLE', 'DOCKED')
        )
        idle_ratio = round(1.0 - (active / max(len(robots), 1)), 2)

        return {
            'avg_distance_per_robot': avg_dist,
            'total_fleet_distance': total_dist,
            'utilization_pct': utilization,
            'idle_ratio': idle_ratio,
            'throughput_per_100_steps': throughput,
            'completed_tasks': completed,
            'active_robots': active,
        }

    def recommend_strategy(
        self,
        benchmark_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Pick the best strategy from benchmark results.

        Scoring: 60% weight on completed_tasks, 40% weight on
        workload balance (inverse gini). Ties broken by runtime.
        """
        data = benchmark_data or self._benchmark_cache
        if not data:
            data = self.benchmark_strategies()

        max_tasks = max(r['completed_tasks'] for r in data) or 1

        best = None
        best_score = -1.0
        for row in data:
            task_score = row['completed_tasks'] / max_tasks
            balance_score = 1.0 - row['gini_index']
            combined = 0.6 * task_score + 0.4 * balance_score
            if combined > best_score or (
                combined == best_score
                and row['runtime_ms'] < (best or {}).get('runtime_ms', 1e9)
            ):
                best_score = combined
                best = row

        if best is None:
            return {'recommended': 'WEIGHTED_MULTI_CRITERIA', 'reason': 'Insufficient data', 'score': 0.0}

        reason = (
            f"Highest combined score ({best_score:.2f}): "
            f"{best['completed_tasks']} tasks completed, "
            f"Gini={best['gini_index']:.3f} (lower=fairer workload), "
            f"runtime={best['runtime_ms']:.1f}ms."
        )
        return {
            'recommended': best['strategy'],
            'recommended_label': best.get('strategy_label', best['strategy']),
            'combined_score': round(best_score, 3),
            'reason': reason,
        }

    def estimate_improvement(
        self,
        current_strategy: str,
        recommended_strategy: str,
        benchmark_data: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """Estimate percent improvement in throughput switching to recommended strategy.

        Returns 0.0 if strategies are identical or data unavailable.
        """
        data = benchmark_data or self._benchmark_cache
        if not data:
            return 0.0

        current_row = next((r for r in data if r['strategy'] == current_strategy), None)
        recommended_row = next((r for r in data if r['strategy'] == recommended_strategy), None)

        if not current_row or not recommended_row:
            return 0.0

        current_tasks = max(current_row['completed_tasks'], 1)
        recommended_tasks = recommended_row['completed_tasks']
        improvement = ((recommended_tasks - current_tasks) / current_tasks) * 100.0
        return round(improvement, 1)
