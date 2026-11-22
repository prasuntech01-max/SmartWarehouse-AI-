"""Module 10 — Shelf Layout Optimizer.

Analyses warehouse shelf layout relative to demand patterns and station
proximity, then recommends advisory relocations to minimise total robot
travel distance. Recommendations are NEVER automatically applied to the
live grid without explicit user approval.
"""

from typing import Dict, List, Tuple, Any, Optional


def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class ShelfOptimizer:
    """Analyses and optimises warehouse shelf placement relative to demand.

    Parameters
    ----------
    grid : WarehouseGrid
        The live warehouse grid (read-only access).
    task_manager : TaskManager
        Source of completed task telemetry.
    demand_heatmap : dict, optional
        {shelf_pos: 0.0-1.0} from DemandForecaster.get_demand_heatmap_data().
    """

    def __init__(
        self,
        grid: Any,
        task_manager: Any,
        demand_heatmap: Optional[Dict[Tuple[int, int], float]] = None,
    ) -> None:
        self.grid = grid
        self.task_manager = task_manager
        self.demand_heatmap: Dict[Tuple[int, int], float] = demand_heatmap or {}

    def analyse_current_layout(self) -> Dict[str, Any]:
        """Compute current average shelf-to-nearest-packing-station distance.

        Returns
        -------
        dict with:
          - 'shelf_count': int
          - 'avg_shelf_to_station_dist': float
          - 'shelf_distances': list of {shelf, nearest_station, dist}
        """
        shelves = list(self.grid.shelves)
        stations = list(self.grid.packing_stations)

        if not shelves or not stations:
            return {
                'shelf_count': 0,
                'avg_shelf_to_station_dist': 0.0,
                'shelf_distances': [],
            }

        shelf_distances = []
        total_dist = 0.0

        for shelf in shelves:
            dists = [_manhattan(shelf, st) for st in stations]
            min_dist = min(dists)
            nearest = stations[dists.index(min_dist)]
            shelf_distances.append({
                'shelf': shelf,
                'nearest_station': nearest,
                'dist': min_dist,
            })
            total_dist += min_dist

        avg_dist = total_dist / len(shelves)

        return {
            'shelf_count': len(shelves),
            'avg_shelf_to_station_dist': round(avg_dist, 2),
            'shelf_distances': shelf_distances,
        }

    def recommend_relocations(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Identify high-demand shelves far from stations and recommend swaps.

        A 'score' is computed as (demand_weight + 0.1) * distance_to_nearest_station.
        High-score shelves are relocation candidates.

        Returns
        -------
        List of advisory recommendation dicts.
        """
        shelves = list(self.grid.shelves)
        stations = list(self.grid.packing_stations)

        if not shelves or not stations:
            return []

        scored = []
        for shelf in shelves:
            dists = [_manhattan(shelf, st) for st in stations]
            min_dist = min(dists)
            nearest = stations[dists.index(min_dist)]
            demand = self.demand_heatmap.get(shelf, 0.0)
            score = (demand + 0.1) * min_dist
            scored.append({
                'shelf': shelf,
                'demand': demand,
                'dist_to_station': min_dist,
                'nearest_station': nearest,
                'score': round(score, 3),
            })

        # Shelves with lowest demand that are closest to packing stations
        low_demand_near_station = sorted(
            scored,
            key=lambda x: (x['demand'], x['dist_to_station'])
        )

        scored.sort(key=lambda x: x['score'], reverse=True)
        recommendations = []
        for idx, item in enumerate(scored[:top_n]):
            # Pick a suitable swap target that is distinct from item
            target_swap = None
            for cand in low_demand_near_station:
                if cand['shelf'] != item['shelf'] and cand['dist_to_station'] < item['dist_to_station']:
                    target_swap = cand['shelf']
                    break

            if item['demand'] > 0.5:
                suggestion = (
                    f"HIGH-DEMAND shelf at {item['shelf']} is {item['dist_to_station']} "
                    f"cells from nearest packing station — recommend swapping closer to reduce travel."
                )
            elif item['dist_to_station'] > 8:
                suggestion = (
                    f"Shelf at {item['shelf']} is far from stations (dist={item['dist_to_station']}). "
                    f"Moving it nearer would reduce idle travel."
                )
            else:
                suggestion = (
                    f"Shelf at {item['shelf']} has demand={item['demand']:.2f} and "
                    f"dist={item['dist_to_station']} — moderate relocation benefit."
                )
            item['suggestion'] = suggestion
            item['target_swap'] = target_swap or (2, 3)
            recommendations.append(item)

        return recommendations

    def estimate_distance_saving(
        self,
        relocation_plan: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Estimate total travel savings if top recommendations are implemented.

        Returns
        -------
        dict with 'current_avg_dist', 'estimated_improvement_pct', 'actionable_items'.
        """
        layout = self.analyse_current_layout()
        current_avg = layout['avg_shelf_to_station_dist']

        if relocation_plan is None:
            relocation_plan = self.recommend_relocations()

        if not relocation_plan or current_avg == 0.0:
            return {
                'current_avg_dist': current_avg,
                'estimated_improvement_pct': 0.0,
                'actionable_items': 0,
            }

        total_current_dist = sum(r['dist_to_station'] for r in relocation_plan)
        estimated_saved = total_current_dist * 0.25
        avg_reduction = estimated_saved / max(len(relocation_plan), 1)
        improvement_pct = min(
            30.0,
            (avg_reduction / max(current_avg, 1.0)) * 100.0,
        )

        return {
            'current_avg_dist': current_avg,
            'estimated_improvement_pct': round(improvement_pct, 1),
            'actionable_items': len(relocation_plan),
        }

    def apply_relocation(
        self,
        source_shelf: Tuple[int, int],
        target_shelf: Tuple[int, int],
    ) -> Tuple[bool, str]:
        """Apply an approved relocation or swap between two shelf locations.

        Requires explicit user approval before invocation.
        """
        if source_shelf not in self.grid.shelves:
            return False, f"Source coordinate {source_shelf} is not an existing shelf."

        # Case 1: Both are existing shelves -> swap contents/demand mappings
        if target_shelf in self.grid.shelves:
            if source_shelf == target_shelf:
                return False, "Source and target shelf locations are identical."
            # Swap demand heatmap metrics
            s_d = self.demand_heatmap.get(source_shelf, 0.0)
            t_d = self.demand_heatmap.get(target_shelf, 0.0)
            self.demand_heatmap[source_shelf] = t_d
            self.demand_heatmap[target_shelf] = s_d
            return True, f"Successfully swapped shelf contents between {source_shelf} and {target_shelf}."

        # Case 2: Relocating to a new valid cell
        if not self.grid.in_bounds(*target_shelf):
            return False, f"Target coordinate {target_shelf} is out of warehouse bounds."
        if target_shelf in getattr(self.grid, 'charging_docks', []):
            return False, f"Target coordinate {target_shelf} is a reserved charging dock."
        if target_shelf in getattr(self.grid, 'packing_stations', []):
            return False, f"Target coordinate {target_shelf} is a reserved packing station."
        if not self.grid.is_walkable(*target_shelf):
            return False, f"Target coordinate {target_shelf} is obstructed."

        # Apply shelf move on grid obstacles
        if hasattr(self.grid, 'obstacles') and hasattr(self.grid.obstacles, 'shelves'):
            self.grid.obstacles.shelves.discard(source_shelf)
            self.grid.obstacles.shelves.add(target_shelf)
        elif hasattr(self.grid, 'shelves') and isinstance(self.grid.shelves, set):
            self.grid.shelves.discard(source_shelf)
            self.grid.shelves.add(target_shelf)

        if source_shelf in self.demand_heatmap:
            self.demand_heatmap[target_shelf] = self.demand_heatmap.pop(source_shelf)

        return True, f"Successfully relocated shelf from {source_shelf} to {target_shelf}."

    def get_optimization_report(self) -> Dict[str, Any]:
        """Full advisory optimisation report combining layout analysis and recommendations."""
        layout = self.analyse_current_layout()
        recs = self.recommend_relocations()
        savings = self.estimate_distance_saving(recs)

        return {
            'layout_analysis': layout,
            'recommendations': recs,
            'savings_estimate': savings,
            'advisory_note': (
                'These are advisory recommendations only. '
                'User approval is required before applying layout changes.'
            ),
        }
