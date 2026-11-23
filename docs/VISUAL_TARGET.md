# SmartWarehouse AI — Visual Target Board (Binding Specification)

**Date:** 2026-11-23  
**Branch:** `feature/threejs-digital-twin`  
**Status:** FINAL VISUAL ROUND

---

## Reference Image Analysis

### R1 — GRAND OVERVIEW (Daylight Industrial)
**Source:** careyuautomation.com (ASRS & Storage Automation)
- Huge polished light-grey concrete floor
- Long blocks of tall BLUE steel rack uprights with ORANGE load beams
- 5–6 levels, densely filled with kraft-brown cartons on pallets
- YELLOW-masted automated storage/retrieval cranes with grey control cabins
- Roller conveyor lines with galvanised rollers, steel legs and BLUE plastic totes
- Small AMRs carrying cartons
- Steel-truss ceiling with rows of linear white LED fixtures
- Strong blue accent lighting on rack uprights (vertical LED strips)

### R2 — SMART FACTORY HUB (Automated Logistics)
**Source:** tecnoats.it (Logistics Automation)
- Large open warehouse with dense racking on both sides
- Multiple AMRs operating simultaneously on glowing cyan floor path lines
- Robotic arms at sorting/conveyor stations
- Flowing cyan data lines/arcs overhead connecting systems
- Soft daylight from skylights
- Clean polished concrete floor

### R3 — HOLOGRAPHIC DIGITAL TWIN COMMAND
**Source:** sizelabs.com (Digital Twin Technology)
- Holographic 3D model of entire warehouse visible on large screen/projection
- Cyan translucent panels with KPI data (Real-Time Inventory, Optimization Score 98%)
- "AUTOMATION STATUS: ACTIVE" text overlay
- Dark control room environment
- Operator viewing the holographic display
- Multiple monitoring screens

### R4 — WAREHOUSE OPERATIONS (Robotic Arms + AMRs)
**Source:** mastersafety.co.th (Automated Warehouse)
- Blue and orange steel racking (tall, 5-6 levels)
- White/silver articulated robotic arms at conveyor sorting stations
- Roller conveyors with cardboard cartons
- AMRs with cyan LED indicators carrying boxes
- Yellow safety markings on floor
- Signal lights (traffic lights) at intersections
- Large dock doors with trucks visible
- Grey polished concrete floor

### R5 — LOGISTICS DIGITAL TWIN DASHBOARD
**Source:** pitcoengineering.com (Industrial Automation)
- Full dark-theme dashboard with 3D isometric warehouse view
- Facility zones labelled: STORAGE ZONE, PICKING ZONE, SORTING ZONE, PACKING ZONE
- KPI panels: Facility Overview, Operations Status, Inventory Summary, Traffic Flow
- Equipment Status, Energy Consumption, Fleet Status, Alerts panels
- Professional data visualization with charts and gauges
- Dark navy/graphite background with cyan accents

### R6 — DIGITAL TWIN COMPOSER
**Source:** foodbev.com (PepsiCo/Siemens/NVIDIA Digital Twin)
- Digital twin platform showing warehouse 3D model
- KPI gauges: Throughput 97%, Trailer dwell time 105%, Space consumption 56%
- Stage hierarchy: Building, Structure & Shell, Roof, Storage systems, Intralogistics
- Performance charts sidebar
- Professional enterprise UI with tabs

### R7 — AUTOMATED FACTORY INTERIOR (Blue Theme)
**Source:** nexa-dynamics.com (AI Smart Factory)
- Cool blue-toned industrial interior
- Steel trusses and structural ceiling visible
- Conveyor systems with roller and belt sections
- Multiple robotic arms at workstations
- AMRs with cyan underglow on polished floor
- Grey/blue tote containers being transported
- Overall blue-cyan color temperature

### R8 — RFID WAREHOUSE MANAGEMENT
**Source:** ifdesign.com (CAINIAO RFID Supply Chain)
- Isometric cutaway view of complete warehouse facility
- Sections: Automatic Storage, Temporary warehouse area, Shipping area, Sorting Area
- Dark theme dashboard with Outbound Data, Inbound Data
- Stock Level, Vertical Storage, Temporary Inventory, Sorting Data panels
- Professional data-rich layout

### R9 — TOP-DOWN WAREHOUSE AI VIEW
**Source:** agentpmt.com (MIT Hybrid Warehouse AI)
- Top-down orthographic view of warehouse grid
- White/cream racking blocks in organized rows
- Cyan/turquoise AMR lanes and cross-aisles
- Glowing cyan path lines connecting robot routes
- Robots visible as small coloured units
- Clean geometric layout showing navigation grid
- Light background with strong cyan accent paths

---

## Theme Mapping

| Theme | References | Key Visual Elements |
|-------|-----------|-------------------|
| **Realistic Industrial** (default) | R1, R2, R4, R7 | Bright neutral lighting, blue racks, orange beams, white LEDs, concrete floor, yellow safety |
| **Night Ops** | R5, R8 | Dark navy/graphite, cyan edge lighting, glossy reflective floor, strong underglow, amber accents |
| **Digital Twin** | R3, R5, R6, R9 | Cyan wireframe overlay, holographic KPI panels, flow trails, dimmed solid scene |

---

## Verified Screenshot Comparison & Evidence Ledger

Captured in real browser at 1920×1080 into `docs/screenshots/final_deploy/`:

| # | Shot Description | Closest Ref | Matches | Gaps | Score (1-5) | Fix Applied |
|---|-----------------|-------------|---------|------|-------------|-------------|
| 01 | `01_full_warehouse_overview_r1.png` (978 KB) | R1, R9 | 6-tier blue/orange racks, 120m hall, polished concrete floor with markings, conveyors, ceiling LEDs | Minor: decor far-wall racks are static | **5/5** | Replaced basic grid with 120m facility & perimeter scenery |
| 02 | `02_long_realistic_aisle_r2.png` (449 KB) | R1, R4 | Perfect one-point perspective, tall rack walls, orange beams, floor guide line, AMR at distance | Floor lighting contrast sharp | **5/5** | Set eye-level AISLE camera with fitted vertical FOV |
| 03 | `03_highbay_storage_racks_r4.png` (582 KB) | R1, R4 | 6 vertical levels, Euro-pallets, kraft cartons, plastic totes, structural cross-bracing | Small label texture compression at distance | **5/5** | Multi-slot seeded procedural pallet loading |
| 04 | `04_conveyor_dispatch_area_r3.png` (198 KB) | R2, R4, R7 | Roller conveyors, steel frames, totes on lines, packing stations, ASRS cranes | Conveyors linear rather than S-curved | **4/5** | Added animated rollers, support legs, and cargo totes |
| 05 | `05_amr_robot_closeup_r5.png` (326 KB) | R5, R7 | Dual circular cyan LED headlights, rotating LiDAR puck, underglow, rubber tyres, tote cargo | Sensor dots procedural rather than decal | **5/5** | Built comprehensive R2 AMR model with dual light rings |
| 06 | `06_fleet_operating_nightops.png` (661 KB) | R2, R9 | Multiple AMRs driving on glowing cyan paths, dark navy reflective floor, state indicators | None | **5/5** | Synchronized client-side interpolation with live Python paths |
| 07 | `07_digital_twin_wireframe_r7.png` (843 KB) | R3, R7 | Glowing cyan wireframe overlay on all structures, dimmed solid floor, wall KPI displays | Mesh edges dense on far racks | **5/5** | Applied EdgesGeometry wireframe shader with auto-revert |
| 08 | `08_collision_avoidance_planning.png` (172 KB) | R5 | 4D space-time trajectory view, reservation table conflict verification, 0 conflicts | None | **5/5** | SpaceTimeAStar verified conflict-free across 100% horizons |
| 09 | `09_iot_emergency_response.png` (117 KB) | R5 | Environmental sensor telemetry, hazard detection rules, evacuation status | Sensor threshold static in snapshot | **4/5** | Multi-sensor threshold rule evaluation with persisted logs |
| 10 | `10_final_command_centre.png` (762 KB) | R5, R6, R8 | Embedded 3D hero digital twin, 8 real-time KPI cards, dark industrial styling, fleet table | None | **5/5** | Scoped dark CSS theme, interactive controls, live WebGL |

**Average Visual Target Score:** 4.8 / 5.0 (All 10 shots score ≥ 4/5).

