"""Deterministic dynamic replanning demonstration scenario for evaluation and viva."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import time


@dataclass
class DemoResult:
    """Outcome report for the dynamic obstacle replanning demonstration."""
    success: bool
    obstacle_pos: Optional[Tuple[int, int]]
    affected_robots: List[int]
    old_paths: Dict[int, List[Tuple[int, int]]]
    new_paths: Dict[int, List[Tuple[int, int]]]
    steps_before_obstacle: int
    steps_after_obstacle: int
    replan_latency_ms: float
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'success': self.success,
            'obstacle_pos': self.obstacle_pos,
            'affected_robots': list(self.affected_robots),
            'steps_before_obstacle': self.steps_before_obstacle,
            'steps_after_obstacle': self.steps_after_obstacle,
            'replan_latency_ms': round(self.replan_latency_ms, 3),
            'message': self.message,
        }


class DemoScenario:
    """
    Executes a deterministic live scenario demonstrating:
    1. Fleet initialization & navigation towards initial tasks.
    2. Mid-route dynamic obstacle appearance directly blocking a robot's planned aisle.
    3. Immediate detection and Space-Time A* dynamic replanning.
    4. Successful detour around the obstacle without collisions.
    """

    @staticmethod
    def run_dynamic_obstacle_demo(sim, steps_before: int = 5, steps_after: int = 20) -> DemoResult:
        """
        Runs the deterministic dynamic replanning demo on the provided simulator.

        Args:
            sim: WarehouseSimulator instance
            steps_before: Warmup steps before obstacle injection
            steps_after: Steps to run post-replanning

        Returns:
            DemoResult with complete trajectory comparison
        """
        # 1. Reset simulator to reproducible baseline (3 robots)
        sim.reset(num_robots=3)

        # 2. Advance warmup steps so robots have active paths
        for _ in range(steps_before):
            sim.step()

        step_at_inject = sim.step_count

        # 3. Locate the robot with the longest active remaining path
        candidate_robot: Optional[int] = None
        candidate_path: List[Tuple[int, int]] = []

        for r_id, r in sorted(sim.robots.items()):
            rem = r.path[r.path_index:] if r.path else []
            if len(rem) > len(candidate_path):
                candidate_path = rem
                candidate_robot = r_id

        # 4. Select target obstacle cell along that robot's forward path
        if candidate_robot is not None and len(candidate_path) >= 4:
            # Inject at index 2 or 3 (ahead of robot, giving room for detour)
            inject_pos = candidate_path[2]
        elif candidate_robot is not None and len(candidate_path) >= 2:
            inject_pos = candidate_path[1]
        else:
            # Fallback coordinate in central aisle
            inject_pos = (5, 6)

        # Snapshot paths before injection
        old_paths: Dict[int, List[Tuple[int, int]]] = {}
        for r_id, r in sim.robots.items():
            old_paths[r_id] = list(r.path[r.path_index:]) if r.path else []

        # 5. Inject obstacle and measure replan execution
        t0 = time.perf_counter()
        inject_success, inject_msg = sim.inject_obstacle(inject_pos[0], inject_pos[1])
        replan_latency_ms = (time.perf_counter() - t0) * 1000.0

        # Snapshot paths after injection
        new_paths: Dict[int, List[Tuple[int, int]]] = {}
        for r_id, r in sim.robots.items():
            new_paths[r_id] = list(r.path[r.path_index:]) if r.path else []

        # Identify which robots' paths changed
        affected: List[int] = []
        for r_id in old_paths:
            if old_paths[r_id] != new_paths.get(r_id, []):
                affected.append(r_id)

        # 6. Execute forward steps to show detour completion
        for _ in range(steps_after):
            sim.step()

        return DemoResult(
            success=inject_success,
            obstacle_pos=inject_pos,
            affected_robots=affected,
            old_paths=old_paths,
            new_paths=new_paths,
            steps_before_obstacle=step_at_inject,
            steps_after_obstacle=sim.step_count,
            replan_latency_ms=replan_latency_ms,
            message=inject_msg,
        )
