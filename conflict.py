"""Multi-Robot Conflict Detection re-export module.

Re-exports MultiRobotConflictDetector, ConflictReport, and ConflictType
directly from core.conflict to maintain a single canonical implementation.
"""

from core.conflict import (
    ConflictType,
    ConflictReport,
    MultiRobotConflictDetector,
)

__all__ = [
    "ConflictType",
    "ConflictReport",
    "MultiRobotConflictDetector",
]
