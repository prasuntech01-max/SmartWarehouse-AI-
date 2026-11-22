"""Data models and provenance definitions for the analytics service."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ProvenanceType(str, Enum):
    """Data provenance classification."""
    MEASURED = "MEASURED"                     # Wall-clock timing, OS memory, DB rows
    SIMULATED = "SIMULATED"                   # Produced by discrete-time simulation engine
    SIMULATED_TELEMETRY = "SIMULATED-TELEMETRY" # Produced by simulated IoT sensors
    ESTIMATED = "ESTIMATED"                   # Derived, extrapolated, or theoretical optimal


@dataclass(frozen=True)
class MetricValue:
    """A strongly-typed metric value with explicit provenance."""
    value: Any
    unit: str = ""
    provenance: ProvenanceType = ProvenanceType.SIMULATED
    confidence: str = "HIGH"                  # HIGH, MEDIUM, PRELIMINARY
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.value,
            "confidence": self.confidence,
            "notes": self.notes,
        }


@dataclass
class FilterSpec:
    """Filter specifications for analytics aggregation."""
    start_step: int = 0
    end_step: Optional[int] = None
    robot_ids: Optional[List[int]] = None
    hazard_types: Optional[List[str]] = None
    severity_levels: Optional[List[str]] = None


@dataclass
class AnalyticsSnapshot:
    """Comprehensive snapshot of warehouse analytics."""
    timestamp: float
    simulation_step: int
    wall_clock_uptime_sec: float
    summary_kpis: Dict[str, MetricValue] = field(default_factory=dict)
    fleet_metrics: Dict[int, Dict[str, MetricValue]] = field(default_factory=dict)
    workload_balance: Dict[str, MetricValue] = field(default_factory=dict)
    path_efficiency: Dict[str, MetricValue] = field(default_factory=dict)
    safety_kpis: Dict[str, MetricValue] = field(default_factory=dict)
    iot_kpis: Dict[str, MetricValue] = field(default_factory=dict)
    task_breakdown: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "simulation_step": self.simulation_step,
            "wall_clock_uptime_sec": self.wall_clock_uptime_sec,
            "summary_kpis": {k: v.to_dict() for k, v in self.summary_kpis.items()},
            "fleet_metrics": {
                r_id: {k: v.to_dict() for k, v in m.items()}
                for r_id, m in self.fleet_metrics.items()
            },
            "workload_balance": {k: v.to_dict() for k, v in self.workload_balance.items()},
            "path_efficiency": {k: v.to_dict() for k, v in self.path_efficiency.items()},
            "safety_kpis": {k: v.to_dict() for k, v in self.safety_kpis.items()},
            "iot_kpis": {k: v.to_dict() for k, v in self.iot_kpis.items()},
            "task_breakdown": self.task_breakdown,
        }
