"""Module 10 — Demand Forecasting Engine.

Analyses historical task data to forecast warehouse order demand,
identify high-traffic shelves, and compute demand heatmap overlays.
Uses exponential weighted moving average (EWMA) — no sklearn required.
"""

from typing import Dict, List, Tuple, Optional, Any
import math


class DemandForecaster:
    """Forecasts warehouse order demand from completed task telemetry.

    All forecasts are derived from actual simulation task history.
    When fewer than 3 tasks have been completed, results are labelled
    'preliminary' to indicate limited data.
    """

    # Smoothing factor for EWMA forecast (0 < alpha <= 1)
    ALPHA: float = 0.3

    def __init__(self) -> None:
        self._shelf_freq: Dict[Tuple[int, int], int] = {}
        self._delivery_freq: Dict[Tuple[int, int], int] = {}
        self._completion_steps: List[int] = []
        self._total_updated: int = 0
        self._data_sufficient: bool = False

    # ------------------------------------------------------------------
    # Public update interface
    # ------------------------------------------------------------------

    def update(self, completed_tasks: List[Any]) -> None:
        """Rebuild frequency tables from the full completed-task list.

        Parameters
        ----------
        completed_tasks : list of WarehouseTask
            All tasks whose status == 'COMPLETED'.
        """
        self._shelf_freq.clear()
        self._delivery_freq.clear()
        self._completion_steps.clear()

        for task in completed_tasks:
            # Count shelf pickups
            shelf = getattr(task, 'shelf_loc', None) or getattr(task, 'pick_spot', None)
            if shelf:
                self._shelf_freq[shelf] = self._shelf_freq.get(shelf, 0) + 1

            # Count delivery destinations
            delivery = getattr(task, 'delivery_station', None)
            if delivery:
                self._delivery_freq[delivery] = self._delivery_freq.get(delivery, 0) + 1

            # Record completion timestep
            step = getattr(task, 'completed_at_step', None)
            if step is not None:
                self._completion_steps.append(step)

        self._total_updated = len(completed_tasks)
        self._data_sufficient = self._total_updated >= 3

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_top_shelves(self, n: int = 10) -> List[Tuple[Tuple[int, int], int]]:
        """Returns the n most frequently picked shelf locations with their counts.

        Returns
        -------
        List of ((x, y), count) sorted descending by count.
        """
        sorted_shelves = sorted(
            self._shelf_freq.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return sorted_shelves[:n]

    def get_demand_trend(
        self,
        shelf_loc: Tuple[int, int],
        window: int = 5,
    ) -> List[float]:
        """Compute a simple moving average completion rate over rolling windows.

        Returns a list of avg tasks-per-window for each sequential window
        across all recorded completion steps. Returns [] when data is
        insufficient for the shelf location requested.
        """
        if shelf_loc not in self._shelf_freq or not self._completion_steps:
            return []

        sorted_steps = sorted(self._completion_steps)
        if not sorted_steps:
            return []

        min_step = sorted_steps[0]
        max_step = sorted_steps[-1]
        span = max_step - min_step
        if span == 0:
            return [float(self._shelf_freq.get(shelf_loc, 0))]

        # Build a histogram of completions in windows of size `window`
        num_buckets = max(1, math.ceil(span / window))
        buckets = [0.0] * num_buckets
        for s in sorted_steps:
            idx = min(int((s - min_step) / window), num_buckets - 1)
            buckets[idx] += 1.0

        # Normalise by shelf frequency proportion
        shelf_count = self._shelf_freq.get(shelf_loc, 0)
        total_count = max(1, sum(self._shelf_freq.values()))
        ratio = shelf_count / total_count

        return [round(b * ratio, 2) for b in buckets]

    def forecast_next_demand(self, steps_ahead: int = 10) -> Dict[str, Any]:
        """Forecast demand rate for the next `steps_ahead` simulation steps.

        Uses EWMA on historical inter-completion intervals.

        Returns
        -------
        dict with keys:
          - 'predicted_tasks': float
          - 'confidence': str — 'low' | 'medium' | 'high'
          - 'preliminary': bool
          - 'alpha': float
        """
        if len(self._completion_steps) < 2:
            return {
                'predicted_tasks': 0.0,
                'confidence': 'low',
                'preliminary': True,
                'alpha': self.ALPHA,
            }

        sorted_steps = sorted(self._completion_steps)
        intervals = [
            sorted_steps[i + 1] - sorted_steps[i]
            for i in range(len(sorted_steps) - 1)
            if sorted_steps[i + 1] - sorted_steps[i] > 0
        ]

        if not intervals:
            predicted = float(self._total_updated)
            return {
                'predicted_tasks': predicted,
                'confidence': 'medium',
                'preliminary': not self._data_sufficient,
                'alpha': self.ALPHA,
            }

        # Exponential weighted moving average of inter-arrival intervals
        ewma_interval = float(intervals[0])
        for iv in intervals[1:]:
            ewma_interval = self.ALPHA * iv + (1.0 - self.ALPHA) * ewma_interval

        predicted = steps_ahead / max(ewma_interval, 0.1)

        confidence = (
            'high' if self._total_updated >= 10
            else 'medium' if self._total_updated >= 5
            else 'low'
        )

        return {
            'predicted_tasks': round(predicted, 2),
            'confidence': confidence,
            'preliminary': not self._data_sufficient,
            'alpha': self.ALPHA,
        }

    def get_demand_heatmap_data(self) -> Dict[Tuple[int, int], float]:
        """Returns a normalised heatmap dict {grid_pos: 0.0-1.0} for overlays."""
        if not self._shelf_freq:
            return {}
        max_freq = max(self._shelf_freq.values(), default=1)
        return {
            pos: round(count / max_freq, 3)
            for pos, count in self._shelf_freq.items()
        }

    def get_delivery_heatmap_data(self) -> Dict[Tuple[int, int], float]:
        """Normalised heatmap of delivery station traffic."""
        if not self._delivery_freq:
            return {}
        max_freq = max(self._delivery_freq.values(), default=1)
        return {
            pos: round(count / max_freq, 3)
            for pos, count in self._delivery_freq.items()
        }

    @property
    def total_tasks_analysed(self) -> int:
        return self._total_updated

    @property
    def data_sufficient(self) -> bool:
        return self._data_sufficient

    def get_summary(self) -> Dict[str, Any]:
        """Returns a concise analysis summary dict."""
        forecast = self.forecast_next_demand()
        top = self.get_top_shelves(5)
        return {
            'total_tasks_analysed': self._total_updated,
            'unique_shelf_locations': len(self._shelf_freq),
            'top_shelf': top[0] if top else None,
            'predicted_next_10_steps': forecast['predicted_tasks'],
            'forecast_confidence': forecast['confidence'],
            'preliminary': forecast['preliminary'],
        }
