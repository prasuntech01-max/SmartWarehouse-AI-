# SmartWarehouse AI — Robot Fleet Path Planning & Collision Avoidance Simulator

A high-performance Python-based autonomous warehouse robot simulator implementing multi-agent pathfinding, time-indexed reservation tables, deadlock handling, dynamic replanning, and fleet performance analytics.

---

## Key Features

1. **Space-Time A\* Path Planner**:
   - Time-indexed coordinate planning $(x, y, t)$ with `{Up, Down, Left, Right, Wait}` actions.
   - Admissible Manhattan distance heuristic with tie-breakers.

2. **Collision-Free Multi-Robot Coordination**:
   - **Vertex Conflict Prevention**: Ensures no two robots occupy cell $(x, y)$ at the same time $t$.
   - **Edge / Swap Conflict Prevention**: Guarantees no two robots traverse opposite directions along edge $(u, v)$ concurrently at timestep $t$.
   - Space-time reservation table maintaining mathematical collision guarantees ($0\%$ collision rate).

3. **Deadlock Resolution & Dynamic Replanning**:
   - Staggered departures, priority inversion, and open-bay yielding maneuvers.
   - Sudden mid-route dynamic obstacle injection with real-time recalculation of affected trajectories.

4. **Task Allocation & Mission Lifecycle**:
   - Autonomous dispatch: Idle at Dock $\to$ Transit to Shelf Pick Spot $\to$ Item Pickup $\to$ Transit to Packing Station $\to$ Delivery Offload.
   - Real metrics: Makespan, throughput, utilization, replanning latency (ms).

5. **Interactive Streamlit & Matplotlib Dashboard**:
   - Default $15 \times 15$ grid layout with 3 robots (configurable from 1 to 5 robots).
   - Live step-by-step or multi-step execution.
   - Point-and-click dynamic obstacle insertion.
   - Fleet scalability benchmark generator ($N=1\dots5$ robots).

---

## Directory Structure

```
SmartWarehouse-AI.2/
├── app.py                 # Streamlit interactive application
├── core/
│   ├── grid.py            # 15x15 warehouse floorplan (shelves, aisles, docks, stations)
│   ├── reservation.py     # Vertex & edge reservation tables
│   ├── planner.py         # Space-Time A* planner with wait-action support
│   ├── multi_agent.py     # Prioritized Planning & conflict detection verification
│   ├── deadlock.py        # Deadlock detection, yielding & priority inversion
│   ├── replanner.py       # Dynamic replanning engine upon obstacle insertion
│   └── task_manager.py    # Order queue & mission lifecycle
├── simulation/
│   ├── engine.py          # Discrete-time simulation engine
│   └── metrics.py         # Throughput, makespan, collision rate & latency analytics
├── visualization/
│   └── renderer.py        # Matplotlib 2D warehouse floorplan renderer
└── tests/
    ├── test_phase1.py     # Grid, Reservation, and A* unit tests
    ├── test_phase2.py     # Multi-Agent, Deadlocks, Replanning, Task Manager tests
    ├── test_phase3.py     # Simulation engine & metrics tests
    └── test_integration.py# End-to-end mission lifecycle & renderer tests
```

---

## Quickstart

### 1. Run the Interactive Streamlit Dashboard
```bash
streamlit run app.py
```

### 2. Run the Automated Test Suite
```bash
python -m pytest tests/ -v
```
