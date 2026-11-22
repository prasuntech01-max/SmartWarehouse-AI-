# SmartWarehouse AI — Autonomous Warehouse Robot Path Planning & Collision Avoidance Simulator

**Course:** CSE276 — Artificial Intelligence Foundations  
**Institution:** Lovely Professional University (LPU)  
**Degree:** B.Tech Computer Science & Engineering (AI & ML)  
**Technology Stack:** Python 3.13, Streamlit, Plotly 3D, Matplotlib, NetworkX, SciPy, NumPy, Pandas, Pytest  

---

## 📌 Executive Summary

**SmartWarehouse AI** is an industrial-grade autonomous multi-robot warehouse coordination and digital-twin simulator. It combines state-of-the-art space-time heuristic search algorithms, reservation-table collision avoidance, wait-for-graph (WFG) deadlock recovery, dynamic re-planning, multi-criteria task dispatching, and **Module 10 AI-Powered Warehouse Intelligence & Predictive Analytics**.

The simulator features a responsive **Streamlit Industrial Control Centre** backed by an interactive **3D Digital Twin** rendered via Plotly 3D, providing real-time telemetry, trajectory visualisation, bottleneck heatmaps, and predictive diagnostics.

---

## 🏗️ System Architecture & Module Breakdown

```
SmartWarehouse-AI.2/
├── app.py                         # Streamlit Industrial Control Centre Dashboard
├── warehouse.py                   # Canonical Warehouse environment & grid topology
├── astar.py                       # Classical 2D static A* algorithm
├── time_expanded.py               # Space-Time 3D A* Search with reservation constraints
├── robot.py                       # Robot lifecycle state definitions
├── priority.py                    # Priority-based path coordination schemes
├── conflict.py                    # Vertex & Edge-swap collision detection
├── deadlock.py                    # Wait-For Graph (WFG) & cycle detection
├── obstacles.py                   # Static shelf and dynamic obstacle storage
│
├── core/
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
│   └── fleet_optimizer.py         # Module 10: Multi-strategy benchmark runner & recommendation
│
├── simulation/
│   ├── engine.py                  # WarehouseSimulator discrete-time event execution engine
│   ├── metrics.py                 # Telemetry collector, throughput, Gini index & latency
│   ├── demo.py                    # Deterministic viva evaluation demonstration scenarios
│   └── ai_analytics.py            # Central coordinator caching all Module 10 AI analytics
│
├── visualization/
│   ├── renderer.py                # 2D Matplotlib warehouse floorplan renderer
│   ├── renderer_3d.py             # Interactive 3D Plotly Digital Twin with camera presets
│   └── ai_dashboard.py            # Plotly analytical chart renderers for Module 10
│
└── tests/                         # 151 Automated unit and integration tests (100% passing)
    ├── test_phase1.py             # Phase 1: Grid, obstacles, single-robot A*
    ├── test_phase1_modules.py     # Modular grid & robot tests
    ├── test_phase2.py             # Phase 2: Multi-agent coordination & replanning
    ├── test_phase3.py             # Phase 3: Simulation stepping & scaling
    ├── test_reservation_priority.py # Reservation table & edge-swap prevention
    ├── test_time_expanded.py      # Space-time graph transitions & wait actions
    ├── test_conflict_detection.py # Vertex, edge, and trajectory conflict detection
    ├── test_deadlock_and_3d.py    # Wait-For Graph cycle detection & 3D renderer
    ├── test_module8.py            # Module 8: Dynamic obstacle injection & replanning
    ├── test_module9.py            # Module 9: Multi-strategy assignment & task operations
    └── test_module10.py           # Module 10: AI intelligence, predictive analytics & 3D twin
```

---

## 🧠 Module 10: AI Warehouse Intelligence & Predictive Analytics

Module 10 transforms the simulator into an intelligent industrial control platform:

### 1. AI Demand Forecasting (`core/demand_forecasting.py`)
- **Telemetry-Driven:** Continuously monitors completed task pick spots, shelf locations, and delivery stations.
- **Forecasting Model:** Uses Exponentially Weighted Moving Averages (EWMA with $\alpha = 0.3$) over inter-completion steps to project incoming order rates for the next horizon.
- **Safety Safeguard:** When fewer than 3 tasks have been completed, forecasts are explicitly flagged as *Preliminary* with confidence levels (`low`, `medium`, `high`) to prevent premature decision-making.
- **Heatmap Export:** Generates normalized demand overlays ($0.0 \to 1.0$) for both 2D floorplans and 3D scenes.

### 2. Intelligent Shelf Optimization (`core/shelf_optimizer.py`)
- **Layout Scoring:** Analyzes Manhattan travel distances from each storage rack to the nearest packing stations:
  $$\text{Score} = (\text{Demand Weight} + 0.1) \times \min_{s \in \text{Stations}} \text{Dist}(\text{Shelf}, s)$$
- **Advisory Swaps:** Identifies high-demand shelves located far from stations and pairs them with low-demand shelves near packing zones.
- **Human-in-the-Loop Governance:** Relocation recommendations are strictly advisory by default. Operators can inspect the estimated travel savings (typically 15%–28%) and click **"Apply Approved Relocation"** to execute approved layout swaps safely without breaking aisle connectivity.

### 3. Congestion Prediction & Intelligence (`core/congestion_predictor.py`)
- **Horizon Scanning:** Reads active remaining paths from `RobotState.path[path_index:]` and cross-references space-time reservations.
- **Bottleneck Classification:** Identifies intersecting path corridors and assigns risk scores:
  - 🟢 **Green (< 0.30):** Clear aisle flow
  - 🟡 **Yellow (0.30 – 0.49):** Moderate traffic
  - 🟠 **Orange (0.50 – 0.74):** High-density bottleneck
  - 🔴 **Red ($\ge$ 0.75):** Critical congestion / potential circular wait
- **Rerouting Advisory:** Automatically recommends switching dispatch strategies (e.g., to Workload-Balanced or Hungarian Batch) when fleet congestion exceeds threshold tolerances.

### 4. Predictive Robot Maintenance (`core/predictive_maintenance.py`)
- **Transparent Multi-Factor Health Model:**
  $$\text{Health} = 100 - \Delta_{\text{Battery}} - \min(30, \frac{\text{Distance}}{20}) - \min(20, \text{Tasks} \times 2)$$
  - Battery deduction: $-20$ if battery $< 20\%$, $-10$ if battery $< 40\%$.
  - Mechanical wear: Deductions scaled proportionally with cumulative meters travelled.
  - Workload fatigue: Workload deductions scaled with total completed missions.
- **Urgency Tiers:** Categorized into *Excellent* ($\ge 80$), *Good* ($60-79$), *Warning* ($40-59$), and *Critical* ($< 40$).
- **Ethical Integrity:** Explicitly labeled as digital-twin simulation telemetry, avoiding false claims of physical sensor readings.

### 5. Multi-Strategy Fleet Optimization (`core/fleet_optimizer.py`)
- **Empirical Strategy Benchmarking:** Executes isolated, non-mutating test simulations over identical task queues for all 6 dispatch algorithms:
  1. Nearest Available Robot
  2. Shortest Total Route
  3. Priority-First Dispatch
  4. Workload-Balanced Allocation
  5. Weighted Multi-Criteria Dispatch
  6. Hungarian Batch Optimizer (Bipartite Matching via SciPy)
- **Fairness Metric:** Computes the Gini coefficient ($0.0 = \text{perfect equality}$) across robot workloads:
  $$G = \frac{\sum_{i=1}^n \sum_{j=1}^n |x_i - x_j|}{2n \sum_{i=1}^n x_i}$$
- **AI Recommendation Engine:** Selects the highest combined scoring strategy based on completed throughput (60% weight) and workload fairness (40% weight).

---

## 🎨 Premium 3D Digital Twin (`visualization/renderer_3d.py`)

- **Industrial Control-Centre Aesthetics:** Sleek dark charcoal/slate floor surfaces (`#0F172A`), illuminated cybernetic perimeter rails (`#0284C7`), steel racks, and vibrant status beacons.
- **Camera Orbit Presets:** Instant one-click camera positioning:
  - 🌐 **Isometric:** Standard 3D perspective ($45^\circ$ angle)
  - 🔝 **Top-Down:** Orthographic plan view for lane monitoring
  - 🔲 **Front:** Elevation view facing charging docks
  - 🔲 **Side:** Lateral aisle view
- **Real-Time Overlays:**
  - Dynamic Obstacle hazard blocks with diamond alert markers
  - Active planned paths (color-coded per robot)
  - Recent movement trails (dotted historical trail)
  - Mission rays connecting robots to pick/delivery targets
  - Congestion heatmap tiles overlaying floor cells
  - Shelf relocation advisory badges
  - Selected Robot highlight beacon (`🎯 R#`)

---

## 🚀 Installation & Launch Instructions

### Prerequisites
- Python 3.10 to 3.13
- Git

### 1. Clone & Set Up Environment
```powershell
cd C:\Users\Prasun\SmartWarehouse-AI.2
# Verify dependencies
python -m pip install streamlit plotly matplotlib pandas numpy scipy networkx pytest
```

### 2. Launch the Streamlit Control Centre
```powershell
python -m streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Automated Test Suite (151 Tests)

All 151 unit, integration, and regression tests run in $\approx 10$ seconds with 0 failures:

```powershell
python -m pytest tests/ -v
```

### Test Coverage Highlights:
- **Baseline Modules 1–7:** Space-time state transitions, vertex reservations, edge-swap prevention, 5-robot collision-free execution, wait-for-graph cycle detection, and deadlock resolution.
- **Module 8:** Dynamic obstacle injection, replan latency recording, reservation rollback, and evasive waiting.
- **Module 9:** 6 task assignment policies, Hungarian bipartite matching, order cancellation reservation cleanup, and workload balance Gini index.
- **Module 10:** Demand forecasting (EWMA, edge cases, preliminary status), shelf layout analysis, advisory relocation approval, congestion risk scoring, predictive maintenance formula, strategy benchmarking, and 3D camera/overlay rendering.

---

## 🎬 Step-by-Step Viva & Evaluation Guide

For university project demonstrations and evaluation vivas, follow this recommended walkthrough:

1. **Dashboard Initialization:**
   - Launch `app.py`. Note that the simulator starts with 3 robots on the 15×15 warehouse floor with 20 pre-populated orders.
   - The headline metric bar displays Makespan, Tasks Completed, Fleet Throughput, Replan Success Rate, Fleet Health, and Congestion Index.

2. **Run Execution & Movement:**
   - In the sidebar, select **Step Batch Size = 5** and click **⏩ Run ×5** several times.
   - Watch the robots in the **🗺 3D Digital Twin** tab leave their charging docks, follow color-coded paths, navigate to pickup spots, and proceed to packing stations.
   - Switch camera presets (**Top-Down**, **Isometric**, **Front**, **Side**) to demonstrate camera orbit controls.

3. **Demonstrate Dynamic Obstacle Replanning (Module 8):**
   - Click **🎬 Run Replanning Demo** in the sidebar.
   - The deterministic demo sets up an active route, drops an unexpected obstacle directly on cell `(4, 2)`, triggers Space-Time A* replanning, logs latency ($\approx 1-3\text{ ms}$), and routes the robot safely around the blockage without collisions.

4. **Demonstrate Task Operations (Module 9):**
   - Go to the **📋 Operations & Logs** tab.
   - Under *Create Custom Order*, select a shelf pick coordinate, a packing station, set priority to **Urgent**, and click **Register & Enqueue Order**.
   - Notice the order immediately appears in the queue with urgent priority and receives priority dispatching.

5. **Demonstrate AI Intelligence & Predictive Analytics (Module 10):**
   - Advance the simulation by clicking **⚡ Run 50** in the sidebar.
   - Go to the **🧠 AI Command Centre** tab and click **⚡ Run Full AI Analysis**.
   - Review the *Strategic AI Summary Cards* and the *Prioritized Autonomous Recommendations*.
   - Switch to **📈 Demand Forecasting**: inspect the EWMA trend chart for the top-demand shelves and the pick frequency ranking.
   - Switch to **🏭 Shelf Optimization**: view the 3D shelf relocation scatter, check the travel savings calculation, select an advisory proposal, and click **✅ Apply Approved Relocation**.
   - Switch to **🌡 Congestion Intelligence**: observe the 3D congestion heatmap and active risk zones.
   - Switch to **🤖 Predictive Maintenance**: review the battery, distance, and health scores for robots R1–R3, noting how distance travelled gradually impacts mechanical wear.
   - Switch to **🔬 Fleet Optimization**: click **🚀 Run Multi-Strategy Comparative Benchmark (40 steps)** to observe all 6 algorithms benchmarked head-to-head under identical conditions.

---

## ⚠️ Known Limitations & Future Scope

1. **Discrete Grid Topology:** Paths are computed on discrete 1m grid cells with Manhattan 4-connectivity. Continuous robot kinematics and turn radii can be incorporated in future iterations.
2. **Deterministic Task Arrival:** Initial orders are generated based on accessible shelf coordinates. Integration with live enterprise ERP/WMS APIs (e.g., SAP, Manhattan Associates) is a planned future expansion.
3. **Simulated Telemetry:** Sensor metrics (battery drain, wheel motor wear) are computed using digital-twin mathematical models rather than physical IoT sensors.
