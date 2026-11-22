"""Time-Expanded State Space and Planner re-export module.

Re-exports core time-expanded definitions directly from core.state
to maintain a single canonical implementation.
"""

from core.state import (
    Action,
    TimeExpandedState,
    Trajectory,
    TimeExpandedPlanner,
)

__all__ = [
    "Action",
    "TimeExpandedState",
    "Trajectory",
    "TimeExpandedPlanner",
]
