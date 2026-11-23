# SmartWarehouse AI — Autonomous Warehouse Robotics, Industrial IoT & Enterprise 3D Digital Twin Platform

**Platform:** Module 1–13 Enterprise Final | Three.js WebGL Digital Twin v2.0  
**Technology Stack:** Python 3.13, Streamlit, Three.js (r164), WebGL, Webpack 5, NumPy, Pandas, NetworkX, SQLite, Pytest  

---

## 📌 Executive Summary

**SmartWarehouse AI** is a state-of-the-art autonomous warehouse robotics, predictive intelligence, and 3D digital-twin simulation platform. It brings together space-time heuristic pathfinding, atomic reservation-table collision avoidance, wait-for-graph (WFG) deadlock recovery, multi-strategy task dispatching, industrial IoT hazard detection, explainable AI advisory recommendations, scientific algorithm benchmarking, and audit-grade executive reporting.

The platform is anchored by an **Industrial Executive Command Centre** featuring a photorealistic, real-time **3D WebGL Digital Twin** (Three.js r164), reflecting the Python simulation engine as the single source of truth with zero mocked telemetry.

---

## 🌟 3D Digital Twin Features & Visual Reference Mapping

The 3D WebGL Digital Twin renders a massive, automated industrial facility matching commercial reference benchmarks (R1–R9):

1. **Massive High-Bay Racking (R1, R4)**: 6-tier industrial pallet racks with blue uprights (`#1565c0`), safety-orange load step beams (`#ff8f00`), structural X-bracing, Euro-pallets, kraft cardboard cartons with barcodes, and colour-coded plastic totes.
2. **Reflective Epoxy & Marked Floor (R1, R2, R4)**: High-resolution polished concrete with expansion joints, double yellow perimeter safety borders, cyan robot transit guide tracks, and stenciled floor zone markings ("A03", "MAX 500KG").
3. **Automated Infrastructure (R1, R3, R6, R7)**: Dual roller conveyor lines with instanced rollers and moving totes, 6-axis articulated orange robotic arms performing pick-and-place cycles, and vertical ASRS storage-retrieval crane masts.
4. **Authentic R2 Industrial AMR Fleet (R5)**: Dual-tone silver-grey & dark navy chassis, dual circular cyan LED headlight rings, rotating 360° LiDAR puck with cyan scanning ring, four drive wheels with rubber tyres and steel hubs, ground underglow projection matching state, and stacked tote cargo when carrying tasks.
5. **3 Switchable Visual Themes**:
   - **Realistic Industrial**: High-bay daylight illumination, polished concrete, blue/orange racking, and linear LED fixtures (References R1, R2, R4).
   - **Night Ops**: Atmospheric dark navy facility with piercing cyan/amber LEDs, reflective floor, and focused AMR headlights (References R5, R6).
   - **Digital Twin Wireframe**: Cybernetic holographic aesthetic with cyan line grids, dimmed scene, and real-time telemetry HUD (References R3, R7).
6. **Camera & Interaction System**:
   - **6 Camera Presets**: Cinematic Overview, Top-Down, Narrow Aisle (one-point perspective), Loading Dock, AMR Hero close-up, and Digital Twin.
   - **First-Person WASD Walk Mode**: Eye-level (1.7m) warehouse exploration with keyboard navigation.
   - **Automated 3D Presentation Tour**: Guided walkthrough of key facility zones with smooth camera transitions and contextual captions.
   - **Interactive Raycasting**: Click on any AMR to open its real-time telemetry card with Follow Camera mode.

---

## 🏗️ System Architecture & Directory Structure

```
SmartWarehouse-AI.2/
├── app.py                         # Primary Streamlit Enterprise Command Centre
├── warehouse.py                   # Canonical Warehouse environment & grid topology
├── astar.py                       # Static 2D A* & Space-Time A* pathfinding
├── time_expanded.py               # Space-Time 3D A* Search with reservation constraints
├── robot.py                       # Robot lifecycle state definitions
├── priority.py                    # Priority-based path coordination schemes
├── conflict.py                    # Vertex & Edge-swap collision detection
├── deadlock.py                    # Wait-For Graph (WFG) & cycle detection
├── obstacles.py                   # Static shelf and dynamic obstacle storage
│
├── core/                          # Safety-Critical Multi-Robot Planning Core
│   ├── grid.py                    # Warehouse grid re-export module
│   ├── planner.py                 # SpaceTimeAStarPlanner integrating reservation tables
│   ├── multi_agent.py             # MultiAgentPlanner & fleet conflict validator
│   ├── reservation.py             # Atomic space-time reservation table (vertex + edge)
│   ├── replanner.py               # Dynamic replanning pipeline on unexpected obstacles
│   ├── obstacle_manager.py        # Dynamic obstacle lifecycle & event history
│   ├── task_manager.py            # Task priority tiers, state machine & coordinate validation
│   ├── task_assignment.py        # 6 Dispatch strategies (including Hungarian bipartite matching)
│   ├── demand_forecasting.py      # Module 10: EWMA demand prediction & frequency analysis
│   ├── shelf_optimizer.py         # Module 10: Demand-weighted shelf layout optimization & swaps
│   ├── congestion_predictor.py    # Module 10: Active path horizon traffic density & risk zones
│   ├── predictive_maintenance.py  # Module 10: Multi-factor health scoring (battery, wear, load)
│   ├── fleet_optimizer.py         # Module 10: Multi-strategy benchmark runner & recommendation
│   ├── sensor.py                  # Module 11: Industrial IoT sensor telemetry definitions
│   ├── iot_manager.py             # Module 11: ESP32 device network manager & heartbeats
│   └── hazard_detector.py         # Module 11: Deterministic rule-based hazard detection engine
│
├── simulation/                    # Discrete-Time Simulation Loop
│   ├── engine.py                  # WarehouseSimulator event execution engine
│   ├── metrics.py                 # Telemetry collector, throughput, Gini index & latency
│   ├── demo.py                    # Deterministic viva evaluation demonstration scenarios
│   └── ai_analytics.py            # Central coordinator caching all Module 10 AI analytics
│
├── visualization/                 # 3D Digital Twin & Rendering
│   ├── threejs_bridge.py          # Strict Schema v2.0.0 JSON data bridge serializer
│   ├── renderer_3d.py             # Plotly 3D WebGL renderer (fallback engine)
│   └── renderer.py                # 2D Matplotlib diagnostic renderer
│
├── frontend/threejs_digital_twin/ # Three.js WebGL Digital Twin Application
│   ├── src/
│   │   ├── index.js               # Complete 2900+ line Three.js scene & animation engine
│   │   └── index.html             # HUD template with themes, presets & telemetry cards
│   ├── dist/
│   │   ├── bundle.js              # Production Webpack bundle (564 KiB, minified)
│   │   └── index.html             # Compiled production HTML template
│   ├── package.json               # Node.js dependencies (Three.js r164, Webpack 5)
│   └── webpack.config.js          # Production build configuration
│
├── analytics/                     # Module 13: Analytics Service & Data Layer
├── reporting/                     # Module 13: Professional Reporting & Multi-Format Export
├── benchmarks/                    # Module 13: Scientific Benchmarking Framework
├── recommendations/               # Module 13: Explainable Advisory Recommendation Engine
├── ui/                            # Module 13: Premium Frontend & Navigation System
├── persistence/                   # Module 12: Database Persistence Layer
├── tests/                         # 192 Automated Pytest Tests (100% Passing)
└── docs/                          # Architecture, Bridge Contract, Verification Reports
```

---

## 🚀 Installation & Launch Instructions (Windows / Linux / macOS)

### Prerequisites
- **Python**: 3.10 – 3.13 (Python 3.13.7 verified)
- **Node.js**: v18+ (Node.js v24.20.0, npm 11.19.0 verified)

### 1. Build Frontend Assets
```powershell
Set-Location C:\Users\Prasun\SmartWarehouse-AI.2\frontend\threejs_digital_twin
npm install
npm run build
```

### 2. Launch Streamlit Application
```powershell
Set-Location C:\Users\Prasun\SmartWarehouse-AI.2
python -m streamlit run app.py
```
Open **`http://localhost:8501`** in any web browser (Chrome, Edge, Firefox).

### 3. Run Automated Pytest Suite
```powershell
Set-Location C:\Users\Prasun\SmartWarehouse-AI.2
python -m pytest tests/ -v
```
All **192 tests** across all 13 modules and the Three.js bridge pass cleanly.

---

## 📸 Verified Evidence Screenshots (`docs/screenshots/final_deploy/`)

| # | File | Resolution | Size | Visual Highlights |
|---|------|------------|------|-------------------|
| 01 | `01_full_warehouse_overview_r1.png` | 1920×1080 | 978 KB | Grand Overview: Daylight industrial theme, 6-level racking, conveyors, LED fixtures, polished floor |
| 02 | `02_long_realistic_aisle_r2.png` | 1920×1080 | 449 KB | Narrow High-Bay Aisle: One-point perspective, blue uprights, orange load beams, cyan guide line |
| 03 | `03_highbay_storage_racks_r4.png` | 1920×1080 | 582 KB | Top-Down Grid View: Structural aisles, transit corridors, charging bays, dispatch stations |
| 04 | `04_conveyor_dispatch_area_r3.png` | 1920×1080 | 198 KB | Loading Dock & Conveyor: Roller conveyors, totes, packing stations, ASRS cranes |
| 05 | `05_amr_robot_closeup_r5.png` | 1920×1080 | 326 KB | AMR Hero Close-up: Dual cyan LED headlights, rotating LiDAR, underglow, rubber tyres, tote stack |
| 06 | `06_fleet_operating_nightops.png` | 1920×1080 | 661 KB | Night Ops Fleet View: Multiple AMRs moving simultaneously with illuminated path ribbons |
| 07 | `07_digital_twin_wireframe_r7.png` | 1920×1080 | 843 KB | Cybernetic Digital Twin: Holographic cyan wireframe mode with wall KPI displays |
| 08 | `08_collision_avoidance_planning.png` | 1920×1080 | 172 KB | Space-Time Planning: Collision-free 4D trajectory verification and reservation table |
| 09 | `09_iot_emergency_response.png` | 1920×1080 | 117 KB | IoT Emergency Response: Hazardous environmental monitoring and incident evacuation |
| 10 | `10_final_command_centre.png` | 1920×1080 | 762 KB | Executive Command Centre: Embedded hero 3D digital twin, 8 real-time KPI cards, fleet roster |

---

## 🔒 Security & Data Integrity

- **Password Security**: `hashlib.scrypt` with 128-bit salt and constant-time verification.
- **SQL Injection Defense**: Strict parameterized queries across all database operations.
- **Non-Blocking Persistence**: `WriteBehindQueue` buffers hazard incidents and flushes asynchronously without interrupting simulation ticks.
- **Offline Capability**: Zero external CDNs. All 3D textures are procedurally generated via HTML5 Canvas.
