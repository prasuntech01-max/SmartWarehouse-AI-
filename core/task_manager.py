"""Task and Order assignment manager for warehouse robots."""

from enum import Enum, IntEnum
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
import random
from core.grid import WarehouseGrid


class TaskPriority(IntEnum):
    """Priority tiers for warehouse customer orders."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

    @classmethod
    def from_str(cls, name: str) -> "TaskPriority":
        mapping = {
            "low": cls.LOW,
            "normal": cls.NORMAL,
            "high": cls.HIGH,
            "urgent": cls.URGENT,
        }
        return mapping.get(str(name).lower(), cls.NORMAL)

    @property
    def label(self) -> str:
        names = {
            self.LOW: "Low",
            self.NORMAL: "Normal",
            self.HIGH: "High",
            self.URGENT: "Urgent",
        }
        return names.get(self, "Normal")


class TaskStatus(str, Enum):
    """Lifecycle states of warehouse pick-and-delivery orders."""
    PENDING = "QUEUED"           # Kept as QUEUED for full backward-compatibility
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    MOVING_TO_PICK = "MOVING_TO_PICK"
    PICKING = "PICKING"
    MOVING_TO_DELIVERY = "MOVING_TO_DELIVERY"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


# Valid transition state-machine rules
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "QUEUED": ["ASSIGNED", "MOVING_TO_PICK", "CANCELLED", "FAILED"],
    "ASSIGNED": ["MOVING_TO_PICK", "QUEUED", "CANCELLED", "FAILED"],
    "PICKING_IN_TRANSIT": ["PICKING", "MOVING_TO_PICK", "QUEUED", "CANCELLED", "FAILED"],
    "MOVING_TO_PICK": ["PICKING", "QUEUED", "CANCELLED", "FAILED"],
    "PICKING": ["MOVING_TO_DELIVERY", "DELIVERY_IN_TRANSIT", "CANCELLED", "FAILED"],
    "DELIVERY_IN_TRANSIT": ["DELIVERING", "MOVING_TO_DELIVERY", "CANCELLED", "FAILED"],
    "MOVING_TO_DELIVERY": ["DELIVERING", "CANCELLED", "FAILED"],
    "DELIVERING": ["COMPLETED", "CANCELLED", "FAILED"],
    "COMPLETED": [],     # Terminal
    "CANCELLED": ["QUEUED"],     # Can be re-opened
    "FAILED": ["QUEUED"],        # Can be re-queued
}


@dataclass
class WarehouseTask:
    """Represents a discrete warehouse order with priority, route, and lifecycle metrics."""
    task_id: int
    shelf_loc: Tuple[int, int]
    pick_spot: Tuple[int, int]
    delivery_station: Tuple[int, int]
    priority: int = TaskPriority.NORMAL
    status: str = 'QUEUED'
    assigned_robot: Optional[int] = None
    created_at_step: int = 0
    assigned_at_step: Optional[int] = None
    completed_at_step: Optional[int] = None
    estimated_cost: float = 0.0
    state_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.state_history:
            self.state_history.append({
                "from_status": None,
                "to_status": self.status,
                "step": self.created_at_step,
                "note": "Task created",
            })

    def transition_to(self, new_status: str, current_step: int, note: str = "") -> bool:
        """
        Executes a validated state transition.
        Prevents illegal state leaps and logs state transition history.
        """
        allowed = VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed and new_status != self.status:
            return False

        old_status = self.status
        self.status = new_status
        self.state_history.append({
            "from_status": old_status,
            "to_status": new_status,
            "step": current_step,
            "note": note,
        })
        return True

    def cancel(self, current_step: int, reason: str = "User cancellation") -> bool:
        """Cancels task if eligible."""
        if self.status in ("COMPLETED", "CANCELLED"):
            return False
        old_status = self.status
        self.status = "CANCELLED"
        self.assigned_robot = None
        self.state_history.append({
            "from_status": old_status,
            "to_status": "CANCELLED",
            "step": current_step,
            "note": reason,
        })
        return True

    def fail(self, current_step: int, reason: str = "Robot blocked or route unavailable") -> bool:
        """Marks task as failed and clears assigned robot."""
        if self.status in ("COMPLETED", "CANCELLED", "FAILED"):
            return False
        old_status = self.status
        self.status = "FAILED"
        self.assigned_robot = None
        self.state_history.append({
            "from_status": old_status,
            "to_status": "FAILED",
            "step": current_step,
            "note": reason,
        })
        return True

    @property
    def priority_label(self) -> str:
        try:
            return TaskPriority(self.priority).label
        except ValueError:
            return "Normal"

    def to_dict(self) -> Dict[str, Any]:
        """Convert task details to dictionary representation."""
        return {
            "task_id": self.task_id,
            "priority": self.priority,
            "priority_label": self.priority_label,
            "shelf_loc": self.shelf_loc,
            "pick_spot": self.pick_spot,
            "delivery_station": self.delivery_station,
            "status": self.status,
            "assigned_robot": self.assigned_robot,
            "created_at_step": self.created_at_step,
            "assigned_at_step": self.assigned_at_step,
            "completed_at_step": self.completed_at_step,
            "estimated_cost": round(self.estimated_cost, 2),
            "state_history": list(self.state_history),
        }


class TaskManager:
    """Manages order creation, validation, assignment tracking, and completion metrics."""

    def __init__(self, grid: WarehouseGrid, seed: int = 42):
        self.grid = grid
        self.random = random.Random(seed)
        self.tasks: Dict[int, WarehouseTask] = {}
        self.task_counter = 1
        self.completed_tasks: List[WarehouseTask] = []

    def validate_task_coordinates(
        self,
        pick_spot: Tuple[int, int],
        delivery_station: Tuple[int, int],
    ) -> Tuple[bool, str, Optional[Tuple[int, int]]]:
        """
        Validates pickup and delivery coordinates against warehouse boundaries,
        walkability, shelf accessibility, and packing station layout.
        Returns: (is_valid, error_message, shelf_loc)
        """
        px, py = pick_spot
        dx, dy = delivery_station

        # 1. Bounds check
        if not self.grid.in_bounds(px, py):
            return False, f"Pickup coordinate ({px}, {py}) is outside warehouse boundaries.", None
        if not self.grid.in_bounds(dx, dy):
            return False, f"Delivery coordinate ({dx}, {dy}) is outside warehouse boundaries.", None

        # 2. Walkability check
        if not self.grid.is_walkable(px, py):
            return False, f"Pickup coordinate ({px}, {py}) is blocked or inside a permanent shelf.", None
        if not self.grid.is_walkable(dx, dy):
            return False, f"Delivery coordinate ({dx}, {dy}) is blocked or non-walkable.", None

        # 3. Delivery station verification
        if delivery_station not in self.grid.packing_stations:
            return False, f"Delivery location ({dx}, {dy}) is not a registered warehouse packing station.", None

        # 4. Shelf proximity check: pick_spot must be adjacent to at least one shelf
        adjacent_shelf: Optional[Tuple[int, int]] = None
        for sx, sy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            cand = (px + sx, py + sy)
            if cand in self.grid.shelves:
                adjacent_shelf = cand
                break

        if adjacent_shelf is None:
            # If no adjacent shelf, use pick_spot as shelf_loc fallback
            adjacent_shelf = pick_spot

        if pick_spot == delivery_station:
            return False, "Pickup location and delivery station cannot be identical.", None

        return True, "", adjacent_shelf

    def create_custom_task(
        self,
        pick_spot: Tuple[int, int],
        delivery_station: Tuple[int, int],
        priority: int = TaskPriority.NORMAL,
        current_step: int = 0,
    ) -> Tuple[Optional[WarehouseTask], str]:
        """
        Creates and enqueues a user-defined custom warehouse task with full coordinate validation.
        """
        is_valid, err_msg, shelf_loc = self.validate_task_coordinates(pick_spot, delivery_station)
        if not is_valid:
            return None, err_msg

        task = WarehouseTask(
            task_id=self.task_counter,
            shelf_loc=shelf_loc,
            pick_spot=pick_spot,
            delivery_station=delivery_station,
            priority=priority,
            status='QUEUED',
            created_at_step=current_step,
            estimated_cost=abs(pick_spot[0] - delivery_station[0]) + abs(pick_spot[1] - delivery_station[1]),
        )
        self.tasks[self.task_counter] = task
        self.task_counter += 1
        return task, f"Task #{task.task_id} successfully registered with priority {task.priority_label}."

    def generate_random_task(
        self,
        current_step: int = 0,
        priority: Optional[int] = None,
    ) -> WarehouseTask:
        """Generates a pick-and-deliver order from accessible shelves to packing stations."""
        accessible_picks = self.grid.get_accessible_shelf_locations()
        if not accessible_picks:
            pick_spot = (1, 1)
            shelf_loc = (2, 3)
        else:
            pick_spot = self.random.choice(accessible_picks)
            shelf_loc = pick_spot
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                candidate = (pick_spot[0] + dx, pick_spot[1] + dy)
                if candidate in self.grid.shelves:
                    shelf_loc = candidate
                    break

        delivery_station = (
            self.random.choice(self.grid.packing_stations)
            if self.grid.packing_stations
            else (2, 14)
        )

        # Distribute priorities: 60% Normal, 20% High, 10% Urgent, 10% Low
        if priority is None:
            p_roll = self.random.random()
            if p_roll < 0.10:
                p_val = TaskPriority.LOW
            elif p_roll < 0.70:
                p_val = TaskPriority.NORMAL
            elif p_roll < 0.90:
                p_val = TaskPriority.HIGH
            else:
                p_val = TaskPriority.URGENT
        else:
            p_val = priority

        est_dist = abs(pick_spot[0] - delivery_station[0]) + abs(pick_spot[1] - delivery_station[1])

        task = WarehouseTask(
            task_id=self.task_counter,
            shelf_loc=shelf_loc,
            pick_spot=pick_spot,
            delivery_station=delivery_station,
            priority=p_val,
            status='QUEUED',
            created_at_step=current_step,
            estimated_cost=est_dist,
        )
        self.tasks[self.task_counter] = task
        self.task_counter += 1
        return task

    def populate_initial_tasks(self, count: int = 10, current_step: int = 0) -> None:
        """Pre-populate task queue with initial warehouse orders."""
        for _ in range(count):
            self.generate_random_task(current_step)

    def assign_next_task(self, robot_id: int, current_step: int) -> Optional[WarehouseTask]:
        """
        Finds the highest-priority pending task and assigns it to robot_id.
        Preserves backward compatibility while respecting priority ordering.
        """
        pending = self.get_pending_tasks()
        if not pending:
            return None

        # Sort primarily by priority descending, then created_at_step ascending
        pending.sort(key=lambda t: (-t.priority, t.created_at_step))
        task = pending[0]
        task.status = 'PICKING_IN_TRANSIT'
        task.assigned_robot = robot_id
        task.assigned_at_step = current_step
        task.state_history.append({
            "from_status": "QUEUED",
            "to_status": "PICKING_IN_TRANSIT",
            "step": current_step,
            "note": f"Assigned to Robot {robot_id}",
        })
        return task

    def assign_task_to_robot(
        self,
        task_id: int,
        robot_id: int,
        current_step: int,
    ) -> bool:
        """Directly assigns a specific task to a target robot."""
        if task_id not in self.tasks:
            return False
        task = self.tasks[task_id]
        if task.status not in ('QUEUED', 'PENDING'):
            return False

        task.status = 'PICKING_IN_TRANSIT'
        task.assigned_robot = robot_id
        task.assigned_at_step = current_step
        task.state_history.append({
            "from_status": "QUEUED",
            "to_status": "PICKING_IN_TRANSIT",
            "step": current_step,
            "note": f"Manual assignment to Robot {robot_id}",
        })
        return True

    def cancel_task(self, task_id: int, current_step: int, reason: str = "User cancellation") -> bool:
        """Cancels task and detaches assigned robot."""
        if task_id not in self.tasks:
            return False
        return self.tasks[task_id].cancel(current_step, reason)

    def complete_task(self, task_id: int, current_step: int) -> None:
        """Marks a task as completed and archives it."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = 'COMPLETED'
            task.completed_at_step = current_step
            task.state_history.append({
                "from_status": "DELIVERING",
                "to_status": "COMPLETED",
                "step": current_step,
                "note": "Delivery verified",
            })
            if task not in self.completed_tasks:
                self.completed_tasks.append(task)

    def get_pending_tasks(self) -> List[WarehouseTask]:
        """Returns all queued orders waiting for robot dispatch."""
        return [t for t in self.tasks.values() if t.status in ('QUEUED', 'PENDING')]

    def get_active_tasks(self) -> List[WarehouseTask]:
        """Returns all tasks currently being executed by robots."""
        return [
            t for t in self.tasks.values()
            if t.status in ('ASSIGNED', 'PICKING_IN_TRANSIT', 'MOVING_TO_PICK', 'PICKING', 'DELIVERY_IN_TRANSIT', 'MOVING_TO_DELIVERY', 'DELIVERING')
        ]

    def get_completed_tasks(self) -> List[WarehouseTask]:
        """Returns all completed tasks."""
        return list(self.completed_tasks)

    def get_pending_count(self) -> int:
        """Number of tasks queued or in progress."""
        return sum(1 for t in self.tasks.values() if t.status not in ('COMPLETED', 'CANCELLED', 'FAILED'))

    def get_completed_count(self) -> int:
        """Total number of completed tasks."""
        return len(self.completed_tasks)
