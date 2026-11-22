"""Deadlock Detection and Recovery Subsystem using Wait-For Graph (WFG) analysis.

Features:
1. Wait-For Graph (WFG) construction tracking spatial-temporal resource contention.
2. Directed cycle detection (DFS-based) identifying circular wait deadlocks.
3. Multi-tiered intelligent recovery:
   - Priority inversion / elevation
   - Evasive yielding and temporary side-stepping into open bays
   - Staggered wait backoff
4. Safe transactional reservation release and rollback protection.
5. Persistent deadlock event logging and anti-starvation mechanisms.
"""

from typing import Dict, List, Tuple, Optional, Set, Any, Union
from dataclasses import dataclass, field
import copy
import time

from warehouse import Warehouse
from core.reservation import ReservationTable
from core.state import TimeExpandedPlanner, Trajectory, Action, TimeExpandedState
from core.conflict import MultiRobotConflictDetector, ConflictReport
from core.priority import PriorityPlanner, PriorityManager, PriorityScheme


@dataclass
class DeadlockEvent:
    """Structured record of a detected and handled deadlock event."""
    event_id: int
    timestamp: int
    cycle: List[int]
    affected_robots: List[int]
    graph_edges: Dict[int, List[int]]
    strategy_used: str
    success: bool
    message: str
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "cycle": self.cycle,
            "affected_robots": self.affected_robots,
            "graph_edges": self.graph_edges,
            "strategy_used": self.strategy_used,
            "success": self.success,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
        }


class WaitForGraph:
    """
    Directed Wait-For Graph (WFG) modeling resource contention between robots.
    A directed edge u -> v signifies that robot u is waiting for robot v to vacate
    or release a spatial-temporal cell.
    """

    def __init__(self):
        self.nodes: Set[int] = set()
        self.edges: Dict[int, Set[int]] = {}
        self.edge_metadata: Dict[Tuple[int, int], Dict[str, Any]] = {}

    def add_node(self, robot_id: int) -> None:
        self.nodes.add(robot_id)
        if robot_id not in self.edges:
            self.edges[robot_id] = set()

    def add_edge(
        self,
        waiter_id: int,
        blocker_id: int,
        target_cell: Tuple[int, int],
        reason: str = "blocked_cell",
    ) -> None:
        """Add a dependency edge: waiter_id depends on blocker_id."""
        if waiter_id == blocker_id:
            return  # No self-loops
        self.add_node(waiter_id)
        self.add_node(blocker_id)
        self.edges[waiter_id].add(blocker_id)
        self.edge_metadata[(waiter_id, blocker_id)] = {
            "target_cell": target_cell,
            "reason": reason,
        }

    def find_cycles(self) -> List[List[int]]:
        """
        Detects all elementary directed cycles in the Wait-For Graph using DFS.
        Returns a list of cycles, each represented as an ordered list of robot IDs.
        """
        cycles: List[List[int]] = []
        # Colors: 0 = unvisited (WHITE), 1 = visiting (GRAY), 2 = visited (BLACK)
        color: Dict[int, int] = {node: 0 for node in self.nodes}
        parent: Dict[int, Optional[int]] = {node: None for node in self.nodes}

        def dfs(u: int, path: List[int]):
            color[u] = 1
            path.append(u)

            for v in sorted(list(self.edges.get(u, set()))):
                if color[v] == 1:
                    # Found back-edge -> Cycle detected!
                    cycle_start_idx = path.index(v)
                    detected_cycle = list(path[cycle_start_idx:])
                    # Normalize cycle so smallest ID is first for deterministic deduplication
                    min_idx = detected_cycle.index(min(detected_cycle))
                    normalized = detected_cycle[min_idx:] + detected_cycle[:min_idx]
                    if normalized not in cycles:
                        cycles.append(normalized)
                elif color[v] == 0:
                    parent[v] = u
                    dfs(v, path)

            path.pop()
            color[u] = 2

        for node in sorted(list(self.nodes)):
            if color[node] == 0:
                dfs(node, [])

        return cycles

    def has_cycle(self) -> bool:
        """Returns True if any circular wait condition exists."""
        return len(self.find_cycles()) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary representation."""
        return {
            "nodes": sorted(list(self.nodes)),
            "edges": {node: sorted(list(targets)) for node, targets in self.edges.items()},
        }


class DeadlockHandler:
    """Robust Deadlock Detection and Recovery Engine."""

    def __init__(
        self,
        warehouse: Warehouse,
        reservation_table: ReservationTable,
        planner: Optional[TimeExpandedPlanner] = None,
    ):
        self.warehouse = warehouse
        self.reservation_table = reservation_table
        self.planner = planner or TimeExpandedPlanner(self.warehouse, self.reservation_table)
        self.priority_planner = PriorityPlanner(self.warehouse, self.reservation_table)
        self.detector = MultiRobotConflictDetector(warehouse=self.warehouse)
        self.event_log: List[DeadlockEvent] = []
        self._event_counter = 1
        self.robot_deadlock_counts: Dict[int, int] = {}

    def build_wait_for_graph(
        self,
        robot_states: Dict[int, Dict[str, Any]],
        current_time: int,
    ) -> WaitForGraph:
        """
        Builds the live Wait-For Graph based on current positions, desired next moves,
        and reservation table dependencies.
        
        robot_states format:
            robot_id -> {
                'pos': (x, y),
                'goal': (x, y),
                'path': List[(x, y)],
                'path_index': int,
                'is_waiting': bool,
            }
        """
        graph = WaitForGraph()
        for r_id in robot_states.keys():
            graph.add_node(r_id)

        # Map current positions to robot_id
        pos_to_robot = {s['pos']: r_id for r_id, s in robot_states.items()}

        for r_id, state in robot_states.items():
            curr_pos = state['pos']
            path = state.get('path', [])
            idx = state.get('path_index', 0)

            # Determine where robot desires to step next
            if path and idx < len(path) - 1:
                next_desired = path[idx + 1]
            else:
                next_desired = None

            if next_desired is not None and next_desired != curr_pos:
                # 1. Direct cell occupancy: another robot is currently sitting at next_desired
                if next_desired in pos_to_robot:
                    blocker = pos_to_robot[next_desired]
                    if blocker != r_id:
                        graph.add_edge(r_id, blocker, next_desired, reason="occupied_cell")

                # 2. Reservation table dependency: cell reserved at t+1 by another robot
                res_holder = self.reservation_table.get_vertex_reservation(
                    next_desired[0], next_desired[1], current_time + 1
                )
                if res_holder is not None and res_holder != r_id:
                    graph.add_edge(r_id, res_holder, next_desired, reason="reserved_vertex")

                # 3. Head-on edge swap contention: another robot traversing reverse edge
                edge_holder = self.reservation_table.get_edge_reservation(
                    next_desired, curr_pos, current_time
                )
                if edge_holder is not None and edge_holder != r_id:
                    graph.add_edge(r_id, edge_holder, next_desired, reason="edge_swap")

        return graph

    def detect_deadlocks(
        self,
        robot_states: Dict[int, Dict[str, Any]],
        current_time: int,
    ) -> List[List[int]]:
        """Constructs Wait-For Graph and returns all detected circular wait cycles."""
        wfg = self.build_wait_for_graph(robot_states, current_time)
        return wfg.find_cycles()

    def resolve_deadlock(
        self,
        cycle: List[int],
        robot_states: Dict[int, Dict[str, Any]],
        current_time: int,
    ) -> Tuple[bool, Dict[int, Any], str]:
        """
        Attempts to resolve a deadlock cycle using multi-tiered recovery strategies:
        - Strategy 1: Priority Inversion & Elevation
        - Strategy 2: Evasive Side-Step / Bay Yielding
        - Strategy 3: Staggered Backoff Waiting
        
        Returns:
            (success, updated_trajectories_dict, log_message)
        """
        t0 = time.perf_counter()
        if not cycle:
            return False, {}, "No deadlock cycle provided"

        # Update deadlock counters to prevent repeated starvation
        for r in cycle:
            self.robot_deadlock_counts[r] = self.robot_deadlock_counts.get(r, 0) + 1

        wfg = self.build_wait_for_graph(robot_states, current_time)
        graph_edges = {u: list(targets) for u, targets in wfg.edges.items() if u in cycle}

        # -------------------------------------------------------------
        # Strategy 1: Priority Inversion / Elevation
        # -------------------------------------------------------------
        # Try elevating each member of the cycle to highest priority
        for lead_robot in cycle:
            success, paths = self._try_priority_replan(lead_robot, cycle, robot_states, current_time)
            if success:
                latency = (time.perf_counter() - t0) * 1000.0
                msg = f"Deadlock cycle {cycle} resolved via Priority Elevation of Robot {lead_robot}."
                event = DeadlockEvent(
                    event_id=self._event_counter,
                    timestamp=current_time,
                    cycle=cycle,
                    affected_robots=cycle,
                    graph_edges=graph_edges,
                    strategy_used="PRIORITY_ELEVATION",
                    success=True,
                    message=msg,
                    latency_ms=latency,
                )
                self._event_counter += 1
                self.event_log.append(event)
                return True, paths, msg

        # -------------------------------------------------------------
        # Strategy 2: Evasive Side-Step / Bay Yielding
        # -------------------------------------------------------------
        success, paths = self._try_evasive_yield(cycle, robot_states, current_time)
        if success:
            latency = (time.perf_counter() - t0) * 1000.0
            msg = f"Deadlock cycle {cycle} resolved via Evasive Side-Step Yielding."
            event = DeadlockEvent(
                event_id=self._event_counter,
                timestamp=current_time,
                cycle=cycle,
                affected_robots=cycle,
                graph_edges=graph_edges,
                strategy_used="EVASIVE_YIELD",
                success=True,
                message=msg,
                latency_ms=latency,
            )
            self._event_counter += 1
            self.event_log.append(event)
            return True, paths, msg

        # -------------------------------------------------------------
        # Strategy 3: Staggered Backoff Waiting
        # -------------------------------------------------------------
        success, paths = self._try_staggered_backoff(cycle, robot_states, current_time)
        if success:
            latency = (time.perf_counter() - t0) * 1000.0
            msg = f"Deadlock cycle {cycle} resolved via Staggered Backoff Waiting."
            event = DeadlockEvent(
                event_id=self._event_counter,
                timestamp=current_time,
                cycle=cycle,
                affected_robots=cycle,
                graph_edges=graph_edges,
                strategy_used="STAGGERED_BACKOFF",
                success=True,
                message=msg,
                latency_ms=latency,
            )
            self._event_counter += 1
            self.event_log.append(event)
            return True, paths, msg

        # Failed recovery
        latency = (time.perf_counter() - t0) * 1000.0
        msg = f"Failed to resolve deadlock cycle {cycle} after evaluating all recovery strategies."
        event = DeadlockEvent(
            event_id=self._event_counter,
            timestamp=current_time,
            cycle=cycle,
            affected_robots=cycle,
            graph_edges=graph_edges,
            strategy_used="EXHAUSTED_ALL",
            success=False,
            message=msg,
            latency_ms=latency,
        )
        self._event_counter += 1
        self.event_log.append(event)
        return False, {}, msg

    def _try_priority_replan(
        self,
        lead_robot: int,
        cycle: List[int],
        robot_states: Dict[int, Dict[str, Any]],
        current_time: int,
    ) -> Tuple[bool, Dict[int, Trajectory]]:
        """Elevates lead_robot to top priority and sequentially replans cycle members."""
        snapshot = self.reservation_table.snapshot()

        # Release future reservations for cycle members
        for r_id in cycle:
            self.reservation_table.release_future_reservations(r_id, from_time=current_time)

        # Ordering: lead_robot first, followed by remaining cycle members
        order = [lead_robot] + [r for r in cycle if r != lead_robot]
        reconciled_paths: Dict[int, Trajectory] = {}

        for r_id in order:
            state = robot_states[r_id]
            traj = self.planner.plan(
                start=state['pos'],
                goal=state['goal'],
                start_time=current_time,
                robot_id=r_id,
            )
            if traj is None:
                # Rollback and fail
                self.reservation_table.restore(snapshot)
                return False, {}

            reconciled_paths[r_id] = traj
            self.reservation_table.reserve_path(traj, robot_id=r_id, start_time=current_time)

        # Verify 0 conflicts
        conflicts = self.detector.detect_conflicts(reconciled_paths)
        if conflicts:
            self.reservation_table.restore(snapshot)
            return False, {}

        return True, reconciled_paths

    def _try_evasive_yield(
        self,
        cycle: List[int],
        robot_states: Dict[int, Dict[str, Any]],
        current_time: int,
    ) -> Tuple[bool, Dict[int, Trajectory]]:
        """
        Picks one robot from cycle to temporarily side-step into an open neighbor cell
        (open bay / turnout), wait until other robots pass, and then resume.
        """
        snapshot = self.reservation_table.snapshot()

        for yield_robot in cycle:
            other_robots = [r for r in cycle if r != yield_robot]

            # Clear future reservations for cycle members
            for r_id in cycle:
                self.reservation_table.release_future_reservations(r_id, from_time=current_time)

            # Plan paths for the other robots first
            other_paths: Dict[int, Trajectory] = {}
            others_succeeded = True
            for o_id in other_robots:
                o_state = robot_states[o_id]
                traj = self.planner.plan(
                    start=o_state['pos'],
                    goal=o_state['goal'],
                    start_time=current_time,
                    robot_id=o_id,
                )
                if traj is None:
                    others_succeeded = False
                    break
                other_paths[o_id] = traj
                self.reservation_table.reserve_path(traj, robot_id=o_id, start_time=current_time)

            if not others_succeeded:
                self.reservation_table.restore(snapshot)
                continue

            # Now find a safe open neighbor cell for yield_robot to step into
            y_state = robot_states[yield_robot]
            neighbors = self.warehouse.get_neighbors(y_state['pos'][0], y_state['pos'][1])

            # Filter candidates: cell not reserved at t=current_time+1
            candidates = [
                n for n in neighbors
                if not self.reservation_table.is_vertex_reserved(n[0], n[1], current_time + 1)
            ]

            for side_cell in candidates:
                # Step 1: move to side_cell
                # Step 2: wait K steps (e.g. 4 steps)
                # Step 3: move to goal
                wait_steps = 4
                traj_side = self.planner.plan(
                    start=y_state['pos'],
                    goal=side_cell,
                    start_time=current_time,
                    robot_id=yield_robot,
                )
                if traj_side is None:
                    continue

                t_side = current_time + len(traj_side) - 1
                t_resume = t_side + wait_steps

                # Temporarily reserve the wait period
                for dt in range(len(traj_side)):
                    self.reservation_table.reserve_vertex(
                        traj_side[dt][0], traj_side[dt][1], current_time + dt, robot_id=yield_robot
                    )
                for dt in range(1, wait_steps + 1):
                    self.reservation_table.reserve_vertex(
                        side_cell[0], side_cell[1], t_side + dt, robot_id=yield_robot
                    )

                # Step 3: plan from side_cell to original goal
                traj_final = self.planner.plan(
                    start=side_cell,
                    goal=y_state['goal'],
                    start_time=t_resume,
                    robot_id=yield_robot,
                )

                if traj_final is not None:
                    # Construct composite trajectory
                    composite_states = list(traj_side.states)
                    for dt in range(1, wait_steps + 1):
                        composite_states.append(TimeExpandedState(side_cell[0], side_cell[1], t_side + dt))
                    composite_states.extend(traj_final.states[1:])
                    full_yield_traj = Trajectory(composite_states)

                    # Reserve full trajectory
                    self.reservation_table.reserve_path(full_yield_traj, robot_id=yield_robot, start_time=current_time)

                    all_paths = dict(other_paths)
                    all_paths[yield_robot] = full_yield_traj

                    # Verify 0 conflicts
                    if len(self.detector.detect_conflicts(all_paths)) == 0:
                        return True, all_paths

            # If this yield_robot couldn't find a path, restore and try next
            self.reservation_table.restore(snapshot)

        return False, {}

    def _try_staggered_backoff(
        self,
        cycle: List[int],
        robot_states: Dict[int, Dict[str, Any]],
        current_time: int,
    ) -> Tuple[bool, Dict[int, Trajectory]]:
        """Staggers departure times by having lower-priority robots wait in place."""
        snapshot = self.reservation_table.snapshot()

        for delay in [2, 4, 6]:
            for r_id in cycle:
                self.reservation_table.release_future_reservations(r_id, from_time=current_time)

            paths: Dict[int, Trajectory] = {}
            all_ok = True

            for rank, r_id in enumerate(cycle):
                r_delay = rank * delay
                actual_start = current_time + r_delay
                state = robot_states[r_id]

                # Reserve stationary wait at start position
                for dt in range(r_delay):
                    self.reservation_table.reserve_vertex(
                        state['pos'][0], state['pos'][1], current_time + dt, robot_id=r_id
                    )

                traj = self.planner.plan(
                    start=state['pos'],
                    goal=state['goal'],
                    start_time=actual_start,
                    robot_id=r_id,
                )

                if traj is None:
                    all_ok = False
                    break

                # Prefix stationary wait states
                wait_states = [
                    TimeExpandedState(state['pos'][0], state['pos'][1], current_time + dt)
                    for dt in range(r_delay)
                ]
                full_traj = Trajectory(wait_states + traj.states)
                paths[r_id] = full_traj
                self.reservation_table.reserve_path(full_traj, robot_id=r_id, start_time=current_time)

            if all_ok and len(self.detector.detect_conflicts(paths)) == 0:
                return True, paths

            self.reservation_table.restore(snapshot)

        return False, {}
