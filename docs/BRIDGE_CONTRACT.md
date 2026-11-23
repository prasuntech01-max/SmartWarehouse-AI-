# SmartWarehouse AI — Python-to-JavaScript Data Bridge Contract

**Version:** 2.0.0  
**Specification:** JSON Data Schema for Three.js Industrial Digital Twin (Module 13 Final)  
**Backward Compatibility:** Fully backward-compatible with 1.0.0 consumers  

---

## 1. Overview
The Three.js digital twin receives complete world state updates from Python's `WarehouseSimulator` via `window.updateSimulation(payload)`. Every field is sourced directly from live simulation models, spatial reservation tables, and environmental hazard monitors. No simulated data is falsified.

---

## 2. Top-Level Schema (v2.0.0)

```json
{
  "meta": {
    "schema_version": "2.0.0",
    "sim_tick": 42,
    "sim_time": 42.0,
    "running": true,
    "speed": 1.0,
    "layout_version": 1,
    "generated_at": 1795372800.0
  },
  "layout": {
    "grid": { "width": 15, "height": 15 },
    "cell_size": 2.0,
    "shelves": [ { "x": 2, "y": 3 }, ... ],
    "charging_docks": [ { "id": 1, "coord": [1, 0] }, ... ],
    "packing_stations": [ { "id": 1, "coord": [2, 14] }, ... ],
    "picking_stations": [ { "id": 1, "coord": [0, 4] }, ... ],
    "conveyors": [ { "id": 1, "x": 2, "y": 13, "length": 4, "axis": "x" }, ... ],
    "rack_config": [
      { "id": 1, "x": 2, "y": 3, "orientation": "NS", "levels": 6, "bays": 3, "type": "active" }
    ],
    "conveyor_paths": [
      { "id": 1, "start": [2, 13], "end": [5, 13], "speed": 1.0, "status": "active" }
    ],
    "dock_bays": [
      { "id": 1, "name": "Dock 01", "coord": [0, 14], "status": "AVAILABLE" }
    ],
    "zone_definitions": [
      { "type": "DOCK", "bounds": { "x_min": 0, "x_max": 15, "y_min": 0, "y_max": 2 }, "label": "Dock Row" }
    ],
    "lane_definitions": [
      { "id": "lane_1", "axis": "NS", "x": 5, "y_start": 0, "y_end": 14, "bidirectional": true }
    ],
    "crane_lines": [
      { "id": 1, "x": 5, "y_start": 3, "y_end": 11, "levels": 6 }
    ],
    "charger_positions": [ [1, 0], [4, 0], [7, 0] ]
  },
  "robots": [
    {
      "id": 1,
      "x": 1,
      "y": 0,
      "world_y": 0.35,
      "yaw": 0.0,
      "speed": 1.0,
      "state": "IDLE",
      "battery": 98.5,
      "distance": 14,
      "tasks_done": 2,
      "wait_ticks": 0,
      "carrying": false,
      "path": [ [1, 1], [1, 2], [2, 2] ],
      "trail": [ [1, 0] ],
      "task_id": 104,
      "task_priority": 1,
      "pick_pos": [2, 3],
      "drop_pos": [2, 14],
      "replan_count": 0,
      "collision_risk": false,
      "blocked_by": [],
      "carrying_type": null,
      "eta_ticks": 0
    }
  ],
  "obstacles": [
    { "x": 4, "y": 2, "type": "DYNAMIC", "id": 1 }
  ],
  "sensors": [
    {
      "sensor_id": "temp_aisle1",
      "type": "Temperature",
      "value": 24.5,
      "unit": "°C",
      "status": "NORMAL",
      "coord": [3, 3],
      "threshold": 45.0,
      "radius": 2.5
    }
  ],
  "hazards": [
    {
      "type": "FIRE",
      "severity": "CRITICAL",
      "coord": [4, 2],
      "radius": 1.8,
      "active": true
    }
  ],
  "alerts": [
    {
      "type": "REPLAN",
      "severity": "INFO",
      "message": "Robot 1 replanned around dynamic obstacle at (4, 2)",
      "timestamp": 42
    }
  ],
  "metrics": {
    "step_count": 42,
    "num_robots": 3,
    "active_robots": 2,
    "idle_robots": 1,
    "pending_tasks": 18,
    "completed_tasks": 2,
    "total_distance": 28,
    "avg_battery": 97.4,
    "throughput": 4.76,
    "utilization": 66.7,
    "vertex_conflicts": 0,
    "edge_conflicts": 0,
    "deadlocks_resolved": 0,
    "uptime": "00:01:24",
    "collision_avoidance_events": 0,
    "deadlock_count": 0,
    "warehouse_utilization": 12.5
  }
}
```

---

## 3. Validation
The Python module provides `validate_payload(state)` which inspects the state object against schema constraints and returns an empty list `[]` when valid.
