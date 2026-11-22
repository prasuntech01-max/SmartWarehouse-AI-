"""Task and Order assignment manager for warehouse robots."""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
import random
from core.grid import WarehouseGrid


@dataclass
class WarehouseTask:
    task_id: int
    shelf_loc: Tuple[int, int]
    pick_spot: Tuple[int, int]
    delivery_station: Tuple[int, int]
    status: str = 'QUEUED'  # QUEUED, PICKING_IN_TRANSIT, AT_PICK, DELIVERY_IN_TRANSIT, COMPLETED
    assigned_robot: Optional[int] = None
    created_at_step: int = 0
    completed_at_step: Optional[int] = None


class TaskManager:
    def __init__(self, grid: WarehouseGrid, seed: int = 42):
        self.grid = grid
        self.random = random.Random(seed)
        self.tasks: Dict[int, WarehouseTask] = {}
        self.task_counter = 1
        self.completed_tasks: List[WarehouseTask] = []

    def generate_random_task(self, current_step: int = 0) -> WarehouseTask:
        """Generates a pick-and-deliver order from accessible shelves to packing stations."""
        accessible_picks = self.grid.get_accessible_shelf_locations()
        if not accessible_picks:
            pick_spot = (1, 1)
            shelf_loc = (2, 3)
        else:
            pick_spot = self.random.choice(accessible_picks)
            # Find an adjacent shelf
            shelf_loc = pick_spot
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                candidate = (pick_spot[0] + dx, pick_spot[1] + dy)
                if candidate in self.grid.shelves:
                    shelf_loc = candidate
                    break

        delivery_station = self.random.choice(self.grid.packing_stations)

        task = WarehouseTask(
            task_id=self.task_counter,
            shelf_loc=shelf_loc,
            pick_spot=pick_spot,
            delivery_station=delivery_station,
            status='QUEUED',
            created_at_step=current_step,
        )
        self.tasks[self.task_counter] = task
        self.task_counter += 1
        return task

    def populate_initial_tasks(self, count: int = 10, current_step: int = 0) -> None:
        """Pre-populate task queue with initial warehouse orders."""
        for _ in range(count):
            self.generate_random_task(current_step)

    def assign_next_task(self, robot_id: int, current_step: int) -> Optional[WarehouseTask]:
        """Finds the first queued task and assigns it to robot_id."""
        for task in self.tasks.values():
            if task.status == 'QUEUED':
                task.status = 'PICKING_IN_TRANSIT'
                task.assigned_robot = robot_id
                return task
        return None

    def complete_task(self, task_id: int, current_step: int) -> None:
        """Marks a task as completed."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = 'COMPLETED'
            task.completed_at_step = current_step
            self.completed_tasks.append(task)

    def get_pending_count(self) -> int:
        """Number of tasks queued or in progress."""
        return sum(1 for t in self.tasks.values() if t.status != 'COMPLETED')

    def get_completed_count(self) -> int:
        """Total number of completed tasks."""
        return len(self.completed_tasks)
