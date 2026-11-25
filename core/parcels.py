"""Parcel and Inventory domain model for SmartWarehouse AI.

Implements a typed parcel lifecycle with strict state machine enforcement,
inventory tracking, and integration hooks for the robot task engine.

Phase 2 deliverable: additive module, does not modify existing code.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Parcel Type Enumeration
# ---------------------------------------------------------------------------

class ParcelType(str, Enum):
    """Physical parcel categories with distinct handling requirements."""
    SMALL_BOX = "small_box"
    MEDIUM_CARTON = "medium_carton"
    LARGE_CARTON = "large_carton"
    WOODEN_PALLET = "wooden_pallet"
    PLASTIC_CONTAINER = "plastic_container"
    COURIER_PACKAGE = "courier_package"
    FRAGILE = "fragile"
    HEAVY_INDUSTRIAL = "heavy_industrial"
    TOTE_BLUE = "tote_blue"
    TOTE_GREY = "tote_grey"


class ParcelPriority(IntEnum):
    """Delivery urgency levels."""
    NORMAL = 1
    EXPRESS = 2


class ParcelStatus(str, Enum):
    """Parcel lifecycle states (enforced state machine)."""
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# State Machine Transitions
# ---------------------------------------------------------------------------

PARCEL_TRANSITIONS: Dict[str, List[str]] = {
    "AVAILABLE":  ["RESERVED"],
    "RESERVED":   ["PICKED_UP", "AVAILABLE"],  # cancel/timeout -> AVAILABLE
    "PICKED_UP":  ["IN_TRANSIT"],
    "IN_TRANSIT":  ["DELIVERED"],
    "DELIVERED":  [],  # terminal
    "FAILED":     [],  # terminal
    "CANCELLED":  [],  # terminal
}

# States that can transition to FAILED or CANCELLED
_FAIL_CANCEL_ELIGIBLE = {"AVAILABLE", "RESERVED", "PICKED_UP", "IN_TRANSIT"}


class ParcelTransitionError(Exception):
    """Raised when an illegal parcel state transition is attempted."""
    pass


class ParcelInvariantError(Exception):
    """Raised when a parcel invariant is violated (e.g. double reservation)."""
    pass


# ---------------------------------------------------------------------------
# Parcel Type Specifications
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParcelSpec:
    """Physical specifications for a parcel type."""
    length_cm: float
    width_cm: float
    height_cm: float
    weight_kg: float
    fragile: bool = False
    heavy: bool = False


PARCEL_SPECS: Dict[ParcelType, ParcelSpec] = {
    ParcelType.SMALL_BOX:         ParcelSpec(30, 20, 15, 2.0),
    ParcelType.MEDIUM_CARTON:     ParcelSpec(50, 40, 30, 8.0),
    ParcelType.LARGE_CARTON:      ParcelSpec(80, 60, 50, 15.0),
    ParcelType.WOODEN_PALLET:     ParcelSpec(120, 80, 15, 25.0, heavy=True),
    ParcelType.PLASTIC_CONTAINER: ParcelSpec(60, 40, 35, 10.0),
    ParcelType.COURIER_PACKAGE:   ParcelSpec(35, 25, 15, 3.0),
    ParcelType.FRAGILE:           ParcelSpec(40, 30, 25, 5.0, fragile=True),
    ParcelType.HEAVY_INDUSTRIAL:  ParcelSpec(100, 80, 60, 50.0, heavy=True),
    ParcelType.TOTE_BLUE:         ParcelSpec(60, 40, 30, 7.0),
    ParcelType.TOTE_GREY:         ParcelSpec(60, 40, 30, 7.0),
}


# ---------------------------------------------------------------------------
# Parcel Event Log
# ---------------------------------------------------------------------------

@dataclass
class ParcelEvent:
    """Immutable record of a parcel lifecycle event."""
    event_id: int
    parcel_id: str
    tick: int
    from_status: Optional[str]
    to_status: str
    robot_id: Optional[int] = None
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Parcel Object
# ---------------------------------------------------------------------------

@dataclass
class Parcel:
    """A physical parcel in the warehouse with lifecycle tracking."""
    parcel_id: str
    parcel_type: ParcelType
    spec: ParcelSpec
    priority: ParcelPriority = ParcelPriority.NORMAL

    # Location tracking
    location: Optional[Tuple[int, int]] = None  # grid cell or None if carried
    rack_slot_id: Optional[str] = None           # e.g. "A1-L3-S2"
    pickup_cell: Optional[Tuple[int, int]] = None
    destination: Optional[Tuple[int, int]] = None

    # State
    status: str = ParcelStatus.AVAILABLE.value
    assigned_robot: Optional[int] = None
    carrier_robot: Optional[int] = None

    # Timestamps (simulation ticks)
    created_tick: int = 0
    reserved_tick: Optional[int] = None
    picked_up_tick: Optional[int] = None
    delivered_tick: Optional[int] = None
    failure_reason: Optional[str] = None

    def transition_to(self, new_status: str, tick: int,
                      robot_id: Optional[int] = None,
                      reason: str = "") -> ParcelEvent:
        """Execute a validated state transition. Raises ParcelTransitionError on illegal transitions."""
        # Check terminal states
        if self.status in ("DELIVERED", "FAILED", "CANCELLED"):
            raise ParcelTransitionError(
                f"Parcel {self.parcel_id}: cannot transition from terminal state {self.status} to {new_status}"
            )

        # Check FAILED/CANCELLED special transitions
        if new_status in ("FAILED", "CANCELLED"):
            if self.status not in _FAIL_CANCEL_ELIGIBLE:
                raise ParcelTransitionError(
                    f"Parcel {self.parcel_id}: cannot transition from {self.status} to {new_status}"
                )
        else:
            allowed = PARCEL_TRANSITIONS.get(self.status, [])
            if new_status not in allowed:
                raise ParcelTransitionError(
                    f"Parcel {self.parcel_id}: illegal transition {self.status} -> {new_status}. "
                    f"Allowed: {allowed}"
                )

        old_status = self.status
        self.status = new_status

        # Update timestamps
        if new_status == "RESERVED":
            self.reserved_tick = tick
            self.assigned_robot = robot_id
        elif new_status == "PICKED_UP":
            self.picked_up_tick = tick
            self.carrier_robot = robot_id
        elif new_status == "IN_TRANSIT":
            pass  # carrier already set
        elif new_status == "DELIVERED":
            self.delivered_tick = tick
        elif new_status == "AVAILABLE":
            # cancel/timeout resets
            self.assigned_robot = None
            self.reserved_tick = None
        elif new_status in ("FAILED", "CANCELLED"):
            self.failure_reason = reason
            self.assigned_robot = None
            self.carrier_robot = None

        # Return event (caller stores it)
        return ParcelEvent(
            event_id=0,  # assigned by manager
            parcel_id=self.parcel_id,
            tick=tick,
            from_status=old_status,
            to_status=new_status,
            robot_id=robot_id,
            reason=reason,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in ("DELIVERED", "FAILED", "CANCELLED")

    @property
    def is_carriable(self) -> bool:
        return self.status in ("PICKED_UP", "IN_TRANSIT")

    def to_dict(self) -> Dict[str, Any]:
        spec = self.spec
        return {
            "parcel_id": self.parcel_id,
            "type": self.parcel_type.value,
            "priority": self.priority.name,
            "dimensions": f"{spec.length_cm}x{spec.width_cm}x{spec.height_cm}cm",
            "weight_kg": spec.weight_kg,
            "fragile": spec.fragile,
            "heavy": spec.heavy,
            "status": self.status,
            "location": list(self.location) if self.location else None,
            "rack_slot_id": self.rack_slot_id,
            "pickup_cell": list(self.pickup_cell) if self.pickup_cell else None,
            "destination": list(self.destination) if self.destination else None,
            "assigned_robot": self.assigned_robot,
            "carrier_robot": self.carrier_robot,
            "created_tick": self.created_tick,
            "reserved_tick": self.reserved_tick,
            "picked_up_tick": self.picked_up_tick,
            "delivered_tick": self.delivered_tick,
            "failure_reason": self.failure_reason,
        }


# ---------------------------------------------------------------------------
# Inventory Manager
# ---------------------------------------------------------------------------

class InventoryManager:
    """Tracks all parcels, enforces invariants, and maintains event log.

    This is the SINGLE authoritative source for parcel state.
    All parcel operations MUST go through this manager.
    """

    def __init__(self, seed: int = 42):
        self._parcels: Dict[str, Parcel] = {}
        self._events: List[ParcelEvent] = []
        self._event_counter: int = 0
        self._parcel_counter: int = 0
        self._rng = random.Random(seed)
        self._delivery_history: List[Dict[str, Any]] = []

    @property
    def parcels(self) -> Dict[str, Parcel]:
        return self._parcels

    @property
    def events(self) -> List[ParcelEvent]:
        return self._events

    @property
    def delivery_history(self) -> List[Dict[str, Any]]:
        return self._delivery_history

    # -- Parcel creation --

    def _next_parcel_id(self) -> str:
        self._parcel_counter += 1
        return f"PKG-{self._parcel_counter:04d}"

    def create_parcel(
        self,
        parcel_type: ParcelType,
        location: Tuple[int, int],
        pickup_cell: Tuple[int, int],
        destination: Tuple[int, int],
        priority: ParcelPriority = ParcelPriority.NORMAL,
        rack_slot_id: Optional[str] = None,
        tick: int = 0,
    ) -> Parcel:
        """Create and register a new parcel. Returns the created parcel."""
        pid = self._next_parcel_id()
        spec = PARCEL_SPECS[parcel_type]
        parcel = Parcel(
            parcel_id=pid,
            parcel_type=parcel_type,
            spec=spec,
            priority=priority,
            location=location,
            rack_slot_id=rack_slot_id,
            pickup_cell=pickup_cell,
            destination=destination,
            status=ParcelStatus.AVAILABLE.value,
            created_tick=tick,
        )
        self._parcels[pid] = parcel
        self._record_event(ParcelEvent(
            event_id=0, parcel_id=pid, tick=tick,
            from_status=None, to_status="AVAILABLE",
            reason="Parcel created",
        ))
        return parcel

    # -- State transitions (all go through here) --

    def _record_event(self, event: ParcelEvent) -> ParcelEvent:
        self._event_counter += 1
        event.event_id = self._event_counter
        self._events.append(event)
        return event

    def reserve_parcel(self, parcel_id: str, robot_id: int, tick: int) -> ParcelEvent:
        """Reserve a parcel for a robot. Raises if already reserved or unavailable."""
        parcel = self._get_parcel(parcel_id)

        # Invariant: no two robots can reserve the same parcel
        if parcel.status == "RESERVED" and parcel.assigned_robot != robot_id:
            raise ParcelInvariantError(
                f"Parcel {parcel_id} already reserved by robot {parcel.assigned_robot}"
            )
        if parcel.status != "AVAILABLE":
            raise ParcelInvariantError(
                f"Parcel {parcel_id} is {parcel.status}, cannot reserve (must be AVAILABLE)"
            )

        event = parcel.transition_to("RESERVED", tick, robot_id=robot_id, reason=f"Reserved by robot {robot_id}")
        return self._record_event(event)

    def cancel_reservation(self, parcel_id: str, tick: int, reason: str = "Reservation cancelled") -> ParcelEvent:
        """Cancel a reservation, returning parcel to AVAILABLE."""
        parcel = self._get_parcel(parcel_id)
        if parcel.status != "RESERVED":
            raise ParcelTransitionError(
                f"Parcel {parcel_id} is {parcel.status}, cannot cancel reservation (must be RESERVED)"
            )
        event = parcel.transition_to("AVAILABLE", tick, reason=reason)
        return self._record_event(event)

    def pickup_parcel(self, parcel_id: str, robot_id: int, tick: int) -> ParcelEvent:
        """Robot picks up a parcel. Validates reservation ownership."""
        parcel = self._get_parcel(parcel_id)

        if parcel.status == "AVAILABLE":
            # Allow direct pickup without prior reservation
            pass
        elif parcel.status == "RESERVED":
            if parcel.assigned_robot != robot_id:
                raise ParcelInvariantError(
                    f"Parcel {parcel_id} reserved by robot {parcel.assigned_robot}, "
                    f"not by robot {robot_id}"
                )
        else:
            raise ParcelTransitionError(
                f"Parcel {parcel_id} is {parcel.status}, cannot pick up"
            )

        # If AVAILABLE, need to transition through RESERVED first
        if parcel.status == "AVAILABLE":
            self.reserve_parcel(parcel_id, robot_id, tick)

        event = parcel.transition_to("PICKED_UP", tick, robot_id=robot_id,
                                      reason=f"Picked up by robot {robot_id}")
        parcel.location = None  # now carried
        return self._record_event(event)

    def begin_transit(self, parcel_id: str, robot_id: int, tick: int) -> ParcelEvent:
        """Transition parcel to IN_TRANSIT (robot moving to destination)."""
        parcel = self._get_parcel(parcel_id)
        if parcel.carrier_robot != robot_id:
            raise ParcelInvariantError(
                f"Parcel {parcel_id} carried by robot {parcel.carrier_robot}, not {robot_id}"
            )
        event = parcel.transition_to("IN_TRANSIT", tick, robot_id=robot_id,
                                      reason=f"In transit with robot {robot_id}")
        return self._record_event(event)

    def deliver_parcel(self, parcel_id: str, robot_id: int, tick: int,
                       destination_cell: Tuple[int, int]) -> ParcelEvent:
        """Complete delivery. Validates carrier and sets final location."""
        parcel = self._get_parcel(parcel_id)
        if parcel.status != "IN_TRANSIT":
            raise ParcelTransitionError(
                f"Parcel {parcel_id} is {parcel.status}, must be IN_TRANSIT to deliver"
            )
        if parcel.carrier_robot != robot_id:
            raise ParcelInvariantError(
                f"Parcel {parcel_id} carried by robot {parcel.carrier_robot}, not {robot_id}"
            )

        event = parcel.transition_to("DELIVERED", tick, robot_id=robot_id,
                                      reason=f"Delivered by robot {robot_id} at {destination_cell}")
        parcel.location = destination_cell
        parcel.carrier_robot = None

        # Record delivery history
        self._delivery_history.append({
            "parcel_id": parcel_id,
            "type": parcel.parcel_type.value,
            "robot_id": robot_id,
            "pickup_cell": parcel.pickup_cell,
            "destination": destination_cell,
            "created_tick": parcel.created_tick,
            "delivered_tick": tick,
            "duration_ticks": tick - parcel.created_tick,
            "priority": parcel.priority.name,
        })
        return self._record_event(event)

    def fail_parcel(self, parcel_id: str, tick: int, reason: str,
                    safe_drop_cell: Optional[Tuple[int, int]] = None) -> ParcelEvent:
        """Mark a parcel as failed with reason. Optionally sets drop location."""
        parcel = self._get_parcel(parcel_id)
        event = parcel.transition_to("FAILED", tick, reason=reason)
        if safe_drop_cell:
            parcel.location = safe_drop_cell
        parcel.carrier_robot = None
        parcel.assigned_robot = None
        return self._record_event(event)

    def cancel_parcel(self, parcel_id: str, tick: int, reason: str = "Cancelled") -> ParcelEvent:
        """Cancel a parcel."""
        parcel = self._get_parcel(parcel_id)
        event = parcel.transition_to("CANCELLED", tick, reason=reason)
        parcel.carrier_robot = None
        parcel.assigned_robot = None
        return self._record_event(event)

    # -- Query methods --

    def _get_parcel(self, parcel_id: str) -> Parcel:
        if parcel_id not in self._parcels:
            raise KeyError(f"Parcel {parcel_id} not found")
        return self._parcels[parcel_id]

    def get_available_parcels(self) -> List[Parcel]:
        """Get all parcels that can be assigned to a robot."""
        return [p for p in self._parcels.values() if p.status == "AVAILABLE"]

    def get_parcels_by_status(self, status: str) -> List[Parcel]:
        return [p for p in self._parcels.values() if p.status == status]

    def get_parcels_by_type(self, parcel_type: ParcelType) -> List[Parcel]:
        return [p for p in self._parcels.values() if p.parcel_type == parcel_type]

    def get_parcel_by_id(self, parcel_id: str) -> Optional[Parcel]:
        return self._parcels.get(parcel_id)

    def get_carried_parcel(self, robot_id: int) -> Optional[Parcel]:
        """Get the parcel currently carried by a robot (if any)."""
        for p in self._parcels.values():
            if p.carrier_robot == robot_id and p.is_carriable:
                return p
        return None

    def get_reserved_parcel(self, robot_id: int) -> Optional[Parcel]:
        """Get the parcel reserved by a robot (if any)."""
        for p in self._parcels.values():
            if p.assigned_robot == robot_id and p.status == "RESERVED":
                return p
        return None

    # -- Inventory counts --

    def get_counts_by_status(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for p in self._parcels.values():
            counts[p.status] = counts.get(p.status, 0) + 1
        return counts

    def get_counts_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for p in self._parcels.values():
            counts[p.parcel_type.value] = counts.get(p.parcel_type.value, 0) + 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        """Comprehensive inventory statistics."""
        total = len(self._parcels)
        status_counts = self.get_counts_by_status()
        delivered = status_counts.get("DELIVERED", 0)
        failed = status_counts.get("FAILED", 0)
        cancelled = status_counts.get("CANCELLED", 0)
        active = total - delivered - failed - cancelled

        return {
            "total_parcels": total,
            "active": active,
            "delivered": delivered,
            "failed": failed,
            "cancelled": cancelled,
            "by_status": status_counts,
            "by_type": self.get_counts_by_type(),
            "delivery_count": len(self._delivery_history),
            "success_rate": (delivered / max(delivered + failed, 1)) * 100,
        }

    # -- Scenario seeding --

    def seed_inventory(
        self,
        grid,  # WarehouseGrid
        count: int = 20,
        tick: int = 0,
    ) -> List[Parcel]:
        """Seed deterministic initial inventory on the warehouse grid.

        Places parcels at accessible shelf locations with delivery destinations
        at packing/dispatch stations.
        """
        created: List[Parcel] = []
        accessible = grid.get_accessible_shelf_locations()
        destinations = list(grid.packing_stations)

        if not accessible or not destinations:
            return created

        types = list(ParcelType)

        for i in range(count):
            ptype = self._rng.choice(types)
            pickup = accessible[i % len(accessible)]
            dest = destinations[i % len(destinations)]
            # Find a shelf adjacent to pickup and format structured rack/level ID
            location = pickup
            rack_zone = "A" if pickup[0] < 5 else ("B" if pickup[0] < 9 else "C")
            rack_num = (i % 6) + 1
            level_num = (i % 4) + 1
            priority = ParcelPriority.EXPRESS if self._rng.random() < 0.2 else ParcelPriority.NORMAL
            rack_id = f"RACK-{rack_zone}{rack_num:02d}-L{level_num}"

            parcel = self.create_parcel(
                parcel_type=ptype,
                location=location,
                pickup_cell=pickup,
                destination=dest,
                priority=priority,
                rack_slot_id=rack_id,
                tick=tick,
            )
            created.append(parcel)

        return created

    def to_bridge_payload(self) -> List[Dict[str, Any]]:
        """Serialize all parcels for the Three.js bridge."""
        return [p.to_dict() for p in self._parcels.values()]

    def get_events_since(self, since_event_id: int = 0) -> List[Dict[str, Any]]:
        """Get events after a given event ID for incremental sync."""
        result = []
        for e in self._events:
            if e.event_id > since_event_id:
                result.append({
                    "event_id": e.event_id,
                    "parcel_id": e.parcel_id,
                    "tick": e.tick,
                    "from_status": e.from_status,
                    "to_status": e.to_status,
                    "robot_id": e.robot_id,
                    "reason": e.reason,
                })
        return result
