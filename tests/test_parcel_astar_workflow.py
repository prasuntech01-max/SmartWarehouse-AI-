"""End-to-end functional tests for interactive parcel pickup, A* routing, placement, and telemetry."""

from simulation.engine import WarehouseSimulator
from visualization.threejs_bridge import build_simulation_state, to_json


def test_end_to_end_parcel_pickup_transport_and_placement():
    sim = WarehouseSimulator(num_robots=5, width=15, height=15, seed=42)
    assert len(sim.inventory_manager.parcels) == 30

    # Pick a non-heavy available parcel
    avail = [p for p in sim.inventory_manager.get_available_parcels() if not p.spec.heavy]
    assert len(avail) > 0
    parcel = avail[0]
    assert parcel.rack_slot_id.startswith("RACK-")
    dest = sim.grid.packing_stations[0]
    if dest == parcel.pickup_cell:
        dest = sim.grid.packing_stations[1]

    # Assign to Robot 2 (ATLAS)
    ok, msg = sim.assign_parcel_task(parcel.parcel_id, robot_id=2, destination=dest)
    assert ok, msg
    assert parcel.status == "RESERVED"
    assert parcel.assigned_robot == 2

    # Duplicate claim by Robot 3 must fail
    ok_dup, _ = sim.assign_parcel_task(parcel.parcel_id, robot_id=3, destination=dest)
    assert not ok_dup

    # Real A* telemetry populated
    tlm = sim.get_astar_telemetry()
    assert tlm["nodes_explored"] >= 1
    assert tlm["path_length"] >= 1

    # Advance simulation until Robot 2 completes the full pickup -> transit -> delivery cycle
    saw_carrying = False
    for _ in range(120):
        sim.step()
        if sim.robots[2].carrying_parcel and sim.robots[2].carrying_parcel.parcel_id == parcel.parcel_id:
            saw_carrying = True
            assert parcel.location is None
        if parcel.status == "DELIVERED":
            break

    assert saw_carrying
    assert parcel.status == "DELIVERED"
    assert parcel.location == dest
    assert sim.robots[2].carrying_parcel is None
    assert sim.robots[2].completed_tasks >= 1
    assert sim.inventory_manager.get_stats()["delivered"] >= 1
    assert len(sim.event_log) >= 3

    # Bridge includes top-level paths, astar_stats, and event_log
    state = build_simulation_state(sim)
    assert "paths" in state
    assert "astar_stats" in state
    assert "event_log" in state
    assert len(to_json(state).encode("utf-8")) / 1024.0 < 35.0


def test_heavy_parcel_requires_titan_x_and_estop_blocks():
    sim = WarehouseSimulator(num_robots=5, width=15, height=15, seed=42)
    heavy = [p for p in sim.inventory_manager.get_available_parcels() if p.spec.heavy]
    assert len(heavy) > 0
    hp = heavy[0]

    # Humanoid R2 cannot claim heavy parcel
    ok_r2, reason = sim.assign_parcel_task(hp.parcel_id, robot_id=2)
    assert not ok_r2
    assert "TITAN-X" in reason

    # E-stop blocks assignment
    sim.submit_command(1, "EMERGENCY_STOP")
    ok_estop, _ = sim.assign_parcel_task(hp.parcel_id, robot_id=1)
    assert not ok_estop
