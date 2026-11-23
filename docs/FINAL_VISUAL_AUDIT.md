# SmartWarehouse AI — Final Visual Audit

**Date:** 2026-11-23  
**Branch:** `feature/threejs-digital-twin`  
**Phase:** Final Visual Round

---

## 1. Current Scene Inventory (Pre-Upgrade)

### Existing Elements
| Element | Present | Implementation | Quality |
|---------|---------|---------------|---------|
| Floor (polished concrete) | ✅ | Canvas texture, 92×76m | Good |
| Rack blocks (blue uprights) | ✅ | 3 active pods + 3 decor banks | Good |
| Orange beams | ✅ | Per-level BoxGeometry | Good |
| Cartons/totes | ✅ | Per-slot meshes | Moderate |
| Pallets | ✅ | BoxGeometry per slot | Basic |
| Conveyors | ✅ | 3 lines with instanced rollers | Good |
| Robotic arms | ✅ | 4 stations, animated | Good |
| ASRS cranes | ✅ | 2 aisles, yellow masts | Good |
| AMR robots | ✅ | Detailed R2 model | Good |
| Ceiling LED fixtures | ✅ | 120 InstancedMesh | Good |
| Steel columns | ✅ | Regular grid + yellow guards | Good |
| Mezzanine | ✅ | Glass balustrade + control room | Moderate |
| Roof trusses | ✅ | Long beam InstancedMesh | Basic |
| Wall displays | ✅ | Canvas texture KPI screen | Good |
| Charging docks | ✅ | 5 stations with cyan rings | Good |
| Floor markings | ✅ | Yellow lines, cyan tracks, decals | Good |
| Themes (3) | ✅ | Realistic/Night Ops/Wireframe | Good |
| Path ribbons | ✅ | TubeGeometry with chevrons | Good |
| Walk mode | ✅ | WASD + eye height 1.7m | Good |
| Presentation tour | ✅ | 5 stops with theme switching | Good |

### Missing Elements (Gap List)
| Element | Priority | Spec Reference |
|---------|----------|---------------|
| Perimeter walls (cladding) | HIGH | R1, R4 |
| Dock doors (sectional) | HIGH | R4 |
| Rack diagonal bracing | MEDIUM | R1 |
| Rack base plates | MEDIUM | R1 |
| Wire-mesh decking | LOW | R1 |
| Pallet realistic slats | MEDIUM | R1 |
| Shrink-wrap variation | LOW | R1 |
| Inventory height variation | MEDIUM | R1 |
| Empty slots on some levels | MEDIUM | R1 |
| Hanging aisle signs | HIGH | R1, R2 |
| Zone signs | HIGH | R5 |
| Safety signs | MEDIUM | R4 |
| Guard rails at rack bases | HIGH | R4 |
| Bollards at aisle ends | MEDIUM | R4 |
| Belt conveyors | LOW | R7 |
| Conveyor curves/merges | LOW | R7 |
| Sensor markers (domes) | MEDIUM | Sec 9.6 |
| Hazard zone visuals | MEDIUM | Sec 9.6 |
| Collision prediction rings | MEDIUM | Sec 9.3 |
| Heatmap overlay | LOW | Sec 9.7 |
| Debug overlay | MEDIUM | Sec 12.5 |
| Auto quality tier | MEDIUM | Sec 12.1 |
| __SW_DEBUG.getRobots() | HIGH | Sec 12.5 |

## 2. Grid → World Mapping

```
gridToWorld(gx, gy) = { x: gx * CELL_SIZE_M, y: 0, z: gy * CELL_SIZE_M }
CELL_SIZE_M = 2.0
Active grid: 15×15 → 30m × 30m
Visual hall: 120m × 100m (40m decor on each side)
Hall height: 16m clear
```

## 3. Renderer/Lighting/Material State

### Renderer
- WebGLRenderer with antialias, PCFSoftShadowMap
- ACESFilmicToneMapping, exposure 1.2
- SRGBColorSpace output
- Pixel ratio: min(devicePixelRatio, 2)

### Lighting
- 1× HemisphereLight (sky #94a3b8, ground #0f172a, 0.75)
- 1× DirectionalLight (key sun, shadow casting, 2048px map)
- 1× DirectionalLight (night accent, cyan tint, no shadow)

### Materials
- MeshStandardMaterial throughout (no Physical except shrink-wrap)
- Proper metalness/roughness PBR values
- Canvas textures for floor, cartons, decals, monitor, path arrows

## 4. Baseline Performance Numbers

| Metric | Value | Notes |
|--------|-------|-------|
| Draw calls | ~180 | With 3 robots, all racks |
| Triangles | ~350k | Moderate |
| FPS | 55-60 | On discrete GPU |
| Bundle size | 529 KiB | Minified |
| Texture memory | ~8 MB | Canvas textures |
| Scene objects | ~1200 | Groups + meshes |

## 5. Triangle/Draw-Call/Texture Budget

| Tier | Draw Calls | Triangles | Textures | FPS Target |
|------|-----------|-----------|----------|-----------|
| LOW | ≤150 | ≤250k | ≤2048² | ≥30 |
| MEDIUM | ≤300 | ≤700k | ≤2048² | ≥30 |
| HIGH | ≤600 | ≤1.5M | ≤2048² | ≥30 |

## 6. MUST-PRESERVE List

- All 13 modules and their pages
- 189 existing tests
- Bridge contract compatibility
- Plotly 3D and 2D Matplotlib fallbacks
- Existing camera presets (ISO, TOP, AISLE, DOCK, HERO, CINE)
- Walk mode and presentation tour
- Robot selection and inspection card
- Theme switching (Realistic, Night Ops, Wireframe)
- Simulation controls integration
- IoT sensor and hazard display
- Authentication and database integrity

## 7. Upgrade Plan

### Phase 1: Enhanced Foundation
- Expand visual hall dimensions (120m × 100m)
- Add perimeter walls, dock doors, additional structural elements
- Enhance floor markings with more zones and detail

### Phase 2: Dense Industrial Content
- Upgrade racking with bracing, base plates, wire decking
- Add varied inventory (pallets with slats, varied cartons, empty slots)
- Add hanging signs, zone markers, safety signage
- Add guard rails and bollards

### Phase 3: Enhanced AMR and Automation
- Refine AMR model details
- Enhance conveyor detail
- Add dock bay detail with signal lights

### Phase 4: Overlays and Effects
- Add sensor dome markers
- Add hazard zone visualizations
- Add collision prediction rings
- Add heatmap floor overlay
- Add debug overlay panel

### Phase 5: Performance and Polish
- Implement quality tiers with auto-switching
- Add __SW_DEBUG interface
- Optimize instancing and merging
- Test and profile
