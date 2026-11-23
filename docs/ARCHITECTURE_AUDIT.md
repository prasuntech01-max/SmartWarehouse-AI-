# SmartWarehouse AI — Architecture Audit & System Inventory

**Date:** 2026-11-23  
**Branch:** `feature/threejs-digital-twin`  
**Auditor:** Principal Software Architect & Lead Digital Twin Engineer  

---

## 1. Executive Summary & Inventory

SmartWarehouse AI is an industrial-grade autonomous mobile robot (AMR) warehouse simulator and intelligence platform. It models discrete space-time coordination, dynamic obstacle management, multi-agent path reservation, IoT telemetry, predictive analytics, and executive decision support across 13 core modules.

### Module-by-Module Inventory

| Module | Core Responsibility | Key Classes / Files | Status |
|--------|---------------------|---------------------|--------|
| **Module 1: Warehouse Grid** | 15×15 discrete grid layout, aisles, zones, docks | `warehouse.py`, `obstacles.py`, `core/grid.py` | Complete, Fully Tested |
| **Module 2: AMR Entity & Kinematics** | Robot model, states, battery, kinematics, step execution | `robot.py`, `core/state.py` | Complete, Fully Tested |
| **Module 3: 2D Shortest Path A\*** | Static A\* pathfinding on 2D warehouse topology | `astar.py`, `core/planner.py` | Complete, Fully Tested |
| **Module 4: Space-Time A\*** | Time-expanded reservation graph & 4D A\* trajectory planning | `time_expanded.py`, `core/planner.py` | Complete, Fully Tested |
| **Module 5: Conflict & Collision** | Vertex and edge-swap collision prediction and verification | `conflict.py`, `core/conflict.py` | Complete, Fully Tested |
| **Module 6: Reservation Table & Priority**| Atomic space-time reservation table & prioritized multi-agent planner | `priority.py`, `core/reservation.py` | Complete, Fully Tested |
| **Module 7: Deadlock Handling** | Wait-For Graph (WFG) cycle detection, yield actions, priority escalation | `deadlock.py`, `core/deadlock.py` | Complete, Fully Tested |
| **Module 8: Dynamic Obstacles & Replanning** | Real-time obstacle injection, affected trajectory identification & localized replan | `core/replanner.py`, `core/obstacle_manager.py` | Complete, Fully Tested |
| **Module 9: Task Management & Allocation** | Order queue, multi-strategy dispatch (Hungarian, Shortest, Weighted Multi-Criteria) | `core/task_manager.py`, `core/task_assignment.py` | Complete, Fully Tested |
| **Module 10: Predictive Analytics** | Heatmap congestion forecasting, shelf frequency optimization, maintenance models | `simulation/ai_analytics.py`, `core/demand_forecasting.py`, `core/shelf_optimizer.py` | Complete, Fully Tested |
| **Module 11: Industrial IoT & Emergency** | Sensor networks (Temp, Smoke, Gas, Vibration), deterministic hazard rules & incident pipeline | `core/sensor.py`, `core/hazard_detector.py`, `core/iot_manager.py` | Complete, Fully Tested |
| **Module 12: Auth & Persistence** | PBKDF2/HMAC authentication, SQLite WAL schema with migrations | `persistence/db.py`, `persistence/repo.py`, `auth/crypto.py` | Complete, Fully Tested |
| **Module 13: Command Centre & Reporting** | Empirical benchmarks, audit-grade report builders (HTML/CSV/ZIP), executive dashboards | `analytics/service.py`, `benchmarks/runner.py`, `reporting/builder.py`, `ui/` | Complete, Fully Tested |

---

## 2. 3D Digital Twin State: Current vs. Target

### Existing State
- Initial prototype had a basic 1-rack geometry and a box robot.
- Webpack build outputs `frontend/threejs_digital_twin/dist/bundle.js`.
- Streamlit integrates the twin via `st.components.v1.html` in `ui/pages/digital_twin_view.py`.
- Basic Python bridge `visualization/threejs_bridge.py` created to serialize robot positions.

### Target State (Industrial Reference Images)
As dictated by the reference images:
1. **High-Bay Racking & Cybernetic Vertical Lighting:** Tall multi-tier steel racks with realistic blue uprights, safety orange load beams, Euro-pallets, shrink-wrapped packages, and vertical cyan/green LED guide strip lights along column uprights (Image 1, 2, 3).
2. **Polished Floor & Visual Markings:** Highly reflective epoxy floor reflecting lights, yellow boundary caution lanes, cyan AMR guidance routes, and pedestrian crossing zones (Image 1, 2).
3. **Automated Infrastructure:** Articulated yellow robotic arm manipulators at sorting/packing tables, high-speed package conveyor lines with moving cartons, and gantry pallet transfer arches at aisle ends (Image 1, 5).
4. **Detailed AMRs:** Rounded industrial safety housing, matrix LED headlights/status displays, motorized lifting top deck, dual drive wheels with steel hubs, and rotating 360° LiDAR turret (Image 2).
5. **Cybernetic Digital Twin Overlays:** Glowing trajectory ribbons with chevron particle flow, conflict zone warning rings, deadlock cycle link vectors, volumetric IoT sensor discs with status halos, and particle-based hazard zones (fire/smoke and toxic gas) (Image 3, 5).
6. **Hero Command Centre View:** Embedded 3D twin in the Command Centre and Digital Twin views with full camera presets, live KPIs, and responsive controls (Image 6).

---

## 3. Streamlit Simulation State Flow

1. `st.session_state.sim` holds the singleton instance of `WarehouseSimulator`.
2. When the user interacts (Step +1, Run ×5, Reset, Inject Obstacle), `sim.step()` advances the discrete tick.
3. `visualization/threejs_bridge.py` transforms the live state into a structured JSON payload adhering to the Data Contract (`docs/BRIDGE_CONTRACT.md`).
4. In `ui/pages/digital_twin_view.py` and `ui/pages/command_centre.py`, the HTML component mounts or receives updates via `window.updateSimulation(state)`.
5. The Three.js scene applies client-side delta updates to meshes, rotating wheels, updating LED colors, and smoothly interpolating coordinates between ticks at 60 FPS.

---

## 4. Renderers & Fallback Architecture

- **Primary:** `3D Three.js (WebGL)` — High-fidelity WebGL digital twin with custom materials, shadows, and animated cybernetic elements.
- **Fallback 1:** `3D Plotly (WebGL)` — `visualization/renderer_3d.Warehouse3DRenderer` (Trace-budgeted Plotly graph objects).
- **Fallback 2:** `2D Matplotlib` — `visualization/renderer.WarehouseRenderer` (Direct matplotlib 2D floorplan plot).
- **Graceful Degradation:** If WebGL fails, the bundle is absent, or a JS error occurs, a non-blocking warning is displayed and the view seamlessly reverts to Plotly or 2D without Python exceptions.

---

## 5. Must-Preserve Features
- All 182 existing unit tests across all 13 modules.
- 14 Streamlit views: Command Centre, 3D Digital Twin, Robot Fleet, Operations, Path Planning, IoT Command Centre, Emergency Response, AI Recommendations, Deep Analytics, Benchmarking, Reports, Admin, Settings.
- Database integrity: SQLite database with zero schema breakage.
