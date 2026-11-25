"""Discrete-time simulation engine for the multi-robot warehouse."""

import math
import time
from typing import Dict, List, Tuple, Optional, Any, Set
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
from core.parcels import Parcel, ParcelType, ParcelStatus, ParcelPriority, InventoryManager, PARCEL_SPECS
from core.commands import CommandType, CommandResult, RobotCommandLogEntry
from simulation.metrics import MetricsCollector


@dataclass
class RobotState:
    robot_id: int
    home_dock: Tuple[int, int]
    pos: Tuple[int, int]
    state: str = 'IDLE'  # IDLE, MOVING_TO_PICK, PICKING, MOVING_TO_DELIVERY, DELIVERING, RETURNING_DOCK, CARRYING, E_STOPPED, PAUSED
    mode: str = 'AUTO'   # 'AUTO' or 'MANUAL'
    heading: float = 0.0 # Yaw heading in radians (0 = +X, pi/2 = +Y, pi = -X, -pi/2 = -Y)
    goal: Optional[Tuple[int, int]] = None
    path: List[Tuple[int, int]] = field(default_factory=list)
    path_index: int = 0
    assigned_task: Optional[WarehouseTask] = None
    carrying_parcel: Optional[Parcel] = None
    trail: List[Tuple[int, int]] = field(default_factory=list)
    wait_counter: int = 0
    battery: float = 100.0
    speed: float = 1.2
    health: float = 100.0
    total_distance: int = 0
    completed_tasks: int = 0
    replan_count: int = 0
    e_stopped: bool = False


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
        self.inventory_manager = InventoryManager(seed=self.seed)
        self.command_history: List[RobotCommandLogEntry] = []
        self.command_counter: int = 0
        self.event_log: List[Dict[str, Any]] = []
        self.global_e_stop: bool = False
        self.assignment_strategy = AssignmentStrategy.WEIGHTED_MULTI_CRITERIA
        self.assignment_engine = TaskAssignmentEngine(self.grid, default_strategy=self.assignment_strategy)
        self.metrics = MetricsCollector()

        # Fleet of robots
        self.robots: Dict[int, RobotState] = {}
        self._init_fleet()
        self.task_manager.populate_initial_tasks(count=20, current_step=0)
        self.inventory_manager.seed_inventory(self.grid, count=30, tick=0)
        self._log_event("Warehouse simulator initialized with 5 autonomous robots and 30 parcels.", category="SYSTEM")

    @property
    def tasks(self) -> Dict[int, WarehouseTask]:
        """Provides direct access to all tasks registered in the task manager."""
        return self.task_manager.tasks

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
        self.inventory_manager = InventoryManager(seed=self.seed)
        self.command_history.clear()
        self.event_log.clear()
        self.global_e_stop = False
        self.assignment_engine = TaskAssignmentEngine(self.grid, default_strategy=self.assignment_strategy)
        self.task_manager.populate_initial_tasks(count=20, current_step=0)
        self.inventory_manager.seed_inventory(self.grid, count=30, tick=0)
        self._init_fleet()
        self._log_event("Warehouse simulator reset to tick 0.", category="SYSTEM")

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

    def _log_event(
        self,
        message: str,
        category: str = "OPS",
        robot_id: Optional[int] = None,
        parcel_id: Optional[str] = None,
    ) -> None:
        """Append a real timestamped operational event to the live event log."""
        self.event_log.append({
            "time": time.strftime("%H:%M:%S"),
            "tick": self.step_count,
            "category": category,
            "robot_id": robot_id,
            "parcel_id": parcel_id,
            "message": message,
        })
        if len(self.event_log) > 100:
            self.event_log.pop(0)

    def get_astar_telemetry(self) -> Dict[str, Any]:
        """Return real A* planner statistics, active path metrics, and conflict counts."""
        stats = dict(getattr(self.planner, "last_plan_stats", {}) or {})
        total_replan = sum(getattr(r, "replan_count", 0) for r in self.robots.values())
        active_routes = []
        for rid, r in sorted(self.robots.items()):
            rem = r.path[r.path_index:] if r.path else []
            active_routes.append({
                "robot_id": rid,
                "state": r.state,
                "pos": r.pos,
                "goal": r.goal,
                "remaining_steps": max(0, len(rem) - 1),
                "replan_count": getattr(r, "replan_count", 0),
            })
        stats["total_replans"] = total_replan
        stats["active_routes"] = active_routes
        stats["detected_conflicts"] = self.metrics.detected_conflicts_count
        stats["deadlocks_resolved"] = self.metrics.deadlock_events_count
        return stats

    def assign_parcel_task(
        self,
        parcel_id: str,
        robot_id: int,
        destination: Optional[Tuple[int, int]] = None,
    ) -> Tuple[bool, str]:
        """Assign an available shelf parcel to a robot for real A* pickup and delivery."""
        if self.global_e_stop:
            return False, "GLOBAL EMERGENCY STOP is active. Clear emergency before assigning parcels."
        if robot_id not in self.robots:
            return False, f"Robot R{robot_id} does not exist."
        robot = self.robots[robot_id]
        if robot.e_stopped:
            return False, f"Robot R{robot_id} is in EMERGENCY STOP state."
        if robot.state != 'IDLE':
            return False, f"Robot R{robot_id} is currently {robot.state}. Only IDLE robots can be assigned."
        if robot.carrying_parcel is not None:
            return False, f"Robot R{robot_id} is already carrying {robot.carrying_parcel.parcel_id}."

        parcel = self.inventory_manager.get_parcel_by_id(parcel_id)
        if not parcel:
            return False, f"Parcel {parcel_id} not found."
        if parcel.status != 'AVAILABLE':
            return False, f"Parcel {parcel_id} is currently {parcel.status} and cannot be claimed."
        if parcel.spec.heavy and robot_id != 1:
            return False, f"Heavy parcel {parcel_id} ({parcel.spec.weight_kg}kg) requires Heavy AMR TITAN-X (Robot 1)."

        pickup_cell = parcel.pickup_cell or parcel.location
        if not pickup_cell or not self.grid.is_walkable(pickup_cell[0], pickup_cell[1]):
            return False, f"Pickup cell {pickup_cell} for {parcel_id} is not navigable."

        target_dest = tuple(destination) if destination is not None else parcel.destination
        if not target_dest or not self.grid.is_walkable(target_dest[0], target_dest[1]):
            return False, f"Destination {target_dest} is not walkable."
        if target_dest == pickup_cell:
            return False, "Pickup location and destination cannot be identical."

        # Plan Space-Time A* path from robot's current position to parcel pickup cell
        path = self.planner.plan(
            start=robot.pos,
            goal=pickup_cell,
            start_time=self.step_count,
            robot_id=robot_id,
        )
        if not path:
            return False, f"No collision-free A* route from R{robot_id} {robot.pos} to {pickup_cell}."

        # Reserve parcel in single authoritative InventoryManager
        self.inventory_manager.reserve_parcel(parcel_id, robot_id, self.step_count)
        parcel.destination = target_dest

        # Create & assign corresponding WarehouseTask
        task = self.task_manager.create_custom_task(
            pick_spot=pickup_cell,
            delivery_station=target_dest if target_dest in self.grid.packing_stations else (self.grid.packing_stations[0] if self.grid.packing_stations else target_dest),
            priority=TaskPriority.HIGH if parcel.priority == ParcelPriority.EXPRESS else TaskPriority.NORMAL,
            current_step=self.step_count,
        )[0]
        if task is None:
            # Fallback direct WarehouseTask when delivering to a shelf/counter outside packing_stations
            from core.task_manager import WarehouseTask
            tid = self.task_manager.task_counter
            self.task_manager.task_counter += 1
            task = WarehouseTask(
                task_id=tid,
                shelf_loc=pickup_cell,
                pick_spot=pickup_cell,
                delivery_station=target_dest,
                priority=TaskPriority.HIGH if parcel.priority == ParcelPriority.EXPRESS else TaskPriority.NORMAL,
                status='QUEUED',
                created_at_step=self.step_count,
                estimated_cost=abs(pickup_cell[0] - target_dest[0]) + abs(pickup_cell[1] - target_dest[1]),
            )
            self.task_manager.tasks[tid] = task

        self.task_manager.assign_task_to_robot(task.task_id, robot_id, self.step_count)
        robot.assigned_task = task
        robot.goal = pickup_cell
        robot.state = 'MOVING_TO_PICK'
        robot.path = path
        robot.path_index = 0
        self.reservation_table.reserve_path(path, robot_id=robot_id, start_time=self.step_count)

        pstats = self.planner.last_plan_stats
        self._log_event(
            f"{parcel_id} reserved for R{robot_id} ({parcel.rack_slot_id or pickup_cell} -> {target_dest}). "
            f"A* route: {len(path)} steps, {pstats.get('nodes_explored', 0)} nodes, {pstats.get('planning_time_ms', 0.0):.2f}ms.",
            category="DISPATCH",
            robot_id=robot_id,
            parcel_id=parcel_id,
        )
        return True, f"Parcel {parcel_id} assigned to Robot R{robot_id} via Space-Time A* ({len(path)} waypoints)."

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

    def submit_command(
        self,
        robot_id: int,
        command: Any,
        params: Optional[Dict[str, Any]] = None,
    ) -> CommandResult:
        """Executes a validated command on a robot with safety interlocks."""
        cmd_str = command.value if isinstance(command, CommandType) else str(command).upper()
        params = params or {}

        if robot_id not in self.robots:
            res = CommandResult(ok=False, reason=f"Robot R{robot_id} not found in fleet.", robot_id=robot_id, command=cmd_str, params=params)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        robot = self.robots[robot_id]

        # Global emergency stop check
        if self.global_e_stop and cmd_str not in ("RESUME", "RESET"):
            res = CommandResult(ok=False, reason="GLOBAL EMERGENCY STOP is active. All commands rejected until cleared/resumed.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        # Individual robot safety stop check
        if robot.e_stopped and cmd_str not in ("RESUME", "RESET"):
            res = CommandResult(ok=False, reason=f"Robot R{robot_id} is in EMERGENCY STOP state. Must RESUME or RESET first.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        if cmd_str == "SET_MODE":
            target_mode = str(params.get("mode", "AUTO")).upper()
            if target_mode not in ("AUTO", "MANUAL"):
                res = CommandResult(ok=False, reason="Invalid mode. Must be 'AUTO' or 'MANUAL'.", robot_id=robot_id, command=cmd_str, params=params)
            else:
                robot.mode = target_mode
                res = CommandResult(ok=True, reason=f"Robot R{robot_id} switched to {target_mode} mode.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "EMERGENCY_STOP":
            robot.e_stopped = True
            robot.state = "E_STOPPED"
            robot.path.clear()
            robot.path_index = 0
            self.reservation_table.release_future_reservations(robot_id, from_time=self.step_count)
            res = CommandResult(ok=True, reason=f"EMERGENCY STOP engaged on Robot R{robot_id}.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "RESUME":
            robot.e_stopped = False
            self.global_e_stop = False
            if robot.state in ("E_STOPPED", "PAUSED"):
                robot.state = "IDLE" if not robot.carrying_parcel else "CARRYING"
            res = CommandResult(ok=True, reason=f"Robot R{robot_id} resumed normal operation.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "PAUSE":
            if robot.state not in ("E_STOPPED", "IDLE"):
                robot.state = "PAUSED"
            res = CommandResult(ok=True, reason=f"Robot R{robot_id} paused.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "STOP":
            robot.path.clear()
            robot.path_index = 0
            robot.goal = None
            if robot.assigned_task:
                self.task_manager.cancel_task(robot.assigned_task.task_id, self.step_count, reason="Manual STOP command")
                robot.assigned_task = None
            self.reservation_table.release_future_reservations(robot_id, from_time=self.step_count)
            robot.state = "IDLE" if not robot.carrying_parcel else "CARRYING"
            res = CommandResult(ok=True, reason=f"Robot R{robot_id} halted. Active path cleared.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "RESET":
            robot.e_stopped = False
            robot.path.clear()
            robot.path_index = 0
            robot.goal = None
            if robot.carrying_parcel:
                self.inventory_manager.fail_parcel(robot.carrying_parcel.parcel_id, self.step_count, reason="Manual robot reset", safe_drop_cell=robot.pos)
                robot.carrying_parcel = None
            if robot.assigned_task:
                self.task_manager.cancel_task(robot.assigned_task.task_id, self.step_count, reason="Manual reset")
                robot.assigned_task = None
            self.reservation_table.release_future_reservations(robot_id, from_time=self.step_count)
            robot.pos = robot.home_dock
            robot.heading = 0.0
            robot.battery = 100.0
            robot.state = "IDLE"
            self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], self.step_count + 1, robot_id=robot_id)
            res = CommandResult(ok=True, reason=f"Robot R{robot_id} reset to charging dock {robot.home_dock}.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str in ("TURN_LEFT", "TURN_RIGHT"):
            delta = -math.pi / 2 if cmd_str == "TURN_LEFT" else math.pi / 2
            robot.heading = (robot.heading + delta) % (2 * math.pi)
            res = CommandResult(ok=True, reason=f"Robot R{robot_id} turned {cmd_str.replace('TURN_', '')}. Heading: {math.degrees(robot.heading):.0f}°", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str in ("MOVE_FORWARD", "MOVE_BACKWARD"):
            deg = round(math.degrees(robot.heading)) % 360
            if deg in (0, 360):
                dx, dy = (1, 0)
            elif deg == 90:
                dx, dy = (0, 1)
            elif deg == 180:
                dx, dy = (-1, 0)
            else:
                dx, dy = (0, -1)

            if cmd_str == "MOVE_BACKWARD":
                dx, dy = -dx, -dy

            nx, ny = robot.pos[0] + dx, robot.pos[1] + dy

            # Safety Interlock 1: Boundaries
            if not self.grid.in_bounds(nx, ny):
                res = CommandResult(ok=False, reason=f"Movement rejected: Cell ({nx}, {ny}) is outside warehouse perimeter.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            # Safety Interlock 2: Shelves and Static Obstacles
            if (nx, ny) in self.grid.shelves:
                res = CommandResult(ok=False, reason=f"Movement rejected: Cell ({nx}, {ny}) is blocked by high-bay storage racks.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            # Safety Interlock 3: Dynamic Obstacles
            if (nx, ny) in self.grid.dynamic_obstacles:
                res = CommandResult(ok=False, reason=f"Movement rejected: Dynamic obstacle detected at cell ({nx}, {ny}).", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            # Safety Interlock 4: Other Robots
            for other_id, other_r in self.robots.items():
                if other_id != robot_id and other_r.pos == (nx, ny):
                    res = CommandResult(ok=False, reason=f"Collision hazard: Cell ({nx}, {ny}) occupied by Robot R{other_id} ({other_r.pos}).", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                    self._log_command(robot_id, cmd_str, params, res)
                    return res

            # Safety Interlock 5: Reservation Table
            if self.reservation_table.is_vertex_reserved(nx, ny, self.step_count + 1, ignore_robot=robot_id):
                res = CommandResult(ok=False, reason=f"Space-Time conflict: Cell ({nx}, {ny}) reserved by another robot at tick {self.step_count + 1}.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            # Apply step
            robot.pos = (nx, ny)
            robot.trail.append((nx, ny))
            if len(robot.trail) > 8:
                robot.trail.pop(0)
            robot.total_distance += 1
            robot.battery = max(0.0, robot.battery - 0.1)
            self.reservation_table.reserve_vertex(nx, ny, self.step_count + 1, robot_id=robot_id)
            res = CommandResult(ok=True, reason=f"Robot R{robot_id} moved to ({nx}, {ny}).", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "GOTO_CELL":
            target = params.get("target")
            if not target or len(target) != 2:
                res = CommandResult(ok=False, reason="Target coordinate missing. Specify target: (x, y).", robot_id=robot_id, command=cmd_str, params=params)
                self._log_command(robot_id, cmd_str, params, res)
                return res
            tx, ty = int(target[0]), int(target[1])

            if not self.grid.is_walkable(tx, ty):
                res = CommandResult(ok=False, reason=f"Target ({tx}, {ty}) is not navigable (shelf/obstacle/out of bounds).", robot_id=robot_id, command=cmd_str, params=params)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            path = self.planner.plan(
                start=robot.pos,
                goal=(tx, ty),
                start_time=self.step_count,
                robot_id=robot_id,
            )
            if not path:
                res = CommandResult(ok=False, reason=f"No collision-free A* route found from {robot.pos} to ({tx}, {ty}).", robot_id=robot_id, command=cmd_str, params=params)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            robot.goal = (tx, ty)
            robot.path = path
            robot.path_index = 0
            robot.state = "MOVING_TO_DELIVERY" if robot.carrying_parcel else "MOVING_TO_PICK"
            self.reservation_table.reserve_path(path, robot_id=robot_id, start_time=self.step_count)
            res = CommandResult(ok=True, reason=f"Route planned to ({tx}, {ty}): {len(path)} waypoints calculated via Space-Time A*.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str in ("PICKUP", "CARRY"):
            if robot.carrying_parcel:
                res = CommandResult(ok=False, reason=f"Robot R{robot_id} is already carrying Parcel {robot.carrying_parcel.parcel_id}. Drop it first.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            target_pid = params.get("parcel_id")
            parcel = None
            if target_pid:
                parcel = self.inventory_manager.get_parcel_by_id(target_pid)
            else:
                candidates = [
                    p for p in self.inventory_manager.parcels.values()
                    if p.status in ("AVAILABLE", "RESERVED")
                    and (p.pickup_cell == robot.pos or (p.location and abs(p.location[0] - robot.pos[0]) + abs(p.location[1] - robot.pos[1]) <= 1))
                ]
                if candidates:
                    parcel = candidates[0]

            if not parcel:
                res = CommandResult(ok=False, reason=f"No available parcel at or adjacent to Robot R{robot_id} position {robot.pos}.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            if parcel.spec.heavy and robot_id != 1:
                res = CommandResult(ok=False, reason=f"Capacity rule violation: Heavy parcel ({parcel.parcel_type.value}, {parcel.spec.weight_kg}kg) requires Heavy AMR TITAN-X (Robot 1). Humanoid R{robot_id} capacity is 15kg max.", robot_id=robot_id, command=cmd_str, params=params)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            if parcel.status == "AVAILABLE":
                self.inventory_manager.reserve_parcel(parcel.parcel_id, robot_id, self.step_count)
            self.inventory_manager.pickup_parcel(parcel.parcel_id, robot_id, self.step_count)
            self.inventory_manager.begin_transit(parcel.parcel_id, robot_id, self.step_count)
            robot.carrying_parcel = parcel
            robot.state = "CARRYING"
            res = CommandResult(ok=True, reason=f"Parcel {parcel.parcel_id} ({parcel.parcel_type.value}) picked up and secured by Robot R{robot_id}.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "DROP":
            if not robot.carrying_parcel:
                res = CommandResult(ok=False, reason=f"Robot R{robot_id} is not carrying any parcel to drop.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            parcel = robot.carrying_parcel
            if not self.grid.is_walkable(robot.pos[0], robot.pos[1]):
                res = CommandResult(ok=False, reason=f"Cannot drop parcel at non-walkable cell {robot.pos}.", robot_id=robot_id, command=cmd_str, params=params)
                self._log_command(robot_id, cmd_str, params, res)
                return res

            self.inventory_manager.deliver_parcel(parcel.parcel_id, robot_id, self.step_count, destination_cell=robot.pos)
            robot.carrying_parcel = None
            robot.state = "IDLE"
            robot.completed_tasks += 1
            if robot.assigned_task:
                self.task_manager.complete_task(robot.assigned_task.task_id, self.step_count)
                robot.assigned_task = None
            res = CommandResult(ok=True, reason=f"Parcel {parcel.parcel_id} successfully delivered at {robot.pos}. Inventory updated.", robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
            self._log_command(robot_id, cmd_str, params, res)
            return res

        elif cmd_str == "ASSIGN_TASK":
            tid = params.get("task_id")
            if tid:
                ok, reason = self.assign_task_manually(int(tid), robot_id)
                res = CommandResult(ok=ok, reason=reason, robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                self._log_command(robot_id, cmd_str, params, res)
                return res
            else:
                pick = params.get("pick")
                drop = params.get("drop")
                if pick and drop:
                    task, msg = self.create_custom_task(tuple(pick), tuple(drop))
                    if task:
                        ok, reason = self.assign_task_manually(task.task_id, robot_id)
                        res = CommandResult(ok=ok, reason=reason, robot_id=robot_id, command=cmd_str, params=params, resulting_pos=robot.pos, resulting_state=robot.state, resulting_mode=robot.mode)
                    else:
                        res = CommandResult(ok=False, reason=msg, robot_id=robot_id, command=cmd_str, params=params)
                else:
                    res = CommandResult(ok=False, reason="Missing task_id or (pick, drop) coordinates.", robot_id=robot_id, command=cmd_str, params=params)
                self._log_command(robot_id, cmd_str, params, res)
                return res

        else:
            res = CommandResult(ok=False, reason=f"Unrecognized command: {cmd_str}", robot_id=robot_id, command=cmd_str, params=params)
            self._log_command(robot_id, cmd_str, params, res)
            return res

    def _log_command(self, robot_id: int, command: str, params: Dict[str, Any], result: CommandResult) -> None:
        self.command_counter += 1
        entry = RobotCommandLogEntry(
            entry_id=self.command_counter,
            tick=self.step_count,
            robot_id=robot_id,
            command=command,
            params=params,
            result=result,
        )
        self.command_history.append(entry)
        if len(self.command_history) > 200:
            self.command_history.pop(0)

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
                self.robots[r_id].replan_count += 1

        self.metrics.record_replan_event(latency_ms)
        self._log_event(
            f"Dynamic obstacle at ({x}, {y}): replanned {len(affected)} robot(s) in {latency_ms:.2f}ms.",
            category="REPLAN",
        )
        return True, f"Obstacle injected at ({x}, {y}). Affected {len(affected)} robot(s). Replan latency: {latency_ms:.2f}ms."

    def step(self) -> None:
        """Advance the simulation world by 1 discrete time step."""
        current_step = self.step_count

        # 1. Multi-Robot Task Assignment & Dispatch for IDLE robots (AUTO mode only)
        idle_robots = {r_id: self.robots[r_id] for r_id, r in self.robots.items() if r.state == 'IDLE' and r.mode == 'AUTO' and not r.e_stopped}
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
                    # Physically attach reserved parcel for this robot first, else available at pickup cell
                    reserved_for_me = self.inventory_manager.get_reserved_parcel(r_id)
                    if reserved_for_me and reserved_for_me.pickup_cell == robot.assigned_task.pick_spot:
                        p_obj = reserved_for_me
                    else:
                        avail_parcels = [
                            p for p in self.inventory_manager.parcels.values()
                            if p.pickup_cell == robot.assigned_task.pick_spot and p.status == 'AVAILABLE'
                        ]
                        if avail_parcels:
                            p_obj = avail_parcels[0]
                        else:
                            p_obj = self.inventory_manager.create_parcel(
                                parcel_type=ParcelType.MEDIUM_CARTON,
                                location=robot.assigned_task.pick_spot,
                                pickup_cell=robot.assigned_task.pick_spot,
                                destination=robot.assigned_task.delivery_station,
                                tick=current_step,
                            )
                    if p_obj.status == 'AVAILABLE':
                        self.inventory_manager.reserve_parcel(p_obj.parcel_id, r_id, current_step)
                    if p_obj.status == 'RESERVED':
                        self.inventory_manager.pickup_parcel(p_obj.parcel_id, r_id, current_step)
                        self.inventory_manager.begin_transit(p_obj.parcel_id, r_id, current_step)
                        robot.carrying_parcel = p_obj
                        self._log_event(
                            f"R{r_id} picked up & attached {p_obj.parcel_id} ({p_obj.parcel_type.value}) at {robot.pos}.",
                            category="PICKUP",
                            robot_id=r_id,
                            parcel_id=p_obj.parcel_id,
                        )

                    robot.goal = p_obj.destination or robot.assigned_task.delivery_station
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
                    delivered_pid = None
                    if robot.carrying_parcel:
                        delivered_pid = robot.carrying_parcel.parcel_id
                        self.inventory_manager.deliver_parcel(
                            delivered_pid,
                            r_id,
                            current_step,
                            destination_cell=robot.pos,
                        )
                        robot.carrying_parcel = None
                    robot.completed_tasks += 1
                    self.task_manager.complete_task(robot.assigned_task.task_id, current_step)
                    self.metrics.record_task_completion()
                    self._log_event(
                        f"R{r_id} placed {delivered_pid or 'cargo'} at {robot.pos}. Task #{robot.assigned_task.task_id} completed.",
                        category="DELIVERY",
                        robot_id=r_id,
                        parcel_id=delivered_pid,
                    )
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
                dx = new_pos[0] - robot.pos[0]
                dy = new_pos[1] - robot.pos[1]
                robot.heading = math.atan2(dy, dx)
                robot.total_distance += 1
                robot.battery = max(0.0, robot.battery - 0.1)
            robot.pos = new_pos
            robot.trail.append(new_pos)
            if len(robot.trail) > 8:
                robot.trail.pop(0)
            if robot.carrying_parcel:
                robot.carrying_parcel.location = None

        # Ensure stationary manual / idle robots hold their cell in reservation table for next tick
        for r_id, robot in self.robots.items():
            if robot.mode == 'MANUAL' or robot.state in ('IDLE', 'CARRYING', 'E_STOPPED', 'PAUSED'):
                self.reservation_table.reserve_vertex(robot.pos[0], robot.pos[1], current_step + 1, robot_id=r_id)

        # 4. Record step metrics
        robot_statuses = {r_id: r.state for r_id, r in self.robots.items()}
        self.metrics.record_step(self.step_count, robot_statuses, conflicts)

        self.step_count += 1
