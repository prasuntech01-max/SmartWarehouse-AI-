"""Unit and integration tests for Parcels, Inventory Manager, and Robot Command Interface."""

import pytest
from core.grid import WarehouseGrid
from core.parcels import (
    Parcel, ParcelType, ParcelStatus, ParcelPriority,
    InventoryManager, ParcelTransitionError, ParcelInvariantError,
    PARCEL_SPECS
)
from core.commands import CommandType, CommandResult
from simulation.engine import WarehouseSimulator


class TestParcelLifecycle:
    def test_parcel_creation_and_specs(self):
        inv = InventoryManager(seed=42)
        p = inv.create_parcel(
            parcel_type=ParcelType.SMALL_BOX,
            location=(2, 3),
            pickup_cell=(2, 3),
            destination=(2, 14),
            priority=ParcelPriority.NORMAL,
        )
        assert p.parcel_id == "PKG-0001"
        assert p.status == "AVAILABLE"
        assert p.spec.weight_kg == 2.0
        assert not p.spec.heavy
        assert not p.spec.fragile

    def test_state_machine_valid_transitions(self):
        inv = InventoryManager(seed=42)
        p = inv.create_parcel(ParcelType.MEDIUM_CARTON, (2, 3), (2, 3), (2, 14))

        # AVAILABLE -> RESERVED
        ev1 = inv.reserve_parcel(p.parcel_id, robot_id=1, tick=5)
        assert p.status == "RESERVED"
        assert p.assigned_robot == 1

        # RESERVED -> PICKED_UP
        ev2 = inv.pickup_parcel(p.parcel_id, robot_id=1, tick=6)
        assert p.status == "PICKED_UP"
        assert p.carrier_robot == 1
        assert p.location is None

        # PICKED_UP -> IN_TRANSIT
        ev3 = inv.begin_transit(p.parcel_id, robot_id=1, tick=7)
        assert p.status == "IN_TRANSIT"

        # IN_TRANSIT -> DELIVERED
        ev4 = inv.deliver_parcel(p.parcel_id, robot_id=1, tick=12, destination_cell=(2, 14))
        assert p.status == "DELIVERED"
        assert p.location == (2, 14)
        assert p.carrier_robot is None
        assert len(inv.delivery_history) == 1

    def test_state_machine_illegal_transition_raises(self):
        inv = InventoryManager(seed=42)
        p = inv.create_parcel(ParcelType.SMALL_BOX, (2, 3), (2, 3), (2, 14))

        # Cannot jump from AVAILABLE directly to DELIVERED
        with pytest.raises(ParcelTransitionError):
            p.transition_to("DELIVERED", tick=1)

    def test_double_reservation_prevention(self):
        inv = InventoryManager(seed=42)
        p = inv.create_parcel(ParcelType.SMALL_BOX, (2, 3), (2, 3), (2, 14))
        inv.reserve_parcel(p.parcel_id, robot_id=1, tick=1)

        # Robot 2 tries to reserve the same parcel
        with pytest.raises(ParcelInvariantError):
            inv.reserve_parcel(p.parcel_id, robot_id=2, tick=2)

    def test_wrong_carrier_pickup_prevention(self):
        inv = InventoryManager(seed=42)
        p = inv.create_parcel(ParcelType.SMALL_BOX, (2, 3), (2, 3), (2, 14))
        inv.reserve_parcel(p.parcel_id, robot_id=1, tick=1)

        # Robot 2 tries to pick up Robot 1's reserved parcel
        with pytest.raises(ParcelInvariantError):
            inv.pickup_parcel(p.parcel_id, robot_id=2, tick=2)

    def test_inventory_counts_and_stats(self):
        grid = WarehouseGrid(width=15, height=15)
        inv = InventoryManager(seed=42)
        seeded = inv.seed_inventory(grid, count=10)
        assert len(seeded) == 10
        stats = inv.get_stats()
        assert stats["total_parcels"] == 10
        assert stats["active"] == 10
        assert stats["delivered"] == 0


class TestManualModeCommands:
    def test_set_mode_and_exclusion_from_auto_dispatch(self):
        sim = WarehouseSimulator(num_robots=3, width=15, height=15)
        # Put Robot 1 into MANUAL mode
        res = sim.submit_command(1, CommandType.SET_MODE, {"mode": "MANUAL"})
        assert res.ok
        assert sim.robots[1].mode == "MANUAL"

        # Step simulator — Robot 1 must remain IDLE (not assigned automatically)
        sim.step()
        assert sim.robots[1].state == "IDLE"
        assert sim.robots[1].assigned_task is None

    def test_turn_left_right(self):
        sim = WarehouseSimulator(num_robots=1, width=15, height=15)
        res_r = sim.submit_command(1, CommandType.TURN_RIGHT)
        assert res_r.ok
        assert round(sim.robots[1].heading, 2) == round(1.57, 2)  # pi/2

        res_l = sim.submit_command(1, CommandType.TURN_LEFT)
        assert res_l.ok
        assert round(sim.robots[1].heading, 2) == 0.0

    def test_move_forward_safety_interlocks(self):
        sim = WarehouseSimulator(num_robots=2, width=15, height=15)
        # Robot 1 starts at dock (1, 0)
        # Turn heading to face south (+Y, 90 deg)
        sim.submit_command(1, CommandType.TURN_RIGHT)

        # Move forward from (1, 0) to (1, 1) — walkable aisle
        res = sim.submit_command(1, CommandType.MOVE_FORWARD)
        assert res.ok
        assert sim.robots[1].pos == (1, 1)

    def test_move_into_shelf_rejected(self):
        sim = WarehouseSimulator(num_robots=1, width=15, height=15)
        # Dock (1,0) -> move to (1, 3) adjacent to shelf block at (2, 3)
        sim.robots[1].pos = (1, 3)
        # Heading 0 deg = +X (towards shelf at 2, 3)
        sim.robots[1].heading = 0.0

        res = sim.submit_command(1, CommandType.MOVE_FORWARD)
        assert not res.ok
        assert "blocked by high-bay storage racks" in res.reason
        assert sim.robots[1].pos == (1, 3)  # Did not move!

    def test_move_out_of_bounds_rejected(self):
        sim = WarehouseSimulator(num_robots=1, width=15, height=15)
        sim.robots[1].pos = (0, 0)
        # Heading 180 deg = -X (towards -1, 0)
        import math
        sim.robots[1].heading = math.pi

        res = sim.submit_command(1, CommandType.MOVE_FORWARD)
        assert not res.ok
        assert "outside warehouse perimeter" in res.reason

    def test_move_into_other_robot_rejected(self):
        sim = WarehouseSimulator(num_robots=2, width=15, height=15)
        # (4, 1) and (5, 1) are walkable aisle cells
        sim.robots[1].pos = (4, 1)
        sim.robots[2].pos = (5, 1)
        sim.robots[1].heading = 0.0  # +X towards Robot 2 at (5, 1)

        res = sim.submit_command(1, CommandType.MOVE_FORWARD)
        assert not res.ok
        assert "Collision hazard" in res.reason
        assert sim.robots[1].pos == (4, 1)

    def test_goto_cell_with_real_astar(self):
        sim = WarehouseSimulator(num_robots=1, width=15, height=15)
        start_pos = sim.robots[1].pos
        res = sim.submit_command(1, CommandType.GOTO_CELL, {"target": (2, 14)})
        assert res.ok
        assert len(sim.robots[1].path) > 1
        assert sim.robots[1].goal == (2, 14)
        assert sim.robots[1].state == "MOVING_TO_PICK"

    def test_pickup_capacity_rule(self):
        sim = WarehouseSimulator(num_robots=2, width=15, height=15)
        # Create a heavy industrial pallet
        heavy_parcel = sim.inventory_manager.create_parcel(
            parcel_type=ParcelType.WOODEN_PALLET,
            location=(5, 5),
            pickup_cell=(5, 5),
            destination=(2, 14),
        )
        sim.robots[2].pos = (5, 5)  # Humanoid Robot 2 (ATLAS)

        # Humanoid attempts to pick heavy pallet -> REJECTED
        res_humanoid = sim.submit_command(2, CommandType.PICKUP, {"parcel_id": heavy_parcel.parcel_id})
        assert not res_humanoid.ok
        assert "Capacity rule violation" in res_humanoid.reason

        # Heavy AMR TITAN-X (Robot 1) attempts to pick heavy pallet -> ACCEPTED
        sim.robots[1].pos = (5, 5)
        res_amr = sim.submit_command(1, CommandType.PICKUP, {"parcel_id": heavy_parcel.parcel_id})
        assert res_amr.ok
        assert sim.robots[1].carrying_parcel == heavy_parcel
        assert sim.robots[1].state == "CARRYING"

    def test_drop_and_inventory_delivery(self):
        sim = WarehouseSimulator(num_robots=1, width=15, height=15)
        parcel = sim.inventory_manager.create_parcel(
            parcel_type=ParcelType.SMALL_BOX,
            location=(1, 1),
            pickup_cell=(1, 1),
            destination=(2, 14),
        )
        sim.robots[1].pos = (1, 1)
        sim.submit_command(1, CommandType.PICKUP, {"parcel_id": parcel.parcel_id})
        assert sim.robots[1].carrying_parcel is not None

        # Drop at packing station (2, 14)
        sim.robots[1].pos = (2, 14)
        res_drop = sim.submit_command(1, CommandType.DROP)
        assert res_drop.ok
        assert sim.robots[1].carrying_parcel is None
        assert parcel.status == "DELIVERED"
        assert parcel.location == (2, 14)

    def test_emergency_stop_blocks_commands(self):
        sim = WarehouseSimulator(num_robots=1, width=15, height=15)
        # Engage E-Stop
        res_stop = sim.submit_command(1, CommandType.EMERGENCY_STOP)
        assert res_stop.ok
        assert sim.robots[1].e_stopped
        assert sim.robots[1].state == "E_STOPPED"

        # Movement command while in E-stop must be rejected
        res_move = sim.submit_command(1, CommandType.MOVE_FORWARD)
        assert not res_move.ok
        assert "EMERGENCY STOP" in res_move.reason

        # Resume allows operations again
        res_resume = sim.submit_command(1, CommandType.RESUME)
        assert res_resume.ok
        assert not sim.robots[1].e_stopped
