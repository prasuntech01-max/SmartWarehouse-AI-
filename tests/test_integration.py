"""End-to-end integration tests for SmartWarehouse AI."""

import pytest
import matplotlib.pyplot as plt
from core.grid import WarehouseGrid
from simulation.engine import WarehouseSimulator
from visualization.renderer import WarehouseRenderer


def test_renderer_output():
    grid = WarehouseGrid(15, 15)
    sim = WarehouseSimulator(num_robots=3)
    renderer = WarehouseRenderer(grid)

    fig = renderer.render(sim.robots, step_count=sim.step_count)
    assert fig is not None
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_full_mission_lifecycle():
    sim = WarehouseSimulator(num_robots=4, width=15, height=15, seed=99)

    # Run for 60 steps to observe full pick-and-deliver cycles
    for _ in range(60):
        sim.step()

    metrics = sim.metrics.get_summary()

    # Confirms tasks were assigned and completed
    assert metrics['completed_tasks'] > 0
    # Guarantees zero collisions across all 4 robots over 60 timesteps
    assert metrics['detected_conflicts'] == 0
    assert metrics['collision_rate_percent'] == 0.0

    # Inject obstacle mid-course
    success, msg = sim.inject_obstacle(5, 5)
    assert success is True

    # Advance 20 more steps
    for _ in range(20):
        sim.step()

    metrics_post = sim.metrics.get_summary()
    assert metrics_post['detected_conflicts'] == 0
    assert metrics_post['replan_events'] >= 1
