"""Deadlock Detection and Recovery re-export module.

Re-exports DeadlockHandler, WaitForGraph, and DeadlockEvent
directly from core.deadlock to maintain a single canonical implementation.
"""

from core.deadlock import (
    DeadlockEvent,
    WaitForGraph,
    DeadlockHandler,
)

__all__ = [
    "DeadlockEvent",
    "WaitForGraph",
    "DeadlockHandler",
]
