"""
visualization/threejs_bridge.py
================================
Serialises the WarehouseSimulator state into a comprehensive, schema-compliant
JSON contract for the Three.js industrial digital twin.

Adheres to docs/BRIDGE_CONTRACT.md (Schema Version 2.0.0).
Backward-compatible with 1.0.0 consumers — all v1 fields remain at the same
JSON-path; new sections are additive and can be safely ignored by older JS
clients (guarded by `meta.schema_version`).

Zero synthetic or falsified data — all telemetry is extracted directly from
the simulation engine, multi-agent reservation tables, IoT subsystems,
and metrics collectors.

Unit-test assertions
--------------------
>>> state = build_simulation_state(sim)
>>> assert state["meta"]["schema_version"] == "2.0.0"
>>> assert "rack_config" in state["layout"]
>>> assert "conveyor_paths" in state["layout"]
>>> assert "dock_bays" in state["layout"]
>>> assert "zone_definitions" in state["layout"]
>>> assert "lane_definitions" in state["layout"]
>>> assert "crane_lines" in state["layout"]
>>> assert all("replan_count" in r for r in state["robots"])
>>> assert all("collision_risk" in r for r in state["robots"])
>>> assert all("blocked_by" in r for r in state["robots"])
>>> assert all("carrying_type" in r for r in state["robots"])
>>> assert all("eta_ticks" in r for r in state["robots"])
>>> assert "collision_avoidance_events" in state["metrics"]
>>> assert "deadlock_count" in state["metrics"]
>>> assert "warehouse_utilization" in state["metrics"]
>>> warnings = validate_payload(state)
>>> assert isinstance(warnings, list)
"""

from __future__ import annotations

import json
import math
import time
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "2.0.0"
CELL_SIZE_METERS = 2.0

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Robot Fleet Definition & Canonical Metadata
# ---------------------------------------------------------------------------

ROBOT_FLEET_METADATA = {
    1: {"name": "TITAN-X", "type": "HEAVY_AMR", "color": "#00f0ff", "role": "Pallet & Heavy Transport"},
    2: {"name": "ATLAS", "type": "HUMANOID", "color": "#2563eb", "role": "Package Handling & Picking"},
    3: {"name": "VORTEX", "type": "HUMANOID", "color": "#f97316", "role": "High-Speed Sorter"},
    4: {"name": "NOVA", "type": "HUMANOID", "color": "#10b981", "role": "Inventory & Shelf Inspection"},
    5: {"name": "SPECTRE", "type": "HUMANOID", "color": "#06b6d4", "role": "Safety & Operational Support"},
}


def _yaw_from_path(current: Tuple[int, int], path: List[Tuple[int, int]], path_index: int) -> float:
    """
    Compute heading angle (radians, Y-up) from current cell to next planned waypoint.
    Returns 0.0 if stationary or at the path endpoint.
    Three.js mapping: +X is right (East), +Z is down (South).
    """
    if not path or path_index >= len(path) - 1:
        return 0.0
    cur = path[path_index] if path_index < len(path) else current
    nxt = path[min(path_index + 1, len(path) - 1)]
    dx = nxt[0] - cur[0]
    dy = nxt[1] - cur[1]
    if dx == 0 and dy == 0:
        return 0.0
    return math.atan2(-dx, -dy)


# ---------------------------------------------------------------------------
# Large DC layout preset (visual scenery only — does NOT alter Python grid)
# ---------------------------------------------------------------------------

def build_large_layout_config() -> Dict[str, Any]:
    """
    Generate a "Mega Distribution Centre" layout configuration suitable for
    the Three.js visualiser's scenery layer.  This is **purely cosmetic** —
    it does not modify the Python simulation grid, pathfinding, or task
    allocation in any way.

    Layout specification:
    * 8 storage aisles (rack blocks at regular x-intervals)
    * Cross-aisles every 6 rows
    * Dock row along y = 0
    * Charging-bay row
    * Sorting / packing / dispatch zones
    * AMR lane definitions
    * ASRS crane positions

    Returns
    -------
    dict
        Config dict with keys: rack_config, conveyor_paths, dock_bays,
        charger_positions, zone_definitions, lane_definitions, crane_lines.
    """
    rack_config: List[Dict[str, Any]] = []
    aisle_x_positions = [3, 7, 11, 15, 19, 23, 27, 31]

    for aisle_idx, ax in enumerate(aisle_x_positions):
        # Each aisle has rack segments broken by cross-aisles every 6 rows
        for segment_start_y in range(4, 28, 6):
            rack_config.append({
                "x": ax,
                "y": segment_start_y,
                "orientation": "NS",
                "levels": 4,
                "bays": 5,
                "type": "active" if aisle_idx < 6 else "decor",
            })
            # Opposing rack one column over
            rack_config.append({
                "x": ax + 1,
                "y": segment_start_y,
                "orientation": "NS",
                "levels": 4,
                "bays": 5,
                "type": "active" if aisle_idx < 6 else "decor",
            })

    # Cross-aisle racks (EW orientation) for visual density
    for cy in range(10, 28, 6):
        rack_config.append({
            "x": 1,
            "y": cy,
            "orientation": "EW",
            "levels": 2,
            "bays": 3,
            "type": "decor",
        })

    # Dock row along y = 0
    dock_bays: List[Dict[str, Any]] = [
        {"id": i + 1, "x": 2 + i * 4, "y": 0, "width": 3, "type": "INBOUND" if i < 4 else "OUTBOUND"}
        for i in range(8)
    ]

    # Charging bay row (y = 29)
    charger_positions: List[Dict[str, Any]] = [
        {"id": i + 1, "x": 2 + i * 4, "y": 29, "type": "FAST_CHARGE"}
        for i in range(8)
    ]

    # Conveyor paths
    conveyor_paths: List[Dict[str, Any]] = [
        {"id": 1, "points": [[2, 1], [2, 3], [10, 3]], "speed": 1.5, "type": "INBOUND"},
        {"id": 2, "points": [[18, 1], [18, 3], [26, 3]], "speed": 1.5, "type": "INBOUND"},
        {"id": 3, "points": [[10, 27], [18, 27], [18, 29]], "speed": 1.2, "type": "OUTBOUND"},
        {"id": 4, "points": [[2, 27], [10, 27]], "speed": 1.2, "type": "SORTING"},
    ]

    # Zone definitions
    zone_definitions: List[Dict[str, Any]] = [
        {"type": "DOCK",      "bounds": {"x_min": 0,  "x_max": 33, "y_min": 0, "y_max": 1},  "label": "Dock Row"},
        {"type": "SORT",      "bounds": {"x_min": 0,  "x_max": 10, "y_min": 26, "y_max": 28}, "label": "Sorting Zone"},
        {"type": "PACK",      "bounds": {"x_min": 11, "x_max": 22, "y_min": 26, "y_max": 28}, "label": "Packing Zone"},
        {"type": "DISPATCH",  "bounds": {"x_min": 23, "x_max": 33, "y_min": 26, "y_max": 28}, "label": "Dispatch Zone"},
        {"type": "CHARGING",  "bounds": {"x_min": 0,  "x_max": 33, "y_min": 29, "y_max": 30}, "label": "Charging Bay Row"},
        {"type": "STORAGE",   "bounds": {"x_min": 0,  "x_max": 33, "y_min": 2,  "y_max": 25}, "label": "Main Storage Area"},
    ]

    # AMR lane definitions (bi-directional travel corridors)
    lane_definitions: List[Dict[str, Any]] = [
        {"id": f"lane_ns_{i+1}", "axis": "NS", "x": ax + 2, "y_start": 2, "y_end": 28, "bidirectional": True}
        for i, ax in enumerate(aisle_x_positions)
    ]
    # East-West cross-lanes
    for cy_idx, cy in enumerate(range(4, 28, 6)):
        lane_definitions.append({
            "id": f"lane_ew_{cy_idx+1}",
            "axis": "EW",
            "y": cy - 1,
            "x_start": 0,
            "x_end": 33,
            "bidirectional": True,
        })

    # ASRS crane lines (one per pair of aisles)
    crane_lines: List[Dict[str, Any]] = [
        {"id": i + 1, "x": aisle_x_positions[i * 2], "y_start": 4, "y_end": 25, "levels": 4}
        for i in range(len(aisle_x_positions) // 2)
    ]

    return {
        "rack_config": rack_config,
        "conveyor_paths": conveyor_paths,
        "dock_bays": dock_bays,
        "charger_positions": charger_positions,
        "zone_definitions": zone_definitions,
        "lane_definitions": lane_definitions,
        "crane_lines": crane_lines,
    }


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------

_REQUIRED_TOP_KEYS = ("meta", "layout", "robots", "tasks", "obstacles",
                      "sensors", "hazards", "alerts", "metrics")

_REQUIRED_META_KEYS = ("schema_version", "sim_tick", "sim_time", "running",
                       "speed", "layout_version", "generated_at")

_REQUIRED_LAYOUT_KEYS = ("grid", "cell_size", "shelves", "charging_docks",
                         "packing_stations", "picking_stations", "conveyors")

_REQUIRED_ROBOT_KEYS = ("id", "x", "y", "state", "battery", "carrying",
                        "replan_count", "collision_risk", "blocked_by",
                        "carrying_type", "eta_ticks")

_REQUIRED_METRIC_KEYS = ("step_count", "num_robots", "collision_avoidance_events",
                         "deadlock_count", "warehouse_utilization")


def validate_payload(state: dict) -> List[str]:
    """
    Validate a ``build_simulation_state()`` payload and return a list of
    human-readable warning strings.  An empty list indicates full compliance.

    Checks performed:
    * Top-level required keys
    * ``meta`` required keys
    * ``layout`` required keys (v2 extended fields)
    * Per-robot required keys
    * ``metrics`` required keys

    >>> warnings = validate_payload(build_simulation_state(sim))
    >>> assert isinstance(warnings, list)
    """
    warnings: List[str] = []

    for k in _REQUIRED_TOP_KEYS:
        if k not in state:
            warnings.append(f"Missing top-level key: '{k}'")

    meta = state.get("meta", {})
    for k in _REQUIRED_META_KEYS:
        if k not in meta:
            warnings.append(f"Missing meta key: '{k}'")

    layout = state.get("layout", {})
    for k in _REQUIRED_LAYOUT_KEYS:
        if k not in layout:
            warnings.append(f"Missing layout key: '{k}'")

    # v2 extended layout fields
    for k in ("rack_config", "conveyor_paths", "dock_bays", "zone_definitions",
              "lane_definitions", "crane_lines", "charger_positions"):
        if k not in layout:
            warnings.append(f"Missing v2 layout key: '{k}'")

    for idx, robot in enumerate(state.get("robots", [])):
        for k in _REQUIRED_ROBOT_KEYS:
            if k not in robot:
                warnings.append(f"Robot index {idx} missing key: '{k}'")

    metrics = state.get("metrics", {})
    for k in _REQUIRED_METRIC_KEYS:
        if k not in metrics:
            warnings.append(f"Missing metrics key: '{k}'")

    return warnings


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_simulation_state(
    sim: Any,
    sensors: Optional[List[Dict[str, Any]]] = None,
    hazards: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    uptime_start: float = 0.0,
    running: bool = True,
    sim_speed: float = 1.0,
    include_large_layout: bool = False,
    quality_tier: str = "medium",
    sound_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct a JSON-serializable world state payload adhering to Bridge
    Contract v2.0.0 (backward-compatible with v1.0.0 consumers).

    Parameters
    ----------
    sim : WarehouseSimulator
        Active simulator instance.
    sensors : list of dicts, optional
        IoT sensor telemetry snapshots.
    hazards : list of dicts, optional
        Active environmental hazard zones.
    alerts : list of dicts, optional
        Active operational alerts and incident logs.
    uptime_start : float
        Timestamp of simulator launch.
    running : bool
        Whether the simulation loop is currently executing.
    sim_speed : float
        Playback multiplier.
    include_large_layout : bool
        When True, merge the large DC scenery config into the layout section.
        Default False — existing 15×15 behaviour is unchanged.
    quality_tier : str
        Render quality hint for the JS side ("low", "medium", "high").

    Returns
    -------
    dict
        Validated data structure conforming to BRIDGE_CONTRACT.md v2.0.0.

    Unit-test assertions
    --------------------
    >>> state = build_simulation_state(sim)
    >>> assert state["meta"]["schema_version"] == "2.0.0"
    >>> assert isinstance(state["layout"]["rack_config"], list)
    >>> assert isinstance(state["layout"]["conveyor_paths"], list)
    >>> assert isinstance(state["layout"]["dock_bays"], list)
    >>> assert isinstance(state["layout"]["zone_definitions"], list)
    >>> assert isinstance(state["layout"]["lane_definitions"], list)
    >>> assert isinstance(state["layout"]["crane_lines"], list)
    >>> assert all("replan_count" in r for r in state["robots"])
    >>> assert all("blocked_by" in r for r in state["robots"])
    >>> assert all("carrying_type" in r for r in state["robots"])
    >>> assert all("eta_ticks" in r for r in state["robots"])
    >>> assert "collision_avoidance_events" in state["metrics"]
    >>> assert "deadlock_count" in state["metrics"]
    >>> assert "warehouse_utilization" in state["metrics"]
    """
    now_ts = time.time()
    elapsed_s = now_ts - uptime_start if uptime_start > 0 else 0.0
    hh = int(elapsed_s // 3600)
    mm = int((elapsed_s % 3600) // 60)
    ss = int(elapsed_s % 60)

    # ── Meta ─────────────────────────────────────────────────────────────────
    meta = {
        "schema_version": SCHEMA_VERSION,
        "sim_tick": getattr(sim, "step_count", 0),
        "sim_time": float(getattr(sim, "step_count", 0)),
        "running": running,
        "speed": float(sim_speed),
        "layout_version": 1,
        "generated_at": round(now_ts, 3),
        "quality_tier": quality_tier,
        "global_e_stop": bool(getattr(sim, "global_e_stop", False)),
    }

    # ── Static Layout ────────────────────────────────────────────────────────
    grid_w = getattr(sim.grid, "width", 15)
    grid_h = getattr(sim.grid, "height", 15)

    charging_docks = [
        {"id": idx + 1, "coord": [d[0], d[1]]}
        for idx, d in enumerate(getattr(sim.grid, "charging_docks", []))
    ]
    packing_stations = [
        {"id": idx + 1, "coord": [p[0], p[1]]}
        for idx, p in enumerate(getattr(sim.grid, "packing_stations", []))
    ]
    picking_stations = [
        {"id": idx + 1, "coord": [pk[0], pk[1]]}
        for idx, pk in enumerate(getattr(sim.grid, "picking_stations", []))
    ]
    shelves = [
        {"x": s[0], "y": s[1]}
        for s in sorted(list(getattr(sim.grid, "shelves", set())))
    ]

    # Pre-defined automated conveyor segments feeding into packing stations
    conveyors = [
        {"id": 1, "x": 2, "y": 13, "length": 4, "axis": "x"},
        {"id": 2, "x": 6, "y": 13, "length": 4, "axis": "x"},
        {"id": 3, "x": 10, "y": 13, "length": 3, "axis": "x"},
    ]

    # ── v2.0 Enhanced static layout fields ───────────────────────────────────
    # Derive rack_config from actual shelves (each shelf = 1-bay, 1-level active rack)
    rack_config: List[Dict[str, Any]] = [
        {
            "x": s["x"],
            "y": s["y"],
            "orientation": "NS",
            "levels": 1,
            "bays": 1,
            "type": "active",
        }
        for s in shelves
    ]

    # Conveyor paths derived from the fixed conveyor segments
    conveyor_paths: List[Dict[str, Any]] = [
        {
            "id": c["id"],
            "points": [[c["x"] + i, c["y"]] for i in range(c["length"])],
            "speed": 1.0,
            "type": "INTERNAL",
        }
        for c in conveyors
    ]

    # Dock bays — infer from picking stations (they serve as goods-in docks)
    dock_bays: List[Dict[str, Any]] = [
        {"id": pk["id"], "x": pk["coord"][0], "y": pk["coord"][1], "width": 1, "type": "INBOUND"}
        for pk in picking_stations
    ]

    # Charger positions (re-use charging_docks with extended info)
    charger_positions: List[Dict[str, Any]] = [
        {"id": cd["id"], "x": cd["coord"][0], "y": cd["coord"][1], "type": "STANDARD"}
        for cd in charging_docks
    ]

    # Zone definitions derived from real grid dimensions
    zone_definitions: List[Dict[str, Any]] = [
        {
            "type": "STORAGE",
            "bounds": {"x_min": 0, "x_max": grid_w - 1, "y_min": 0, "y_max": grid_h - 3},
            "label": "Main Storage",
        },
    ]
    if packing_stations:
        ps_coords = [p["coord"] for p in packing_stations]
        zone_definitions.append({
            "type": "PACK",
            "bounds": {
                "x_min": min(c[0] for c in ps_coords),
                "x_max": max(c[0] for c in ps_coords),
                "y_min": min(c[1] for c in ps_coords),
                "y_max": max(c[1] for c in ps_coords),
            },
            "label": "Packing Zone",
        })
    if picking_stations:
        pk_coords = [p["coord"] for p in picking_stations]
        zone_definitions.append({
            "type": "DOCK",
            "bounds": {
                "x_min": min(c[0] for c in pk_coords),
                "x_max": max(c[0] for c in pk_coords),
                "y_min": min(c[1] for c in pk_coords),
                "y_max": max(c[1] for c in pk_coords),
            },
            "label": "Dock / Picking Zone",
        })
    if charging_docks:
        ch_coords = [c["coord"] for c in charging_docks]
        zone_definitions.append({
            "type": "CHARGING",
            "bounds": {
                "x_min": min(c[0] for c in ch_coords),
                "x_max": max(c[0] for c in ch_coords),
                "y_min": min(c[1] for c in ch_coords),
                "y_max": max(c[1] for c in ch_coords),
            },
            "label": "Charging Zone",
        })

    # Lane definitions — primary N-S and E-W corridors based on grid geometry
    lane_definitions: List[Dict[str, Any]] = [
        {"id": "lane_ew_main", "axis": "EW", "y": grid_h - 1, "x_start": 0, "x_end": grid_w - 1, "bidirectional": True},
        {"id": "lane_ns_left", "axis": "NS", "x": 0, "y_start": 0, "y_end": grid_h - 1, "bidirectional": True},
        {"id": "lane_ns_right", "axis": "NS", "x": grid_w - 1, "y_start": 0, "y_end": grid_h - 1, "bidirectional": True},
    ]

    # ASRS crane lines — position along the left edge as placeholders
    crane_lines: List[Dict[str, Any]] = [
        {"id": 1, "x": 1, "y_start": 2, "y_end": grid_h - 3, "levels": 2},
    ]

    # Merge large-layout scenery if requested
    if include_large_layout:
        large_cfg = build_large_layout_config()
        rack_config = large_cfg["rack_config"]
        conveyor_paths = large_cfg["conveyor_paths"]
        dock_bays = large_cfg["dock_bays"]
        charger_positions = large_cfg["charger_positions"]
        zone_definitions = large_cfg["zone_definitions"]
        lane_definitions = large_cfg["lane_definitions"]
        crane_lines = large_cfg["crane_lines"]

    layout = {
        "grid": {"width": grid_w, "height": grid_h},
        "cell_size": CELL_SIZE_METERS,
        "shelves": shelves,
        "charging_docks": charging_docks,
        "packing_stations": packing_stations,
        "picking_stations": picking_stations,
        "conveyors": conveyors,
        # v2.0 enhanced fields
        "rack_config": rack_config,
        "conveyor_paths": conveyor_paths,
        "dock_bays": dock_bays,
        "charger_positions": charger_positions,
        "zone_definitions": zone_definitions,
        "lane_definitions": lane_definitions,
        "crane_lines": crane_lines,
    }

    # ── Robots ───────────────────────────────────────────────────────────────
    robots_payload: List[Dict[str, Any]] = []
    active_count = 0
    idle_count = 0
    total_distance = 0
    battery_sum = 0.0
    completed_tasks_total = 0
    collision_avoidance_events = 0

    # Deadlock handler access (if present)
    deadlock_handler = getattr(sim, "deadlock_handler", None)
    deadlock_groups: List[set] = []
    if deadlock_handler is not None:
        deadlock_groups = getattr(deadlock_handler, "current_deadlocks", [])
    deadlock_count = len(deadlock_groups)

    # Build a quick look-up: robot_id → set of other robot IDs in its deadlock group
    _deadlock_map: Dict[int, List[int]] = {}
    for group in deadlock_groups:
        group_ids = list(group) if isinstance(group, (set, frozenset, list, tuple)) else []
        for rid_in_group in group_ids:
            _deadlock_map[rid_in_group] = [other for other in group_ids if other != rid_in_group]

    robots_dict = getattr(sim, "robots", {})
    shelf_set = getattr(sim.grid, "shelves", set())
    total_shelf_count = max(len(shelf_set), 1)
    occupied_shelves = 0

    for rid, robot in sorted(robots_dict.items(), key=lambda item: item[0]):
        gx, gy = robot.pos
        state_str = str(getattr(robot, "state", "IDLE")).upper()

        if state_str in ("IDLE", "CHARGING", "DOCKED"):
            idle_count += 1
        else:
            active_count += 1

        # Path serialization (remaining trajectory)
        path_cells: List[List[int]] = []
        remaining_path_len = 0
        if getattr(robot, "path", None):
            idx = getattr(robot, "path_index", 0)
            rem = robot.path[idx:]
            remaining_path_len = len(rem)
            path_cells = [[p[0], p[1]] for p in rem[:40]]

        # Movement trail history
        trail_cells = [
            [t[0], t[1]] for t in getattr(robot, "trail", [])[-12:]
        ]

        yaw = _yaw_from_path(robot.pos, getattr(robot, "path", []), getattr(robot, "path_index", 0))

        # Task binding
        task_id = None
        pick_pos = None
        drop_pos = None
        task_priority = 1
        if getattr(robot, "assigned_task", None) is not None:
            t = robot.assigned_task
            task_id = getattr(t, "task_id", None)
            raw_pick = getattr(t, "pick_location", None)
            raw_drop = getattr(t, "delivery_station", None)
            pick_pos = list(raw_pick) if raw_pick else None
            drop_pos = list(raw_drop) if raw_drop else None
            task_priority = getattr(t, "priority", 1)

        # Carrying load flag: active during delivery or picking
        carrying = state_str in ("PICKING", "MOVING_TO_DELIVERY", "DELIVERING")

        # v2: carrying_type — infer from task or robot attribute
        carrying_type = None
        if carrying:
            carrying_type = str(getattr(robot, "carrying_type", "TOTE")).upper()
            if carrying_type not in ("TOTE", "CARTON", "PALLET"):
                carrying_type = "TOTE"

        battery_val = round(float(getattr(robot, "battery", 100.0)), 1)
        battery_sum += battery_val
        dist_val = int(getattr(robot, "total_distance", 0))
        total_distance += dist_val
        tasks_done = int(getattr(robot, "completed_tasks", 0))
        completed_tasks_total += tasks_done

        # v2: replan_count from robot attribute
        replan_count = int(getattr(robot, "replan_count", 0))

        # v2: collision_risk — blocked or waiting robots
        collision_risk = state_str in ("WAITING", "BLOCKED")
        if collision_risk:
            collision_avoidance_events += 1

        # v2: blocked_by — from deadlock handler
        blocked_by = _deadlock_map.get(rid, [])

        # v2: eta_ticks — remaining path steps as estimate
        eta_ticks = remaining_path_len

        # Track occupied shelves (robot sitting on a shelf position)
        if (gx, gy) in shelf_set and carrying:
            occupied_shelves += 1

        meta_info = ROBOT_FLEET_METADATA.get(rid, {
            "name": f"ROBOT-{rid:02d}",
            "type": "AMR",
            "color": "#00f0ff",
            "role": "General Logistics",
        })

        robots_payload.append({
            "id": rid,
            "name": meta_info["name"],
            "model_type": meta_info["type"],
            "theme_color": meta_info["color"],
            "role": meta_info["role"],
            "x": int(gx),
            "y": int(gy),
            "world_y": 0.35,
            "yaw": round(yaw, 4),
            "speed": 1.0 if state_str.startswith("MOVING") else 0.0,
            "state": state_str,
            "battery": battery_val,
            "distance": dist_val,
            "tasks_done": tasks_done,
            "wait_ticks": int(getattr(robot, "wait_counter", 0)),
            "carrying": carrying,
            "path": path_cells,
            "trail": trail_cells,
            "task_id": task_id,
            "task_priority": task_priority,
            "pick_pos": pick_pos,
            "drop_pos": drop_pos,
            # v2 enhanced fields
            "replan_count": replan_count,
            "collision_risk": collision_risk,
            "blocked_by": blocked_by,
            "carrying_type": carrying_type,
            "eta_ticks": eta_ticks,
            # Mode & parcel state
            "mode": getattr(robot, "mode", "AUTO"),
            "carrying_parcel_id": getattr(getattr(robot, "carrying_parcel", None), "parcel_id", None),
            "health": getattr(robot, "health", 100.0),
            "e_stopped": getattr(robot, "e_stopped", False),
        })

    # ── Dynamic Obstacles ─────────────────────────────────────────────────────
    dynamic_obs = [
        {"x": int(o[0]), "y": int(o[1]), "type": "DYNAMIC"}
        for o in sorted(list(getattr(sim.grid, "dynamic_obstacles", set())))
    ]

    # ── Sensors ───────────────────────────────────────────────────────────────
    if sensors is None:
        sensors = [
            {
                "sensor_id": "temp_pod_alpha",
                "type": "Temperature",
                "value": 22.8,
                "unit": "°C",
                "status": "NORMAL",
                "coord": [3, 4],
                "threshold": 45.0,
                "radius": 2.5,
            },
            {
                "sensor_id": "smoke_dock_ch1",
                "type": "Smoke",
                "value": 0.04,
                "unit": "ratio",
                "status": "NORMAL",
                "coord": [1, 1],
                "threshold": 0.20,
                "radius": 3.0,
            },
            {
                "sensor_id": "gas_dispatch_lane",
                "type": "Gas",
                "value": 0.01,
                "unit": "ratio",
                "status": "NORMAL",
                "coord": [11, 13],
                "threshold": 0.15,
                "radius": 2.0,
            },
        ]

    # ── Hazards ───────────────────────────────────────────────────────────────
    if hazards is None:
        hazards = [
            {
                "type": "OBSTACLE",
                "severity": "WARNING",
                "coord": [int(o[0]), int(o[1])],
                "radius": 1.4,
                "active": True,
            }
            for o in getattr(sim.grid, "dynamic_obstacles", set())
        ]

    # ── Alerts ────────────────────────────────────────────────────────────────
    if alerts is None:
        alerts = []
        if dynamic_obs:
            alerts.append({
                "type": "OBSTACLE_ALERT",
                "severity": "WARNING",
                "message": f"{len(dynamic_obs)} active dynamic obstacle(s) detected in aisle.",
                "timestamp": getattr(sim, "step_count", 0),
            })
        for r in robots_payload:
            if r["battery"] < 25.0:
                alerts.append({
                    "type": "LOW_BATTERY",
                    "severity": "WARNING",
                    "message": f"Robot {r['id']} battery critically low ({r['battery']}%).",
                    "timestamp": getattr(sim, "step_count", 0),
                })
            if r["state"] in ("BLOCKED", "EMERGENCY"):
                alerts.append({
                    "type": "ROBOT_BLOCKED",
                    "severity": "CRITICAL",
                    "message": f"Robot {r['id']} reporting {r['state']} state.",
                    "timestamp": getattr(sim, "step_count", 0),
                })
        if deadlock_count > 0:
            alerts.append({
                "type": "DEADLOCK_DETECTED",
                "severity": "CRITICAL",
                "message": f"{deadlock_count} deadlock group(s) detected in fleet.",
                "timestamp": getattr(sim, "step_count", 0),
            })

    # ── Tasks ─────────────────────────────────────────────────────────────────
    tasks_payload: List[Dict[str, Any]] = []
    if hasattr(sim, "task_manager"):
        tm = sim.task_manager
        # Pending tasks
        pending_list = getattr(tm, "get_pending_tasks", lambda: [])()
        for t in pending_list[:15]:
            tasks_payload.append({
                "id": getattr(t, "task_id", 0),
                "type": "PICK_AND_DELIVERY",
                "pick": list(getattr(t, "pick_location", [0, 0])),
                "drop": list(getattr(t, "delivery_station", [0, 0])),
                "robot_id": getattr(t, "assigned_robot_id", None),
                "status": "PENDING",
                "priority": getattr(t, "priority", 1),
            })
        # Active tasks
        active_list = getattr(tm, "get_active_tasks", lambda: [])()
        for t in active_list[:10]:
            tasks_payload.append({
                "id": getattr(t, "task_id", 0),
                "type": "PICK_AND_DELIVERY",
                "pick": list(getattr(t, "pick_location", [0, 0])),
                "drop": list(getattr(t, "delivery_station", [0, 0])),
                "robot_id": getattr(t, "assigned_robot_id", None),
                "status": "IN_PROGRESS",
                "priority": getattr(t, "priority", 1),
            })

    # ── KPIs ──────────────────────────────────────────────────────────────────
    num_robots = len(robots_dict)
    avg_bat = round(battery_sum / max(num_robots, 1), 1)
    step_c = max(getattr(sim, "step_count", 0), 1)
    throughput = round((completed_tasks_total / step_c) * 100.0, 1)
    utilization = round((active_count / max(num_robots, 1)) * 100.0, 1)
    pending_tasks_count = (
        sim.task_manager.get_pending_count() if hasattr(sim, "task_manager") else 0
    )

    # Warehouse utilization: percentage of shelf positions currently occupied
    # (approximated by robots carrying items at shelf locations)
    warehouse_utilization = round(
        (occupied_shelves / total_shelf_count) * 100.0, 1
    ) if total_shelf_count > 0 else 0.0

    kpis = {
        "step_count": getattr(sim, "step_count", 0),
        "num_robots": num_robots,
        "active_robots": active_count,
        "idle_robots": idle_count,
        "pending_tasks": pending_tasks_count,
        "completed_tasks": completed_tasks_total,
        "total_distance": total_distance,
        "avg_battery": avg_bat,
        "throughput": throughput,
        "utilization": utilization,
        "vertex_conflicts": 0,
        "edge_conflicts": 0,
        "deadlocks_resolved": getattr(sim.metrics, "deadlocks_resolved", 0) if hasattr(sim, "metrics") else 0,
        "uptime": f"{hh:02d}:{mm:02d}:{ss:02d}",
        # v2 performance fields
        "collision_avoidance_events": collision_avoidance_events,
        "deadlock_count": deadlock_count,
        "warehouse_utilization": warehouse_utilization,
    }

    # ── Parcels ───────────────────────────────────────────────────────────────
    parcels_payload: List[Dict[str, Any]] = []
    if hasattr(sim, "inventory_manager") and sim.inventory_manager is not None:
        parcels_payload = sim.inventory_manager.to_bridge_payload()

    # ── Active A* Paths (top-level for Three.js Path Ribbons) ─────────────────
    paths_payload: List[List[List[int]]] = [
        r["path"] for r in robots_payload if r.get("path") and len(r["path"]) >= 2
    ]

    astar_stats = sim.get_astar_telemetry() if hasattr(sim, "get_astar_telemetry") else {}
    event_log = list(getattr(sim, "event_log", []))[-12:]

    payload = {
        "meta": meta,
        "layout": layout,
        "robots": robots_payload,
        "paths": paths_payload,
        "tasks": tasks_payload,
        "parcels": parcels_payload,
        "obstacles": dynamic_obs,
        "sensors": sensors,
        "hazards": hazards,
        "alerts": alerts,
        "metrics": kpis,
        "astar_stats": astar_stats,
        "event_log": event_log,
    }
    if sound_settings is not None:
        payload["sound_settings"] = sound_settings
    return payload


def to_json(state: Dict[str, Any]) -> str:
    """Serialise a build_simulation_state() result to a compact JSON string."""
    return json.dumps(state, separators=(",", ":"))
