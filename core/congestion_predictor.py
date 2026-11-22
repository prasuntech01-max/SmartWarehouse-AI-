"""Module 10 — Congestion Prediction Engine.

Computes real-time traffic density across warehouse grid cells by analysing
active robot remaining paths from the live simulation state.
"""

from typing import Dict, List, Tuple, Any


# Severity colour bands (for UI rendering)
SEVERITY_BANDS = [
    (0.75, 'RED',    '#E74C3C'),
    (0.50, 'ORANGE', '#E67E22'),
    (0.30, 'YELLOW', '#F1C40F'),
    (0.00, 'GREEN',  '#27AE60'),
]


def _severity_label(score: float) -> Tuple[str, str]:
    """Return (label, hex_colour) for a normalised 0.0-1.0 score."""
    for threshold, label, colour in SEVERITY_BANDS:
        if score >= threshold:
            return label, colour
    return 'GREEN', '#27AE60'


class CongestionPredictor:
    """Predicts traffic hotspots from active robot path futures.

    Parameters
    ----------
    grid : WarehouseGrid
        Warehouse grid (read-only, for dimensions).
    """

    def __init__(self, grid: Any) -> None:
        self.grid = grid

    def compute_cell_traffic(
        self,
        robots: Dict[int, Any],
    ) -> Dict[Tuple[int, int], int]:
        """Count how many robot remaining paths pass through each cell.

        Only future path segments (from path_index onward) are considered.

        Returns
        -------
        dict {(x, y): count}  — raw traversal counts.
        """
        traffic: Dict[Tuple[int, int], int] = {}

        for robot in robots.values():
            path = getattr(robot, 'path', [])
            path_index = getattr(robot, 'path_index', 0)
            remaining = path[path_index:] if path_index < len(path) else []

            for cell in remaining:
                traffic[cell] = traffic.get(cell, 0) + 1

        return traffic

    def get_congestion_heatmap(
        self,
        robots: Dict[int, Any],
    ) -> Dict[Tuple[int, int], float]:
        """Returns normalised congestion {(x, y): 0.0-1.0} for all active paths."""
        traffic = self.compute_cell_traffic(robots)
        if not traffic:
            return {}

        max_traffic = max(traffic.values(), default=1)
        return {
            cell: round(count / max_traffic, 3)
            for cell, count in traffic.items()
        }

    def get_risk_zones(
        self,
        robots: Dict[int, Any],
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Identifies grid cells with congestion above `threshold`.

        Returns
        -------
        List of dicts with keys: cell, score, severity_label, colour.
        Sorted descending by score.
        """
        heatmap = self.get_congestion_heatmap(robots)
        zones = []
        for cell, score in heatmap.items():
            if score >= threshold:
                label, colour = _severity_label(score)
                zones.append({
                    'cell': cell,
                    'score': score,
                    'severity_label': label,
                    'colour': colour,
                })

        zones.sort(key=lambda z: z['score'], reverse=True)
        return zones

    def get_congestion_score(self, robots: Dict[int, Any]) -> float:
        """Returns an overall fleet congestion score (0 to 100).

        Computed as the mean normalised congestion across all active path cells,
        scaled to 0-100.
        """
        heatmap = self.get_congestion_heatmap(robots)
        if not heatmap:
            return 0.0
        mean_score = sum(heatmap.values()) / len(heatmap)
        return round(mean_score * 100.0, 1)

    def get_recommendations(self, robots: Dict[int, Any]) -> List[str]:
        """Returns text recommendations based on current congestion analysis."""
        score = self.get_congestion_score(robots)
        risk_zones = self.get_risk_zones(robots, threshold=0.6)
        recommendations = []

        if score > 70:
            recommendations.append(
                f"CRITICAL — Overall congestion score is {score:.0f}/100. "
                "Consider reducing active robots or switching to WORKLOAD_BALANCED strategy."
            )
        elif score > 45:
            recommendations.append(
                f"HIGH — Congestion score {score:.0f}/100. "
                "Activate deadlock-prevention buffers or stagger task dispatch."
            )
        elif score > 20:
            recommendations.append(
                f"MODERATE — Congestion score {score:.0f}/100. "
                "Monitor high-traffic aisles and consider path diversity strategies."
            )
        else:
            recommendations.append(
                f"LOW — Congestion score {score:.0f}/100. Fleet routing is efficient."
            )

        if risk_zones:
            top = risk_zones[0]
            recommendations.append(
                f"Highest-risk cell: {top['cell']} (score {top['score']:.2f} — {top['severity_label']}). "
                "Consider temporarily rerouting robots through alternative aisles."
            )
            if len(risk_zones) >= 3:
                recommendations.append(
                    f"{len(risk_zones)} high-traffic zones detected. "
                    "Switching to SHORTEST_TOTAL_ROUTE or BATCH_OPTIMAL strategy may reduce aisle contention."
                )

        num_active = sum(
            1 for r in robots.values()
            if getattr(r, 'state', '') not in ('IDLE', 'DOCKED')
        )
        if num_active == 0:
            recommendations = ["No active robots — congestion analysis unavailable."]

        return recommendations

    def get_full_report(self, robots: Dict[int, Any]) -> Dict[str, Any]:
        """Returns a complete congestion analysis snapshot."""
        return {
            'congestion_score': self.get_congestion_score(robots),
            'risk_zones': self.get_risk_zones(robots),
            'recommendations': self.get_recommendations(robots),
            'heatmap': self.get_congestion_heatmap(robots),
        }
