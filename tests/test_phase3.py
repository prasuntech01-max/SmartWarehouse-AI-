"""Unit tests for Phase 3: Simulation Engine & Performance Metrics."""

import pytest
from simulation.engine import WarehouseSimulator


def test_simulation_initialization():
    sim = WarehouseSimulator(num_robots=3)
    assert len(sim.robots) == 3
    assert sim.step_count == 0
    assert sim.grid.width == 15
    assert sim.grid.height == 15

    # Check initial robot positions are at docks
    for r_id in [1, 2, 3]:
        assert sim.robots[r_id].pos == sim.grid.charging_docks[r_id - 1]
        assert sim.robots[r_id].state == 'IDLE'


def test_simulation_stepping_and_zero_collisions():
    sim = WarehouseSimulator(num_robots=3)

    # Run for 40 steps
    for _ in range(40):
        sim.step()

    assert sim.step_count == 40
    summary = sim.metrics.get_summary()

    # Verify zero collisions
    assert summary['detected_conflicts'] == 0
    assert summary['collision_rate_percent'] == 0.0
    assert summary['makespan'] == 39
    assert summary['total_robot_steps'] > 0


def test_simulation_dynamic_obstacle_injection():
    sim = WarehouseSimulator(num_robots=3)

    # Step until robots are moving
    for _ in range(5):
        sim.step()

    # Find a robot with an active path ahead
    target_robot = None
    for r in sim.robots.values():
        if r.path and r.path_index < len(r.path) - 2:
            target_robot = r
            break

    if target_robot:
        target_cell = target_robot.path[target_robot.path_index + 2]
        success, msg = sim.inject_obstacle(target_cell[0], target_cell[1])
        assert success is True
        assert (target_cell[0], target_cell[1]) in sim.grid.dynamic_obstacles

        # Step forward and ensure the robot does not collide with the newly injected obstacle
        for _ in range(10):
            sim.step()
            assert target_robot.pos != target_cell

    summary = sim.metrics.get_summary()
    assert summary['detected_conflicts'] == 0


def test_scaling_5_robots_execution():
    sim = WarehouseSimulator(num_robots=5)
    for _ in range(35):
        sim.step()

    summary = sim.metrics.get_summary()
    assert summary['detected_conflicts'] == 0
    assert summary['completed_tasks'] >= 1
