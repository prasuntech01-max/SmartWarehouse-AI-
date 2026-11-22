"""Recommendation engine coordinating evaluation across all diagnostic rules."""

from typing import List, Dict, Any, Optional
from .models import Recommendation
from .rules import (
    BaseRecommendationRule,
    UnderutilizedRobotRule,
    BatteryDepletionRiskRule,
    CongestedAreaRule,
    PredictiveMaintenanceRule,
    ShelfLayoutInefficiencyRule,
)
from analytics.service import AnalyticsService


class RecommendationEngine:
    """Evaluates transparent, rule-based advisory recommendations using live warehouse data."""

    def __init__(self, analytics_service: AnalyticsService):
        self.analytics_service = analytics_service
        self.rules: List[BaseRecommendationRule] = [
            BatteryDepletionRiskRule(),
            PredictiveMaintenanceRule(),
            CongestedAreaRule(),
            UnderutilizedRobotRule(),
            ShelfLayoutInefficiencyRule(),
        ]

    def register_rule(self, rule: BaseRecommendationRule) -> None:
        self.rules.append(rule)

    def evaluate_all(self) -> List[Recommendation]:
        """Runs all rules and returns triggered recommendations sorted by priority."""
        snapshot = self.analytics_service.get_snapshot()
        sim = self.analytics_service.sim
        recommendations: List[Recommendation] = []

        for rule in self.rules:
            try:
                rec = rule.evaluate(sim, snapshot)
                if rec is not None:
                    recommendations.append(rec)
            except Exception:
                pass

        # Sort priority order: CRITICAL -> HIGH -> MEDIUM -> LOW
        priority_weights = {
            "CRITICAL": 0,
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3,
        }
        recommendations.sort(key=lambda r: priority_weights.get(r.priority.value, 99))
        return recommendations
