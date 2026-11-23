# SmartWarehouse AI — Visual Upgrade Audit & Architectural Plan

**Date:** 2026-11-23  
**Branch:** `feature/threejs-digital-twin`  

---

## 1. Current State vs Target State

| Dimension | Current Scene (v1.0) | Target Scene (v2.0 Visual Transformation) |
|---|---|---|
| **World Scale** | 30m × 30m grid room | **90m × 70m Massive Logistics Complex** with active zone + peripheral ASRS scenery banks + mezzanine |
| **Floor** | Standard reflective slab | **High-gloss polished concrete with procedural wear, expansion joints, yellow safety zones, cyan transit tracks, and painted load markings ("A03", "MAX 500KG")** |
| **Racks & Inventory** | 3 pods × 2 blocks, basic boxes | **Towering 6-tier blue uprights (`#1F4E9C`) + orange beams (`#E8600C`), Euro-pallets, shrink-wrapped cartons, plastic totes, barcode plates** |
| **Robots (AMRs)** | Rounded yellow box AMR | **Authentic R2 AMR model: silver-grey + navy rounded chassis, dual circular cyan LED headlight rings, top LiDAR puck, cyan underglow, carrying stacked lidded totes** |
| **Conveyors & Arms** | Static conveyors, basic arm | **Dual roller + belt conveyors with animated rollers and blue totes, 6-axis articulated orange robotic arms with smooth pick-and-place cycles** |
| **Roof & Lighting** | Simple trusses, 5 point lights | **Steel Pratt/Warren trusses, skylight glazing pattern, endless rows of linear LED shop lights (InstancedMesh), soft contact shadows** |
| **Visual Modes** | Single dark industrial theme | **3 Switchable Modes: `Realistic Industrial` (R1/R4/R5), `Night Ops` (R2/R3/R6), `Digital Twin Wireframe` (R6/R7)** |
| **Overlays** | Path ribbons, discs, cylinders | **Animated chevron ribbons, particle flow streams, floating translucent holographic telemetry panels, volumetric hazard clouds** |
| **Camera & Control** | OrbitControls + 5 presets | **Extended presets (incl. Hero Close-Up), First-Person Walk Mode (WASD), and Autonomous Guided Presentation Tour** |

---

## 2. Performance Budgets (Targeted for Student Laptop)

- **Draw Calls:** ≤ 250 on Medium, ≤ 450 on High
- **Triangles:** ≤ 500k on Medium, ≤ 900k on High
- **Target Frame Rate:** ≥ 30 FPS at 1080p on Intel UHD / Iris Xe Graphics
- **Techniques:** Extensive `InstancedMesh` for ceiling lights, pallet racks, cartons, rollers; shared PBR materials; canvas texture atlases.
