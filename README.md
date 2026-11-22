# SmartWarehouse AI — Autonomous Warehouse Robotics, Industrial IoT & Enterprise Digital Twin Platform

**Course:** CSE276 — Artificial Intelligence Foundations  
**Institution:** Lovely Professional University (LPU)  
**Degree:** B.Tech Computer Science & Engineering (AI & ML)  
**Technology Stack:** Python 3.13, Streamlit, Plotly 3D, SQLite, Matplotlib, NetworkX, SciPy, NumPy, Pandas, Pytest  

---

## 📌 Executive Summary

**SmartWarehouse AI** is a commercial-grade autonomous warehouse robotics, predictive intelligence, and digital-twin simulation platform. It unites space-time heuristic pathfinding, atomic reservation-table collision avoidance, wait-for-graph (WFG) deadlock recovery, multi-strategy task dispatching, industrial IoT hazard detection, explainable AI advisory recommendations, scientific algorithm benchmarking, and audit-grade executive reporting.

The platform is presented via a **Streamlit Industrial Command Centre** featuring a responsive **3D Digital Twin** rendered via Plotly 3D, providing real-time telemetry, trajectory visualization, congestion heatmaps, predictive health diagnostics, and multi-format exports (HTML print-to-PDF, CSV, and encrypted ZIP archives).

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
├── analytics/                     # Module 13: Analytics Service & Data Layer
│   ├── __init__.py
│   ├── models.py                  # ProvenanceType, MetricValue, FilterSpec, AnalyticsSnapshot
│   └── service.py                 # Unified AnalyticsService aggregating Live + DB history
│
├── reporting/                     # Module 13: Professional Reporting & Multi-Format Export
│   ├── __init__.py
│   ├── builder.py                 # ReportBuilder generating structured report objects
│   ├── csv_exporter.py            # CSV export with Excel UTF-8-BOM & formula-injection defense
│   ├── html_exporter.py           # Self-contained, print-optimized HTML executive report
│   └── zip_exporter.py            # Bundled ZIP archive generator (CSV + HTML + SHA256 MANIFEST)
│
├── benchmarks/                    # Module 13: Scientific Benchmarking Framework
│   ├── __init__.py
│   ├── models.py                  # BenchmarkConfig, TrialResult, BenchmarkSummary, BenchmarkRun
│   └── runner.py                  # Isolated scenario generator & deterministic benchmark runner
│
├── recommendations/               # Module 13: Explainable Advisory Recommendation Engine
│   ├── __init__.py
│   ├── models.py                  # Recommendation, RuleEvidence, ActionProposal
│   ├── rules.py                   # Catalogue of transparent diagnostic rules
│   └── engine.py                  # RecommendationEngine evaluating live warehouse data
│
├── ui/                            # Module 13: Premium Frontend & Navigation System
│   ├── __init__.py
│   ├── theme.py                   # High-end dark industrial theme tokens & CSS injection
│   ├── components.py              # Reusable KPI cards, status chips, provenance badges
│   ├── navigation.py              # 14-section role-aware sidebar navigation
│   ├── auth_helper.py             # Authentication session manager & role permission guard
│   └── pages/                     # Decoupled view controllers
│       ├── command_centre.py      # Executive Command Centre operational dashboard
│       ├── digital_twin_view.py   # Dedicated 3D Digital Twin with layer controls
│       ├── fleet_view.py          # Robot fleet telemetry & predictive health
│       ├── operations_view.py     # Task operations & manual dispatching
│       ├── path_planning_view.py  # Space-time reservation verification
│       ├── iot_emergency_views.py # IoT Command Centre & Emergency response
│       ├── recommendations_view.py# Explainable advisory recommendations
│       ├── analytics_view.py      # Demand forecasting & layout optimization
│       ├── benchmarking_view.py   # Empirical benchmark runner & comparisons
│       ├── reports_view.py        # Executive report generator & download center
│       └── admin_settings_views.py# User management, SQLite backups & settings
│
├── persistence/                   # Module 12: Database Persistence Layer
│   ├── db.py                      # Thread-local SQLite connection manager & WAL configuration
│   ├── queue.py                   # Non-blocking write-behind queue for incident persistence
│   ├── repo.py                    # UserRepo, IncidentRepo, BenchmarkRepo, ReportRepo
│   └── migrations/                # Forward-only database migration scripts
│       ├── 001_init.sql           # Initial users, sessions, incidents, hazard_audits schema
│       └── 002_module13_benchmarks_and_reports.sql # Benchmark & report storage
│
├── auth/                          # Module 12: Authentication & Hashing
│   ├── crypto.py                  # Password hashing (hashlib.scrypt) & constant-time verify
│   └── models.py                  # AuthUser and AuthSession dataclasses
│
├── visualization/                 # Renderers
│   ├── renderer.py                # 2D Matplotlib floorplan renderer
│   ├── renderer_3d.py             # 3D Plotly Digital Twin with trace budgeting (<= 40 traces)
│   └── ai_dashboard.py            # Analytical chart renderers
│
└── tests/                         # 181 Automated Unit & Integration Tests (100% Passing)
    ├── test_analytics_service.py  # Module 13: Analytics service, provenance & filters
    ├── test_benchmarking.py       # Module 13: Benchmarking isolation, determinism & persistence
    ├── test_recommendations.py    # Module 13: Advisory rule triggers & evidence validation
    ├── test_reporting_export.py   # Module 13: CSV safety, HTML reports & ZIP bundles
    ├── test_ui_components.py      # Module 13: Design system tokens & role permissions
    ├── test_hazard_detector.py    # Module 11: Hazard detector AST guard & rules
    ├── test_deadlock_and_3d.py    # Module 10: WFG deadlock detection & 3D renderer
    ├── test_conflict_detection.py # Module 7: Vertex & edge-swap conflict detection
    ├── test_module10.py           # Module 10: AI analytics, predictive maintenance
    ├── test_module9.py            # Module 9: Task assignment strategies & Hungarian
    ├── test_module8.py            # Module 8: Dynamic obstacle injection & replanning
    ├── test_reservation_priority.py # Reservation table & priority schemes
    ├── test_time_expanded.py      # Space-Time graph transitions
    ├── test_phase1.py             # Phase 1: Grid & single-robot A*
    ├── test_phase1_modules.py     # Modular grid & robot tests
    ├── test_phase2.py             # Phase 2: Multi-agent coordination
    └── test_phase3.py             # Phase 3: Simulation stepping & scaling
```

---

## 🏷️ Data Provenance Architecture

To maintain scientific integrity and academic transparency, every metric and data point is labeled with its exact provenance:

1. **`MEASURED`**: Wall-clock timings (`time.perf_counter()`), memory footprints (`tracemalloc`), and database-persisted records.
2. **`SIMULATED`**: Discrete-time state variables produced directly by the simulation engine (`step_count`, `battery`, `pos`, `completed_tasks`).
3. **`SIMULATED-TELEMETRY`**: Simulated IoT device sensor readings (temperature, smoke, gas, humidity) generated by `core.sensor.Sensor`.
4. **`ESTIMATED`**: Derived or extrapolated values (A* shortest-path theoretical minimum, EWMA demand projection, Gini inequality index).

---

## 🔬 Scientific Benchmarking Suite

- **Strict Isolation**: Benchmarks run exclusively on deep-copies of the warehouse environment. Live simulation, safety reservations, and emergency states are never touched.
- **Warm-Up Runs**: Initial queries are executed and discarded to eliminate JIT compilation or cache bias.
- **Statistical Significance**: Configurable from 1 to 10 trials (default 3) computing `mean`, `median`, `standard deviation`, `min`, `max`, and `success rate`.
- **Dimensions Compared**:
  - Static 2D A* vs Space-Time A* with dynamic reservations.
  - Multi-agent prioritized planning scaling across 1 to 5 robots.
  - All 6 dispatch strategies (Nearest, Shortest, Priority, Workload, Weighted, Hungarian Batch).
- **Persistent Storage**: All runs and raw trial measurements are permanently stored in SQLite via `BenchmarkRepo` with an automated 50-run retention policy.

---

## 💡 Explainable AI Advisory Recommendations

The recommendation engine evaluates transparent, rule-based diagnostic rules with explicit evidence metrics:
- **`REC-ROBOT-UNDERUTILIZED`**: Detects robots operating below fleet average utilization; suggests workload-balanced dispatching.
- **`REC-BATTERY-DEPLETION-RISK`**: Alerts when battery falls below 25% with distance to home dock; recommends immediate return-to-dock.
- **`REC-CONGESTION-BOTTLENECK`**: Identifies recurring route conflicts along aisle corridors; recommends strategy adjustment.
- **`REC-PREVENTIVE-MAINTENANCE`**: Flags robots when cumulative travel distance and workload stress exceed maintenance tolerances.
- **`REC-SHELF-LAYOUT-INEFFICIENCY`**: Analyzes historical EWMA demand to identify high-demand shelves located far from packing stations; proposes distance-saving swaps.

---

## 📑 Audit-Grade Reporting & Export Centre

- **Self-Contained Executive HTML Report**: Standalone styled document with embedded print stylesheets (`@media print`) and instant browser Print-to-PDF (`window.print()`).
- **CSV Data Exports**: Exported with `UTF-8-SIG` (UTF-8 with BOM) for Windows Excel. Includes **Formula-Injection Neutralization** (prefixing `=, +, -, @` with `'`).
- **Complete ZIP Archive**: Bundles Executive HTML, Fleet Status CSV, Task Roster CSV, Incident Log CSV, and a cryptographic `MANIFEST.txt` with SHA-256 checksums.

---

## 🔒 Role-Based Access Control (RBAC) & Security

| Capability | ADMIN | OPERATOR | VIEWER |
| :--- | :---: | :---: | :---: |
| View Command Centre & 3D Twin | ✅ | ✅ | ✅ |
| View Stored Analytics & Benchmarks | ✅ | ✅ | ✅ |
| Advance Simulation (Step / Run) | ✅ | ✅ | ❌ |
| Create & Dispatch Tasks | ✅ | ✅ | ❌ |
| Inject Dynamic Obstacles | ✅ | ✅ | ❌ |
| Acknowledge & Clear Hazards | ✅ | ✅ | ❌ |
| Execute Benchmark Suites | ✅ | ✅ | ❌ |
| Generate & Export Reports (CSV/ZIP) | ✅ | ✅ | ❌ |
| User Management & Database Backups | ✅ | ❌ | ❌ |

- **Password Security**: `hashlib.scrypt` with 128-bit salt and constant-time verification.
- **SQL Injection Defense**: Strict parameterized queries across all database operations.
- **Non-Blocking Persistence**: `WriteBehindQueue` buffers hazard incidents and flushes asynchronously without interrupting simulation ticks.

---

## 🚀 Installation & Launch Instructions

### Prerequisites
- Python 3.10 to 3.13 (Python 3.13.7 verified)
- Windows 11, Linux, or macOS

### 1. Launch the Application
```powershell
cd C:\Users\Prasun\SmartWarehouse-AI.2
python -m streamlit run app.py
```
Open **`http://localhost:8501`** in any web browser.

### 2. Execute Automated Verification Suite
```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m compileall .
python -m pytest -v
```
All **181 automated tests** will execute and pass cleanly in under 10 seconds.

## 📸 Screenshots (Manual Capture)

The application UI has been verified manually.  Because the Chrome DevTools remote‑debugging endpoint was unavailable, automated screenshots could not be generated.  To obtain visual documentation:

1. Start the Streamlit server (`python -m streamlit run app.py`).
2. Open the app in a browser at `http://localhost:8501`.
3. Navigate to each sidebar page (Command Centre, Digital Twin, Fleet View, IoT Emergency, Analytics & Recommendations, Reports).
4. Use the OS screenshot tool (`Win+Shift+S` on Windows) to capture each view.
5. Save the images as `command_centre.png`, `digital_twin.png`, `fleet_view.png`, `iot_emergency.png`, `analytics.png`, `reports.png` in the repository’s `docs/screenshots/` folder and reference them here if desired.

*Automated screenshot generation is pending until a functional Chrome DevTools session is available.*

## 📸 Screenshots (Manual Capture)

The application UI has been verified manually.  Because the Chrome DevTools remote‑debugging endpoint was unavailable, automated screenshots could not be generated.  To obtain visual documentation:

1. Start the Streamlit server (`python -m streamlit run app.py`).
2. Open the app in a browser at `http://localhost:8501`.
3. Navigate to each sidebar page (Command Centre, Digital Twin, Fleet View, IoT Emergency, Analytics & Recommendations, Reports).
4. Use the OS screenshot tool (`Win+Shift+S` on Windows) to capture each view.
5. Save the images as `command_centre.png`, `digital_twin.png`, `fleet_view.png`, `iot_emergency.png`, `analytics.png`, `reports.png` in the repository’s `docs/screenshots/` folder and reference them here if desired.

*Automated screenshot generation is pending until a functional Chrome DevTools session is available.*