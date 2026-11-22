"""Intelligent multi-robot task assignment and fleet optimization engine.

Implements multiple allocation strategies:
1. NEAREST_ROBOT — Minimizes robot-to-pickup approach distance.
2. SHORTEST_TOTAL_ROUTE — Minimizes complete mission route (robot -> pick -> delivery).
3. PRIORITY_FIRST — Prioritizes Urgent & High priority orders first to closest robots.
4. WORKLOAD_BALANCED — Dispatches tasks to robots with fewest completed/assigned tasks to balance fleet wear.
5. WEIGHTED_MULTI_CRITERIA — Normalized weighted composite score balancing distance, workload, priority, and route duration.
6. BATCH_OPTIMAL — Global optimal bipartite matching (Hungarian algorithm) for simultaneous multi-robot allocation.
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
import math

from core.grid import WarehouseGrid
from core.task_manager import WarehouseTask, TaskPriority


class AssignmentStrategy(str, Enum):
    """Strategies for allocating warehouse tasks to robot fleet."""
    NEAREST_ROBOT = "NEAREST_ROBOT"
    SHORTEST_TOTAL_ROUTE = "SHORTEST_TOTAL_ROUTE"
    PRIORITY_FIRST = "PRIORITY_FIRST"
    WORKLOAD_BALANCED = "WORKLOAD_BALANCED"
    WEIGHTED_MULTI_CRITERIA = "WEIGHTED_MULTI_CRITERIA"
    BATCH_OPTIMAL = "BATCH_OPTIMAL"

    @property
    def label(self) -> str:
        labels = {
            self.NEAREST_ROBOT: "Nearest Available Robot",
            self.SHORTEST_TOTAL_ROUTE: "Shortest Total Route",
            self.PRIORITY_FIRST: "Priority-First Dispatch",
            self.WORKLOAD_BALANCED: "Workload-Balanced Allocation",
            self.WEIGHTED_MULTI_CRITERIA: "Weighted Multi-Criteria",
            self.BATCH_OPTIMAL: "Hungarian Batch Optimizer",
        }
        return labels.get(self, self.value)


@dataclass
class AssignmentWeights:
    """Configurable weights for weighted multi-criteria assignment."""
    w_distance: float = 0.40      # Distance cost
    w_workload: float = 0.25      # Fleet workload balance cost
    w_priority: float = 0.25      # Priority urgency cost (higher priority reduces cost)
    w_duration: float = 0.10      # Mission duration cost

    def normalize(self) -> "AssignmentWeights":
        """Ensure sum of weights equals 1.0."""
        total = self.w_distance + self.w_workload + self.w_priority + self.w_duration
        if total <= 0:
            return AssignmentWeights()
        return AssignmentWeights(
            w_distance=self.w_distance / total,
            w_workload=self.w_workload / total,
            w_priority=self.w_priority / total,
            w_duration=self.w_duration / total,
        )


@dataclass
class AssignmentDecision:
    """Structured result of a task-to-robot assignment decision."""
    task_id: int
    robot_id: int
    strategy: str
    cost: float
    distance_to_pick: int
    total_mission_distance: int
    priority: int
    robot_workload: int
    timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "robot_id": self.robot_id,
            "strategy": self.strategy,
            "cost": round(self.cost, 3),
            "distance_to_pick": self.distance_to_pick,
            "total_mission_distance": self.total_mission_distance,
            "priority": self.priority,
            "robot_workload": self.robot_workload,
            "timestamp": self.timestamp,
        }


class TaskAssignmentEngine:
    """
    Intelligent decision engine matching warehouse orders to autonomous robots
    under online (single-robot) and batch (multi-robot) allocation policies.
    """

    def __init__(
        self,
        grid: WarehouseGrid,
        default_strategy: AssignmentStrategy = AssignmentStrategy.WEIGHTED_MULTI_CRITERIA,
        weights: Optional[AssignmentWeights] = None,
    ):
        self.grid = grid
        self.strategy = default_strategy
        self.weights = weights.normalize() if weights else AssignmentWeights()
        self.history: List[AssignmentDecision] = []

    @staticmethod
    def manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
        """Calculates Manhattan distance between two 2D coordinates."""
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def calculate_cost(
        self,
        robot_id: int,
        robot_pos: Tuple[int, int],
        robot_workload: int,
        task: WarehouseTask,
        strategy: Optional[AssignmentStrategy] = None,
        weights: Optional[AssignmentWeights] = None,
        max_workload: int = 10,
    ) -> float:
        """
        Computes assignment cost for assigning `task` to `robot_id` at `robot_pos`.
        Lower cost indicates a better, more favorable match.
        """
        strat = strategy or self.strategy
        w = (weights or self.weights).normalize()

        d_pick = self.manhattan_distance(robot_pos, task.pick_spot)
        d_delivery = self.manhattan_distance(task.pick_spot, task.delivery_station)
        d_total = d_pick + d_delivery

        max_grid_dist = max(1, self.grid.width + self.grid.height)
        max_route = max_grid_dist * 2

        if strat == AssignmentStrategy.NEAREST_ROBOT:
            return float(d_pick)

        elif strat == AssignmentStrategy.SHORTEST_TOTAL_ROUTE:
            return float(d_total)

        elif strat == AssignmentStrategy.PRIORITY_FIRST:
            # Urgent (4) gets massive cost deduction, distance breaks ties
            priority_penalty = (5 - int(task.priority)) * 100.0
            return priority_penalty + float(d_pick)

        elif strat == AssignmentStrategy.WORKLOAD_BALANCED:
            # Heavy penalty on robots with high workload, distance breaks ties
            return (float(robot_workload) * 20.0) + float(d_pick)

        elif strat in (AssignmentStrategy.WEIGHTED_MULTI_CRITERIA, AssignmentStrategy.BATCH_OPTIMAL):
            # Normalized multi-criteria score in [0, 1]
            norm_dist = min(1.0, d_pick / max_grid_dist)
            norm_workload = min(1.0, robot_workload / max(1, max_workload))
            norm_priority = (4.0 - float(task.priority)) / 3.0  # Priority 4 -> 0.0 (best), Priority 1 -> 1.0 (worst)
            norm_duration = min(1.0, d_total / max_route)

            cost = (
                (w.w_distance * norm_dist)
                + (w.w_workload * norm_workload)
                + (w.w_priority * norm_priority)
                + (w.w_duration * norm_duration)
            )
            return cost

        return float(d_pick)

    def select_best_task_for_robot(
        self,
        robot_id: int,
        robot_pos: Tuple[int, int],
        robot_workload: int,
        available_tasks: List[WarehouseTask],
        strategy: Optional[AssignmentStrategy] = None,
        weights: Optional[AssignmentWeights] = None,
        current_step: int = 0,
    ) -> Optional[AssignmentDecision]:
        """
        Online single-robot assignment: finds the best available task for an idle robot.
        """
        if not available_tasks:
            return None

        strat = strategy or self.strategy
        w = weights or self.weights

        max_wl = max([robot_workload] + [1])
        best_decision: Optional[AssignmentDecision] = None
        min_cost = float('inf')

        for task in available_tasks:
            cost = self.calculate_cost(
                robot_id=robot_id,
                robot_pos=robot_pos,
                robot_workload=robot_workload,
                task=task,
                strategy=strat,
                weights=w,
                max_workload=max_wl,
            )

            if cost < min_cost:
                min_cost = cost
                d_pick = self.manhattan_distance(robot_pos, task.pick_spot)
                d_total = d_pick + self.manhattan_distance(task.pick_spot, task.delivery_station)
                best_decision = AssignmentDecision(
                    task_id=task.task_id,
                    robot_id=robot_id,
                    strategy=strat.value,
                    cost=cost,
                    distance_to_pick=d_pick,
                    total_mission_distance=d_total,
                    priority=int(task.priority),
                    robot_workload=robot_workload,
                    timestamp=current_step,
                )

        if best_decision:
            self.history.append(best_decision)

        return best_decision

    def assign_batch(
        self,
        idle_robots: Dict[int, Dict[str, Any]],  # robot_id -> {'pos': (x, y), 'workload': int}
        pending_tasks: List[WarehouseTask],
        strategy: Optional[AssignmentStrategy] = None,
        weights: Optional[AssignmentWeights] = None,
        current_step: int = 0,
    ) -> List[AssignmentDecision]:
        """
        Batch allocation matching multiple idle robots to multiple pending orders simultaneously.
        Guarantees 1-to-1 matching: no robot or task is assigned more than once.
        """
        if not idle_robots or not pending_tasks:
            return []

        strat = strategy or self.strategy
        w = weights or self.weights
        decisions: List[AssignmentDecision] = []

        robot_ids = list(idle_robots.keys())
        tasks = list(pending_tasks)

        # 1. BATCH_OPTIMAL via Hungarian Algorithm (Linear Sum Assignment)
        if strat == AssignmentStrategy.BATCH_OPTIMAL:
            decisions = self._hungarian_batch_assign(
                robot_ids, idle_robots, tasks, w, current_step
            )
            for d in decisions:
                self.history.append(d)
            return decisions

        # 2. PRIORITY_FIRST Batch Strategy
        if strat == AssignmentStrategy.PRIORITY_FIRST:
            # Sort tasks by priority descending (Urgent first), then creation step
            sorted_tasks = sorted(tasks, key=lambda t: (-int(t.priority), t.created_at_step))
            available_rids = set(robot_ids)

            for task in sorted_tasks:
                if not available_rids:
                    break
                best_rid = None
                best_cost = float('inf')
                for rid in available_rids:
                    r_info = idle_robots[rid]
                    cost = self.calculate_cost(
                        robot_id=rid,
                        robot_pos=r_info['pos'],
                        robot_workload=r_info.get('workload', 0),
                        task=task,
                        strategy=AssignmentStrategy.PRIORITY_FIRST,
                        weights=w,
                    )
                    if cost < best_cost:
                        best_cost = cost
                        best_rid = rid

                if best_rid is not None:
                    d_pick = self.manhattan_distance(idle_robots[best_rid]['pos'], task.pick_spot)
                    d_total = d_pick + self.manhattan_distance(task.pick_spot, task.delivery_station)
                    dec = AssignmentDecision(
                        task_id=task.task_id,
                        robot_id=best_rid,
                        strategy=strat.value,
                        cost=best_cost,
                        distance_to_pick=d_pick,
                        total_mission_distance=d_total,
                        priority=int(task.priority),
                        robot_workload=idle_robots[best_rid].get('workload', 0),
                        timestamp=current_step,
                    )
                    decisions.append(dec)
                    self.history.append(dec)
                    available_rids.remove(best_rid)

            return decisions

        # 3. WORKLOAD_BALANCED Batch Strategy
        if strat == AssignmentStrategy.WORKLOAD_BALANCED:
            # Sort robots by workload ascending (least loaded first)
            sorted_rids = sorted(robot_ids, key=lambda r: idle_robots[r].get('workload', 0))
            available_tasks = list(tasks)

            for rid in sorted_rids:
                if not available_tasks:
                    break
                r_info = idle_robots[rid]
                best_task_idx = None
                best_cost = float('inf')

                for idx, t in enumerate(available_tasks):
                    cost = self.calculate_cost(
                        robot_id=rid,
                        robot_pos=r_info['pos'],
                        robot_workload=r_info.get('workload', 0),
                        task=t,
                        strategy=AssignmentStrategy.WORKLOAD_BALANCED,
                        weights=w,
                    )
                    if cost < best_cost:
                        best_cost = cost
                        best_task_idx = idx

                if best_task_idx is not None:
                    matched_task = available_tasks.pop(best_task_idx)
                    d_pick = self.manhattan_distance(r_info['pos'], matched_task.pick_spot)
                    d_total = d_pick + self.manhattan_distance(matched_task.pick_spot, matched_task.delivery_station)
                    dec = AssignmentDecision(
                        task_id=matched_task.task_id,
                        robot_id=rid,
                        strategy=strat.value,
                        cost=best_cost,
                        distance_to_pick=d_pick,
                        total_mission_distance=d_total,
                        priority=int(matched_task.priority),
                        robot_workload=r_info.get('workload', 0),
                        timestamp=current_step,
                    )
                    decisions.append(dec)
                    self.history.append(dec)

            return decisions

        # 4. Standard Greedy Matching (NEAREST_ROBOT, SHORTEST_TOTAL_ROUTE, WEIGHTED_MULTI_CRITERIA)
        available_rids = set(robot_ids)
        available_tasks = list(tasks)
        max_wl = max([idle_robots[r].get('workload', 0) for r in robot_ids] + [1])

        while available_rids and available_tasks:
            # Find best global (robot, task) pair with minimum cost
            best_pair = None
            min_cost = float('inf')

            for rid in available_rids:
                r_info = idle_robots[rid]
                for t in available_tasks:
                    cost = self.calculate_cost(
                        robot_id=rid,
                        robot_pos=r_info['pos'],
                        robot_workload=r_info.get('workload', 0),
                        task=t,
                        strategy=strat,
                        weights=w,
                        max_workload=max_wl,
                    )
                    if cost < min_cost:
                        min_cost = cost
                        best_pair = (rid, t)

            if best_pair is None:
                break

            matched_rid, matched_task = best_pair
            r_info = idle_robots[matched_rid]
            d_pick = self.manhattan_distance(r_info['pos'], matched_task.pick_spot)
            d_total = d_pick + self.manhattan_distance(matched_task.pick_spot, matched_task.delivery_station)

            dec = AssignmentDecision(
                task_id=matched_task.task_id,
                robot_id=matched_rid,
                strategy=strat.value,
                cost=min_cost,
                distance_to_pick=d_pick,
                total_mission_distance=d_total,
                priority=int(matched_task.priority),
                robot_workload=r_info.get('workload', 0),
                timestamp=current_step,
            )
            decisions.append(dec)
            self.history.append(dec)

            available_rids.remove(matched_rid)
            available_tasks.remove(matched_task)

        return decisions

    def _hungarian_batch_assign(
        self,
        robot_ids: List[int],
        idle_robots: Dict[int, Dict[str, Any]],
        tasks: List[WarehouseTask],
        weights: AssignmentWeights,
        current_step: int,
    ) -> List[AssignmentDecision]:
        """
        Solves optimal bipartite matching using the Hungarian algorithm (linear_sum_assignment).
        Minimizes total global fleet assignment cost.
        """
        n_robots = len(robot_ids)
        n_tasks = len(tasks)
        max_wl = max([idle_robots[r].get('workload', 0) for r in robot_ids] + [1])

        # Construct Cost Matrix of dimension (n_robots x n_tasks)
        cost_matrix = []
        for rid in robot_ids:
            r_info = idle_robots[rid]
            row = []
            for t in tasks:
                c = self.calculate_cost(
                    robot_id=rid,
                    robot_pos=r_info['pos'],
                    robot_workload=r_info.get('workload', 0),
                    task=t,
                    strategy=AssignmentStrategy.WEIGHTED_MULTI_CRITERIA,
                    weights=weights,
                    max_workload=max_wl,
                )
                row.append(c)
            cost_matrix.append(row)

        try:
            from scipy.optimize import linear_sum_assignment
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
        except Exception:
            # Fallback greedy if scipy fails
            return self._greedy_matrix_fallback(robot_ids, idle_robots, tasks, cost_matrix, current_step)

        decisions = []
        for r_idx, t_idx in zip(row_ind, col_ind):
            rid = robot_ids[r_idx]
            task = tasks[t_idx]
            r_info = idle_robots[rid]
            d_pick = self.manhattan_distance(r_info['pos'], task.pick_spot)
            d_total = d_pick + self.manhattan_distance(task.pick_spot, task.delivery_station)

            decisions.append(AssignmentDecision(
                task_id=task.task_id,
                robot_id=rid,
                strategy=AssignmentStrategy.BATCH_OPTIMAL.value,
                cost=cost_matrix[r_idx][t_idx],
                distance_to_pick=d_pick,
                total_mission_distance=d_total,
                priority=int(task.priority),
                robot_workload=r_info.get('workload', 0),
                timestamp=current_step,
            ))

        return decisions

    def _greedy_matrix_fallback(
        self,
        robot_ids: List[int],
        idle_robots: Dict[int, Dict[str, Any]],
        tasks: List[WarehouseTask],
        cost_matrix: List[List[float]],
        current_step: int,
    ) -> List[AssignmentDecision]:
        """Fallback bipartite matcher if linear_sum_assignment is unavailable."""
        decisions = []
        used_robots = set()
        used_tasks = set()

        # Flatten elements and sort by cost ascending
        entries = []
        for r_idx, row in enumerate(cost_matrix):
            for t_idx, cost in enumerate(row):
                entries.append((cost, r_idx, t_idx))
        entries.sort(key=lambda x: x[0])

        for cost, r_idx, t_idx in entries:
            if r_idx not in used_robots and t_idx not in used_tasks:
                used_robots.add(r_idx)
                used_tasks.add(t_idx)
                rid = robot_ids[r_idx]
                task = tasks[t_idx]
                r_info = idle_robots[rid]
                d_pick = self.manhattan_distance(r_info['pos'], task.pick_spot)
                d_total = d_pick + self.manhattan_distance(task.pick_spot, task.delivery_station)

                decisions.append(AssignmentDecision(
                    task_id=task.task_id,
                    robot_id=rid,
                    strategy=AssignmentStrategy.BATCH_OPTIMAL.value,
                    cost=cost,
                    distance_to_pick=d_pick,
                    total_mission_distance=d_total,
                    priority=int(task.priority),
                    robot_workload=r_info.get('workload', 0),
                    timestamp=current_step,
                ))

        return decisions
