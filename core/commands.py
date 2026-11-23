"""Robot Command & Manual Control Interface for SmartWarehouse AI.

Defines the single authoritative command dispatch API (sim.submit_command)
used by UI controls, keyboard listeners, Three.js bridge events, and unit tests.

Phase 5 Deliverable: Pure Python, fully unit-testable, with safety interlocks.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class CommandType(str, Enum):
    """Supported robot control and dispatch commands."""
    SET_MODE = "SET_MODE"              # params: {"mode": "AUTO" | "MANUAL"}
    MOVE_FORWARD = "MOVE_FORWARD"      # moves 1 cell in current heading direction
    MOVE_BACKWARD = "MOVE_BACKWARD"    # moves 1 cell opposite to current heading
    TURN_LEFT = "TURN_LEFT"            # rotates 90 degrees counter-clockwise
    TURN_RIGHT = "TURN_RIGHT"          # rotates 90 degrees clockwise
    GOTO_CELL = "GOTO_CELL"            # params: {"target": (x, y)} — computes collision-free A* path
    PICKUP = "PICKUP"                  # params: {"parcel_id": str} (or picks adjacent/current parcel)
    CARRY = "CARRY"                    # locks parcel to carry anchor
    DROP = "DROP"                      # releases parcel at current/valid destination cell
    PAUSE = "PAUSE"                    # pauses active movement
    RESUME = "RESUME"                  # resumes paused movement
    STOP = "STOP"                      # halts current path and clears goal
    RESET = "RESET"                    # repositions robot back to home dock safely
    EMERGENCY_STOP = "EMERGENCY_STOP"  # immediate safety stop (blocks movement until RESUME)
    ASSIGN_TASK = "ASSIGN_TASK"        # params: {"task_id": int} or {"pick": (x,y), "drop": (x,y)}


@dataclass
class CommandResult:
    """Standardized response from any robot command execution."""
    ok: bool
    reason: str
    robot_id: int
    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    resulting_pos: Optional[Tuple[int, int]] = None
    resulting_state: Optional[str] = None
    resulting_mode: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "robot_id": self.robot_id,
            "command": self.command,
            "params": self.params,
            "resulting_pos": list(self.resulting_pos) if self.resulting_pos else None,
            "resulting_state": self.resulting_state,
            "resulting_mode": self.resulting_mode,
            "timestamp": self.timestamp,
        }


@dataclass
class RobotCommandLogEntry:
    """Historical audit record of commands issued."""
    entry_id: int
    tick: int
    robot_id: int
    command: str
    params: Dict[str, Any]
    result: CommandResult
