"""Data models for explainable advisory recommendations."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class RecommendationPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RuleEvidence:
    """Quantitative evidence supporting an advisory recommendation."""
    metric_name: str
    measured_value: Any
    threshold_value: Any
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "measured_value": self.measured_value,
            "threshold_value": self.threshold_value,
            "details": self.details,
        }


@dataclass
class Recommendation:
    """An explainable, rule-based recommendation."""
    rule_id: str
    title: str
    problem_detected: str
    evidence: List[RuleEvidence]
    suggested_action: str
    expected_benefit: str
    priority: RecommendationPriority
    confidence: str = "HIGH"
    action_key: Optional[str] = None
    is_advisory: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "problem_detected": self.problem_detected,
            "evidence": [e.to_dict() for e in self.evidence],
            "suggested_action": self.suggested_action,
            "expected_benefit": self.expected_benefit,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "action_key": self.action_key,
            "is_advisory": self.is_advisory,
        }
