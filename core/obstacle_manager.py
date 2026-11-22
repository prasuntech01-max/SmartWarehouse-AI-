"""Dynamic Obstacle Management with lifecycle tracking and path intersection detection.

Supports dynamic obstacle injection, event logging, active obstacle tracking,
and detection of intersections with robot trajectories.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Set
import time


@dataclass
class ObstacleEvent:
    """Structured record of a dynamic obstacle event."""
    obstacle_id: int
    pos: Tuple[int, int]
    activated_at: int
    removed_at: Optional[int] = None
    status: str = 'active'   # 'active' | 'removed'
    affected_robots: List[int] = field(default_factory=list)
    reason: str = 'manual'

    def to_dict(self) -> Dict[str, Any]:
        """Convert obstacle event to serializable dictionary."""
        return {
            'obstacle_id': self.obstacle_id,
            'pos': self.pos,
            'activated_at': self.activated_at,
            'removed_at': self.removed_at,
            'status': self.status,
            'affected_robots': list(self.affected_robots),
            'reason': self.reason,
        }


class DynamicObstacleManager:
    """
    Manages runtime dynamic obstacles, tracks event history, and
    analyzes intersections against robot planned trajectories.
    """

    def __init__(self):
        self._next_id: int = 1
        self._events: List[ObstacleEvent] = []
        self._active: Dict[int, ObstacleEvent] = {}             # obstacle_id -> event
        self._pos_to_id: Dict[Tuple[int, int], int] = {}        # (x, y) -> obstacle_id

    def add_obstacle(
        self,
        pos: Tuple[int, int],
        current_time: int,
        reason: str = 'manual',
    ) -> ObstacleEvent:
        """Register a new dynamic obstacle."""
        # If an active obstacle already exists at this location, reuse or return it
        if pos in self._pos_to_id:
            existing_id = self._pos_to_id[pos]
            return self._active[existing_id]

        obs_id = self._next_id
        self._next_id += 1

        event = ObstacleEvent(
            obstacle_id=obs_id,
            pos=pos,
            activated_at=current_time,
            status='active',
            reason=reason,
        )
        self._events.append(event)
        self._active[obs_id] = event
        self._pos_to_id[pos] = obs_id
        return event

    def remove_obstacle(self, obstacle_id: int, current_time: int) -> bool:
        """Deactivate and archive an active dynamic obstacle by ID."""
        if obstacle_id not in self._active:
            return False

        event = self._active.pop(obstacle_id)
        event.removed_at = current_time
        event.status = 'removed'
        self._pos_to_id.pop(event.pos, None)
        return True

    def remove_obstacle_at(self, pos: Tuple[int, int], current_time: int) -> bool:
        """Deactivate an active obstacle at specified coordinates."""
        obs_id = self._pos_to_id.get(pos)
        if obs_id is None:
            return False
        return self.remove_obstacle(obs_id, current_time)

    def clear(self, current_time: int = 0) -> None:
        """Deactivate all active obstacles."""
        for obs_id in list(self._active.keys()):
            self.remove_obstacle(obs_id, current_time)

    def get_active_obstacles(self) -> List[ObstacleEvent]:
        """Return list of all currently active obstacle events."""
        return list(self._active.values())

    def get_active_positions(self) -> List[Tuple[int, int]]:
        """Return coordinates of all currently active obstacles."""
        return [e.pos for e in self._active.values()]

    def get_history(self) -> List[ObstacleEvent]:
        """Return complete historical event log."""
        return list(self._events)

    def detect_path_intersections(
        self,
        paths: Dict[int, List[Tuple[int, int]]],
        future_steps: int = 50,
    ) -> Dict[int, List[ObstacleEvent]]:
        """
        Scans robot planned trajectories to detect any collision with active dynamic obstacles.

        Args:
            paths: Dict of robot_id -> remaining path coordinates [(x, y), ...]
            future_steps: Horizon limit to inspect along trajectory

        Returns:
            Dict mapping robot_id to list of blocking ObstacleEvents
        """
        active_pos_map = {e.pos: e for e in self._active.values()}
        intersections: Dict[int, List[ObstacleEvent]] = {}

        for robot_id, path in paths.items():
            if not path:
                continue
            blocking_events: List[ObstacleEvent] = []
            for cell in path[:future_steps]:
                if cell in active_pos_map:
                    ev = active_pos_map[cell]
                    if ev not in blocking_events:
                        blocking_events.append(ev)

            if blocking_events:
                intersections[robot_id] = blocking_events

        return intersections

    def mark_affected(self, obstacle_id: int, robot_ids: List[int]) -> None:
        """Associate affected robot IDs with an obstacle event."""
        if obstacle_id in self._active:
            current_affected = set(self._active[obstacle_id].affected_robots)
            for r in robot_ids:
                if r not in current_affected:
                    self._active[obstacle_id].affected_robots.append(r)

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def active_count(self) -> int:
        return len(self._active)
