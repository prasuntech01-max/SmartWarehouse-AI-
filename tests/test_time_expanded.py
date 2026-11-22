"""Comprehensive unit tests for Phase 2, Module 4: Time-Expanded State Space."""

import pytest
from warehouse import Warehouse
from core.reservation import ReservationTable
from core.state import (
    Action,
    TimeExpandedState,
    Trajectory,
    TimeExpandedPlanner,
)
from astar import PathNotFoundError


# ==========================================
# 1. STATE & ACTION TRANSITION TESTS
# ==========================================
def test_action_enum_and_deltas():
    assert Action.UP.value == (0, -1)
    assert Action.DOWN.value == (0, 1)
    assert Action.LEFT.value == (-1, 0)
    assert Action.RIGHT.value == (1, 0)
    assert Action.WAIT.value == (0, 0)

    # Valid delta conversions
    assert Action.from_delta(0, -1) == Action.UP
    assert Action.from_delta(0, 1) == Action.DOWN
    assert Action.from_delta(-1, 0) == Action.LEFT
    assert Action.from_delta(1, 0) == Action.RIGHT
    assert Action.from_delta(0, 0) == Action.WAIT

    # Invalid delta conversions (diagonal or teleportation) must raise ValueError
    with pytest.raises(ValueError):
        Action.from_delta(1, 1)
    with pytest.raises(ValueError):
        Action.from_delta(2, 0)


def test_time_expanded_state_transition():
    s0 = TimeExpandedState(x=2, y=3, t=0)
    assert s0.pos == (2, 3)
    assert s0.as_tuple == (2, 3, 0)

    # Apply actions
    s_up = s0.transition(Action.UP)
    assert s_up == TimeExpandedState(x=2, y=2, t=1)

    s_down = s0.transition(Action.DOWN)
    assert s_down == TimeExpandedState(x=2, y=4, t=1)

    s_left = s0.transition(Action.LEFT)
    assert s_left == TimeExpandedState(x=1, y=3, t=1)

    s_right = s0.transition(Action.RIGHT)
    assert s_right == TimeExpandedState(x=3, y=3, t=1)

    s_wait = s0.transition(Action.WAIT)
    assert s_wait == TimeExpandedState(x=2, y=3, t=1)


def test_transition_validation():
    s0 = TimeExpandedState(x=5, y=5, t=10)

    # Valid successor: single step, t -> t + 1
    s_valid_step = TimeExpandedState(x=5, y=6, t=11)
    assert s0.is_valid_successor(s_valid_step) is True

    # Valid successor: wait in place, t -> t + 1
    s_valid_wait = TimeExpandedState(x=5, y=5, t=11)
    assert s0.is_valid_successor(s_valid_wait) is True

    # Invalid: time didn't increment by 1
    s_bad_time = TimeExpandedState(x=5, y=6, t=12)
    assert s0.is_valid_successor(s_bad_time) is False

    s_reverse_time = TimeExpandedState(x=5, y=6, t=9)
    assert s0.is_valid_successor(s_reverse_time) is False

    # Invalid: diagonal step
    s_diagonal = TimeExpandedState(x=6, y=6, t=11)
    assert s0.is_valid_successor(s_diagonal) is False

    # Invalid: jump > 1 cell
    s_jump = TimeExpandedState(x=5, y=8, t=11)
    assert s0.is_valid_successor(s_jump) is False


# ==========================================
# 2. TIME-BASED PLANNING & WAITING TESTS
# ==========================================
def test_time_expanded_planning_basic():
    wh = Warehouse(15, 15)
    planner = TimeExpandedPlanner(wh)

    start = (1, 0)
    goal = (1, 3)
    traj = planner.plan(start=start, goal=goal, start_time=5)

    assert traj is not None
    assert isinstance(traj, Trajectory)
    assert len(traj) == 4
    assert traj[0] == start
    assert traj[-1] == goal
    assert traj.makespan == 3
    assert traj.states[0].t == 5
    assert traj.states[-1].t == 8
    assert all(a == Action.DOWN for a in traj.actions)


def test_wait_action_when_movement_temporarily_blocked():
    wh = Warehouse(15, 15)
    res_table = ReservationTable()
    planner = TimeExpandedPlanner(wh, res_table)

    start = (1, 0)
    goal = (1, 2)

    # Robot 99 blocks (1, 1) only at t=1
    res_table.reserve_vertex(1, 1, t=1, robot_id=99)

    traj = planner.plan(start=start, goal=goal, start_time=0, robot_id=1)
    assert traj is not None
    assert traj[0] == start
    assert traj[-1] == goal

    # Verify Robot 1 did not step into (1, 1) at t=1
    assert traj.states[1].pos != (1, 1)

    # Verify actions contain wait or detour
    assert len(traj.actions) >= 2


def test_wait_in_narrow_aisle_until_clear():
    # Build a 1-cell corridor where detour is impossible:
    # 5x3 warehouse, with shelves blocking top and bottom rows except aisle at y=1
    wh = Warehouse(5, 3, auto_layout=False)
    # Block y=0 and y=2
    for x in range(5):
        wh.obstacles.add_shelf(x, 0)
        wh.obstacles.add_shelf(x, 2)

    res_table = ReservationTable()
    planner = TimeExpandedPlanner(wh, res_table)

    start = (0, 1)
    goal = (4, 1)

    # Robot 9 blocks (1, 1) at t=1 and t=2, then clears
    res_table.reserve_vertex(1, 1, t=1, robot_id=9)
    res_table.reserve_vertex(1, 1, t=2, robot_id=9)

    traj = planner.plan(start=start, goal=goal, start_time=0, robot_id=1)
    assert traj is not None
    # Robot MUST wait at (0, 1) for t=0, t=1, t=2 because detour is physically impossible
    assert traj.states[0].pos == (0, 1) and traj.states[0].t == 0
    assert traj.states[1].pos == (0, 1) and traj.states[1].t == 1
    assert traj.states[2].pos == (0, 1) and traj.states[2].t == 2
    # At t=3, it steps into (1, 1)
    assert traj.states[3].pos == (1, 1) and traj.states[3].t == 3
    assert traj.wait_count >= 2


def test_edge_swap_collision_prevention_via_wait():
    wh = Warehouse(5, 3, auto_layout=False)
    for x in range(5):
        wh.obstacles.add_shelf(x, 0)
        wh.obstacles.add_shelf(x, 2)

    res_table = ReservationTable()
    planner = TimeExpandedPlanner(wh, res_table)

    # Robot 2 is traversing (1, 1) -> (0, 1) at t=0
    res_table.reserve_edge((1, 1), (0, 1), t=0, robot_id=2)
    res_table.reserve_vertex(0, 1, t=1, robot_id=2)

    # Robot 1 wants to go from (0, 1) to (4, 1) starting at t=0
    traj = planner.plan(start=(0, 1), goal=(4, 1), start_time=0, robot_id=1)
    # Head-on swap is prevented; Robot 1 cannot move (0, 1) -> (1, 1) at t=0
    if traj is not None:
        assert traj.states[1].pos != (1, 1)


# ==========================================
# 3. BOUNDARY & OBSTACLE ENFORCEMENT
# ==========================================
def test_respect_boundaries():
    wh = Warehouse(15, 15)
    planner = TimeExpandedPlanner(wh)

    # Out of bounds start/goal must raise ValueError
    with pytest.raises(ValueError, match="out of bounds"):
        planner.plan(start=(-1, 0), goal=(5, 5))

    with pytest.raises(ValueError, match="out of bounds"):
        planner.plan(start=(0, 0), goal=(15, 5))

    # Transitions near border never produce out-of-bounds states
    border_state = TimeExpandedState(0, 0, 0)
    valid_transitions = planner.get_valid_transitions(border_state)
    for action, n_state in valid_transitions:
        assert wh.in_bounds(n_state.x, n_state.y)


def test_respect_static_and_dynamic_obstacles():
    wh = Warehouse(15, 15)
    planner = TimeExpandedPlanner(wh)

    # Static shelf start/goal raises ValueError
    shelf_pos = next(iter(wh.shelves))
    with pytest.raises(ValueError, match="blocked"):
        planner.plan(start=shelf_pos, goal=(0, 0))

    with pytest.raises(ValueError, match="blocked"):
        planner.plan(start=(0, 0), goal=shelf_pos)

    # Dynamic obstacle avoidance
    wh.add_dynamic_obstacle(1, 1)
    traj = planner.plan(start=(1, 0), goal=(1, 2))
    assert traj is not None
    for coord in traj:
        assert coord != (1, 1)


# ==========================================
# 4. UNREACHABLE GOALS & EDGE CASES
# ==========================================
def test_unreachable_goal():
    # Enclosed warehouse cell
    wh = Warehouse(3, 3, auto_layout=False)
    # Box around (2, 2)
    wh.obstacles.add_shelf(1, 2)
    wh.obstacles.add_shelf(2, 1)

    planner = TimeExpandedPlanner(wh)
    # Return None by default
    assert planner.plan(start=(0, 0), goal=(2, 2), raise_on_failure=False) is None

    # Raise PathNotFoundError when requested
    with pytest.raises(PathNotFoundError):
        planner.plan(start=(0, 0), goal=(2, 2), raise_on_failure=True)


def test_start_equals_goal():
    wh = Warehouse(15, 15)
    planner = TimeExpandedPlanner(wh)

    traj = planner.plan(start=(5, 5), goal=(5, 5), start_time=12)
    assert traj is not None
    assert len(traj) == 1
    assert traj[0] == (5, 5)
    assert traj.makespan == 0
    assert traj.states[0].t == 12
    assert len(traj.actions) == 0


def test_trajectory_compatibility():
    s0 = TimeExpandedState(1, 1, 0)
    s1 = TimeExpandedState(1, 2, 1)
    s2 = TimeExpandedState(2, 2, 2)
    traj = Trajectory([s0, s1, s2])

    # Indexing
    assert traj[0] == (1, 1)
    assert traj[1] == (1, 2)
    assert traj[-1] == (2, 2)

    # Slicing
    assert traj[0:2] == [(1, 1), (1, 2)]

    # Equality with list
    assert traj == [(1, 1), (1, 2), (2, 2)]

    # Actions deduced
    assert traj.actions == [Action.DOWN, Action.RIGHT]
    assert traj.makespan == 2
    assert traj.wait_count == 0
