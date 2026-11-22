"""Discrete-time simulation engine for the multi-robot warehouse."""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner
from core.multi_agent import MultiAgentPlanner
from core.deadlock import DeadlockHandler
from core.replanner import DynamicReplanner
from core.task_manager import TaskManager, WarehouseTask
from simulation.metrics import MetricsCollector


@dataclass
class RobotState:
    robot_id: int
    home_dock: Tuple[int, int]
    pos: Tuple[int, int]
    state: str = 'IDLE'  # IDLE, MOVING_TO_PICK, PICKING, MOVING_TO_DELIVERY, DELIVERING, RETURNING_DOCK
    goal: Optional[Tuple[int, int]] = None
    path: List[Tuple[int, int]] = field(default_factory=list)
    path_index: int = 0
    assigned_task: Optional[WarehouseTask] = None
    trail: List[Tuple[int, int]] = field(default_factory=list)
    wait_counter: int = 0


class WarehouseSimulator:
    def __init__(self, num_robots: int = 3, width: int = 15, height: int = 15, seed: int = 42):
        self.width = width
        self.height = height
        self.num_robots = min(max(1, num_robots), 5)
        self.seed = seed
        self.step_count = 0

        # Subsystems
        self.grid = WarehouseGrid(width=self.width, height=self.height)
        self.reservation_table = ReservationTable()
        self.planner = SpaceTimeAStarPlanner(self.grid, self.reservation_table)
        self.ma_planner = MultiAgentPlanner(self.grid)
        self.deadlock_handler = DeadlockHandler(self.grid, self.planner)
        self.replanner = DynamicReplanner(self.grid, self.reservation_table)
        self.task_manager = TaskManager(self.grid, seed=self.seed)
        self.metrics = MetricsCollector()

        # Fleet of robots
        self.robots: Dict[int, RobotState] = {}
        self._init_fleet()
        self.task_manager.populate_initial_tasks(count=20, current_step=0)

    def _init_fleet(self) -> None:
        """Initializes robot fleet parked at charging docks."""
        self.robots.clear()
        self.reservation_table.clear()

        docks = self.grid.charging_docks[:self.num_robots]
        for idx, dock in enumerate(docks):
            r_id = idx + 1
            self.robots[r_id] = RobotState(
                robot_id=r_id,
                home_dock=dock,
                pos=dock,
                state='IDLE',
                goal=None,
                path=[],
                path_index=0,
                assigned_task=None,
                trail=[dock],
            )
            # Reserve initial stationary spot
            self.reservation_table.reserve_vertex(dock[0], dock[1], 0, robot_id=r_id)

    def reset(self, num_robots: Optional[int] = None) -> None:
        """Resets the simulator back to step 0."""
        if num_robots is not None:
            self.num_robots = min(max(1, num_robots), 5)
        self.step_count = 0
        self.grid.clear_dynamic_obstacles()
        self.reservation_table.clear()
        self.metrics.reset()
        self.task_manager = TaskManager(self.grid, seed=self.seed)
        self.task_manager.populate_initial_tasks(count=20, current_step=0)
        self._init_fleet()

    def inject_obstacle(self, x: int, y: int) -> Tuple[bool, str]:
        """Injects dynamic obstacle mid-route and triggers dynamic replanning."""
        if not self.grid.in_bounds(x, y):
            return False, f"Coordinate ({x}, {y}) out of warehouse bounds."
        if (x, y) in self.grid.shelves:
            return False, f"Coordinate ({x}, {y}) is already a permanent shelf."

        # Check if any robot is already standing at (x, y) right now
        for r in self.robots.values():
            if r.pos == (x, y):
                return False, f"Cannot place obstacle directly on Robot {r.robot_id}."

        robot_states: Dict[int, Dict[str, Any]] = {}
        for r_id, r in self.robots.items():
            if r.path and r.goal is not None:
                # Robot's remaining planned path
                rem_path = r.path[r.path_index:]
                robot_states[r_id] = {
                    'pos': r.pos,
                    'goal': r.goal,
                    'path': rem_path,
                    'start_time': self.step_count,
                }

        updated_paths, latency_ms, affected = self.replanner.handle_obstacle_injection(
            obstacle=(x, y),
            current_time=self.step_count,
            robot_states=robot_states,
        )

        # Apply updated paths
        for r_id in affected:
            if r_id in updated_paths:
                new_path = updated_paths[r_id]
                self.robots[r_id].path = new_path
                self.robots[r_id].path_index = 0

        self.metrics.record_replan_event(latency_ms)
        return True, f"Obstacle injected at ({x}, {y}). Affected {len(affected)} robot(s). Replan latency: {latency_ms:.2f}ms."

    def step(self) -> None:
        """Advance the simulation world by 1 discrete time step."""
        current_step = self.step_count

        # 1. State machine and path allocation for each robot
        for r_id, robot in self.robots.items():
            if robot.state == 'IDLE':
                # Try assigning next task
                task = self.task_manager.assign_next_task(r_id, current_step)
                if task:
                    robot.assigned_task = task
                    robot.goal = task.pick_spot
                    robot.state = 'MOVING_TO_PICK'
                    path = self.planner.plan(
                        start=robot.pos,
                        goal=task.pick_spot,
                        start_time=current_step,
                        robot_id=r_id,
                    )
                    if path:
                        robot.path = path
                        robot.path_index = 0
                        self.reservation_table.reserve_path(path, robot_id=r_id, start_time=current_step)
                    else:
                        robot.path = [robot.pos]
                        robot.path_index = 0
                else:
                    # Stationary reservation while idle
                    self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)

            elif robot.state == 'MOVING_TO_PICK':
                # Check if path is finished and arrived at pick spot
                if robot.path_index >= len(robot.path) - 1 and robot.pos == robot.goal:
                    robot.state = 'PICKING'
                    robot.wait_counter = 1  # 1 step to pick item
                    self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)

            elif robot.state == 'PICKING':
                self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)
                if robot.wait_counter > 0:
                    robot.wait_counter -= 1
                if robot.wait_counter == 0 and robot.assigned_task:
                    # Switch to delivery phase
                    robot.goal = robot.assigned_task.delivery_station
                    robot.state = 'MOVING_TO_DELIVERY'
                    path = self.planner.plan(
                        start=robot.pos,
                        goal=robot.goal,
                        start_time=current_step,
                        robot_id=r_id,
                    )
                    if path:
                        robot.path = path
                        robot.path_index = 0
                        self.reservation_table.reserve_path(path, robot_id=r_id, start_time=current_step)
                    else:
                        robot.path = [robot.pos]
                        robot.path_index = 0

            elif robot.state == 'MOVING_TO_DELIVERY':
                # Check if path is finished and arrived at delivery station
                if robot.path_index >= len(robot.path) - 1 and robot.pos == robot.goal:
                    robot.state = 'DELIVERING'
                    robot.wait_counter = 1  # 1 step to offload/pack
                    self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)

            elif robot.state == 'DELIVERING':
                self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)
                if robot.wait_counter > 0:
                    robot.wait_counter -= 1
                if robot.wait_counter == 0 and robot.assigned_task:
                    self.task_manager.complete_task(robot.assigned_task.task_id, current_step)
                    self.metrics.record_task_completion()
                    robot.assigned_task = None
                    robot.state = 'IDLE'
                    robot.goal = None
                    robot.path = []
                    robot.path_index = 0

        # 2. Movement execution along paths
        next_positions: Dict[int, Tuple[int, int]] = {}
        for r_id, robot in self.robots.items():
            if robot.state in ('MOVING_TO_PICK', 'MOVING_TO_DELIVERY', 'RETURNING_DOCK') and robot.path:
                if robot.path_index < len(robot.path) - 1:
                    robot.path_index += 1
                    next_positions[r_id] = robot.path[robot.path_index]
                else:
                    next_positions[r_id] = robot.pos
            else:
                next_positions[r_id] = robot.pos

        # 3. Collision verification
        conflicts = 0
        pos_list = list(next_positions.values())
        if len(pos_list) != len(set(pos_list)):
            conflicts += 1

        # Commit movement
        for r_id, new_pos in next_positions.items():
            self.robots[r_id].pos = new_pos
            self.robots[r_id].trail.append(new_pos)
            if len(self.robots[r_id].trail) > 8:
                self.robots[r_id].trail.pop(0)

        # 4. Record step metrics
        robot_statuses = {r_id: r.state for r_id, r in self.robots.items()}
        self.metrics.record_step(self.step_count, robot_statuses, conflicts)

        self.step_count += 1
