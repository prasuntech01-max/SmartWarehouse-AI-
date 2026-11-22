"""Module 10 — AI Analytics Engine (Central Coordinator).

Orchestrates all Module 10 analytics sub-engines:
  - DemandForecaster
  - ShelfOptimizer
  - CongestionPredictor
  - RobotHealthMonitor
  - FleetOptimizer

Caches results and invalidates the cache only when sim.step_count advances.
"""

from typing import Dict, List, Any, Optional


class AIAnalyticsEngine:
    """Central coordinator for all Module 10 AI analytics.

    Parameters
    ----------
    sim : WarehouseSimulator
        The live simulation instance (read-only — never mutated by analytics).
    """

    def __init__(self, sim: Any) -> None:
        self.sim = sim
        self._last_analysis_step: int = -1
        self._cache: Optional[Dict[str, Any]] = None

        # Lazy-import sub-engines to avoid circular dependencies at startup
        from core.demand_forecasting import DemandForecaster
        from core.shelf_optimizer import ShelfOptimizer
        from core.congestion_predictor import CongestionPredictor
        from core.predictive_maintenance import RobotHealthMonitor
        from core.fleet_optimizer import FleetOptimizer

        self.demand_forecaster = DemandForecaster()
        self.shelf_optimizer = ShelfOptimizer(
            grid=sim.grid,
            task_manager=sim.task_manager,
        )
        self.congestion_predictor = CongestionPredictor(grid=sim.grid)
        self.health_monitor = RobotHealthMonitor(
            robots=sim.robots,
            step_count=sim.step_count,
        )
        self.fleet_optimizer = FleetOptimizer(sim=sim)

    def _is_stale(self) -> bool:
        return self.sim.step_count != self._last_analysis_step

    def refresh(self) -> None:
        """Force-refresh analysis from the latest simulation state."""
        self.run_full_analysis()

    def run_full_analysis(self) -> Dict[str, Any]:
        """Runs all analytics engines and caches the results.

        Returns the full analysis dict. Safe to call repeatedly —
        returns cached data if step_count has not advanced.
        """
        if not self._is_stale() and self._cache is not None:
            return self._cache

        sim = self.sim

        # 1. Update demand forecaster with completed task history
        completed = sim.task_manager.get_completed_tasks()
        self.demand_forecaster.update(completed)

        # 2. Update shelf optimizer demand heatmap
        demand_heatmap = self.demand_forecaster.get_demand_heatmap_data()
        self.shelf_optimizer.demand_heatmap = demand_heatmap

        # 3. Congestion analysis from live robot paths
        congestion_report = self.congestion_predictor.get_full_report(sim.robots)

        # 4. Fleet health monitoring
        self.health_monitor.robots = sim.robots
        self.health_monitor.step_count = sim.step_count
        health_summary = self.health_monitor.get_fleet_health_summary()

        # 5. Fleet efficiency metrics (benchmark on-demand — not auto-run)
        efficiency = self.fleet_optimizer.get_current_efficiency_metrics()

        # 6. Shelf optimisation report
        opt_report = self.shelf_optimizer.get_optimization_report()

        self._cache = {
            'step': sim.step_count,
            'demand': {
                'summary': self.demand_forecaster.get_summary(),
                'top_shelves': self.demand_forecaster.get_top_shelves(10),
                'heatmap': demand_heatmap,
                'forecast': self.demand_forecaster.forecast_next_demand(steps_ahead=10),
            },
            'congestion': congestion_report,
            'health': health_summary,
            'fleet_efficiency': efficiency,
            'shelf_optimization': opt_report,
        }

        self._last_analysis_step = sim.step_count
        return self._cache

    def get_summary_kpis(self) -> Dict[str, Any]:
        """Headline KPIs for the executive dashboard."""
        analysis = self.run_full_analysis()
        health = analysis['health']
        fleet_avg_health = round(
            sum(h['score'] for h in health.values()) / max(len(health), 1),
            1,
        ) if health else 100.0

        congestion_score = analysis['congestion'].get('congestion_score', 0.0)
        completed_tasks = self.sim.task_manager.get_completed_count()
        forecast = analysis['demand']['forecast']
        efficiency = analysis['fleet_efficiency']
        recs = analysis['shelf_optimization']['recommendations']

        return {
            'fleet_avg_health': fleet_avg_health,
            'congestion_score': congestion_score,
            'completed_tasks': completed_tasks,
            'predicted_next_tasks': forecast.get('predicted_tasks', 0.0),
            'forecast_confidence': forecast.get('confidence', 'low'),
            'utilization_pct': efficiency.get('utilization_pct', 0.0),
            'shelf_recommendations_count': len(recs),
            'preliminary_data': forecast.get('preliminary', True),
        }

    def get_all_recommendations(self) -> List[Dict[str, Any]]:
        """Aggregated and prioritised list of all system recommendations."""
        analysis = self.run_full_analysis()
        all_recs = []

        # Congestion recommendations
        for rec in analysis['congestion'].get('recommendations', []):
            all_recs.append({'source': 'Congestion', 'priority': 'HIGH', 'message': rec})

        # Health recommendations
        for r_id, h in analysis['health'].items():
            for rec in h.get('recommendations', []):
                pri = 'CRITICAL' if 'CRITICAL' in rec else 'HIGH' if 'WARNING' in rec else 'NORMAL'
                all_recs.append({'source': f'Robot R{r_id} Health', 'priority': pri, 'message': rec})

        # Shelf recommendations
        for r in analysis['shelf_optimization'].get('recommendations', []):
            all_recs.append({'source': 'Shelf Layout', 'priority': 'NORMAL', 'message': r.get('suggestion', '')})

        # Sort: CRITICAL > HIGH > NORMAL
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'NORMAL': 2}
        all_recs.sort(key=lambda r: priority_order.get(r['priority'], 3))
        return all_recs
