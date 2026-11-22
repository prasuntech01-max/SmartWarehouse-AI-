"""Discrete-time simulation engine for the multi-robot warehouse."""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from core.grid import WarehouseGrid
from core.reservation import ReservationTable
from core.planner import SpaceTimeAStarPlanner
from core.multi_agent import MultiAgentPlanner
from core.deadlock import DeadlockHandler
from core.replanner import DynamicReplanner
from core.obstacle_manager import DynamicObstacleManager
from core.task_manager import TaskManager, WarehouseTask, TaskPriority
from core.task_assignment import TaskAssignmentEngine, AssignmentStrategy, AssignmentDecision
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
    battery: float = 100.0
    total_distance: int = 0
    completed_tasks: int = 0


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
        self.deadlock_handler = DeadlockHandler(self.grid, self.reservation_table, self.planner)
        self.replanner = DynamicReplanner(self.grid, self.reservation_table)
        self.obstacle_manager = DynamicObstacleManager()
        self.task_manager = TaskManager(self.grid, seed=self.seed)
        self.assignment_strategy = AssignmentStrategy.WEIGHTED_MULTI_CRITERIA
        self.assignment_engine = TaskAssignmentEngine(self.grid, default_strategy=self.assignment_strategy)
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
                battery=100.0,
                total_distance=0,
                completed_tasks=0,
            )
            # Reserve initial stationary spot
            self.reservation_table.reserve_vertex(dock[0], dock[1], 0, robot_id=r_id)

    def reset(self, num_robots: Optional[int] = None) -> None:
        """Resets the simulator back to step 0."""
        if num_robots is not None:
            self.num_robots = min(max(1, num_robots), 5)
        self.step_count = 0
        self.grid.clear_dynamic_obstacles()
        self.obstacle_manager.clear(0)
        self.reservation_table.clear()
        self.metrics.reset()
        self.task_manager = TaskManager(self.grid, seed=self.seed)
        self.assignment_engine = TaskAssignmentEngine(self.grid, default_strategy=self.assignment_strategy)
        self.task_manager.populate_initial_tasks(count=20, current_step=0)
        self._init_fleet()

    def set_assignment_strategy(self, strategy: AssignmentStrategy) -> None:
        """Configures the current multi-robot assignment strategy."""
        self.assignment_strategy = strategy
        self.assignment_engine.strategy = strategy

    def create_custom_task(
        self,
        pick_spot: Tuple[int, int],
        delivery_station: Tuple[int, int],
        priority: int = TaskPriority.NORMAL,
    ) -> Tuple[Optional[WarehouseTask], str]:
        """Creates a custom user-defined task with coordinate validation."""
        return self.task_manager.create_custom_task(
            pick_spot=pick_spot,
            delivery_station=delivery_station,
            priority=priority,
            current_step=self.step_count,
        )

    def assign_task_manually(self, task_id: int, robot_id: int) -> Tuple[bool, str]:
        """Manually dispatches an eligible order to a selected idle robot."""
        if robot_id not in self.robots:
            return False, f"Robot R{robot_id} does not exist."
        robot = self.robots[robot_id]
        if robot.state != 'IDLE':
            return False, f"Robot R{robot_id} is currently {robot.state}. Only IDLE robots can be assigned."

        task = self.task_manager.tasks.get(task_id)
        if not task:
            return False, f"Task #{task_id} not found."
        if task.status not in ('QUEUED', 'PENDING'):
            return False, f"Task #{task_id} is in status '{task.status}' and cannot be assigned."

        path = self.planner.plan(
            start=robot.pos,
            goal=task.pick_spot,
            start_time=self.step_count,
            robot_id=robot_id,
        )
        if not path:
            return False, f"No collision-free route found from Robot R{robot_id} ({robot.pos}) to pickup {task.pick_spot}."

        self.task_manager.assign_task_to_robot(task_id, robot_id, self.step_count)
        robot.assigned_task = task
        robot.goal = task.pick_spot
        robot.state = 'MOVING_TO_PICK'
        robot.path = path
        robot.path_index = 0
        self.reservation_table.reserve_path(path, robot_id=robot_id, start_time=self.step_count)
        return True, f"Task #{task_id} manually assigned to Robot R{robot_id}."

    def cancel_task(self, task_id: int) -> Tuple[bool, str]:
        """Cancels an active or queued order, safely releasing reservations."""
        if task_id not in self.task_manager.tasks:
            return False, f"Task #{task_id} does not exist."

        task = self.task_manager.tasks[task_id]
        if task.status in ('COMPLETED', 'CANCELLED'):
            return False, f"Task #{task_id} is already {task.status}."

        assigned_rid = task.assigned_robot
        cancelled = self.task_manager.cancel_task(task_id, self.step_count, reason="Manual user cancellation")
        if not cancelled:
            return False, f"Task #{task_id} could not be cancelled."

        # If a robot was currently executing this task, clear future path and reservations safely
        if assigned_rid and assigned_rid in self.robots:
            robot = self.robots[assigned_rid]
            self.reservation_table.release_future_reservations(assigned_rid, from_time=self.step_count)
            robot.assigned_task = None
            robot.state = 'IDLE'
            robot.goal = None
            robot.path = []
            robot.path_index = 0
            self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], self.step_count + 1, robot_id=assigned_rid)

        return True, f"Task #{task_id} successfully cancelled."

    def reassign_task(self, task_id: int, new_robot_id: int) -> Tuple[bool, str]:
        """Transfers an order from its current robot to a new idle robot."""
        if task_id not in self.task_manager.tasks:
            return False, f"Task #{task_id} does not exist."
        task = self.task_manager.tasks[task_id]

        if new_robot_id not in self.robots:
            return False, f"Target Robot R{new_robot_id} does not exist."
        target_robot = self.robots[new_robot_id]
        if target_robot.state != 'IDLE':
            return False, f"Target Robot R{new_robot_id} is currently {target_robot.state}. Target must be IDLE."

        # Release current robot if different
        old_rid = task.assigned_robot
        if old_rid and old_rid in self.robots and old_rid != new_robot_id:
            old_robot = self.robots[old_rid]
            self.reservation_table.release_future_reservations(old_rid, from_time=self.step_count)
            old_robot.assigned_task = None
            old_robot.state = 'IDLE'
            old_robot.goal = None
            old_robot.path = []
            old_robot.path_index = 0
            self.reservation_table.reserve_vertex(old_robot.pos[0], old_robot.pos[1], self.step_count + 1, robot_id=old_rid)

        task.status = 'QUEUED'
        task.assigned_robot = None
        return self.assign_task_manually(task_id, new_robot_id)

    def clear_dynamic_obstacles(self) -> None:
        """Clears all dynamic obstacles from grid and obstacle manager."""
        self.grid.clear_dynamic_obstacles()
        self.obstacle_manager.clear(self.step_count)

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

        # Register obstacle event with DynamicObstacleManager
        obs_event = self.obstacle_manager.add_obstacle((x, y), self.step_count, reason="runtime_injection")

        robot_states: Dict[int, Dict[str, Any]] = {}
        for r_id, r in self.robots.items():
            if r.path and r.goal is not None:
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

        # Update obstacle manager and metrics
        self.obstacle_manager.mark_affected(obs_event.obstacle_id, affected)
        self.metrics.record_obstacle_event()

        for r_id in affected:
            old_len = len(robot_states.get(r_id, {}).get('path', []))
            new_len = len(updated_paths.get(r_id, []))
            success = (
                r_id in updated_paths
                and (new_len > 1 or robot_states[r_id]['pos'] == robot_states[r_id]['goal'])
            )
            self.metrics.record_replan_attempt(
                robot_id=r_id,
                success=success,
                path_delta=new_len - old_len,
                latency_ms=latency_ms,
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

        # 1. Multi-Robot Task Assignment & Dispatch for IDLE robots
        idle_robots = {r_id: self.robots[r_id] for r_id, r in self.robots.items() if r.state == 'IDLE'}
        pending_tasks = self.task_manager.get_pending_tasks()

        if idle_robots and pending_tasks:
            assigned_this_step: Set[int] = set()

            if len(idle_robots) > 1 and len(pending_tasks) > 1:
                # Execute batch allocation
                idle_info = {
                    r_id: {'pos': r.pos, 'workload': r.completed_tasks}
                    for r_id, r in idle_robots.items()
                }
                decisions = self.assignment_engine.assign_batch(
                    idle_robots=idle_info,
                    pending_tasks=pending_tasks,
                    strategy=self.assignment_strategy,
                    current_step=current_step,
                )

                for dec in decisions:
                    t_obj = self.task_manager.tasks.get(dec.task_id)
                    r_obj = self.robots.get(dec.robot_id)
                    if t_obj and r_obj and r_obj.state == 'IDLE' and t_obj.status in ('QUEUED', 'PENDING'):
                        path = self.planner.plan(
                            start=r_obj.pos,
                            goal=t_obj.pick_spot,
                            start_time=current_step,
                            robot_id=r_obj.robot_id,
                        )
                        if path:
                            t_obj.status = 'MOVING_TO_PICK'
                            t_obj.assigned_robot = r_obj.robot_id
                            t_obj.assigned_at_step = current_step
                            r_obj.assigned_task = t_obj
                            r_obj.goal = t_obj.pick_spot
                            r_obj.state = 'MOVING_TO_PICK'
                            r_obj.path = path
                            r_obj.path_index = 0
                            self.reservation_table.reserve_path(path, robot_id=r_obj.robot_id, start_time=current_step)
                            assigned_this_step.add(r_obj.robot_id)
                        else:
                            r_obj.path = [r_obj.pos]
                            r_obj.path_index = 0

            # Single-robot dispatch for any remaining idle robots
            for r_id, robot in idle_robots.items():
                if robot.state == 'IDLE' and r_id not in assigned_this_step:
                    remaining_pending = self.task_manager.get_pending_tasks()
                    if remaining_pending:
                        dec = self.assignment_engine.select_best_task_for_robot(
                            robot_id=r_id,
                            robot_pos=robot.pos,
                            robot_workload=robot.completed_tasks,
                            available_tasks=remaining_pending,
                            strategy=self.assignment_strategy,
                            current_step=current_step,
                        )
                        if dec:
                            t_obj = self.task_manager.tasks.get(dec.task_id)
                            path = self.planner.plan(
                                start=robot.pos,
                                goal=t_obj.pick_spot,
                                start_time=current_step,
                                robot_id=r_id,
                            )
                            if path:
                                t_obj.status = 'MOVING_TO_PICK'
                                t_obj.assigned_robot = r_id
                                t_obj.assigned_at_step = current_step
                                robot.assigned_task = t_obj
                                robot.goal = t_obj.pick_spot
                                robot.state = 'MOVING_TO_PICK'
                                robot.path = path
                                robot.path_index = 0
                                self.reservation_table.reserve_path(path, robot_id=r_id, start_time=current_step)
                            else:
                                robot.path = [robot.pos]
                                robot.path_index = 0
                        else:
                            self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)
                    else:
                        self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)
        elif idle_robots:
            for r_id, robot in idle_robots.items():
                self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)

        # 1.2 State machine progression for robots in transit / stations
        for r_id, robot in self.robots.items():
            if robot.state == 'MOVING_TO_PICK':
                if robot.path_index >= len(robot.path) - 1 and robot.pos == robot.goal:
                    robot.state = 'PICKING'
                    robot.wait_counter = 1
                    if robot.assigned_task:
                        robot.assigned_task.transition_to('PICKING', current_step, "Arrived at pickup location")
                    self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)

            elif robot.state == 'PICKING':
                self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)
                if robot.wait_counter > 0:
                    robot.wait_counter -= 1
                if robot.wait_counter == 0 and robot.assigned_task:
                    robot.goal = robot.assigned_task.delivery_station
                    robot.state = 'MOVING_TO_DELIVERY'
                    robot.assigned_task.transition_to('MOVING_TO_DELIVERY', current_step, "Dispatched to delivery station")
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
                if robot.path_index >= len(robot.path) - 1 and robot.pos == robot.goal:
                    robot.state = 'DELIVERING'
                    robot.wait_counter = 1
                    if robot.assigned_task:
                        robot.assigned_task.transition_to('DELIVERING', current_step, "Arrived at delivery station")
                    self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)

            elif robot.state == 'DELIVERING':
                self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)
                if robot.wait_counter > 0:
                    robot.wait_counter -= 1
                if robot.wait_counter == 0 and robot.assigned_task:
                    robot.completed_tasks += 1
                    self.task_manager.complete_task(robot.assigned_task.task_id, current_step)
                    self.metrics.record_task_completion()
                    robot.assigned_task = None
                    robot.state = 'IDLE'
                    robot.goal = None
                    robot.path = []
                    robot.path_index = 0

        # 1.5 Deadlock detection & resolution via Wait-For Graph (WFG) analysis
        active_states: Dict[int, Dict[str, Any]] = {}
        for r_id, r in self.robots.items():
            if r.path and r.goal is not None:
                active_states[r_id] = {
                    'pos': r.pos,
                    'goal': r.goal,
                    'path': r.path,
                    'path_index': r.path_index,
                    'is_waiting': (r.pos == r.path[r.path_index] if r.path_index < len(r.path) else True),
                }

        if len(active_states) >= 2:
            cycles = self.deadlock_handler.detect_deadlocks(active_states, current_step)
            for cycle in cycles:
                resolved, new_paths, msg = self.deadlock_handler.resolve_deadlock(
                    cycle, active_states, current_step
                )
                if resolved:
                    self.metrics.record_deadlock_event()
                    for c_id, new_traj in new_paths.items():
                        if c_id in self.robots:
                            self.robots[c_id].path = list(new_traj)
                            self.robots[c_id].path_index = 0

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
            robot = self.robots[r_id]
            if new_pos != robot.pos:
                robot.total_distance += 1
                robot.battery = max(0.0, robot.battery - 0.1)
            robot.pos = new_pos
            robot.trail.append(new_pos)
            if len(robot.trail) > 8:
                robot.trail.pop(0)

        # 4. Record step metrics
        robot_statuses = {r_id: r.state for r_id, r in self.robots.items()}
        self.metrics.record_step(self.step_count, robot_statuses, conflicts)

        self.step_count += 1
