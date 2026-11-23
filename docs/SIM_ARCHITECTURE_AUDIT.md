# SmartWarehouse AI — Simulation Architecture Audit

**Date:** 2026-11-24  
**Branch:** `feature/threejs-digital-twin`

---

## 1. Module Inventory

| Module # | Location | Purpose |
|:---:|:---|:---|
| 1 | `warehouse.py` + `core/grid.py` | 15×15 grid, shelves, docks, stations, obstacles |
| 2 | `obstacles.py` + `core/obstacle_manager.py` | Static shelves, dynamic obstacle management |
| 3 | `astar.py` + `core/planner.py` | A* (2D), Space-Time A* (3D with reservation) |
| 4 | `time_expanded.py` + `core/state.py` | Time-expanded state space, Action enum |
| 5 | `conflict.py` + `core/conflict.py` + `core/multi_agent.py` | Multi-robot conflict detection |
| 6 | `core/reservation.py` + `priority.py` + `core/priority.py` | Reservation table, priority schemes |
| 7 | `deadlock.py` + `core/deadlock.py` | Wait-For Graph deadlock detection/resolution |
| 8 | `core/replanner.py` | Dynamic replanning on obstacle injection |
| 9 | `core/task_manager.py` + `core/task_assignment.py` | Tasks, assignment strategies (Weighted, Hungarian, etc.) |
| 10 | `simulation/ai_analytics.py` + `core/demand_forecasting.py` + related | AI analytics, predictions, shelf optimization |
| 11 | `core/hazard_detector.py` + `core/iot_manager.py` + `core/sensor.py` | IoT sensors, hazard detection, emergency |
| 12 | `auth/` + `persistence/` | Authentication (bcrypt), SQLite WAL, repos |
| 13 | `analytics/` + `recommendations/` + `reporting/` + `benchmarks/` + UI | Full analytics stack, reports, benchmarking |

---

## 2. Simulation Entry Points

### `WarehouseSimulator` (`simulation/engine.py`)
- **Constructor:** `WarehouseSimulator(num_robots=3, width=15, height=15, seed=42)`
- **Tick model:** `sim.step()` advances one discrete time step
- **State storage:**
  - `sim.robots: Dict[int, RobotState]` — Fleet state (pos, path, task, battery, etc.)
  - `sim.task_manager.tasks: Dict[int, WarehouseTask]` — All tasks
  - `sim.reservation_table` — Space-time reservations
  - `sim.grid` — Grid with shelves and obstacles
  - `sim.obstacle_manager` — Dynamic obstacle events
  - `sim.metrics` — Step-level metrics
- **Robot states:** IDLE, MOVING_TO_PICK, PICKING, MOVING_TO_DELIVERY, DELIVERING, RETURNING_DOCK
- **Task states:** QUEUED → ASSIGNED → MOVING_TO_PICK → PICKING → MOVING_TO_DELIVERY → DELIVERING → COMPLETED (also CANCELLED, FAILED)

### Step Cycle (per `sim.step()`):
1. **Task assignment:** Idle robots get tasks via `TaskAssignmentEngine`
2. **State machine transitions:** MOVING→PICKING→MOVING→DELIVERING→IDLE
3. **Deadlock detection:** WFG analysis on active robots
4. **Movement execution:** Path-following along reserved paths
5. **Collision verification:** Check for position conflicts
6. **Metrics recording**

---

## 3. How Streamlit Holds It

- `st.session_state['sim']` — Single `WarehouseSimulator` instance
- `st.session_state['ai_engine']` — `AIAnalyticsEngine` bound to sim
- `st.session_state['analytics_service']` — `AnalyticsService`
- `st.session_state['rec_engine']` — `RecommendationEngine`
- `st.session_state['paused']`, `['num_robots']`, `['batch_size']`
- Simulation advances via UI buttons or auto-step in pages

---

## 4. Python→JS Bridge

- **Module:** `visualization/threejs_bridge.py`
- **Function:** `build_simulation_state(sim)` → dict → JSON
- **Schema:** 2.0.0 (backward compatible with 1.0.0)
- **Payload:** `meta`, `layout` (static grid/racks/docks), `robots` (pos/heading/state/battery/path/task), `obstacles`, `tasks`, `iot`, `metrics`, `alerts`
- **Delivery:** Via Streamlit HTML component embedding `<script>window.updateSimulation(data)</script>`
- **Return path:** Streamlit component return values → `st.session_state`

---

## 5. Database Schema

- **Tables:** `users`, `incidents`, `benchmark_runs`, `benchmark_trials`, `reports`
- **Mode:** SQLite WAL, `persistence/db.py`
- **Migrations:** `persistence/migrations/` (sequential SQL files)
- **No parcel/inventory/task tables yet** — Tasks are purely in-memory in `TaskManager`

---

## 6. Grid Layout (15×15 Standard)

- **Charging docks:** (1,0), (4,0), (7,0), (10,0), (13,0) — top row
- **Packing stations:** (2,14), (6,14), (10,14), (12,14) — bottom row
- **Picking stations:** (0,4), (0,7), (0,10) — left perimeter
- **Shelf blocks:** 3 pods × 2 vertical bands at x∈{2-3, 6-7, 10-11}, y∈{3-5, 8-10}
- **Aisles:** Between shelf pods (walkable corridors)

---

## 7. MUST-PRESERVE List

1. All 13 modules and their public APIs
2. All 206 existing tests (zero weakened/skipped/xfailed)
3. 14 navigation pages in `ui/pages/`
4. `WarehouseGrid`, `RobotState`, `WarehouseTask`, `TaskPriority`, `TaskStatus`
5. `SpaceTimeAStarPlanner`, `ReservationTable`, `DeadlockHandler`, `DynamicReplanner`
6. `TaskManager`, `TaskAssignmentEngine`, assignment strategies
7. Authentication (`auth/`), DB persistence (`persistence/`)
8. Analytics, recommendations, reporting, benchmarking modules
9. Git state: no commits/pushes without user approval

---

## 8. Risks

1. **No parcel/inventory model** — Tasks have pick_spot and delivery_station but no parcel objects
2. **No manual control mode** — Only automatic task dispatch exists
3. **Robot states are simple** — No battery charging, no carrying state, no manual control
4. **Tasks are in-memory only** — No persistence across restarts
5. **15×15 grid is small** — May look sparse in 3D; consider density improvements
6. **Bridge sends full state each tick** — No incremental updates yet
7. **Previous agent changes partially verified** — Need browser testing
