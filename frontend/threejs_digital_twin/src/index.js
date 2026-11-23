/**
 * SmartWarehouse AI — Three.js Digital Twin (Complete Scene)
 * ═══════════════════════════════════════════════════════════
 * A production-ready, AAA-quality 3D warehouse visualization
 * with three switchable themes: Realistic Industrial, Night Ops, Digital Twin Wireframe.
 *
 * Three.js r164 — Webpack 5 bundle — No external assets
 * All textures procedural (CanvasTexture / DataTexture)
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/* ═══════════════════════════════════════════════════════════════
   §0  CONSTANTS & CONFIG
   ═══════════════════════════════════════════════════════════════ */

const TOTAL_W = 120, TOTAL_D = 100, HALL_H = 16;
const GRID_COLS = 15, GRID_ROWS = 15, CELL = 2.0;
const GRID_OX = (TOTAL_W - GRID_COLS * CELL) / 2;
const GRID_OZ = (TOTAL_D - GRID_ROWS * CELL) / 2;
const TIER_H = 1.75, RACK_LEVELS = 6;
const RACK_H = RACK_LEVELS * TIER_H;

const X_BLOCKS = [[2, 3], [6, 7], [10, 11]];
const Y_BLOCKS = [[3, 5], [8, 10]];
const CHARGING = [[1, 0], [4, 0], [7, 0], [10, 0], [13, 0]];
const PACKING = [[2, 14], [6, 14], [10, 14], [12, 14]];
const PICKING = [[0, 4], [0, 7], [0, 10]];

const COL_CYAN = 0x00f0ff, COL_AMBER = 0xffb300, COL_RED = 0xff1744;
const COL_BLUE_RACK = 0x1565c0, COL_ORANGE_BEAM = 0xff8f00;
const COL_YELLOW = 0xffd600, COL_GREEN = 0x00e676;
const COL_NAVY = 0x0a1628, COL_SILVER = 0xb0bec5;
const COL_DARK_BG = 0x0d1420;

const CAMERA_PRESETS = {
  CINEMATIC: { pos: [75, 55, 75], target: [TOTAL_W / 2, 0, TOTAL_D / 2] },
  ISO:       { pos: [90, 60, 90], target: [TOTAL_W / 2, 0, TOTAL_D / 2] },
  TOP:       { pos: [TOTAL_W / 2, 80, TOTAL_D / 2], target: [TOTAL_W / 2, 0, TOTAL_D / 2] },
  AISLE:     { pos: [GRID_OX + 5 * CELL, 1.7, GRID_OZ + 1], target: [GRID_OX + 5 * CELL, 1.7, GRID_OZ + 14 * CELL] },
  DOCK:      { pos: [TOTAL_W / 2, 8, TOTAL_D - 5], target: [TOTAL_W / 2, 4, TOTAL_D] },
  HERO:      { pos: [GRID_OX + 7 * CELL + 4, 3, GRID_OZ + 7 * CELL + 4], target: [GRID_OX + 7 * CELL, 0.6, GRID_OZ + 7 * CELL] },
  DIGITAL_TWIN: { pos: [60, 45, 60], target: [TOTAL_W / 2, 5, TOTAL_D / 2] },
};

const TOUR_STOPS = [
  { preset: 'CINEMATIC', theme: 'realistic', title: 'Grand Overview', caption: 'SmartWarehouse AI — Automated Distribution Centre' },
  { preset: 'AISLE', theme: 'realistic', title: 'Narrow Aisle', caption: 'High-density storage with 6-level racking' },
  { preset: 'DOCK', theme: 'nightops', title: 'Loading Docks', caption: 'Night operations — Dispatch and receiving' },
  { preset: 'HERO', theme: 'nightops', title: 'AMR Close-up', caption: 'Autonomous Mobile Robot fleet' },
  { preset: 'DIGITAL_TWIN', theme: 'wireframe', title: 'Digital Twin', caption: 'Real-time wireframe overlay with KPI analytics' },
];

const STATE_COLORS = {
  MOVING: COL_CYAN, IDLE: 0xffffff, WAITING: COL_AMBER,
  BLOCKED: COL_RED, CHARGING: 0x2979ff, EMERGENCY: COL_RED,
};

/* ═══════════════════════════════════════════════════════════════
   §1  UTILITY FUNCTIONS
   ═══════════════════════════════════════════════════════════════ */

/** Mulberry32 seeded PRNG (deterministic) */
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(42);
const rngRange = (a, b) => a + rng() * (b - a);
const rngInt = (a, b) => Math.floor(rngRange(a, b + 1));
const rngPick = (arr) => arr[rngInt(0, arr.length - 1)];

/** Grid cell to world position */
function gridToWorld(gx, gy) {
  return new THREE.Vector3(GRID_OX + gx * CELL + CELL / 2, 0, GRID_OZ + gy * CELL + CELL / 2);
}

/** Smooth lerp factor (frame-rate independent) */
function damp(lambda, dt) { return 1 - Math.exp(-lambda * dt); }

/** Create eased camera animation state */
function createCamAnim(from, to, dur) {
  return { fromPos: from.pos.clone(), fromTarget: from.target.clone(), toPos: to.pos.clone(), toTarget: to.target.clone(), dur, t: 0 };
}

/** Ease in-out cubic */
function easeInOutCubic(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

/** Create a canvas texture with text/drawings */
function makeCanvasTex(w, h, drawFn) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  drawFn(ctx, w, h);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

/** Shared texture atlas for signage labels */
let _signageAtlas = null, _signageRegions = {};
function getSignageAtlas() {
  if (_signageAtlas) return { tex: _signageAtlas, regions: _signageRegions };
  const W = 1024, H = 1024;
  const tex = makeCanvasTex(W, H, (ctx) => {
    ctx.fillStyle = '#111827';
    ctx.fillRect(0, 0, W, H);
    const labels = [
      'A01', 'A02', 'A03', 'A04', 'A05', 'A06',
      'DOCK', 'SORT', 'PACK', 'DISPATCH', 'CHARGING',
      'MAX 500KG', 'CAUTION', 'HARD HAT AREA', 'NO ENTRY',
      'SmartWarehouse AI — Digital Twin',
      'DOCK 01', 'DOCK 02', 'DOCK 03', 'DOCK 04', 'DOCK 05', 'DOCK 06',
    ];
    const colW = W / 4, rowH = H / 8;
    labels.forEach((lbl, i) => {
      const col = i % 4, row = Math.floor(i / 4);
      const x = col * colW, y = row * rowH;
      _signageRegions[lbl] = { u0: x / W, v0: 1 - (y + rowH) / H, u1: (x + colW) / W, v1: 1 - y / H };
      ctx.fillStyle = lbl.startsWith('DOCK') ? '#1e293b' : (lbl === 'CAUTION' || lbl === 'NO ENTRY' || lbl === 'HARD HAT AREA') ? '#78350f' : '#1e3a5f';
      ctx.fillRect(x + 2, y + 2, colW - 4, rowH - 4);
      ctx.strokeStyle = lbl.includes('CAUTION') || lbl.includes('NO ENTRY') ? '#fbbf24' : '#38bdf8';
      ctx.lineWidth = 2;
      ctx.strokeRect(x + 2, y + 2, colW - 4, rowH - 4);
      ctx.fillStyle = lbl.includes('CAUTION') || lbl.includes('NO ENTRY') || lbl.includes('HARD HAT') ? '#fbbf24' : '#e0f7ff';
      ctx.font = lbl.length > 12 ? 'bold 20px sans-serif' : 'bold 32px sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(lbl, x + colW / 2, y + rowH / 2);
    });
  });
  _signageAtlas = tex;
  return { tex, regions: _signageRegions };
}

/** Create a UV-mapped plane for a specific atlas region */
function makeSignPlane(label, w, h) {
  const { tex, regions } = getSignageAtlas();
  const r = regions[label] || { u0: 0, v0: 0, u1: 0.25, v1: 0.125 };
  const geo = new THREE.PlaneGeometry(w, h);
  const uv = geo.attributes.uv;
  uv.setXY(0, r.u0, r.v1); uv.setXY(1, r.u1, r.v1);
  uv.setXY(2, r.u0, r.v0); uv.setXY(3, r.u1, r.v0);
  uv.needsUpdate = true;
  const mat = new THREE.MeshStandardMaterial({ map: tex, transparent: true, side: THREE.DoubleSide });
  return new THREE.Mesh(geo, mat);
}

/** Dispose helpers */
function disposeMesh(m) {
  if (m.geometry) m.geometry.dispose();
  if (m.material) {
    if (Array.isArray(m.material)) m.material.forEach(mt => { if (mt.map) mt.map.dispose(); mt.dispose(); });
    else { if (m.material.map) m.material.map.dispose(); m.material.dispose(); }
  }
}
function disposeGroup(g) {
  g.traverse(child => { if (child.isMesh) disposeMesh(child); });
}

/* ═══════════════════════════════════════════════════════════════
   §2  PROCEDURAL TEXTURES
   ═══════════════════════════════════════════════════════════════ */

function makeFloorTexture() {
  return makeCanvasTex(2048, 2048, (ctx, w, h) => {
    // Base polished concrete
    ctx.fillStyle = '#8a8a82';
    ctx.fillRect(0, 0, w, h);
    // Noise / wear variation
    const seed = mulberry32(101);
    for (let i = 0; i < 15000; i++) {
      const x = seed() * w, y = seed() * h;
      const s = 2 + seed() * 6;
      const v = 120 + seed() * 40;
      ctx.fillStyle = `rgba(${v},${v},${v - 10},0.15)`;
      ctx.fillRect(x, y, s, s);
    }
    // Expansion joints
    ctx.strokeStyle = '#6b6b62';
    ctx.lineWidth = 3;
    for (let i = 1; i < 8; i++) {
      ctx.beginPath(); ctx.moveTo(i * w / 8, 0); ctx.lineTo(i * w / 8, h); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * h / 8); ctx.lineTo(w, i * h / 8); ctx.stroke();
    }
    // Scuff marks
    for (let i = 0; i < 50; i++) {
      ctx.strokeStyle = `rgba(60,60,55,${0.05 + seed() * 0.1})`;
      ctx.lineWidth = 1 + seed() * 3;
      ctx.beginPath();
      const sx = seed() * w, sy = seed() * h;
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx + (seed() - 0.5) * 100, sy + (seed() - 0.5) * 100);
      ctx.stroke();
    }
  });
}

function makeFloorMarkingsTexture() {
  return makeCanvasTex(2048, 2048, (ctx, w, h) => {
    ctx.clearRect(0, 0, w, h);
    // Scale: texture covers TOTAL_W × TOTAL_D
    const sx = w / TOTAL_W, sy = h / TOTAL_D;

    // Yellow safety lines along main aisles
    ctx.strokeStyle = '#ffd600';
    ctx.lineWidth = 4;
    // Grid boundary double lines
    const gx0 = GRID_OX * sx, gy0 = GRID_OZ * sy;
    const gx1 = (GRID_OX + GRID_COLS * CELL) * sx, gy1 = (GRID_OZ + GRID_ROWS * CELL) * sy;
    ctx.strokeRect(gx0 - 2, gy0 - 2, gx1 - gx0 + 4, gy1 - gy0 + 4);
    ctx.strokeRect(gx0 - 6, gy0 - 6, gx1 - gx0 + 12, gy1 - gy0 + 12);

    // Cyan robot transit lines (centre of each row between racks)
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 6]);
    for (let r = 0; r < GRID_ROWS; r++) {
      const isRackRow = Y_BLOCKS.some(([y0, y1]) => r >= y0 && r <= y1);
      if (!isRackRow) {
        const cy = (GRID_OZ + r * CELL + CELL / 2) * sy;
        ctx.beginPath(); ctx.moveTo(gx0, cy); ctx.lineTo(gx1, cy); ctx.stroke();
      }
    }
    // Vertical transit lines
    for (let c = 0; c < GRID_COLS; c++) {
      const isRackCol = X_BLOCKS.some(([x0, x1]) => c >= x0 && c <= x1);
      if (!isRackCol) {
        const cx = (GRID_OX + c * CELL + CELL / 2) * sx;
        ctx.beginPath(); ctx.moveTo(cx, gy0); ctx.lineTo(cx, gy1); ctx.stroke();
      }
    }
    ctx.setLineDash([]);

    // Zone codes
    ctx.font = 'bold 18px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff88';
    for (let bx = 0; bx < X_BLOCKS.length; bx++) {
      for (let by = 0; by < Y_BLOCKS.length; by++) {
        const [x0] = X_BLOCKS[bx], [y0] = Y_BLOCKS[by];
        const cx = (GRID_OX + (x0 + 0.5) * CELL) * sx;
        const cy = (GRID_OZ + (y0 - 0.5) * CELL) * sy;
        ctx.fillText(`A${String(bx * 2 + by + 1).padStart(2, '0')}`, cx, cy);
      }
    }

    // MAX 500KG markings near racks
    ctx.font = 'bold 12px sans-serif';
    ctx.fillStyle = '#ffd60044';
    for (const [x0] of X_BLOCKS) {
      for (const [y0, y1] of Y_BLOCKS) {
        const cx = (GRID_OX + x0 * CELL) * sx;
        const cy = (GRID_OZ + ((y0 + y1) / 2) * CELL) * sy;
        ctx.fillText('MAX 500KG', cx + 20, cy);
      }
    }

    // Directional arrows
    ctx.fillStyle = '#ffffff55';
    const drawArrow = (x, y, angle) => {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.beginPath();
      ctx.moveTo(0, -10); ctx.lineTo(6, 2); ctx.lineTo(2, 2); ctx.lineTo(2, 10);
      ctx.lineTo(-2, 10); ctx.lineTo(-2, 2); ctx.lineTo(-6, 2);
      ctx.closePath(); ctx.fill();
      ctx.restore();
    };
    // Arrows along main aisles
    for (let i = 0; i < 5; i++) {
      drawArrow(gx0 + (gx1 - gx0) * (i + 0.5) / 5, gy0 - 20, 0);
      drawArrow(gx0 + (gx1 - gx0) * (i + 0.5) / 5, gy1 + 20, Math.PI);
    }

    // White pedestrian walkway lines
    ctx.strokeStyle = '#ffffff44';
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 5]);
    // Along the left side of the grid
    const walkX = (GRID_OX - 2) * sx;
    ctx.beginPath(); ctx.moveTo(walkX, gy0); ctx.lineTo(walkX, gy1); ctx.stroke();
    // Along the bottom
    const walkY = (GRID_OZ + GRID_ROWS * CELL + 2) * sy;
    ctx.beginPath(); ctx.moveTo(gx0, walkY); ctx.lineTo(gx1, walkY); ctx.stroke();
    ctx.setLineDash([]);

    // Hazard stripes at dock zone
    const dockY = (TOTAL_D - 6) * sy;
    for (let i = 0; i < 20; i++) {
      ctx.fillStyle = i % 2 === 0 ? '#ffd600' : '#1a1a1a';
      ctx.fillRect(TOTAL_W / 2 * sx - 200 + i * 20, dockY, 20, 8);
    }
  });
}

function makeCartonTexture() {
  return makeCanvasTex(256, 256, (ctx, w, h) => {
    // Kraft cardboard base
    ctx.fillStyle = '#c4a265';
    ctx.fillRect(0, 0, w, h);
    // Grain variation
    const seed = mulberry32(77);
    for (let i = 0; i < 2000; i++) {
      const v = 170 + seed() * 40;
      ctx.fillStyle = `rgba(${v},${v - 20},${v - 50},0.08)`;
      ctx.fillRect(seed() * w, seed() * h, 3 + seed() * 4, 1 + seed() * 2);
    }
    // Tape stripe
    ctx.fillStyle = '#8b6914aa';
    ctx.fillRect(0, h * 0.44, w, h * 0.12);
    // Barcode label
    ctx.fillStyle = '#fff';
    ctx.fillRect(w * 0.6, h * 0.65, w * 0.3, h * 0.25);
    ctx.fillStyle = '#000';
    for (let i = 0; i < 15; i++) {
      const bw = 1 + seed() * 3;
      ctx.fillRect(w * 0.63 + i * 4, h * 0.70, bw, h * 0.12);
    }
    ctx.font = '10px monospace';
    ctx.fillText('SKU-' + String(seed() * 99999 | 0).padStart(5, '0'), w * 0.63, h * 0.87);
  });
}

function makeWireMeshTexture() {
  return makeCanvasTex(128, 128, (ctx, w, h) => {
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = '#8899aa';
    ctx.lineWidth = 1;
    const sp = 8;
    for (let x = 0; x < w; x += sp) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += sp) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
  });
}

function makeChevronTexture() {
  return makeCanvasTex(256, 64, (ctx, w, h) => {
    ctx.fillStyle = '#001822';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#00f0ff';
    for (let i = 0; i < 8; i++) {
      const x = i * 32;
      ctx.beginPath();
      ctx.moveTo(x, h); ctx.lineTo(x + 16, 0); ctx.lineTo(x + 32, h);
      ctx.lineTo(x + 24, h); ctx.lineTo(x + 16, 12); ctx.lineTo(x + 8, h);
      ctx.closePath(); ctx.fill();
    }
  });
}

function makeKPITexture(data) {
  return makeCanvasTex(512, 256, (ctx, w, h) => {
    ctx.fillStyle = '#0a1628';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#00f0ff44';
    ctx.lineWidth = 1;
    ctx.strokeRect(4, 4, w - 8, h - 8);

    ctx.fillStyle = '#00f0ff';
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('DIGITAL TWIN: SmartWarehouse X-4', w / 2, 28);

    ctx.font = '12px sans-serif';
    ctx.textAlign = 'left';
    const metrics = data || {
      throughput: '127 units/hr', utilization: '84%', robots: '5 active',
      tasks: '23 pending', uptime: '99.7%', alerts: '0'
    };
    const keys = Object.keys(metrics);
    keys.forEach((k, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 20 + col * 240, y = 60 + row * 40;
      ctx.fillStyle = '#64748b';
      ctx.fillText(k.toUpperCase(), x, y);
      ctx.fillStyle = '#e0f7ff';
      ctx.font = 'bold 18px monospace';
      ctx.fillText(String(metrics[k]), x, y + 22);
      ctx.font = '12px sans-serif';
    });

    // Mini bar chart
    ctx.fillStyle = '#00f0ff33';
    const barSeed = mulberry32(99);
    for (let i = 0; i < 12; i++) {
      const bh = 20 + barSeed() * 50;
      ctx.fillRect(20 + i * 38, h - 10 - bh, 30, bh);
    }
    ctx.fillStyle = '#00f0ff';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Hourly Throughput', w / 2, h - 2);
  });
}

/* ═══════════════════════════════════════════════════════════════
   §3  MATERIALS LIBRARY
   ═══════════════════════════════════════════════════════════════ */

const materials = {};

function initMaterials() {
  const floorTex = makeFloorTexture();
  floorTex.wrapS = floorTex.wrapT = THREE.RepeatWrapping;
  floorTex.repeat.set(8, 8);

  materials.floor = new THREE.MeshStandardMaterial({ map: floorTex, roughness: 0.55, metalness: 0.1 });
  materials.floorNight = new THREE.MeshStandardMaterial({ map: floorTex, roughness: 0.2, metalness: 0.4, envMapIntensity: 1.5 });

  materials.concrete = new THREE.MeshStandardMaterial({ color: 0x9e9e9e, roughness: 0.8 });
  materials.steel = new THREE.MeshStandardMaterial({ color: 0x78909c, roughness: 0.35, metalness: 0.8 });
  materials.steelDark = new THREE.MeshStandardMaterial({ color: 0x37474f, roughness: 0.4, metalness: 0.7 });
  materials.wall = new THREE.MeshStandardMaterial({ color: 0xc5c5bd, roughness: 0.9, side: THREE.DoubleSide });
  materials.wallInner = new THREE.MeshStandardMaterial({ color: 0xe0e0d8, roughness: 0.9, side: THREE.DoubleSide });

  materials.rackBlue = new THREE.MeshStandardMaterial({ color: COL_BLUE_RACK, roughness: 0.5, metalness: 0.6 });
  materials.beamOrange = new THREE.MeshStandardMaterial({ color: COL_ORANGE_BEAM, roughness: 0.45, metalness: 0.5 });
  materials.yellow = new THREE.MeshStandardMaterial({ color: COL_YELLOW, roughness: 0.6 });
  materials.yellowGuard = new THREE.MeshStandardMaterial({ color: 0xf9a825, roughness: 0.5, metalness: 0.3 });

  materials.palletWood = new THREE.MeshStandardMaterial({ color: 0xa1662f, roughness: 0.9 });

  const cartonTex = makeCartonTexture();
  materials.carton = new THREE.MeshStandardMaterial({ map: cartonTex, roughness: 0.85 });

  materials.shrinkWrap = new THREE.MeshStandardMaterial({ color: 0xd4e9f7, roughness: 0.1, metalness: 0.0, transparent: true, opacity: 0.45 });
  materials.blueTote = new THREE.MeshStandardMaterial({ color: 0x1976d2, roughness: 0.5 });
  materials.greyTote = new THREE.MeshStandardMaterial({ color: 0x757575, roughness: 0.5 });

  materials.cyanEmissive = new THREE.MeshStandardMaterial({ color: COL_CYAN, emissive: COL_CYAN, emissiveIntensity: 0.8, roughness: 0.3 });
  materials.cyanGlow = new THREE.MeshBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.6 });
  materials.amberEmissive = new THREE.MeshStandardMaterial({ color: COL_AMBER, emissive: COL_AMBER, emissiveIntensity: 1.0 });
  materials.redEmissive = new THREE.MeshStandardMaterial({ color: COL_RED, emissive: COL_RED, emissiveIntensity: 1.0 });
  materials.greenEmissive = new THREE.MeshStandardMaterial({ color: COL_GREEN, emissive: COL_GREEN, emissiveIntensity: 0.8 });
  materials.whiteEmissive = new THREE.MeshStandardMaterial({ color: 0xfff8e1, emissive: 0xfff8e1, emissiveIntensity: 0.6, roughness: 0.3 });

  materials.glass = new THREE.MeshStandardMaterial({ color: 0x90caf9, roughness: 0.05, metalness: 0.2, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
  materials.darkGlass = new THREE.MeshStandardMaterial({ color: 0x1a237e, roughness: 0.05, metalness: 0.3, transparent: true, opacity: 0.5, side: THREE.DoubleSide });

  materials.robotSilver = new THREE.MeshStandardMaterial({ color: COL_SILVER, roughness: 0.3, metalness: 0.7 });
  materials.robotNavy = new THREE.MeshStandardMaterial({ color: COL_NAVY, roughness: 0.4, metalness: 0.5 });
  materials.robotOrange = new THREE.MeshStandardMaterial({ color: 0xff6d00, roughness: 0.4, metalness: 0.5 });
  materials.rubber = new THREE.MeshStandardMaterial({ color: 0x212121, roughness: 0.95 });

  // ── 5 Robot Specific High-Fidelity Materials ──
  materials.titanWhite = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.25, metalness: 0.35 });
  materials.titanDark = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.35, metalness: 0.85 });
  materials.atlasArmorWhite = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.2, metalness: 0.45 });
  materials.atlasArmorBlue = new THREE.MeshStandardMaterial({ color: 0x1d4ed8, roughness: 0.25, metalness: 0.65 });
  materials.atlasCoreCyan = new THREE.MeshStandardMaterial({ color: 0x00f0ff, emissive: 0x00f0ff, emissiveIntensity: 1.2, roughness: 0.1 });
  materials.vortexGraphite = new THREE.MeshStandardMaterial({ color: 0x27272a, roughness: 0.3, metalness: 0.9 });
  materials.vortexSilver = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.25, metalness: 0.8 });
  materials.vortexOrange = new THREE.MeshStandardMaterial({ color: 0xff6b00, emissive: 0xff6b00, emissiveIntensity: 1.2, roughness: 0.2 });
  materials.novaWhite = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.15, metalness: 0.35 });
  materials.novaSilver = new THREE.MeshStandardMaterial({ color: 0xcfd8dc, roughness: 0.2, metalness: 0.85 });
  materials.novaGreen = new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x10b981, emissiveIntensity: 1.2, roughness: 0.2 });
  materials.spectreTitanium = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.25, metalness: 0.95 });
  materials.spectreBlack = new THREE.MeshStandardMaterial({ color: 0x09090b, roughness: 0.4, metalness: 0.7 });
  materials.spectreCyan = new THREE.MeshStandardMaterial({ color: 0x06b6d4, emissive: 0x06b6d4, emissiveIntensity: 1.2, roughness: 0.2 });
  materials.jointCarbon = new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.6, metalness: 0.5 });

  materials.conveyor = new THREE.MeshStandardMaterial({ color: 0x546e7a, roughness: 0.4, metalness: 0.6 });
  materials.belt = new THREE.MeshStandardMaterial({ color: 0x263238, roughness: 0.8 });
  materials.roller = new THREE.MeshStandardMaterial({ color: 0x90a4ae, roughness: 0.3, metalness: 0.7 });

  // Wireframe theme materials
  materials.wireframeCyan = new THREE.MeshBasicMaterial({ color: COL_CYAN, wireframe: true, transparent: true, opacity: 0.4 });
  materials.wireframeBlue = new THREE.MeshBasicMaterial({ color: 0x1e88e5, wireframe: true, transparent: true, opacity: 0.3 });
  materials.edgeCyan = new THREE.LineBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.5 });
  materials.edgeDim = new THREE.LineBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.15 });
  materials.scanline = new THREE.MeshBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.08, side: THREE.DoubleSide });

  // Overlay materials
  materials.pathRibbon = new THREE.MeshBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
  materials.hazardRing = new THREE.MeshBasicMaterial({ color: COL_RED, transparent: true, opacity: 0.5 });
  materials.sensorDome = new THREE.MeshBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.2 });
  materials.taskBeacon = new THREE.MeshBasicMaterial({ color: COL_GREEN, transparent: true, opacity: 0.6 });

  const wireMeshTex = makeWireMeshTexture();
  wireMeshTex.wrapS = wireMeshTex.wrapT = THREE.RepeatWrapping;
  materials.wireMesh = new THREE.MeshStandardMaterial({ map: wireMeshTex, transparent: true, alphaTest: 0.3, side: THREE.DoubleSide, roughness: 0.5, metalness: 0.6 });
}

/* ═══════════════════════════════════════════════════════════════
   §4  GLOBAL STATE
   ═══════════════════════════════════════════════════════════════ */

const state = {
  renderer: null, scene: null, camera: null, controls: null,
  clock: new THREE.Clock(),
  robots: new Map(),       // id -> { group, data, prevData, lerpT }
  activeTheme: 'realistic',
  simRunning: true, simSpeed: 1.0,
  quality: 'high',
  followRobot: null,
  selectedRobot: null,
  walkMode: false,
  tourActive: false, tourIdx: 0, tourTimer: 0,
  camAnim: null,
  keysDown: new Set(),
  showPaths: true, showRacks: true, showSensors: true, showHazards: true,
  frameCount: 0, fpsAccum: 0, lastFpsUpdate: 0,
  animTime: 0,
  groups: {},  // named groups for visibility toggling
  originalMaterials: new Map(),
  wireframeEdges: [],
  overlays: { paths: [], sensors: [], hazards: [], taskBeacons: [], trails: [], parcels: [] },
  conveyorActive: true,
  loadProgress: 0,
  disposed: false,

  // Lighting refs
  keySun: null, hemiLight: null, ambientLight: null,

  // Instanced mesh refs for animations
  rollerInstances: null,
  ledFixtureInstance: null,

  // Scanline
  scanlinePlane: null,

  // KPI display
  kpiMesh: null, kpiTexture: null,

  // Floor markings overlay
  floorMarkingsMesh: null,

  // Auto-quality
  lowFpsCount: 0,
};

/* ═══════════════════════════════════════════════════════════════
   §5  SCENE CONSTRUCTION — FLOOR
   ═══════════════════════════════════════════════════════════════ */

function buildFloor(scene) {
  // Main floor
  const geo = new THREE.PlaneGeometry(TOTAL_W, TOTAL_D);
  geo.rotateX(-Math.PI / 2);
  const floor = new THREE.Mesh(geo, materials.floor);
  floor.position.set(TOTAL_W / 2, 0, TOTAL_D / 2);
  floor.receiveShadow = true;
  floor.matrixAutoUpdate = false;
  floor.updateMatrix();
  floor.userData.type = 'floor';
  scene.add(floor);
  state.groups.floor = floor;

  // Floor markings overlay
  const markTex = makeFloorMarkingsTexture();
  const markMat = new THREE.MeshBasicMaterial({ map: markTex, transparent: true, depthWrite: false });
  const markGeo = new THREE.PlaneGeometry(TOTAL_W, TOTAL_D);
  markGeo.rotateX(-Math.PI / 2);
  const markings = new THREE.Mesh(markGeo, markMat);
  markings.position.set(TOTAL_W / 2, 0.01, TOTAL_D / 2);
  markings.matrixAutoUpdate = false;
  markings.updateMatrix();
  scene.add(markings);
  state.floorMarkingsMesh = markings;
}

/* ═══════════════════════════════════════════════════════════════
   §6  SCENE CONSTRUCTION — WALLS, COLUMNS, ROOF
   ═══════════════════════════════════════════════════════════════ */

function buildStructure(scene) {
  const structGroup = new THREE.Group();
  structGroup.name = 'structure';

  // ── Perimeter walls ──
  const wallH = HALL_H, wallThick = 0.3;
  const wallGeos = [
    { w: TOTAL_W, h: wallH, pos: [TOTAL_W / 2, wallH / 2, 0], rot: [0, 0, 0] },             // North
    { w: TOTAL_W, h: wallH, pos: [TOTAL_W / 2, wallH / 2, TOTAL_D], rot: [0, 0, 0] },        // South
    { w: TOTAL_D, h: wallH, pos: [0, wallH / 2, TOTAL_D / 2], rot: [0, Math.PI / 2, 0] },    // West
    { w: TOTAL_D, h: wallH, pos: [TOTAL_W, wallH / 2, TOTAL_D / 2], rot: [0, Math.PI / 2, 0] }, // East
  ];
  wallGeos.forEach(wg => {
    const geo = new THREE.BoxGeometry(wg.w, wg.h, wallThick);
    const mesh = new THREE.Mesh(geo, materials.wall);
    mesh.position.set(...wg.pos);
    mesh.rotation.set(...wg.rot);
    mesh.matrixAutoUpdate = false;
    mesh.updateMatrix();
    structGroup.add(mesh);
  });

  // Cladding panels (visual texture strips on walls)
  for (let i = 0; i < 20; i++) {
    const panelGeo = new THREE.PlaneGeometry(5.5, wallH - 2);
    const panelMat = new THREE.MeshStandardMaterial({
      color: i % 3 === 0 ? 0xbdbdbd : 0xcfd8dc,
      roughness: 0.85, side: THREE.DoubleSide
    });
    const panel = new THREE.Mesh(panelGeo, panelMat);
    panel.position.set(3 + i * 6, wallH / 2, 0.2);
    panel.matrixAutoUpdate = false;
    panel.updateMatrix();
    structGroup.add(panel);
  }

  // ── Steel columns ──
  const colSpacingX = 15, colSpacingZ = 12.5;
  const colCountX = Math.floor(TOTAL_W / colSpacingX) + 1;
  const colCountZ = Math.floor(TOTAL_D / colSpacingZ) + 1;
  const totalCols = colCountX * colCountZ;

  const colGeo = new THREE.BoxGeometry(0.3, HALL_H, 0.3);
  const colInstance = new THREE.InstancedMesh(colGeo, materials.steel, totalCols);
  colInstance.castShadow = true;
  const colMatrix = new THREE.Matrix4();
  let colIdx = 0;
  for (let cx = 0; cx < colCountX; cx++) {
    for (let cz = 0; cz < colCountZ; cz++) {
      colMatrix.makeTranslation(cx * colSpacingX, HALL_H / 2, cz * colSpacingZ);
      colInstance.setMatrixAt(colIdx++, colMatrix);
    }
  }
  colInstance.instanceMatrix.needsUpdate = true;
  colInstance.matrixAutoUpdate = false;
  structGroup.add(colInstance);

  // Yellow base protectors on columns
  const baseProtGeo = new THREE.BoxGeometry(0.5, 0.6, 0.5);
  const baseProtInstance = new THREE.InstancedMesh(baseProtGeo, materials.yellow, totalCols);
  colIdx = 0;
  for (let cx = 0; cx < colCountX; cx++) {
    for (let cz = 0; cz < colCountZ; cz++) {
      colMatrix.makeTranslation(cx * colSpacingX, 0.3, cz * colSpacingZ);
      baseProtInstance.setMatrixAt(colIdx++, colMatrix);
    }
  }
  baseProtInstance.instanceMatrix.needsUpdate = true;
  baseProtInstance.matrixAutoUpdate = false;
  structGroup.add(baseProtInstance);

  // ── Roof trusses (Warren/Pratt style) ──
  const trussGroup = new THREE.Group();
  trussGroup.name = 'trusses';
  const trussSpacing = 10;
  const trussCount = Math.floor(TOTAL_W / trussSpacing) + 1;

  for (let t = 0; t < trussCount; t++) {
    const tx = t * trussSpacing;
    // Bottom chord
    const bottom = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, TOTAL_D), materials.steelDark);
    bottom.position.set(tx, HALL_H - 0.5, TOTAL_D / 2);
    bottom.matrixAutoUpdate = false; bottom.updateMatrix();
    trussGroup.add(bottom);

    // Top chord (peaked)
    const top = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, TOTAL_D), materials.steelDark);
    top.position.set(tx, HALL_H + 0.5, TOTAL_D / 2);
    top.matrixAutoUpdate = false; top.updateMatrix();
    trussGroup.add(top);

    // Diagonal web members
    const diagCount = Math.floor(TOTAL_D / 4);
    for (let d = 0; d < diagCount; d++) {
      const dz = d * 4;
      const diagGeo = new THREE.BoxGeometry(0.06, 1.2, 0.06);
      const diag = new THREE.Mesh(diagGeo, materials.steelDark);
      diag.position.set(tx, HALL_H, dz + 2);
      diag.rotation.z = d % 2 === 0 ? 0.75 : -0.75;
      diag.matrixAutoUpdate = false; diag.updateMatrix();
      trussGroup.add(diag);
    }

    // Vertical posts
    for (let v = 0; v < diagCount; v++) {
      const vGeo = new THREE.BoxGeometry(0.06, 1.0, 0.06);
      const vMesh = new THREE.Mesh(vGeo, materials.steelDark);
      vMesh.position.set(tx, HALL_H, v * 4);
      vMesh.matrixAutoUpdate = false; vMesh.updateMatrix();
      trussGroup.add(vMesh);
    }
  }

  // Purlins (cross members between trusses)
  const purlinCount = Math.floor(TOTAL_D / 5);
  for (let p = 0; p < purlinCount; p++) {
    const pz = p * 5;
    const purlin = new THREE.Mesh(new THREE.BoxGeometry(TOTAL_W, 0.06, 0.08), materials.steelDark);
    purlin.position.set(TOTAL_W / 2, HALL_H + 0.3, pz);
    purlin.matrixAutoUpdate = false; purlin.updateMatrix();
    trussGroup.add(purlin);
  }

  structGroup.add(trussGroup);

  // ── Dock doors (south wall) ──
  const dockGroup = new THREE.Group();
  dockGroup.name = 'docks';
  for (let d = 0; d < 6; d++) {
    const dx = TOTAL_W / 2 - 25 + d * 10;
    // Sectional door panels
    for (let p = 0; p < 5; p++) {
      const panelGeo = new THREE.BoxGeometry(5, 1.0, 0.15);
      const panelColor = p % 2 === 0 ? 0xe0e0e0 : 0xd0d0d0;
      const doorPanel = new THREE.Mesh(panelGeo, new THREE.MeshStandardMaterial({ color: panelColor, roughness: 0.7 }));
      doorPanel.position.set(dx, 0.5 + p * 1.0, TOTAL_D - 0.2);
      doorPanel.matrixAutoUpdate = false; doorPanel.updateMatrix();
      dockGroup.add(doorPanel);
    }
    // Door frame
    const frameGeo = new THREE.BoxGeometry(5.4, 5.4, 0.1);
    const frame = new THREE.Mesh(frameGeo, materials.steelDark);
    frame.position.set(dx, 2.7, TOTAL_D - 0.3);
    frame.matrixAutoUpdate = false; frame.updateMatrix();
    dockGroup.add(frame);

    // Ramp / bumper
    const bumpGeo = new THREE.BoxGeometry(5, 0.3, 1.5);
    const bump = new THREE.Mesh(bumpGeo, materials.rubber);
    bump.position.set(dx, 0.15, TOTAL_D - 1);
    bump.matrixAutoUpdate = false; bump.updateMatrix();
    dockGroup.add(bump);

    // Signal lights (red/amber/green)
    const lightColors = [0xff1744, 0xffb300, 0x00e676];
    lightColors.forEach((c, li) => {
      const sigGeo = new THREE.SphereGeometry(0.15, 8, 8);
      const sigMat = new THREE.MeshBasicMaterial({ color: c });
      const sig = new THREE.Mesh(sigGeo, sigMat);
      sig.position.set(dx + 2.8, 5.5 - li * 0.5, TOTAL_D - 0.2);
      sig.matrixAutoUpdate = false; sig.updateMatrix();
      dockGroup.add(sig);
    });

    // Number plate
    const dockSign = makeSignPlane(`DOCK ${String(d + 1).padStart(2, '0')}`, 2.5, 0.6);
    dockSign.position.set(dx, 5.8, TOTAL_D - 0.15);
    dockSign.matrixAutoUpdate = false; dockSign.updateMatrix();
    dockGroup.add(dockSign);
  }
  structGroup.add(dockGroup);

  // ── Man-doors ──
  for (let md = 0; md < 3; md++) {
    const mdx = 5 + md * 50;
    const doorGeo = new THREE.BoxGeometry(1.2, 2.4, 0.15);
    const door = new THREE.Mesh(doorGeo, materials.steelDark);
    door.position.set(mdx, 1.2, 0.1);
    door.matrixAutoUpdate = false; door.updateMatrix();
    structGroup.add(door);
  }

  scene.add(structGroup);
  state.groups.structure = structGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §7  MEZZANINE, CONTROL ROOM, STAIRS
   ═══════════════════════════════════════════════════════════════ */

function buildMezzanine(scene) {
  const mezGroup = new THREE.Group();
  mezGroup.name = 'mezzanine';
  const mezH = 5, mezW = 20, mezD = 15;
  const mezX = TOTAL_W - mezW - 3, mezZ = 3;

  // Floor platform
  const platGeo = new THREE.BoxGeometry(mezW, 0.2, mezD);
  const plat = new THREE.Mesh(platGeo, materials.steel);
  plat.position.set(mezX + mezW / 2, mezH, mezZ + mezD / 2);
  plat.receiveShadow = true;
  plat.matrixAutoUpdate = false; plat.updateMatrix();
  mezGroup.add(plat);

  // Support columns (4 corners)
  const corners = [[0, 0], [mezW, 0], [0, mezD], [mezW, mezD]];
  corners.forEach(([cx, cz]) => {
    const col = new THREE.Mesh(new THREE.BoxGeometry(0.25, mezH, 0.25), materials.steel);
    col.position.set(mezX + cx, mezH / 2, mezZ + cz);
    col.matrixAutoUpdate = false; col.updateMatrix();
    mezGroup.add(col);
  });

  // Glass balustrade
  const railH = 1.1;
  const railPositions = [
    { w: mezW, pos: [mezX + mezW / 2, mezH + railH / 2, mezZ] },
    { w: mezW, pos: [mezX + mezW / 2, mezH + railH / 2, mezZ + mezD] },
    { w: mezD, pos: [mezX, mezH + railH / 2, mezZ + mezD / 2], rotY: Math.PI / 2 },
  ];
  railPositions.forEach(rp => {
    const railGeo = new THREE.BoxGeometry(rp.w, railH, 0.05);
    const rail = new THREE.Mesh(railGeo, materials.glass);
    rail.position.set(...rp.pos);
    if (rp.rotY) rail.rotation.y = rp.rotY;
    rail.matrixAutoUpdate = false; rail.updateMatrix();
    mezGroup.add(rail);

    // Top handrail
    const handGeo = new THREE.BoxGeometry(rp.w, 0.05, 0.05);
    const hand = new THREE.Mesh(handGeo, materials.steel);
    hand.position.set(rp.pos[0], mezH + railH, rp.pos[2]);
    if (rp.rotY) hand.rotation.y = rp.rotY;
    hand.matrixAutoUpdate = false; hand.updateMatrix();
    mezGroup.add(hand);
  });

  // ── Control room (glazed box on mezzanine) ──
  const crW = 8, crD = 6, crH = 3;
  const crX = mezX + 2, crZ = mezZ + 2;
  const crWalls = [
    { w: crW, h: crH, pos: [crX + crW / 2, mezH + crH / 2, crZ] },
    { w: crW, h: crH, pos: [crX + crW / 2, mezH + crH / 2, crZ + crD] },
    { w: crD, h: crH, pos: [crX, mezH + crH / 2, crZ + crD / 2], rotY: Math.PI / 2 },
    { w: crD, h: crH, pos: [crX + crW, mezH + crH / 2, crZ + crD / 2], rotY: Math.PI / 2 },
  ];
  crWalls.forEach(cw => {
    const cwGeo = new THREE.BoxGeometry(cw.w, cw.h, 0.08);
    const cwMesh = new THREE.Mesh(cwGeo, materials.darkGlass);
    cwMesh.position.set(...cw.pos);
    if (cw.rotY) cwMesh.rotation.y = cw.rotY;
    cwMesh.matrixAutoUpdate = false; cwMesh.updateMatrix();
    mezGroup.add(cwMesh);
  });

  // Control room roof
  const crRoof = new THREE.Mesh(new THREE.BoxGeometry(crW, 0.15, crD), materials.steel);
  crRoof.position.set(crX + crW / 2, mezH + crH, crZ + crD / 2);
  crRoof.matrixAutoUpdate = false; crRoof.updateMatrix();
  mezGroup.add(crRoof);

  // Glowing screen inside control room
  const screenGeo = new THREE.PlaneGeometry(3, 1.5);
  const screenMat = new THREE.MeshBasicMaterial({ color: 0x00bcd4, transparent: true, opacity: 0.7 });
  const screen = new THREE.Mesh(screenGeo, screenMat);
  screen.position.set(crX + crW / 2, mezH + 1.5, crZ + 0.1);
  screen.matrixAutoUpdate = false; screen.updateMatrix();
  mezGroup.add(screen);

  // ── Stairs ──
  const stairSteps = 15;
  const stairW = 1.8, stepD = 0.6;
  const stairX = mezX + mezW;
  for (let s = 0; s < stairSteps; s++) {
    const stepGeo = new THREE.BoxGeometry(stairW, 0.12, stepD);
    const step = new THREE.Mesh(stepGeo, materials.steel);
    step.position.set(stairX + stairW / 2 + 0.5, (s + 0.5) * (mezH / stairSteps), mezZ + s * stepD);
    step.matrixAutoUpdate = false; step.updateMatrix();
    mezGroup.add(step);
  }
  // Stair stringers (side rails)
  const stringerLen = Math.sqrt(mezH * mezH + (stairSteps * stepD) * (stairSteps * stepD));
  const stringerAngle = Math.atan2(mezH, stairSteps * stepD);
  for (const sx of [-0.1, stairW + 0.1]) {
    const stringer = new THREE.Mesh(new THREE.BoxGeometry(0.06, stringerLen, 0.06), materials.steel);
    stringer.position.set(stairX + sx + 0.5, mezH / 2, mezZ + stairSteps * stepD / 2);
    stringer.rotation.x = Math.PI / 2 - stringerAngle;
    stringer.matrixAutoUpdate = false; stringer.updateMatrix();
    mezGroup.add(stringer);
  }
  // Stair handrail
  const handRailLen = stringerLen;
  const handRail = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.04, handRailLen), materials.yellow);
  handRail.position.set(stairX + stairW + 0.5 + 0.15, mezH / 2 + 1.0, mezZ + stairSteps * stepD / 2);
  handRail.rotation.x = Math.PI / 2 - stringerAngle;
  handRail.matrixAutoUpdate = false; handRail.updateMatrix();
  mezGroup.add(handRail);

  scene.add(mezGroup);
  state.groups.mezzanine = mezGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §8  CEILING LIGHTING (InstancedMesh)
   ═══════════════════════════════════════════════════════════════ */

function buildLighting(scene) {
  const lightGroup = new THREE.Group();
  lightGroup.name = 'lighting';

  // ── LED Fixture Instances ──
  const fixSpacingX = 8, fixSpacingZ = 6;
  const fixCountX = Math.floor(TOTAL_W / fixSpacingX);
  const fixCountZ = Math.floor(TOTAL_D / fixSpacingZ);
  const totalFix = fixCountX * fixCountZ;

  const fixGeo = new THREE.BoxGeometry(2.5, 0.08, 0.3);
  const fixMat = new THREE.MeshBasicMaterial({ color: 0xfff8e1 });
  const fixInstance = new THREE.InstancedMesh(fixGeo, fixMat, totalFix);
  const fixM = new THREE.Matrix4();
  let idx = 0;
  for (let fx = 0; fx < fixCountX; fx++) {
    for (let fz = 0; fz < fixCountZ; fz++) {
      fixM.makeTranslation(fx * fixSpacingX + fixSpacingX / 2, HALL_H - 0.6, fz * fixSpacingZ + fixSpacingZ / 2);
      fixInstance.setMatrixAt(idx++, fixM);
    }
  }
  fixInstance.instanceMatrix.needsUpdate = true;
  fixInstance.matrixAutoUpdate = false;
  lightGroup.add(fixInstance);
  state.ledFixtureInstance = fixInstance;

  // ── Centre-aisle cyan light line ──
  const lineGeo = new THREE.BoxGeometry(0.08, 0.04, TOTAL_D);
  const lineMat = materials.cyanEmissive.clone();
  lineMat.emissiveIntensity = 0.5;
  const aisleLight = new THREE.Mesh(lineGeo, lineMat);
  aisleLight.position.set(TOTAL_W / 2, HALL_H - 0.3, TOTAL_D / 2);
  aisleLight.matrixAutoUpdate = false;
  aisleLight.updateMatrix();
  lightGroup.add(aisleLight);

  // Additional aisle light lines along grid corridors
  for (const [x0, x1] of X_BLOCKS) {
    const cx = GRID_OX + ((x0 + x1) / 2 + 0.5) * CELL;
    const aisleLine = new THREE.Mesh(lineGeo.clone(), lineMat.clone());
    aisleLine.position.set(cx, HALL_H - 0.3, GRID_OZ + GRID_ROWS * CELL / 2);
    aisleLine.scale.z = GRID_ROWS * CELL / TOTAL_D;
    aisleLine.matrixAutoUpdate = false; aisleLine.updateMatrix();
    lightGroup.add(aisleLine);
  }

  scene.add(lightGroup);
  state.groups.lighting = lightGroup;

  // ── Dynamic Lights (max 4) ──
  // 1. Directional key sun
  const keySun = new THREE.DirectionalLight(0xfff5e6, 1.5);
  keySun.position.set(40, 30, 20);
  keySun.castShadow = true;
  keySun.shadow.mapSize.set(2048, 2048);
  keySun.shadow.camera.left = -60;
  keySun.shadow.camera.right = 60;
  keySun.shadow.camera.top = 60;
  keySun.shadow.camera.bottom = -60;
  keySun.shadow.camera.near = 1;
  keySun.shadow.camera.far = 100;
  keySun.shadow.bias = -0.001;
  keySun.shadow.normalBias = 0.02;
  scene.add(keySun);
  state.keySun = keySun;

  // 2. Hemisphere light
  const hemiLight = new THREE.HemisphereLight(0xddeeff, 0x444422, 0.75);
  scene.add(hemiLight);
  state.hemiLight = hemiLight;

  // 3. Ambient fill
  const ambLight = new THREE.AmbientLight(0x404050, 0.3);
  scene.add(ambLight);
  state.ambientLight = ambLight;
}

/* ═══════════════════════════════════════════════════════════════
   §9  RACKING SYSTEM (InstancedMesh)
   ═══════════════════════════════════════════════════════════════ */

function buildRacking(scene) {
  const rackGroup = new THREE.Group();
  rackGroup.name = 'racking';

  // Collect all rack positions: grid shelves + extra decor banks
  const rackPositions = [];
  // Grid-based shelves
  for (const [x0, x1] of X_BLOCKS) {
    for (const [y0, y1] of Y_BLOCKS) {
      for (let gx = x0; gx <= x1; gx++) {
        for (let gy = y0; gy <= y1; gy++) {
          rackPositions.push(gridToWorld(gx, gy));
        }
      }
    }
  }
  // Extra decor racks outside main grid
  const decorRackSeed = mulberry32(200);
  const decorBanks = [
    { x0: 70, z0: 15, cols: 6, rows: 8 },
    { x0: 85, z0: 40, cols: 4, rows: 10 },
    { x0: 10, z0: 60, cols: 5, rows: 6 },
    { x0: 90, z0: 70, cols: 4, rows: 5 },
  ];
  for (const bank of decorBanks) {
    for (let c = 0; c < bank.cols; c++) {
      for (let r = 0; r < bank.rows; r++) {
        rackPositions.push(new THREE.Vector3(bank.x0 + c * CELL, 0, bank.z0 + r * CELL));
      }
    }
  }

  const numRacks = rackPositions.length;

  // ── Uprights (blue, 4 per cell: front-left, front-right, back-left, back-right) ──
  const uprightCount = numRacks * 4;
  const uprightGeo = new THREE.BoxGeometry(0.08, RACK_H, 0.08);
  const uprightIM = new THREE.InstancedMesh(uprightGeo, materials.rackBlue, uprightCount);
  uprightIM.castShadow = true;
  const uM = new THREE.Matrix4();
  let uIdx = 0;
  const offsets = [[-0.8, -0.8], [0.8, -0.8], [-0.8, 0.8], [0.8, 0.8]];
  for (const pos of rackPositions) {
    for (const [ox, oz] of offsets) {
      uM.makeTranslation(pos.x + ox, RACK_H / 2, pos.z + oz);
      uprightIM.setMatrixAt(uIdx++, uM);
    }
  }
  uprightIM.instanceMatrix.needsUpdate = true;
  uprightIM.matrixAutoUpdate = false;
  rackGroup.add(uprightIM);

  // ── Beams (orange, connecting front-to-back and left-to-right per level) ──
  const beamCountPerRack = RACK_LEVELS * 4; // 2 cross + 2 depth per level
  const totalBeams = numRacks * beamCountPerRack;
  const beamGeoX = new THREE.BoxGeometry(1.6, 0.08, 0.06);
  const beamGeoZ = new THREE.BoxGeometry(0.06, 0.08, 1.6);
  const beamIMX = new THREE.InstancedMesh(beamGeoX, materials.beamOrange, numRacks * RACK_LEVELS * 2);
  const beamIMZ = new THREE.InstancedMesh(beamGeoZ, materials.beamOrange, numRacks * RACK_LEVELS * 2);
  let bxIdx = 0, bzIdx = 0;
  const bM = new THREE.Matrix4();
  for (const pos of rackPositions) {
    for (let lv = 0; lv < RACK_LEVELS; lv++) {
      const y = (lv + 1) * TIER_H;
      // Front and back beams (X-direction)
      bM.makeTranslation(pos.x, y, pos.z - 0.8);
      beamIMX.setMatrixAt(bxIdx++, bM);
      bM.makeTranslation(pos.x, y, pos.z + 0.8);
      beamIMX.setMatrixAt(bxIdx++, bM);
      // Left and right beams (Z-direction)
      bM.makeTranslation(pos.x - 0.8, y, pos.z);
      beamIMZ.setMatrixAt(bzIdx++, bM);
      bM.makeTranslation(pos.x + 0.8, y, pos.z);
      beamIMZ.setMatrixAt(bzIdx++, bM);
    }
  }
  beamIMX.instanceMatrix.needsUpdate = true;
  beamIMZ.instanceMatrix.needsUpdate = true;
  beamIMX.matrixAutoUpdate = false;
  beamIMZ.matrixAutoUpdate = false;
  rackGroup.add(beamIMX);
  rackGroup.add(beamIMZ);

  // ── Diagonal X-bracing ──
  const braceCount = numRacks * 2; // front and back face
  const braceGeo = new THREE.BoxGeometry(0.03, Math.sqrt(RACK_H * RACK_H + 1.6 * 1.6), 0.03);
  const braceIM = new THREE.InstancedMesh(braceGeo, materials.rackBlue, braceCount);
  const braceAngle = Math.atan2(1.6, RACK_H);
  let brIdx = 0;
  const brM = new THREE.Matrix4();
  const brR = new THREE.Matrix4();
  for (const pos of rackPositions) {
    // Front face X-brace
    brM.makeTranslation(pos.x, RACK_H / 2, pos.z - 0.8);
    brR.makeRotationZ(braceAngle);
    brM.multiply(brR);
    braceIM.setMatrixAt(brIdx++, brM);
    // Back face X-brace
    brM.makeTranslation(pos.x, RACK_H / 2, pos.z + 0.8);
    brR.makeRotationZ(-braceAngle);
    brM.multiply(brR);
    braceIM.setMatrixAt(brIdx++, brM);
  }
  braceIM.instanceMatrix.needsUpdate = true;
  braceIM.matrixAutoUpdate = false;
  rackGroup.add(braceIM);

  // ── Base plates ──
  const basePlateGeo = new THREE.BoxGeometry(0.25, 0.03, 0.25);
  const basePlateIM = new THREE.InstancedMesh(basePlateGeo, materials.steel, uprightCount);
  uIdx = 0;
  for (const pos of rackPositions) {
    for (const [ox, oz] of offsets) {
      uM.makeTranslation(pos.x + ox, 0.015, pos.z + oz);
      basePlateIM.setMatrixAt(uIdx++, uM);
    }
  }
  basePlateIM.instanceMatrix.needsUpdate = true;
  basePlateIM.matrixAutoUpdate = false;
  rackGroup.add(basePlateIM);

  // ── Upright guards (yellow) ──
  const guardGeo = new THREE.BoxGeometry(0.2, 0.5, 0.2);
  const guardIM = new THREE.InstancedMesh(guardGeo, materials.yellowGuard, uprightCount);
  uIdx = 0;
  for (const pos of rackPositions) {
    for (const [ox, oz] of offsets) {
      uM.makeTranslation(pos.x + ox, 0.25, pos.z + oz);
      guardIM.setMatrixAt(uIdx++, uM);
    }
  }
  guardIM.instanceMatrix.needsUpdate = true;
  guardIM.matrixAutoUpdate = false;
  rackGroup.add(guardIM);

  // ── Wire-mesh decking on some levels ──
  const meshDeckCount = numRacks * 3; // 3 out of 6 levels get wire mesh
  const deckGeo = new THREE.PlaneGeometry(1.5, 1.5);
  deckGeo.rotateX(-Math.PI / 2);
  const deckIM = new THREE.InstancedMesh(deckGeo, materials.wireMesh, meshDeckCount);
  let dkIdx = 0;
  for (const pos of rackPositions) {
    for (const lv of [1, 3, 5]) {
      if (dkIdx >= meshDeckCount) break;
      const y = lv * TIER_H + 0.01;
      uM.makeTranslation(pos.x, y, pos.z);
      deckIM.setMatrixAt(dkIdx++, uM);
    }
  }
  deckIM.instanceMatrix.needsUpdate = true;
  deckIM.matrixAutoUpdate = false;
  rackGroup.add(deckIM);

  // ── Vertical cyan LED strips on uprights (pulsing via animation) ──
  const ledStripGeo = new THREE.BoxGeometry(0.02, RACK_H, 0.02);
  const ledStripMat = materials.cyanEmissive.clone();
  ledStripMat.emissiveIntensity = 0.4;
  const ledStripCount = numRacks * 4;
  const ledStripIM = new THREE.InstancedMesh(ledStripGeo, ledStripMat, ledStripCount);
  uIdx = 0;
  for (const pos of rackPositions) {
    for (const [ox, oz] of offsets) {
      uM.makeTranslation(pos.x + ox + 0.06, RACK_H / 2, pos.z + oz);
      ledStripIM.setMatrixAt(uIdx++, uM);
    }
  }
  ledStripIM.instanceMatrix.needsUpdate = true;
  ledStripIM.matrixAutoUpdate = false;
  rackGroup.add(ledStripIM);
  state.groups.rackLEDs = ledStripIM;

  // ── Location label plates (from signage atlas) ──
  const aisleLabels = ['A01', 'A02', 'A03', 'A04', 'A05', 'A06'];
  let labelIdx = 0;
  for (const [bx_i, [x0]] of X_BLOCKS.entries()) {
    for (const [by_i, [y0]] of Y_BLOCKS.entries()) {
      const lbl = aisleLabels[labelIdx % aisleLabels.length];
      const sign = makeSignPlane(lbl, 0.8, 0.3);
      sign.position.set(GRID_OX + x0 * CELL - 0.5, RACK_H - 0.3, GRID_OZ + y0 * CELL);
      sign.rotation.y = Math.PI / 2;
      sign.matrixAutoUpdate = false; sign.updateMatrix();
      rackGroup.add(sign);
      labelIdx++;
    }
  }

  scene.add(rackGroup);
  state.groups.racking = rackGroup;
  return rackPositions;
}

/* ═══════════════════════════════════════════════════════════════
   §10  INVENTORY (Pallets, Cartons, Totes — InstancedMesh)
   ═══════════════════════════════════════════════════════════════ */

function buildInventory(scene, rackPositions) {
  const invGroup = new THREE.Group();
  invGroup.name = 'inventory';

  const invSeed = mulberry32(314);
  const maxPerLevel = rackPositions.length * RACK_LEVELS;

  // Count items by type
  let palletCount = 0, cartonCount = 0, toteCount = 0, wrapCount = 0;
  const items = [];
  for (const pos of rackPositions) {
    for (let lv = 0; lv < RACK_LEVELS; lv++) {
      if (invSeed() < 0.12) continue; // empty slot
      const y = lv * TIER_H + 0.08;
      const type = invSeed() < 0.35 ? 'pallet' : invSeed() < 0.65 ? 'carton' : invSeed() < 0.85 ? 'tote' : 'wrap';
      items.push({ pos, y, type, lv });
      if (type === 'pallet') palletCount++;
      else if (type === 'carton') cartonCount++;
      else if (type === 'tote') toteCount++;
      else wrapCount++;
    }
  }

  // ── Pallets ──
  const palletGeo = new THREE.BoxGeometry(1.0, 0.14, 0.7);
  const palletIM = new THREE.InstancedMesh(palletGeo, materials.palletWood, Math.max(palletCount, 1));
  const pColor = new THREE.Color();
  let pIdx = 0;
  const iM = new THREE.Matrix4();
  for (const item of items) {
    if (item.type !== 'pallet') continue;
    iM.makeTranslation(item.pos.x, item.y + 0.07, item.pos.z);
    palletIM.setMatrixAt(pIdx, iM);
    const v = 0.55 + invSeed() * 0.25;
    pColor.setRGB(v, v * 0.7, v * 0.4);
    palletIM.setColorAt(pIdx, pColor);
    pIdx++;
  }
  if (palletCount > 0) {
    palletIM.instanceMatrix.needsUpdate = true;
    palletIM.instanceColor.needsUpdate = true;
  }
  palletIM.matrixAutoUpdate = false;
  invGroup.add(palletIM);

  // ── Cartons ──
  const cartonGeo = new THREE.BoxGeometry(0.4, 0.3 + invSeed() * 0.2, 0.3);
  const cartonIM = new THREE.InstancedMesh(cartonGeo, materials.carton, Math.max(cartonCount, 1));
  let cIdx = 0;
  for (const item of items) {
    if (item.type !== 'carton') continue;
    const h = 0.25 + invSeed() * 0.25;
    iM.makeTranslation(item.pos.x + (invSeed() - 0.5) * 0.3, item.y + h / 2, item.pos.z + (invSeed() - 0.5) * 0.3);
    cartonIM.setMatrixAt(cIdx, iM);
    const v = 0.7 + invSeed() * 0.2;
    pColor.setRGB(v, v * 0.85, v * 0.5);
    cartonIM.setColorAt(cIdx, pColor);
    cIdx++;
  }
  if (cartonCount > 0) {
    cartonIM.instanceMatrix.needsUpdate = true;
    cartonIM.instanceColor.needsUpdate = true;
  }
  cartonIM.matrixAutoUpdate = false;
  invGroup.add(cartonIM);

  // ── Totes (blue and grey) ──
  const toteGeo = new THREE.BoxGeometry(0.5, 0.25, 0.35);
  const toteIM = new THREE.InstancedMesh(toteGeo, materials.blueTote, Math.max(toteCount, 1));
  let tIdx = 0;
  for (const item of items) {
    if (item.type !== 'tote') continue;
    iM.makeTranslation(item.pos.x + (invSeed() - 0.5) * 0.2, item.y + 0.125, item.pos.z + (invSeed() - 0.5) * 0.2);
    toteIM.setMatrixAt(tIdx, iM);
    pColor.set(invSeed() < 0.5 ? 0x1976d2 : 0x757575);
    toteIM.setColorAt(tIdx, pColor);
    tIdx++;
  }
  if (toteCount > 0) {
    toteIM.instanceMatrix.needsUpdate = true;
    toteIM.instanceColor.needsUpdate = true;
  }
  toteIM.matrixAutoUpdate = false;
  invGroup.add(toteIM);

  // ── Shrink-wrapped pallet loads ──
  const wrapGeo = new THREE.BoxGeometry(0.9, 0.8, 0.6);
  const wrapIM = new THREE.InstancedMesh(wrapGeo, materials.shrinkWrap, Math.max(wrapCount, 1));
  let wIdx = 0;
  for (const item of items) {
    if (item.type !== 'wrap') continue;
    const h = 0.5 + invSeed() * 0.4;
    iM.makeTranslation(item.pos.x, item.y + h / 2, item.pos.z);
    const sM = new THREE.Matrix4().makeScale(1, 0.8 + invSeed() * 0.4, 1);
    iM.multiply(sM);
    wrapIM.setMatrixAt(wIdx, iM);
    wIdx++;
  }
  if (wrapCount > 0) {
    wrapIM.instanceMatrix.needsUpdate = true;
  }
  wrapIM.matrixAutoUpdate = false;
  invGroup.add(wrapIM);

  scene.add(invGroup);
  state.groups.inventory = invGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §11  CONVEYOR SYSTEM
   ═══════════════════════════════════════════════════════════════ */

function buildConveyors(scene) {
  const convGroup = new THREE.Group();
  convGroup.name = 'conveyors';

  // Define conveyor runs
  const runs = [
    { start: [GRID_OX - 5, 0.8, GRID_OZ + 14 * CELL], dir: [1, 0, 0], len: 20, type: 'roller' },
    { start: [GRID_OX + 15 * CELL + 2, 0.8, GRID_OZ + 14 * CELL], dir: [1, 0, 0], len: 15, type: 'roller' },
    { start: [TOTAL_W / 2 - 10, 0.8, TOTAL_D - 10], dir: [1, 0, 0], len: 20, type: 'belt' },
    { start: [GRID_OX - 5, 0.8, GRID_OZ + 7 * CELL], dir: [1, 0, 0], len: 12, type: 'roller' },
  ];

  const rollerGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.6, 8);
  rollerGeo.rotateZ(Math.PI / 2);
  let totalRollers = 0;
  for (const run of runs) {
    if (run.type === 'roller') totalRollers += Math.floor(run.len / 0.15);
  }

  const rollerIM = new THREE.InstancedMesh(rollerGeo, materials.roller, Math.max(totalRollers, 1));
  let rIdx = 0;
  const rM = new THREE.Matrix4();

  for (const run of runs) {
    const [sx, sy, sz] = run.start;
    const [dx, dy, dz] = run.dir;

    // Frame (side rails)
    const frameLen = run.len;
    for (const side of [-0.35, 0.35]) {
      const railGeo = new THREE.BoxGeometry(frameLen, 0.06, 0.04);
      const rail = new THREE.Mesh(railGeo, materials.conveyor);
      rail.position.set(sx + dx * frameLen / 2, sy, sz + dz * frameLen / 2 + side);
      rail.matrixAutoUpdate = false; rail.updateMatrix();
      convGroup.add(rail);
    }

    // Legs
    const legCount = Math.floor(frameLen / 3) + 1;
    for (let l = 0; l < legCount; l++) {
      const lx = sx + dx * l * 3, lz = sz + dz * l * 3;
      for (const side of [-0.3, 0.3]) {
        const leg = new THREE.Mesh(new THREE.BoxGeometry(0.04, sy, 0.04), materials.conveyor);
        leg.position.set(lx, sy / 2, lz + side);
        leg.matrixAutoUpdate = false; leg.updateMatrix();
        convGroup.add(leg);
      }
    }

    if (run.type === 'roller') {
      // Instanced rollers
      const rollerCount = Math.floor(frameLen / 0.15);
      for (let r = 0; r < rollerCount; r++) {
        const rx = sx + dx * r * 0.15;
        const rz = sz + dz * r * 0.15;
        rM.makeTranslation(rx, sy + 0.02, rz);
        if (rIdx < totalRollers) {
          rollerIM.setMatrixAt(rIdx++, rM);
        }
      }
    } else {
      // Belt surface
      const beltGeo = new THREE.BoxGeometry(frameLen, 0.02, 0.6);
      const belt = new THREE.Mesh(beltGeo, materials.belt);
      belt.position.set(sx + dx * frameLen / 2, sy + 0.02, sz + dz * frameLen / 2);
      belt.matrixAutoUpdate = false; belt.updateMatrix();
      convGroup.add(belt);
    }

    // Status LED indicator
    const ledGeo = new THREE.SphereGeometry(0.06, 8, 8);
    const ledMat = materials.greenEmissive.clone();
    const led = new THREE.Mesh(ledGeo, ledMat);
    led.position.set(sx, sy + 0.15, sz - 0.4);
    led.matrixAutoUpdate = false; led.updateMatrix();
    led.userData.statusLED = true;
    convGroup.add(led);

    // Totes on the conveyor
    const toteOnConv = rngInt(1, 4);
    for (let t = 0; t < toteOnConv; t++) {
      const tx = sx + dx * (rng() * frameLen * 0.8 + frameLen * 0.1);
      const tz = sz + dz * (rng() * frameLen * 0.8);
      const tote = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.2, 0.3), rng() < 0.5 ? materials.blueTote : materials.greyTote);
      tote.position.set(tx, sy + 0.12, tz);
      tote.userData.conveyorItem = true;
      tote.userData.speed = 0.5 + rng() * 0.5;
      tote.userData.dir = new THREE.Vector3(dx, dy, dz);
      tote.userData.startX = sx;
      tote.userData.endX = sx + dx * frameLen;
      tote.matrixAutoUpdate = false; tote.updateMatrix();
      convGroup.add(tote);
    }
  }

  if (totalRollers > 0) {
    rollerIM.instanceMatrix.needsUpdate = true;
  }
  rollerIM.matrixAutoUpdate = false;
  convGroup.add(rollerIM);
  state.rollerInstances = rollerIM;

  scene.add(convGroup);
  state.groups.conveyors = convGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §12  ASRS CRANES
   ═══════════════════════════════════════════════════════════════ */

function buildASRSCranes(scene) {
  const craneGroup = new THREE.Group();
  craneGroup.name = 'asrs';

  // Place 2 ASRS cranes in the decor racks
  const cranePositions = [
    { x: 72, z: 20 },
    { x: 92, z: 48 },
  ];

  for (const cp of cranePositions) {
    const crane = new THREE.Group();
    crane.userData.type = 'asrs_crane';
    crane.userData.label = 'visual only';

    // Mast (yellow)
    const mast = new THREE.Mesh(new THREE.BoxGeometry(0.3, HALL_H - 2, 0.3), materials.yellow);
    mast.position.set(0, (HALL_H - 2) / 2, 0);
    mast.matrixAutoUpdate = false; mast.updateMatrix();
    crane.add(mast);

    // Top rail
    const topRail = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, 8), materials.steel);
    topRail.position.set(0, HALL_H - 2, 0);
    topRail.matrixAutoUpdate = false; topRail.updateMatrix();
    crane.add(topRail);

    // Bottom rail
    const bottomRail = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, 8), materials.steel);
    bottomRail.position.set(0, 0.1, 0);
    bottomRail.matrixAutoUpdate = false; bottomRail.updateMatrix();
    crane.add(bottomRail);

    // Carriage / cabin (grey)
    const cabin = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.0, 0.8), materials.steelDark);
    cabin.position.set(0, HALL_H / 2, 0);
    cabin.userData.carriageY = HALL_H / 2;
    cabin.matrixAutoUpdate = false; cabin.updateMatrix();
    crane.add(cabin);

    // Forks
    const fork = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.05, 0.1), materials.steel);
    fork.position.set(0.4, HALL_H / 2 - 0.5, 0);
    fork.matrixAutoUpdate = false; fork.updateMatrix();
    crane.add(fork);

    crane.position.set(cp.x, 0, cp.z);
    craneGroup.add(crane);
  }

  scene.add(craneGroup);
  state.groups.asrs = craneGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §13  ROBOTIC ARMS (4-5 articulated)
   ═══════════════════════════════════════════════════════════════ */

function buildRoboticArms(scene) {
  const armGroup = new THREE.Group();
  armGroup.name = 'roboticArms';

  const armPositions = [
    { x: GRID_OX + 2 * CELL, z: GRID_OZ + 14 * CELL + 3, label: 'Sort-1' },
    { x: GRID_OX + 6 * CELL, z: GRID_OZ + 14 * CELL + 3, label: 'Sort-2' },
    { x: GRID_OX + 10 * CELL, z: GRID_OZ + 14 * CELL + 3, label: 'Pack-1' },
    { x: TOTAL_W / 2, z: TOTAL_D - 15, label: 'Pack-2' },
    { x: TOTAL_W / 2 + 10, z: TOTAL_D - 15, label: 'Sort-3' },
  ];

  for (const ap of armPositions) {
    const arm = buildArticulatedArm();
    arm.position.set(ap.x, 0, ap.z);
    arm.userData.label = ap.label;
    arm.userData.animPhase = rng() * Math.PI * 2;
    armGroup.add(arm);

    // Heavy industrial table
    const table = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.8, 1.5), materials.steelDark);
    table.position.set(ap.x + 1, 0.4, ap.z);
    table.matrixAutoUpdate = false; table.updateMatrix();
    armGroup.add(table);
  }

  scene.add(armGroup);
  state.groups.roboticArms = armGroup;
}

function buildArticulatedArm() {
  const arm = new THREE.Group();
  arm.userData.isRoboticArm = true;

  // Base
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.3, 0.2, 16), materials.robotOrange);
  base.position.y = 0.9;
  arm.add(base);

  // Shoulder joint
  const shoulder = new THREE.Group();
  shoulder.position.set(0, 1.0, 0);
  const shoulderJoint = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 12), materials.steelDark);
  shoulder.add(shoulderJoint);
  arm.add(shoulder);
  arm.userData.shoulder = shoulder;

  // Upper arm
  const upperArm = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.8, 0.1), materials.robotOrange);
  upperArm.position.y = 0.4;
  shoulder.add(upperArm);

  // Elbow joint
  const elbow = new THREE.Group();
  elbow.position.set(0, 0.8, 0);
  const elbowJoint = new THREE.Mesh(new THREE.SphereGeometry(0.08, 10, 10), materials.steelDark);
  elbow.add(elbowJoint);
  shoulder.add(elbow);
  arm.userData.elbow = elbow;

  // Forearm
  const forearm = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.6, 0.08), materials.robotOrange);
  forearm.position.y = 0.3;
  elbow.add(forearm);

  // Wrist
  const wrist = new THREE.Group();
  wrist.position.set(0, 0.6, 0);
  const wristJoint = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 8), materials.steelDark);
  wrist.add(wristJoint);
  elbow.add(wrist);
  arm.userData.wrist = wrist;

  // Gripper
  const gripBase = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.04, 0.08), materials.steelDark);
  gripBase.position.y = 0.02;
  wrist.add(gripBase);

  const finger1 = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.1, 0.06), materials.steel);
  finger1.position.set(-0.06, -0.03, 0);
  wrist.add(finger1);
  arm.userData.finger1 = finger1;

  const finger2 = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.1, 0.06), materials.steel);
  finger2.position.set(0.06, -0.03, 0);
  wrist.add(finger2);
  arm.userData.finger2 = finger2;

  return arm;
}

/* ═══════════════════════════════════════════════════════════════
   §14  CHARGING STATIONS
   ═══════════════════════════════════════════════════════════════ */

function buildChargingStations(scene) {
  const chargeGroup = new THREE.Group();
  chargeGroup.name = 'charging';

  for (const [gx, gy] of CHARGING) {
    const wp = gridToWorld(gx, gy);

    // Induction pad
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.05, 24), materials.steelDark);
    pad.position.set(wp.x, 0.025, wp.z);
    pad.matrixAutoUpdate = false; pad.updateMatrix();
    chargeGroup.add(pad);

    // Cyan power ring (pulsing via animation)
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.55, 0.04, 8, 32), materials.cyanEmissive.clone());
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(wp.x, 0.06, wp.z);
    ring.userData.chargingRing = true;
    chargeGroup.add(ring);

    // Wall-mount charger post
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.2, 0.15), materials.steel);
    post.position.set(wp.x, 0.6, wp.z - 0.9);
    post.matrixAutoUpdate = false; post.updateMatrix();
    chargeGroup.add(post);

    // Battery indicator (3 bars)
    for (let b = 0; b < 3; b++) {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.08, 0.02), materials.greenEmissive.clone());
      bar.position.set(wp.x, 0.9 + b * 0.12, wp.z - 0.98);
      bar.matrixAutoUpdate = false; bar.updateMatrix();
      chargeGroup.add(bar);
    }
  }

  scene.add(chargeGroup);
  state.groups.charging = chargeGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §15  SIGNAGE
   ═══════════════════════════════════════════════════════════════ */

function buildSignage(scene) {
  const signGroup = new THREE.Group();
  signGroup.name = 'signage';

  // ── Hanging aisle signs ──
  const aisleLabels = ['A01', 'A02', 'A03', 'A04', 'A05', 'A06'];
  for (let i = 0; i < aisleLabels.length; i++) {
    const sign = makeSignPlane(aisleLabels[i], 1.5, 0.6);
    const col = i % 3, row = Math.floor(i / 3);
    const sx = GRID_OX + X_BLOCKS[col][0] * CELL + CELL;
    const sz = GRID_OZ + Y_BLOCKS[row][0] * CELL - 1;
    sign.position.set(sx, HALL_H - 2, sz);
    sign.matrixAutoUpdate = false; sign.updateMatrix();
    signGroup.add(sign);

    // Hanging wire
    const wire = new THREE.Mesh(new THREE.BoxGeometry(0.02, 1.5, 0.02), materials.steel);
    wire.position.set(sx, HALL_H - 1.2, sz);
    wire.matrixAutoUpdate = false; wire.updateMatrix();
    signGroup.add(wire);
  }

  // ── Zone signs ──
  const zoneLabels = [
    { label: 'DOCK', x: TOTAL_W / 2, z: TOTAL_D - 3, y: 7 },
    { label: 'SORT', x: GRID_OX + 6 * CELL, z: GRID_OZ + 14 * CELL + 5, y: 5 },
    { label: 'PACK', x: GRID_OX + 10 * CELL, z: GRID_OZ + 14 * CELL + 5, y: 5 },
    { label: 'DISPATCH', x: TOTAL_W / 2, z: TOTAL_D - 8, y: 5 },
    { label: 'CHARGING', x: GRID_OX + 7 * CELL, z: GRID_OZ - 2, y: 4 },
  ];
  for (const zl of zoneLabels) {
    const sign = makeSignPlane(zl.label, 2.5, 0.8);
    sign.position.set(zl.x, zl.y, zl.z);
    sign.matrixAutoUpdate = false; sign.updateMatrix();
    signGroup.add(sign);
  }

  // ── Safety signs ──
  const safetyLabels = ['CAUTION', 'HARD HAT AREA', 'NO ENTRY'];
  for (let i = 0; i < safetyLabels.length; i++) {
    const sign = makeSignPlane(safetyLabels[i], 1.2, 0.5);
    sign.position.set(5, 3 + i * 1.5, 0.3);
    sign.matrixAutoUpdate = false; sign.updateMatrix();
    signGroup.add(sign);
  }

  // ── Wall banner ──
  const banner = makeSignPlane('SmartWarehouse AI — Digital Twin', 8, 1.5);
  banner.position.set(TOTAL_W / 2, HALL_H - 3, 0.3);
  banner.matrixAutoUpdate = false; banner.updateMatrix();
  signGroup.add(banner);

  scene.add(signGroup);
  state.groups.signage = signGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §16  SAFETY INFRASTRUCTURE (Guard Rails, Bollards, Kiosks)
   ═══════════════════════════════════════════════════════════════ */

function buildSafetyInfra(scene) {
  const safetyGroup = new THREE.Group();
  safetyGroup.name = 'safety';

  // ── Guard rails at rack base rows (instanced) ──
  const guardRailGeo = new THREE.BoxGeometry(0.08, 0.5, GRID_ROWS * CELL);
  const guardRailPositions = [];
  for (const [x0, x1] of X_BLOCKS) {
    guardRailPositions.push(GRID_OX + x0 * CELL - 1.0);
    guardRailPositions.push(GRID_OX + (x1 + 1) * CELL + 1.0);
  }
  const grIM = new THREE.InstancedMesh(guardRailGeo, materials.yellowGuard, guardRailPositions.length);
  const grM = new THREE.Matrix4();
  guardRailPositions.forEach((gx, i) => {
    grM.makeTranslation(gx, 0.25, GRID_OZ + GRID_ROWS * CELL / 2);
    grIM.setMatrixAt(i, grM);
  });
  grIM.instanceMatrix.needsUpdate = true;
  grIM.matrixAutoUpdate = false;
  safetyGroup.add(grIM);

  // ── Bollards at aisle ends ──
  const bollardGeo = new THREE.CylinderGeometry(0.08, 0.1, 0.8, 8);
  const bollardPositions = [];
  for (let c = 0; c < GRID_COLS; c += 4) {
    bollardPositions.push([GRID_OX + c * CELL + CELL / 2, GRID_OZ - 0.5]);
    bollardPositions.push([GRID_OX + c * CELL + CELL / 2, GRID_OZ + GRID_ROWS * CELL + 0.5]);
  }
  const bIM = new THREE.InstancedMesh(bollardGeo, materials.yellow, bollardPositions.length);
  bollardPositions.forEach(([bx, bz], i) => {
    grM.makeTranslation(bx, 0.4, bz);
    bIM.setMatrixAt(i, grM);
  });
  bIM.instanceMatrix.needsUpdate = true;
  bIM.matrixAutoUpdate = false;
  safetyGroup.add(bIM);

  // ── Kiosks / Terminals ──
  const kioskPositions = [
    [GRID_OX - 3, 0, GRID_OZ + 4 * CELL],
    [GRID_OX - 3, 0, GRID_OZ + 10 * CELL],
    [TOTAL_W - 10, 0, TOTAL_D / 2],
  ];
  for (const [kx, ky, kz] of kioskPositions) {
    // Terminal body
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.5, 0.3), materials.steelDark);
    body.position.set(kx, 0.75, kz);
    body.matrixAutoUpdate = false; body.updateMatrix();
    safetyGroup.add(body);

    // Glowing screen
    const screenGeo = new THREE.PlaneGeometry(0.4, 0.3);
    const screenMat = new THREE.MeshBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.8 });
    const screen = new THREE.Mesh(screenGeo, screenMat);
    screen.position.set(kx, 1.3, kz + 0.16);
    screen.matrixAutoUpdate = false; screen.updateMatrix();
    safetyGroup.add(screen);
  }

  scene.add(safetyGroup);
  state.groups.safety = safetyGroup;
}

/* ═══════════════════════════════════════════════════════════════
   §17  KPI WALL DISPLAY
   ═══════════════════════════════════════════════════════════════ */

function buildKPIDisplay(scene) {
  const kpiTex = makeKPITexture(null);
  const kpiMat = new THREE.MeshBasicMaterial({ map: kpiTex, transparent: true });
  const kpiGeo = new THREE.PlaneGeometry(10, 5);
  const kpiMesh = new THREE.Mesh(kpiGeo, kpiMat);
  kpiMesh.position.set(TOTAL_W / 2, 9, 0.4);
  kpiMesh.matrixAutoUpdate = false;
  kpiMesh.updateMatrix();
  scene.add(kpiMesh);
  state.kpiMesh = kpiMesh;
  state.kpiTexture = kpiTex;
}

/* ═══════════════════════════════════════════════════════════════
   §18  AUTONOMOUS ROBOT FLEET — 5 HIGH-FIDELITY MODELS
   1. TITAN-X (Heavy AMR Vehicle)
   2. ATLAS (White & Blue Advanced Humanoid)
   3. VORTEX (Dark Graphite & Orange Industrial Sorter)
   4. NOVA (White & Green Intelligent Inspector)
   5. SPECTRE (Titanium & Cyan Autonomous Assistant)
   ═══════════════════════════════════════════════════════════════ */

function buildRobotLabel(id, name, typeTitle, colorHex) {
  const labelTex = makeCanvasTex(320, 80, (ctx, w, h) => {
    ctx.clearRect(0, 0, w, h);
    // Dark glass backing
    ctx.fillStyle = 'rgba(10, 15, 26, 0.82)';
    ctx.roundRect(4, 4, w - 8, h - 8, 8);
    ctx.fill();
    // Border in robot's accent color
    ctx.strokeStyle = colorHex;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Top row: ID and Name
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 24px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(`${name}`, 14, 14);

    // Right status indicator dot
    ctx.fillStyle = colorHex;
    ctx.beginPath();
    ctx.arc(w - 20, 26, 6, 0, Math.PI * 2);
    ctx.fill();

    // Bottom row: Role / Model Type
    ctx.fillStyle = colorHex;
    ctx.font = '600 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillText(typeTitle.toUpperCase(), 14, 48);
  });
  const labelMat = new THREE.SpriteMaterial({ map: labelTex, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(labelMat);
  sprite.scale.set(2.0, 0.5, 1);
  return sprite;
}

// ── ROBOT 01: TITAN-X (Heavy-Duty AMR Vehicle) ──
function buildTitanXAMR(id, meta) {
  const robot = new THREE.Group();
  robot.name = `amr-${id}`;
  robot.userData = {
    isAMR: true,
    id: id,
    name: 'TITAN-X',
    modelType: 'HEAVY_AMR',
    accentColor: '#00f0ff',
    wheels: [],
  };

  // Heavy-duty lower chassis (graphite / dark metallic)
  const chassisGeo = new THREE.BoxGeometry(1.05, 0.24, 1.35);
  const chassis = new THREE.Mesh(chassisGeo, materials.titanDark);
  chassis.position.y = 0.22;
  chassis.castShadow = true;
  chassis.receiveShadow = true;
  robot.add(chassis);

  // Upper aerodynamic armor shell (pure white metallic with chamfered look)
  const cowlGeo = new THREE.BoxGeometry(0.96, 0.22, 1.25);
  const cowl = new THREE.Mesh(cowlGeo, materials.titanWhite);
  cowl.position.y = 0.40;
  cowl.castShadow = true;
  robot.add(cowl);

  // Front bumper with industrial shock pads and sensors
  const bumperGeo = new THREE.BoxGeometry(1.02, 0.12, 0.10);
  const bumper = new THREE.Mesh(bumperGeo, materials.steelDark);
  bumper.position.set(0, 0.25, 0.68);
  robot.add(bumper);

  // Front optical sensor strip
  for (let s = -3; s <= 3; s++) {
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.018, 8, 8), materials.cyanEmissive);
    dot.position.set(s * 0.12, 0.38, 0.63);
    robot.add(dot);
  }

  // Dual high-intensity LED headlights with cyan halo rings
  for (const sx of [-0.32, 0.32]) {
    const ringGeo = new THREE.TorusGeometry(0.07, 0.014, 8, 24);
    const ring = new THREE.Mesh(ringGeo, materials.cyanEmissive.clone());
    ring.position.set(sx, 0.36, 0.64);
    ring.rotation.y = Math.PI / 2;
    ring.userData.headlightRing = true;
    robot.add(ring);

    const lensGeo = new THREE.CircleGeometry(0.055, 16);
    const lens = new THREE.Mesh(lensGeo, materials.cyanGlow);
    lens.position.set(sx, 0.36, 0.645);
    robot.add(lens);
  }

  // Rear safety tailbar
  const tailGeo = new THREE.BoxGeometry(0.85, 0.04, 0.02);
  const tail = new THREE.Mesh(tailGeo, materials.redEmissive);
  tail.position.set(0, 0.35, -0.68);
  robot.add(tail);

  // 4 Heavy-duty all-terrain wheels with rubber treads & steel rims
  const wheelGeo = new THREE.CylinderGeometry(0.14, 0.14, 0.09, 16);
  wheelGeo.rotateZ(Math.PI / 2);
  const hubGeo = new THREE.CylinderGeometry(0.07, 0.07, 0.10, 10);
  hubGeo.rotateZ(Math.PI / 2);

  const wheelPositions = [
    [-0.54, 0.14, 0.42], [0.54, 0.14, 0.42],
    [-0.54, 0.14, -0.42], [0.54, 0.14, -0.42]
  ];
  for (const [wx, wy, wz] of wheelPositions) {
    const wGroup = new THREE.Group();
    wGroup.position.set(wx, wy, wz);
    const tire = new THREE.Mesh(wheelGeo, materials.rubber);
    tire.castShadow = true;
    wGroup.add(tire);
    const hub = new THREE.Mesh(hubGeo, materials.steel);
    wGroup.add(hub);
    robot.add(wGroup);
    robot.userData.wheels.push(wGroup);
  }

  // Top rotating LiDAR turret puck
  const lidarBase = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, 0.05, 18), materials.steelDark);
  lidarBase.position.set(0, 0.53, 0.35);
  robot.add(lidarBase);

  const lidarDome = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.06, 18), materials.titanDark);
  lidarDome.position.set(0, 0.58, 0.35);
  robot.add(lidarDome);
  robot.userData.lidarDome = lidarDome;

  const lidarRing = new THREE.Mesh(new THREE.TorusGeometry(0.095, 0.01, 8, 24), materials.cyanEmissive.clone());
  lidarRing.rotation.x = -Math.PI / 2;
  lidarRing.position.set(0, 0.57, 0.35);
  robot.add(lidarRing);

  // Wide cyan underglow illumination plane
  const underglowGeo = new THREE.PlaneGeometry(1.1, 1.4);
  underglowGeo.rotateX(-Math.PI / 2);
  const underglowMat = new THREE.MeshBasicMaterial({ color: COL_CYAN, transparent: true, opacity: 0.45, side: THREE.DoubleSide });
  const underglow = new THREE.Mesh(underglowGeo, underglowMat);
  underglow.position.y = 0.02;
  robot.add(underglow);
  robot.userData.underglow = underglow;

  // Cargo Deck & Pallet Stack
  const deckGeo = new THREE.BoxGeometry(0.88, 0.04, 0.85);
  const deck = new THREE.Mesh(deckGeo, materials.steelDark);
  deck.position.set(0, 0.53, -0.15);
  robot.add(deck);

  const cargoGroup = new THREE.Group();
  // Wooden Euro-pallet
  const palletGeo = new THREE.BoxGeometry(0.84, 0.08, 0.80);
  const pallet = new THREE.Mesh(palletGeo, materials.palletWood);
  pallet.position.set(0, 0.59, -0.15);
  cargoGroup.add(pallet);

  // Palletized heavy package containers
  for (let r = 0; r < 2; r++) {
    for (let c = 0; c < 2; c++) {
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.28, 0.36), (r + c) % 2 === 0 ? materials.carton : materials.blueTote);
      box.position.set(-0.2 + r * 0.4, 0.77, -0.32 + c * 0.36);
      box.castShadow = true;
      cargoGroup.add(box);
    }
  }
  robot.add(cargoGroup);
  robot.userData.cargo = cargoGroup;

  // Holographic Billboard Label
  const label = buildRobotLabel(id, '01 TITAN-X', 'Heavy-Duty Autonomous AMR', '#00f0ff');
  label.position.set(0, 1.45, 0);
  robot.add(label);
  robot.userData.label = label;

  return robot;
}

// ── ARTICULATED HUMANOID SKELETON BUILDER (ATLAS, VORTEX, NOVA, SPECTRE) ──
function buildHumanoidSkeleton(config) {
  const {
    id,
    name,
    title,
    primaryMat,
    secondaryMat,
    coreMat,
    accentColor,
    headStyle,
    isInspector,
    isSorter,
  } = config;

  const robot = new THREE.Group();
  robot.name = `amr-${id}`;
  robot.userData = {
    isAMR: true,
    id: id,
    name: name,
    modelType: 'HUMANOID',
    isHumanoid: true,
    accentColor: accentColor,
    walkPhase: id * 1.5,
  };

  // 1. Pelvis / Hips root
  const pelvisGeo = new THREE.BoxGeometry(0.32, 0.16, 0.22);
  const pelvis = new THREE.Mesh(pelvisGeo, secondaryMat);
  pelvis.position.y = 0.85;
  pelvis.castShadow = true;
  robot.add(pelvis);

  // 2. Torso Group
  const torsoGroup = new THREE.Group();
  torsoGroup.position.set(0, 0.88, 0);

  // Segmented abdomen with spine hydraulic cylinder
  const spineGeo = new THREE.CylinderGeometry(0.09, 0.11, 0.24, 12);
  const spine = new THREE.Mesh(spineGeo, materials.jointCarbon);
  spine.position.y = 0.12;
  torsoGroup.add(spine);

  // Sculpted Upper Chest Armor
  const chestGeo = new THREE.BoxGeometry(0.48, 0.34, 0.28);
  const chest = new THREE.Mesh(chestGeo, primaryMat);
  chest.position.y = 0.38;
  chest.castShadow = true;
  torsoGroup.add(chest);

  // Secondary chestplate layer
  const chestPlateGeo = new THREE.BoxGeometry(0.42, 0.28, 0.05);
  const chestPlate = new THREE.Mesh(chestPlateGeo, secondaryMat);
  chestPlate.position.set(0, 0.40, 0.14);
  torsoGroup.add(chestPlate);

  // Central Luminous Arc-Reactor / Core Indicator
  const coreRimGeo = new THREE.TorusGeometry(0.06, 0.015, 8, 24);
  const coreRim = new THREE.Mesh(coreRimGeo, materials.steelDark);
  coreRim.position.set(0, 0.40, 0.168);
  torsoGroup.add(coreRim);

  const coreGeo = new THREE.CircleGeometry(0.05, 16);
  const coreLens = new THREE.Mesh(coreGeo, coreMat);
  coreLens.position.set(0, 0.40, 0.17);
  torsoGroup.add(coreLens);

  // Neck with hydraulic mini-pistons
  const neckGeo = new THREE.CylinderGeometry(0.07, 0.08, 0.12, 10);
  const neck = new THREE.Mesh(neckGeo, materials.steelDark);
  neck.position.y = 0.58;
  torsoGroup.add(neck);

  // 3. Head Group
  const headGroup = new THREE.Group();
  headGroup.position.set(0, 0.70, 0);

  // Sculpted helmet shell
  const helmetGeo = new THREE.BoxGeometry(0.24, 0.24, 0.24);
  const helmet = new THREE.Mesh(helmetGeo, primaryMat);
  helmet.castShadow = true;
  headGroup.add(helmet);

  if (headStyle === 'atlas') {
    // Aerodynamic crown crest
    const crestGeo = new THREE.BoxGeometry(0.08, 0.06, 0.26);
    const crest = new THREE.Mesh(crestGeo, secondaryMat);
    crest.position.y = 0.13;
    headGroup.add(crest);

    // Glowing ocular display band
    const visorGeo = new THREE.BoxGeometry(0.19, 0.05, 0.04);
    const visor = new THREE.Mesh(visorGeo, coreMat);
    visor.position.set(0, 0.02, 0.12);
    headGroup.add(visor);

    // Circular ear actuator pods
    for (const sx of [-0.13, 0.13]) {
      const ear = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.03, 16), materials.steelDark);
      ear.rotation.z = Math.PI / 2;
      ear.position.set(sx, 0.02, 0);
      headGroup.add(ear);
    }
  } else if (headStyle === 'vortex') {
    // Angular heavy industrial helmet
    const browGeo = new THREE.BoxGeometry(0.26, 0.08, 0.10);
    const brow = new THREE.Mesh(browGeo, secondaryMat);
    brow.position.set(0, 0.08, 0.09);
    headGroup.add(brow);

    // Aggressive orange twin sensor slits
    for (const sx of [-0.05, 0.05]) {
      const slit = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.025, 0.04), coreMat);
      slit.position.set(sx, 0.01, 0.12);
      headGroup.add(slit);
    }
  } else if (headStyle === 'nova') {
    // Sleek optical sensor helmet with emerald visor & top lidar pod
    const visorGeo = new THREE.CylinderGeometry(0.10, 0.10, 0.04, 16, 1, false, 0, Math.PI);
    const visor = new THREE.Mesh(visorGeo, coreMat);
    visor.position.set(0, 0.02, 0.10);
    headGroup.add(visor);

    const miniLidar = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.03, 12), materials.steelDark);
    miniLidar.position.set(0, 0.14, 0.03);
    headGroup.add(miniLidar);
  } else {
    // Spectre faceted stealth helmet
    const stealthGeo = new THREE.ConeGeometry(0.14, 0.24, 4);
    stealthGeo.rotateY(Math.PI / 4);
    const stealthFace = new THREE.Mesh(stealthGeo, secondaryMat);
    stealthFace.position.set(0, 0.02, 0.06);
    headGroup.add(stealthFace);

    const eyeLeft = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.06, 0.04), coreMat);
    eyeLeft.position.set(-0.04, 0.03, 0.12);
    headGroup.add(eyeLeft);
    const eyeRight = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.06, 0.04), coreMat);
    eyeRight.position.set(0.04, 0.03, 0.12);
    headGroup.add(eyeRight);
  }

  torsoGroup.add(headGroup);
  robot.userData.head = headGroup;

  // 4. Arms (Pivoting at shoulders)
  function createArm(isLeft) {
    const armGroup = new THREE.Group();
    const sign = isLeft ? -1 : 1;
    armGroup.position.set(sign * 0.32, 0.44, 0);

    // Shoulder pauldron armor
    const pauldronGeo = new THREE.SphereGeometry(0.10, 10, 8, 0, Math.PI * 2, 0, Math.PI / 2);
    const pauldron = new THREE.Mesh(pauldronGeo, secondaryMat);
    pauldron.position.set(0, 0, 0);
    armGroup.add(pauldron);

    // Upper bicep
    const bicepGeo = new THREE.CylinderGeometry(0.05, 0.045, 0.22, 10);
    const bicep = new THREE.Mesh(bicepGeo, primaryMat);
    bicep.position.set(0, -0.11, 0);
    armGroup.add(bicep);

    // Elbow hinge
    const elbowGeo = new THREE.SphereGeometry(0.048, 8, 8);
    const elbow = new THREE.Mesh(elbowGeo, materials.jointCarbon);
    elbow.position.set(0, -0.22, 0);
    armGroup.add(elbow);

    // Forearm
    const forearmGeo = new THREE.BoxGeometry(0.08, 0.20, 0.09);
    const forearm = new THREE.Mesh(forearmGeo, primaryMat);
    forearm.position.set(0, -0.32, 0);
    armGroup.add(forearm);

    // Mechanical hand / gripper / scanner
    if (!isLeft && isInspector) {
      // NOVA's optical scanning module
      const scannerModule = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.10, 0.12), materials.steelDark);
      scannerModule.position.set(0, -0.44, 0.04);
      armGroup.add(scannerModule);

      const scannerEmitter = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.02, 12), materials.novaGreen);
      scannerEmitter.rotation.x = Math.PI / 2;
      scannerEmitter.position.set(0, -0.44, 0.10);
      armGroup.add(scannerEmitter);

      // Green holographic inspection light cone
      const coneGeo = new THREE.ConeGeometry(0.35, 1.2, 16, 1, true);
      coneGeo.rotateX(-Math.PI / 2);
      coneGeo.translate(0, 0, 0.6);
      const coneMat = new THREE.MeshBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
      const scannerCone = new THREE.Mesh(coneGeo, coneMat);
      scannerCone.position.set(0, -0.44, 0.10);
      scannerCone.visible = false;
      armGroup.add(scannerCone);
      robot.userData.scannerCone = scannerCone;
    } else if (isSorter) {
      // VORTEX sorting twin grippers
      for (const gx of [-0.025, 0.025]) {
        const finger = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.08, 0.03), materials.steel);
        finger.position.set(gx, -0.45, 0);
        armGroup.add(finger);
      }
    } else {
      // Articulated fingers
      const palm = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.05, 0.06), materials.steel);
      palm.position.set(0, -0.43, 0);
      armGroup.add(palm);
      for (let f = -1; f <= 1; f++) {
        const finger = new THREE.Mesh(new THREE.BoxGeometry(0.015, 0.04, 0.02), materials.jointCarbon);
        finger.position.set(f * 0.022, -0.47, 0.01);
        armGroup.add(finger);
      }
    }

    return armGroup;
  }

  const leftArm = createArm(true);
  const rightArm = createArm(false);
  torsoGroup.add(leftArm);
  torsoGroup.add(rightArm);
  robot.userData.leftArm = leftArm;
  robot.userData.rightArm = rightArm;

  robot.add(torsoGroup);
  robot.userData.torso = torsoGroup;

  // 5. Legs (Pivoting at hips)
  function createLeg(isLeft) {
    const legGroup = new THREE.Group();
    const sign = isLeft ? -1 : 1;
    legGroup.position.set(sign * 0.14, 0.82, 0);

    // Hip socket
    const hip = new THREE.Mesh(new THREE.SphereGeometry(0.065, 10, 8), materials.jointCarbon);
    legGroup.add(hip);

    // Upper thigh
    const thighGeo = new THREE.BoxGeometry(0.12, 0.32, 0.14);
    const thigh = new THREE.Mesh(thighGeo, primaryMat);
    thigh.position.set(0, -0.16, 0);
    thigh.castShadow = true;
    legGroup.add(thigh);

    // Knee actuator
    const kneeGeo = new THREE.CylinderGeometry(0.055, 0.055, 0.11, 10);
    kneeGeo.rotateZ(Math.PI / 2);
    const knee = new THREE.Mesh(kneeGeo, materials.jointCarbon);
    knee.position.set(0, -0.34, 0);
    legGroup.add(knee);

    // Calf Group (pivoting at knee)
    const calfGroup = new THREE.Group();
    calfGroup.position.set(0, -0.34, 0);

    const shinGeo = new THREE.BoxGeometry(0.11, 0.34, 0.12);
    const shin = new THREE.Mesh(shinGeo, secondaryMat);
    shin.position.set(0, -0.17, 0);
    shin.castShadow = true;
    calfGroup.add(shin);

    // Ankle joint & stabilizer foot
    const footGeo = new THREE.BoxGeometry(0.12, 0.06, 0.22);
    const foot = new THREE.Mesh(footGeo, materials.titanDark);
    foot.position.set(0, -0.36, 0.04);
    foot.castShadow = true;
    calfGroup.add(foot);

    // Magnetic sole plate in accent color
    const soleGeo = new THREE.PlaneGeometry(0.11, 0.20);
    soleGeo.rotateX(-Math.PI / 2);
    const sole = new THREE.Mesh(soleGeo, new THREE.MeshBasicMaterial({ color: accentColor }));
    sole.position.set(0, -0.39, 0.04);
    calfGroup.add(sole);

    legGroup.add(calfGroup);
    legGroup.userData.calf = calfGroup;

    return legGroup;
  }

  const leftLeg = createLeg(true);
  const rightLeg = createLeg(false);
  robot.add(leftLeg);
  robot.add(rightLeg);
  robot.userData.leftLeg = leftLeg;
  robot.userData.rightLeg = rightLeg;
  robot.userData.leftCalf = leftLeg.userData.calf;
  robot.userData.rightCalf = rightLeg.userData.calf;

  // Subtle circular underglow footprint
  const discGeo = new THREE.CircleGeometry(0.45, 18);
  discGeo.rotateX(-Math.PI / 2);
  const discMat = new THREE.MeshBasicMaterial({ color: accentColor, transparent: true, opacity: 0.35 });
  const underglow = new THREE.Mesh(discGeo, discMat);
  underglow.position.y = 0.02;
  robot.add(underglow);
  robot.userData.underglow = underglow;

  // Floating Holographic Billboard Label
  const label = buildRobotLabel(id, `0${id} ${name}`, title, accentColor);
  label.position.set(0, 2.15, 0);
  robot.add(label);
  robot.userData.label = label;

  // Parcel Cargo carried in front of humanoid (visible when carrying)
  const cargoGroup = new THREE.Group();
  const boxGeo = new THREE.BoxGeometry(0.38, 0.28, 0.32);
  const boxMat = new THREE.MeshStandardMaterial({ color: 0xc8965a, roughness: 0.8 });
  const carriedBox = new THREE.Mesh(boxGeo, boxMat);
  carriedBox.position.set(0, 0.95, 0.32);
  carriedBox.castShadow = true;
  cargoGroup.add(carriedBox);

  const tapeGeo = new THREE.BoxGeometry(0.39, 0.04, 0.33);
  const tapeMat = new THREE.MeshStandardMaterial({ color: 0x93663a, roughness: 0.5 });
  const tape = new THREE.Mesh(tapeGeo, tapeMat);
  tape.position.set(0, 0.95, 0.32);
  cargoGroup.add(tape);

  cargoGroup.visible = false;
  robot.add(cargoGroup);
  robot.userData.cargo = cargoGroup;

  return robot;
}

// ── ROBOT BUILDERS FOR THE 5 AUTONOMOUS AGENTS ──

function buildAtlasHumanoid(id, meta) {
  return buildHumanoidSkeleton({
    id: id,
    name: 'ATLAS',
    title: 'Advanced Humanoid Logistics',
    primaryMat: materials.atlasArmorWhite,
    secondaryMat: materials.atlasArmorBlue,
    coreMat: materials.atlasCoreCyan,
    accentColor: '#2563eb',
    headStyle: 'atlas',
    isInspector: false,
    isSorter: false,
  });
}

function buildVortexHumanoid(id, meta) {
  return buildHumanoidSkeleton({
    id: id,
    name: 'VORTEX',
    title: 'Industrial Humanoid Sorter',
    primaryMat: materials.vortexGraphite,
    secondaryMat: materials.vortexSilver,
    coreMat: materials.vortexOrange,
    accentColor: '#ff6b00',
    headStyle: 'vortex',
    isInspector: false,
    isSorter: true,
  });
}

function buildNovaHumanoid(id, meta) {
  return buildHumanoidSkeleton({
    id: id,
    name: 'NOVA',
    title: 'Intelligent Inspection Humanoid',
    primaryMat: materials.novaWhite,
    secondaryMat: materials.novaSilver,
    coreMat: materials.novaGreen,
    accentColor: '#10b981',
    headStyle: 'nova',
    isInspector: true,
    isSorter: false,
  });
}

function buildSpectreHumanoid(id, meta) {
  return buildHumanoidSkeleton({
    id: id,
    name: 'SPECTRE',
    title: 'Autonomous Humanoid Assistant',
    primaryMat: materials.spectreTitanium,
    secondaryMat: materials.spectreBlack,
    coreMat: materials.spectreCyan,
    accentColor: '#06b6d4',
    headStyle: 'spectre',
    isInspector: false,
    isSorter: false,
  });
}

// ── MASTER DISPATCHER FOR ROBOT MODELS ──
function buildRobot(id, data = {}) {
  const robotId = Number(id);
  let robot;
  if (robotId === 1) robot = buildTitanXAMR(1, data);
  else if (robotId === 2) robot = buildAtlasHumanoid(2, data);
  else if (robotId === 3) robot = buildVortexHumanoid(3, data);
  else if (robotId === 4) robot = buildNovaHumanoid(4, data);
  else if (robotId === 5) robot = buildSpectreHumanoid(5, data);
  else robot = buildTitanXAMR(robotId, data);

  // Prominent realistic industrial scale: clearly visible across the entire warehouse
  if (robotId === 1) {
    robot.scale.set(1.35, 1.35, 1.35);
  } else {
    robot.scale.set(1.42, 1.42, 1.42);
  }
  return robot;
}

/* ═══════════════════════════════════════════════════════════════
   §19  DIGITAL TWIN OVERLAYS
   ═══════════════════════════════════════════════════════════════ */

function buildOverlayGroup(scene) {
  const overlayGroup = new THREE.Group();
  overlayGroup.name = 'overlays';

  // ── Scanline sweep plane (wireframe theme) ──
  const scanGeo = new THREE.PlaneGeometry(TOTAL_W, HALL_H);
  const scanPlane = new THREE.Mesh(scanGeo, materials.scanline);
  scanPlane.position.set(TOTAL_W / 2, HALL_H / 2, 0);
  scanPlane.visible = false;
  overlayGroup.add(scanPlane);
  state.scanlinePlane = scanPlane;

  scene.add(overlayGroup);
  state.groups.overlays = overlayGroup;
}

function updatePathRibbons(paths) {
  const overlayGroup = state.groups.overlays;
  if (!overlayGroup) return;

  // Remove old path ribbons
  state.overlays.paths.forEach(p => { overlayGroup.remove(p); disposeMesh(p); });
  state.overlays.paths = [];

  if (!state.showPaths || !paths) return;

  const chevronTex = makeChevronTexture();
  chevronTex.wrapS = THREE.RepeatWrapping;
  chevronTex.wrapT = THREE.RepeatWrapping;
  chevronTex.repeat.set(4, 1);

  for (const path of paths) {
    if (!path || path.length < 2) continue;
    const points = path.map(([gx, gy]) => {
      const wp = gridToWorld(gx, gy);
      return new THREE.Vector3(wp.x, 0.1, wp.z);
    });
    const curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.3);
    const tubeGeo = new THREE.TubeGeometry(curve, Math.max(points.length * 4, 8), 0.12, 6, false);
    const tubeMat = new THREE.MeshBasicMaterial({ map: chevronTex, transparent: true, opacity: 0.6, side: THREE.DoubleSide });
    const tube = new THREE.Mesh(tubeGeo, tubeMat);
    tube.userData.chevronOffset = 0;
    overlayGroup.add(tube);
    state.overlays.paths.push(tube);
  }
}

function updateSensorMarkers(sensors) {
  const overlayGroup = state.groups.overlays;
  if (!overlayGroup) return;

  state.overlays.sensors.forEach(s => { overlayGroup.remove(s); disposeMesh(s); });
  state.overlays.sensors = [];

  if (!state.showSensors || !sensors) return;

  const domeGeo = new THREE.SphereGeometry(0.5, 12, 8);
  for (const sensor of sensors) {
    const wp = gridToWorld(sensor.x, sensor.y);
    const dome = new THREE.Mesh(domeGeo, materials.sensorDome.clone());
    dome.position.set(wp.x, 0.5, wp.z);
    dome.matrixAutoUpdate = false; dome.updateMatrix();
    overlayGroup.add(dome);
    state.overlays.sensors.push(dome);
  }
}

function updateHazardZones(hazards) {
  const overlayGroup = state.groups.overlays;
  if (!overlayGroup) return;

  state.overlays.hazards.forEach(h => { overlayGroup.remove(h); disposeMesh(h); });
  state.overlays.hazards = [];

  if (!state.showHazards || !hazards) return;

  for (const hz of hazards) {
    const wp = gridToWorld(hz.x, hz.y);
    const ringGeo = new THREE.TorusGeometry(0.8, 0.06, 8, 32);
    const ring = new THREE.Mesh(ringGeo, materials.hazardRing.clone());
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(wp.x, 0.1, wp.z);
    ring.userData.hazardPulse = true;
    overlayGroup.add(ring);
    state.overlays.hazards.push(ring);
  }
}

function updateTaskBeacons(tasks) {
  const overlayGroup = state.groups.overlays;
  if (!overlayGroup) return;

  state.overlays.taskBeacons.forEach(tb => { overlayGroup.remove(tb); disposeMesh(tb); });
  state.overlays.taskBeacons = [];

  if (!tasks) return;

  for (const task of tasks) {
    if (task.pickup) {
      const wp = gridToWorld(task.pickup[0], task.pickup[1]);
      const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), materials.taskBeacon.clone());
      beacon.position.set(wp.x, 1.5, wp.z);
      beacon.userData.beacon = true;
      overlayGroup.add(beacon);
      state.overlays.taskBeacons.push(beacon);
    }
    if (task.dropoff) {
      const wp = gridToWorld(task.dropoff[0], task.dropoff[1]);
      const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), materials.amberEmissive.clone());
      beacon.position.set(wp.x, 1.5, wp.z);
      beacon.userData.beacon = true;
      overlayGroup.add(beacon);
      state.overlays.taskBeacons.push(beacon);
    }
  }
}

function updateParcels(parcels) {
  const overlayGroup = state.groups.overlays;
  if (!overlayGroup) return;

  if (!state.overlays.parcels) state.overlays.parcels = [];
  state.overlays.parcels.forEach(pMesh => { overlayGroup.remove(pMesh); disposeMesh(pMesh); });
  state.overlays.parcels = [];

  if (!parcels || !Array.isArray(parcels)) return;

  for (const p of parcels) {
    // Only render static parcel when not currently picked up by a robot
    if (p.status === 'AVAILABLE' || p.status === 'RESERVED') {
      const loc = p.location || [0, 0];
      const wp = gridToWorld(loc[0], loc[1]);
      let geo, mat;
      if (p.parcel_type === 'WOODEN_PALLET' || p.parcel_type === 'HEAVY_INDUSTRIAL') {
        geo = new THREE.BoxGeometry(0.8, 0.45, 0.8);
        mat = materials.palletWood || new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.8 });
      } else if (p.parcel_type === 'TOTE_BLUE') {
        geo = new THREE.BoxGeometry(0.45, 0.3, 0.35);
        mat = materials.blueTote || new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.5 });
      } else if (p.parcel_type === 'TOTE_RED' || p.parcel_type === 'HAZMAT') {
        geo = new THREE.BoxGeometry(0.45, 0.3, 0.35);
        mat = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.5 });
      } else if (p.parcel_type === 'FRAGILE') {
        geo = new THREE.BoxGeometry(0.4, 0.3, 0.35);
        mat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.5 });
      } else {
        geo = new THREE.BoxGeometry(0.4, 0.3, 0.35);
        mat = materials.carton || new THREE.MeshStandardMaterial({ color: 0xc8965a, roughness: 0.8 });
      }
      const parcelMesh = new THREE.Mesh(geo, mat);
      parcelMesh.position.set(wp.x, 0.25, wp.z);
      parcelMesh.castShadow = true;
      parcelMesh.userData.isParcel = true;
      parcelMesh.userData.parcelId = p.parcel_id;
      overlayGroup.add(parcelMesh);
      state.overlays.parcels.push(parcelMesh);
    } else if (p.status === 'DELIVERED') {
      const dest = p.destination || [0, 0];
      const wp = gridToWorld(dest[0], dest[1]);
      const geo = new THREE.BoxGeometry(0.4, 0.3, 0.35);
      const mat = new THREE.MeshStandardMaterial({ color: 0x10b981, roughness: 0.6 });
      const parcelMesh = new THREE.Mesh(geo, mat);
      parcelMesh.position.set(wp.x, 0.2, wp.z);
      parcelMesh.castShadow = true;
      parcelMesh.userData.isParcel = true;
      parcelMesh.userData.parcelId = p.parcel_id;
      overlayGroup.add(parcelMesh);
      state.overlays.parcels.push(parcelMesh);
    }
  }
}

/* ═══════════════════════════════════════════════════════════════
   §20  THEME SYSTEM
   ═══════════════════════════════════════════════════════════════ */

function setTheme(themeName) {
  state.activeTheme = themeName;
  const scene = state.scene;
  const renderer = state.renderer;

  // Restore original materials if switching away from wireframe
  if (state.originalMaterials.size > 0 && themeName !== 'wireframe') {
    state.originalMaterials.forEach((origMat, mesh) => {
      mesh.material = origMat;
    });
    state.originalMaterials.clear();
    // Remove edge lines
    state.wireframeEdges.forEach(edge => scene.remove(edge));
    state.wireframeEdges = [];
  }

  if (themeName === 'realistic') {
    scene.background = new THREE.Color(COL_DARK_BG);
    scene.fog = new THREE.FogExp2(COL_DARK_BG, 0.004);
    state.keySun.intensity = 1.5;
    state.keySun.color.set(0xfff5e6);
    state.hemiLight.intensity = 0.75;
    state.ambientLight.intensity = 0.3;
    if (state.groups.floor) state.groups.floor.material = materials.floor;
    if (state.scanlinePlane) state.scanlinePlane.visible = false;
    if (state.ledFixtureInstance) state.ledFixtureInstance.material.color.set(0xfff8e1);

  } else if (themeName === 'nightops') {
    scene.background = new THREE.Color(0x040711);
    scene.fog = new THREE.FogExp2(0x040711, 0.008);
    state.keySun.intensity = 0.3;
    state.keySun.color.set(0x8899bb);
    state.hemiLight.intensity = 0.2;
    state.ambientLight.intensity = 0.15;
    if (state.groups.floor) state.groups.floor.material = materials.floorNight;
    if (state.scanlinePlane) state.scanlinePlane.visible = false;
    if (state.ledFixtureInstance) state.ledFixtureInstance.material.color.set(0xccddee);

  } else if (themeName === 'wireframe') {
    scene.background = new THREE.Color(0x020408);
    scene.fog = new THREE.FogExp2(0x020408, 0.006);
    state.keySun.intensity = 0.1;
    state.hemiLight.intensity = 0.1;
    state.ambientLight.intensity = 0.05;
    if (state.scanlinePlane) state.scanlinePlane.visible = true;

    // Swap materials to wireframe (preserve originals)
    scene.traverse(child => {
      if (child.isMesh && !child.userData.isOverlay && child !== state.scanlinePlane) {
        if (!state.originalMaterials.has(child)) {
          state.originalMaterials.set(child, child.material);
        }
        if (child.userData.isAMR || child.userData.headlightRing || child.userData.chargingRing || child.userData.beacon || child.userData.hazardPulse) {
          // Keep emissive for robot parts
          return;
        }
        if (child instanceof THREE.InstancedMesh) {
          child.material = materials.wireframeBlue;
        } else {
          child.material = materials.wireframeCyan;
        }
      }
    });

    // Add EdgesGeometry for key structures
    const edgeTargets = ['structure', 'racking', 'mezzanine'];
    for (const tgt of edgeTargets) {
      const group = state.groups[tgt];
      if (!group) continue;
      group.traverse(child => {
        if (child.isMesh && child.geometry && !(child instanceof THREE.InstancedMesh)) {
          const edges = new THREE.EdgesGeometry(child.geometry, 15);
          const line = new THREE.LineSegments(edges, materials.edgeCyan);
          line.position.copy(child.position);
          line.rotation.copy(child.rotation);
          line.scale.copy(child.scale);
          line.matrixAutoUpdate = false;
          line.updateMatrix();
          scene.add(line);
          state.wireframeEdges.push(line);
        }
      });
    }
  }

  // Update theme buttons
  document.querySelectorAll('#btn-theme-real, #btn-theme-night, #btn-theme-twin').forEach(b => b.classList.remove('active'));
  if (themeName === 'realistic') document.getElementById('btn-theme-real')?.classList.add('active');
  else if (themeName === 'nightops') document.getElementById('btn-theme-night')?.classList.add('active');
  else document.getElementById('btn-theme-twin')?.classList.add('active');
}

/* ═══════════════════════════════════════════════════════════════
   §21  CAMERA SYSTEM
   ═══════════════════════════════════════════════════════════════ */

function initCamera(renderer) {
  const container = document.getElementById('canvas-container');
  const w = container ? container.clientWidth : window.innerWidth;
  const h = container ? container.clientHeight : window.innerHeight;
  const camera = new THREE.PerspectiveCamera(50, w / h, 0.5, 500);
  const preset = CAMERA_PRESETS.CINEMATIC;
  camera.position.set(...preset.pos);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(...preset.target);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxPolarAngle = Math.PI / 2 - 0.05;
  controls.minDistance = 2;
  controls.maxDistance = 200;
  controls.update();

  return { camera, controls };
}

function setCamPresetSmooth(presetName) {
  const preset = CAMERA_PRESETS[presetName];
  if (!preset) return;

  state.followRobot = null;
  state.walkMode = false;

  const from = {
    pos: state.camera.position.clone(),
    target: state.controls.target.clone()
  };
  const to = {
    pos: new THREE.Vector3(...preset.pos),
    target: new THREE.Vector3(...preset.target)
  };

  state.camAnim = createCamAnim(from, to, 1.5);

  // Update camera preset buttons
  document.querySelectorAll('#btn-iso, #btn-top, #btn-aisle, #btn-dock, #btn-cinematic').forEach(b => b.classList.remove('active'));
  const btnMap = { ISO: 'btn-iso', TOP: 'btn-top', AISLE: 'btn-aisle', DOCK: 'btn-dock', CINEMATIC: 'btn-cinematic' };
  const btn = document.getElementById(btnMap[presetName]);
  if (btn) btn.classList.add('active');
}

function resetCamera() {
  state.followRobot = null;
  state.walkMode = false;
  state.tourActive = false;
  setCamPresetSmooth('CINEMATIC');
}

function startFollowCamera(robotId) {
  state.followRobot = robotId;
  state.walkMode = false;
  state.tourActive = false;
}

function startWalkMode() {
  state.walkMode = !state.walkMode;
  if (state.walkMode) {
    state.followRobot = null;
    state.tourActive = false;
    state.camera.position.y = 1.7;
    state.controls.target.set(state.camera.position.x, 1.7, state.camera.position.z - 5);
    document.getElementById('btn-walk')?.classList.add('active');
  } else {
    document.getElementById('btn-walk')?.classList.remove('active');
  }
}

function startTour() {
  state.tourActive = !state.tourActive;
  if (state.tourActive) {
    state.tourIdx = 0;
    state.tourTimer = 0;
    state.followRobot = null;
    state.walkMode = false;
    applyTourStop(0);
    document.getElementById('btn-tour')?.classList.add('active');
  } else {
    document.getElementById('btn-tour')?.classList.remove('active');
    const tourCaption = document.getElementById('tour-caption');
    const tourTitle = document.getElementById('tour-title');
    if (tourCaption) tourCaption.textContent = '';
    if (tourTitle) tourTitle.textContent = '';
  }
}

function applyTourStop(idx) {
  const stop = TOUR_STOPS[idx];
  if (!stop) return;
  setCamPresetSmooth(stop.preset);
  setTheme(stop.theme);
  const tourCaption = document.getElementById('tour-caption');
  const tourTitle = document.getElementById('tour-title');
  if (tourTitle) tourTitle.textContent = stop.title;
  if (tourCaption) tourCaption.textContent = stop.caption;
}

function startHeroCamera() {
  // Find first robot and follow it
  const firstRobot = state.robots.values().next().value;
  if (firstRobot) {
    startFollowCamera(firstRobot.group.userData.id);
  } else {
    setCamPresetSmooth('HERO');
  }
}

function updateCamera(dt) {
  // Camera animation
  if (state.camAnim) {
    state.camAnim.t += dt / state.camAnim.dur;
    if (state.camAnim.t >= 1) {
      state.camera.position.copy(state.camAnim.toPos);
      state.controls.target.copy(state.camAnim.toTarget);
      state.camAnim = null;
    } else {
      const e = easeInOutCubic(state.camAnim.t);
      state.camera.position.lerpVectors(state.camAnim.fromPos, state.camAnim.toPos, e);
      state.controls.target.lerpVectors(state.camAnim.fromTarget, state.camAnim.toTarget, e);
    }
  }

  // Follow camera
  if (state.followRobot !== null) {
    const rData = state.robots.get(state.followRobot);
    if (rData) {
      const rPos = rData.group.position;
      const targetPos = new THREE.Vector3(rPos.x + 4, 3, rPos.z + 4);
      const f = damp(3, dt);
      state.camera.position.lerp(targetPos, f);
      state.controls.target.lerp(new THREE.Vector3(rPos.x, 0.6, rPos.z), f);
    }
  }

  // Walk mode (WASD)
  if (state.walkMode) {
    state.camera.position.y = 1.7;
    const speed = 8 * dt;
    const forward = new THREE.Vector3();
    state.camera.getWorldDirection(forward);
    forward.y = 0;
    forward.normalize();
    const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

    if (state.keysDown.has('KeyW') || state.keysDown.has('ArrowUp')) {
      state.camera.position.addScaledVector(forward, speed);
      state.controls.target.addScaledVector(forward, speed);
    }
    if (state.keysDown.has('KeyS') || state.keysDown.has('ArrowDown')) {
      state.camera.position.addScaledVector(forward, -speed);
      state.controls.target.addScaledVector(forward, -speed);
    }
    if (state.keysDown.has('KeyA') || state.keysDown.has('ArrowLeft')) {
      state.camera.position.addScaledVector(right, -speed);
      state.controls.target.addScaledVector(right, -speed);
    }
    if (state.keysDown.has('KeyD') || state.keysDown.has('ArrowRight')) {
      state.camera.position.addScaledVector(right, speed);
      state.controls.target.addScaledVector(right, speed);
    }
    state.controls.target.y = 1.7;
  }

  // Tour mode
  if (state.tourActive) {
    state.tourTimer += dt;
    if (state.tourTimer > 6) {
      state.tourTimer = 0;
      state.tourIdx = (state.tourIdx + 1) % TOUR_STOPS.length;
      applyTourStop(state.tourIdx);
    }
  }

  state.controls.update();
}

/* ═══════════════════════════════════════════════════════════════
   §22  BRIDGE INTEGRATION — window.updateSimulation
   ═══════════════════════════════════════════════════════════════ */

function initBridge() {
  window.updateSimulation = function (jsonData) {
    if (state.disposed) return;
    let data;
    try {
      data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
    } catch (e) {
      console.error('SmartWarehouse bridge: invalid JSON', e);
      return;
    }

    const { step, robots: robotsData, tasks, parcels, metrics, paths, sensors, hazards, collisions, heatmap } = data;

    // Update HUD metrics
    if (step !== undefined) updateHUDMetric('dash-step', `Step: <strong>${step}</strong>`);
    if (metrics) {
      if (metrics.active_robots !== undefined) updateHUDMetric('dash-robots', `Robots: <strong>${metrics.active_robots}/${metrics.total_robots || metrics.active_robots}</strong>`);
      if (metrics.pending_tasks !== undefined) updateHUDMetric('dash-tasks', `Tasks: <strong>${metrics.pending_tasks} pending</strong>`);
      if (metrics.throughput !== undefined) updateHUDMetric('dash-throughput', `Throughput: <strong>${metrics.throughput.toFixed(1)}</strong>`);
      if (metrics.uptime !== undefined) updateHUDMetric('dash-uptime', `Uptime: <strong>${metrics.uptime}</strong>`);
    }

    // Create / update / remove robots
    if (robotsData) {
      const activeIds = new Set();
      for (const rd of robotsData) {
        activeIds.add(rd.id);
        let entry = state.robots.get(rd.id);
        if (!entry) {
          // Create new robot (TITAN-X, ATLAS, VORTEX, NOVA, or SPECTRE)
          const group = buildRobot(rd.id, rd);
          state.scene.add(group);
          entry = { group, data: { ...rd }, prevData: { ...rd }, lerpT: 1 };
          state.robots.set(rd.id, entry);
        }
        // Store previous for interpolation
        entry.prevData = { ...entry.data };
        entry.data = { ...rd };
        entry.lerpT = 0;
      }
      // Remove robots no longer present
      for (const [id, entry] of state.robots) {
        if (!activeIds.has(id)) {
          state.scene.remove(entry.group);
          disposeGroup(entry.group);
          state.robots.delete(id);
        }
      }
    }

    // Update path ribbons
    if (paths) updatePathRibbons(paths);

    // Update sensor markers
    if (sensors) updateSensorMarkers(sensors);

    // Update hazard zones
    if (hazards) updateHazardZones(hazards);

    // Update task beacons
    if (tasks) updateTaskBeacons(tasks);

    // Update dynamic inventory parcels across warehouse racks & docks
    if (parcels) updateParcels(parcels);

    // Update collision predictions
    if (collisions) {
      // Create pulsing amber rings at conflict cells
      const overlayGroup = state.groups.overlays;
      if (overlayGroup) {
        // Clear old collision markers (tagged)
        overlayGroup.children.filter(c => c.userData.collisionMarker).forEach(c => {
          overlayGroup.remove(c); disposeMesh(c);
        });
        for (const col of collisions) {
          const wp = gridToWorld(col.x, col.y);
          const ring = new THREE.Mesh(
            new THREE.TorusGeometry(1.0, 0.08, 8, 32),
            new THREE.MeshBasicMaterial({ color: COL_AMBER, transparent: true, opacity: 0.6 })
          );
          ring.rotation.x = -Math.PI / 2;
          ring.position.set(wp.x, 0.15, wp.z);
          ring.userData.collisionMarker = true;
          ring.userData.hazardPulse = true;
          overlayGroup.add(ring);
        }
      }
    }

    // Update KPI display
    if (metrics) {
      updateKPIDisplay(metrics);
    }
  };

  // Debug API
  window.__SW_DEBUG = {
    getRobots: () => {
      const result = {};
      state.robots.forEach((entry, id) => {
        result[id] = {
          position: { x: entry.group.position.x, y: entry.group.position.y, z: entry.group.position.z },
          state: entry.data.state,
          battery: entry.data.battery,
        };
      });
      return result;
    },
    getTheme: () => state.activeTheme,
    setTheme: (t) => setTheme(t),
    setCamPreset: (p) => setCamPresetSmooth(p),
  };
}

function updateKPIDisplay(metrics) {
  if (!state.kpiMesh) return;
  const newTex = makeKPITexture({
    throughput: `${(metrics.throughput || 0).toFixed(1)} units/hr`,
    utilization: `${(metrics.utilization || 84).toFixed(0)}%`,
    robots: `${metrics.active_robots || 0} active`,
    tasks: `${metrics.pending_tasks || 0} pending`,
    uptime: metrics.uptime || '00:00:00',
    alerts: `${metrics.alerts || 0}`,
  });
  if (state.kpiMesh.material.map) state.kpiMesh.material.map.dispose();
  state.kpiMesh.material.map = newTex;
  state.kpiMesh.material.needsUpdate = true;
}

/* ═══════════════════════════════════════════════════════════════
   §23  ROBOT UPDATE & INTERPOLATION
   ═══════════════════════════════════════════════════════════════ */

function updateRobots(dt) {
  for (const [id, entry] of state.robots) {
    const { group, data, prevData } = entry;

    // Client-side interpolation
    entry.lerpT = Math.min(entry.lerpT + dt * 4, 1); // Catch up over 0.25s
    const t = easeInOutCubic(entry.lerpT);

    // Position interpolation
    if (data.x !== undefined && data.y !== undefined) {
      const prevWP = gridToWorld(prevData.x !== undefined ? prevData.x : data.x, prevData.y !== undefined ? prevData.y : data.y);
      const curWP = gridToWorld(data.x, data.y);
      group.position.x = THREE.MathUtils.lerp(prevWP.x, curWP.x, t);
      group.position.z = THREE.MathUtils.lerp(prevWP.z, curWP.z, t);
    }

    // Heading interpolation
    if (data.heading !== undefined || data.yaw !== undefined) {
      const targetH = data.yaw !== undefined ? data.yaw : (data.heading || 0);
      const prevH = prevData.yaw !== undefined ? prevData.yaw : (prevData.heading || targetH);
      let dh = targetH - prevH;
      while (dh > Math.PI) dh -= 2 * Math.PI;
      while (dh < -Math.PI) dh += 2 * Math.PI;
      group.rotation.y = prevH + dh * t;
    }

    // State-driven underglow color
    const stateColor = STATE_COLORS[data.state] || STATE_COLORS.IDLE;
    const underglow = group.userData.underglow;
    if (underglow) {
      const nightMultiplier = state.activeTheme === 'nightops' ? 3.5 : 1.0;
      underglow.material.color.set(stateColor);
      underglow.material.opacity = 0.4 * nightMultiplier;

      // Emergency flash
      if (data.state === 'EMERGENCY') {
        underglow.material.opacity = Math.sin(state.animTime * 10) > 0 ? 0.8 : 0.1;
      }
    }

    // Cargo visibility
    if (group.userData.cargo) {
      group.userData.cargo.visible = (data.carrying === true) || Boolean(data.carrying_parcel_id);
    }

    // Movement detection for kinematics
    const dx = (data.x || 0) - (prevData.x || data.x || 0);
    const dy = (data.y || 0) - (prevData.y || data.y || 0);
    const hasVelocity = (data.speed > 0 || Math.hypot(dx, dy) > 0.01 || entry.lerpT < 0.95);
    const isMoving = hasVelocity && state.simRunning !== false && data.state !== 'PAUSED' && data.state !== 'EMERGENCY' && data.state !== 'IDLE';

    // ── AMR Specific Kinematics (TITAN-X) ──
    if (group.userData.modelType === 'HEAVY_AMR') {
      // 4 All-terrain wheels rotation
      if (group.userData.wheels) {
        for (const wGroup of group.userData.wheels) {
          const wheelMesh = wGroup.children[0];
          if (wheelMesh) wheelMesh.rotation.x += isMoving ? dt * 10.0 : 0.0;
        }
      }
      // Top LiDAR turret rotation
      if (group.userData.lidarDome) {
        group.userData.lidarDome.rotation.y += dt * 8.0;
      }
    }

    // ── Humanoid Articulated Kinematics (ATLAS, VORTEX, NOVA, SPECTRE) ──
    if (group.userData.isHumanoid) {
      entry.walkPhase = (entry.walkPhase || 0) + (isMoving ? dt * 7.5 : dt * 1.2);

      // Thighs (hips)
      if (group.userData.leftLeg) group.userData.leftLeg.rotation.x = Math.sin(entry.walkPhase) * (isMoving ? 0.52 : 0.04);
      if (group.userData.rightLeg) group.userData.rightLeg.rotation.x = -Math.sin(entry.walkPhase) * (isMoving ? 0.52 : 0.04);

      // Knees (calves)
      if (group.userData.leftCalf) group.userData.leftCalf.rotation.x = -Math.max(0, -Math.sin(entry.walkPhase)) * (isMoving ? 0.78 : 0.02);
      if (group.userData.rightCalf) group.userData.rightCalf.rotation.x = -Math.max(0, Math.sin(entry.walkPhase)) * (isMoving ? 0.78 : 0.02);

      // Arms (shoulders)
      if (group.userData.leftArm) group.userData.leftArm.rotation.x = -Math.sin(entry.walkPhase) * (isMoving ? 0.42 : 0.08);
      if (group.userData.rightArm) {
        if (group.userData.scannerCone && (data.state === 'INSPECTING' || (!isMoving && Math.sin(state.animTime * 2) > 0.1))) {
          // NOVA optical inspection scanning pose
          group.userData.rightArm.rotation.x = -0.85 + Math.sin(state.animTime * 4) * 0.15;
          group.userData.scannerCone.visible = true;
        } else {
          group.userData.rightArm.rotation.x = Math.sin(entry.walkPhase) * (isMoving ? 0.42 : 0.08);
          if (group.userData.scannerCone) group.userData.scannerCone.visible = false;
        }
      }

      // Torso bobbing & walking rhythm
      if (group.userData.torso) {
        group.userData.torso.position.y = 0.88 + Math.abs(Math.sin(entry.walkPhase * 2)) * (isMoving ? 0.035 : 0.005);
        group.userData.torso.rotation.y = Math.sin(entry.walkPhase) * (isMoving ? 0.06 : 0.02);
      }

      // Head tracking
      if (group.userData.head) {
        group.userData.head.rotation.y = Math.sin(state.animTime * 1.5 + Number(id)) * 0.12;
      }
    }

    // Headlight pulsing
    group.traverse(child => {
      if (child.userData && child.userData.headlightRing && child.material) {
        child.material.emissiveIntensity = 0.5 + 0.3 * Math.sin(state.animTime * 3);
      }
    });
  }
}

/* ═══════════════════════════════════════════════════════════════
   §24  HUD & INPUT MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */

function updateHUDMetric(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function initHUD() {
  // Theme buttons
  document.getElementById('btn-theme-real')?.addEventListener('click', () => setTheme('realistic'));
  document.getElementById('btn-theme-night')?.addEventListener('click', () => setTheme('nightops'));
  document.getElementById('btn-theme-twin')?.addEventListener('click', () => setTheme('wireframe'));

  // Camera presets
  document.getElementById('btn-iso')?.addEventListener('click', () => setCamPresetSmooth('ISO'));
  document.getElementById('btn-top')?.addEventListener('click', () => setCamPresetSmooth('TOP'));
  document.getElementById('btn-aisle')?.addEventListener('click', () => setCamPresetSmooth('AISLE'));
  document.getElementById('btn-dock')?.addEventListener('click', () => setCamPresetSmooth('DOCK'));
  document.getElementById('btn-cinematic')?.addEventListener('click', () => setCamPresetSmooth('CINEMATIC'));

  // Special modes
  document.getElementById('btn-hero')?.addEventListener('click', startHeroCamera);
  document.getElementById('btn-walk')?.addEventListener('click', startWalkMode);
  document.getElementById('btn-tour')?.addEventListener('click', startTour);

  // Simulation controls
  document.getElementById('btn-play')?.addEventListener('click', () => {
    state.simRunning = true;
    document.getElementById('btn-play')?.classList.add('active');
    document.getElementById('btn-pause')?.classList.remove('active');
  });
  document.getElementById('btn-pause')?.addEventListener('click', () => {
    state.simRunning = false;
    document.getElementById('btn-pause')?.classList.add('active');
    document.getElementById('btn-play')?.classList.remove('active');
  });
  document.getElementById('btn-step')?.addEventListener('click', () => {
    state.simRunning = false;
    document.getElementById('btn-pause')?.classList.add('active');
    document.getElementById('btn-play')?.classList.remove('active');
    window.parent?.postMessage({ type: 'STEP_SIMULATION' }, '*');
  });
  document.getElementById('btn-reset')?.addEventListener('click', resetCamera);

  // Control Dock Collapse / Expand Toggle
  const toggleDock = () => {
    if (window.innerWidth <= 850) {
      document.body.classList.toggle('dock-expanded-mobile');
      const isOpen = document.body.classList.contains('dock-expanded-mobile');
      const btn = document.getElementById('btn-toggle-dock');
      if (btn) btn.innerHTML = isOpen ? '◀ Hide Controls' : '⚙️ Controls';
    } else {
      document.body.classList.toggle('dock-collapsed');
      const isCollapsed = document.body.classList.contains('dock-collapsed');
      const btn = document.getElementById('btn-toggle-dock');
      if (btn) btn.innerHTML = isCollapsed ? '▶ Show Controls' : '◀ Collapse Controls';
    }
    setTimeout(onResize, 40);
    setTimeout(onResize, 260);
  };
  document.getElementById('btn-toggle-dock')?.addEventListener('click', toggleDock);
  document.getElementById('btn-toggle-dock-float')?.addEventListener('click', toggleDock);

  // Speed slider
  const speedSlider = document.getElementById('speed-slider');
  const speedLabel = document.getElementById('speed-label');
  if (speedSlider) {
    speedSlider.addEventListener('input', () => {
      state.simSpeed = parseFloat(speedSlider.value);
      if (speedLabel) speedLabel.textContent = `${state.simSpeed.toFixed(1)}×`;
    });
  }

  // Toggle checkboxes
  document.getElementById('toggle-paths')?.addEventListener('change', (e) => {
    state.showPaths = e.target.checked;
    state.overlays.paths.forEach(p => p.visible = state.showPaths);
  });
  document.getElementById('toggle-racks')?.addEventListener('change', (e) => {
    state.showRacks = e.target.checked;
    if (state.groups.racking) state.groups.racking.visible = state.showRacks;
    if (state.groups.inventory) state.groups.inventory.visible = state.showRacks;
  });
  document.getElementById('toggle-sensors')?.addEventListener('change', (e) => {
    state.showSensors = e.target.checked;
    state.overlays.sensors.forEach(s => s.visible = state.showSensors);
  });
  document.getElementById('toggle-hazards')?.addEventListener('change', (e) => {
    state.showHazards = e.target.checked;
    state.overlays.hazards.forEach(h => h.visible = state.showHazards);
  });
  document.getElementById('toggle-labels')?.addEventListener('change', (e) => {
    state.showLabels = e.target.checked;
    if (state.groups.signage) state.groups.signage.visible = state.showLabels;
  });
  document.getElementById('toggle-scenery')?.addEventListener('change', (e) => {
    state.showScenery = e.target.checked;
    if (state.groups.decor) state.groups.decor.visible = state.showScenery;
  });

  // Quality select
  const qualitySelect = document.getElementById('quality-select');
  if (qualitySelect) {
    qualitySelect.addEventListener('change', () => {
      setQuality(qualitySelect.value);
    });
  }

  // ── Fleet Command Actions (Start All, Pause All, Resume All, E-Stop) ──
  document.getElementById('btn-fleet-start')?.addEventListener('click', () => {
    state.simRunning = true;
    for (const [id, entry] of state.robots) {
      if (entry.data.state === 'PAUSED' || entry.data.state === 'IDLE') {
        entry.data.state = 'MOVING';
      }
    }
    document.getElementById('btn-play')?.classList.add('active');
    document.getElementById('btn-pause')?.classList.remove('active');
    window.parent?.postMessage({ type: 'START_FLEET' }, '*');
  });

  document.getElementById('btn-fleet-pause')?.addEventListener('click', () => {
    state.simRunning = false;
    for (const [id, entry] of state.robots) {
      entry.data.state = 'PAUSED';
    }
    document.getElementById('btn-pause')?.classList.add('active');
    document.getElementById('btn-play')?.classList.remove('active');
    window.parent?.postMessage({ type: 'PAUSE_FLEET' }, '*');
  });

  document.getElementById('btn-fleet-resume')?.addEventListener('click', () => {
    state.simRunning = true;
    for (const [id, entry] of state.robots) {
      if (entry.data.state === 'PAUSED') entry.data.state = 'MOVING';
    }
    document.getElementById('btn-play')?.classList.add('active');
    document.getElementById('btn-pause')?.classList.remove('active');
    window.parent?.postMessage({ type: 'RESUME_FLEET' }, '*');
  });

  document.getElementById('btn-fleet-estop')?.addEventListener('click', () => {
    state.simRunning = false;
    for (const [id, entry] of state.robots) {
      entry.data.state = 'EMERGENCY';
    }
    document.getElementById('btn-pause')?.classList.add('active');
    document.getElementById('btn-play')?.classList.remove('active');
    window.parent?.postMessage({ type: 'EMERGENCY_STOP' }, '*');
  });

  // Individual robot quick selector buttons in dock
  document.querySelectorAll('.robot-select-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const botId = Number(btn.dataset.bot);
      selectRobot(botId);
      const entry = state.robots.get(botId);
      if (entry) {
        state.controls.target.set(entry.group.position.x, 1.0, entry.group.position.z);
      }
    });
  });

  // Selected Robot Actions in Inspector Panel
  document.getElementById('btn-bot-assign')?.addEventListener('click', () => {
    if (state.selectedRobot === null) return;
    const taskSelect = document.getElementById('bot-task-select');
    const taskCode = taskSelect ? taskSelect.value : 'A1_PICK';
    const entry = state.robots.get(state.selectedRobot);
    if (!entry) return;

    const WAYPOINTS = {
      'A1_PICK': { x: 2, y: 4, name: 'Pick Pallet A1', state: 'PICKING' },
      'DOCK_DELIVER': { x: 2, y: 14, name: 'Deliver to Loading Bay', state: 'DELIVERING' },
      'SORT_STATION': { x: 6, y: 14, name: 'Sort Packages Station', state: 'MOVING' },
      'RACK_INSPECT': { x: 6, y: 4, name: 'Inspect Rack B2', state: 'INSPECTING' },
      'PATROL_SAFETY': { x: 10, y: 8, name: 'Patrol Safety Zone', state: 'MOVING' },
      'CHARGE_RETURN': { x: (state.selectedRobot - 1) * 3 + 1, y: 0, name: 'Return to Charger', state: 'CHARGING' },
    };

    const wp = WAYPOINTS[taskCode] || WAYPOINTS['A1_PICK'];
    entry.prevData = { ...entry.data };
    entry.data.x = wp.x;
    entry.data.y = wp.y;
    entry.data.state = wp.state;
    entry.data.current_task = wp.name;
    entry.data.task_id = wp.name;
    entry.lerpT = 0;
    updateRobotPanel(entry.data);
    window.parent?.postMessage({ type: 'ASSIGN_ROBOT_TASK', robot_id: state.selectedRobot, task: wp.name, target: [wp.x, wp.y] }, '*');
  });

  document.getElementById('btn-bot-reset')?.addEventListener('click', () => {
    if (state.selectedRobot === null) return;
    const entry = state.robots.get(state.selectedRobot);
    if (!entry) return;
    const homeX = (state.selectedRobot - 1) * 3 + 1;
    const homeY = 0;
    entry.prevData = { ...entry.data };
    entry.data.x = homeX;
    entry.data.y = homeY;
    entry.data.state = 'IDLE';
    entry.data.current_task = 'Docked / Standby';
    entry.lerpT = 0;
    updateRobotPanel(entry.data);
  });

  document.getElementById('btn-bot-start')?.addEventListener('click', () => {
    if (state.selectedRobot === null) return;
    const entry = state.robots.get(state.selectedRobot);
    if (!entry) return;
    entry.data.state = 'MOVING';
    updateRobotPanel(entry.data);
  });

  document.getElementById('btn-bot-pause')?.addEventListener('click', () => {
    if (state.selectedRobot === null) return;
    const entry = state.robots.get(state.selectedRobot);
    if (!entry) return;
    entry.data.state = 'PAUSED';
    updateRobotPanel(entry.data);
  });

  document.getElementById('btn-bot-resume')?.addEventListener('click', () => {
    if (state.selectedRobot === null) return;
    const entry = state.robots.get(state.selectedRobot);
    if (!entry) return;
    entry.data.state = 'MOVING';
    updateRobotPanel(entry.data);
  });

  document.getElementById('btn-bot-stop')?.addEventListener('click', () => {
    if (state.selectedRobot === null) return;
    const entry = state.robots.get(state.selectedRobot);
    if (!entry) return;
    entry.data.state = 'IDLE';
    entry.data.path = [];
    updateRobotPanel(entry.data);
  });

  // Robot panel actions & close
  document.getElementById('panel-close-btn')?.addEventListener('click', () => {
    const p = document.getElementById('robot-panel');
    if (p) p.style.display = 'none';
    state.selectedRobot = null;
  });
  document.getElementById('panel-follow-btn')?.addEventListener('click', () => {
    if (state.selectedRobot !== null) {
      startFollowCamera(state.selectedRobot);
    }
  });
  document.getElementById('panel-closeup-btn')?.addEventListener('click', () => {
    if (state.selectedRobot !== null) {
      const rob = state.robots.get(state.selectedRobot);
      if (rob) {
        setCamPresetSmooth('HERO');
      }
    }
  });

  // Keyboard input
  window.addEventListener('keydown', (e) => {
    state.keysDown.add(e.code);
    if (e.code === 'KeyC') {
      toggleDock();
    }
    if (e.code === 'Escape') {
      state.followRobot = null;
      state.walkMode = false;
      state.tourActive = false;
      document.getElementById('btn-walk')?.classList.remove('active');
      document.getElementById('btn-tour')?.classList.remove('active');
    }
  });
  window.addEventListener('keyup', (e) => state.keysDown.delete(e.code));

  // Robot selection via raycasting
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  const container = document.getElementById('canvas-container');
  if (container) {
    container.addEventListener('click', (event) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, state.camera);

      // Check all robot meshes
      const robotMeshes = [];
      state.robots.forEach(entry => {
        entry.group.traverse(child => {
          if (child.isMesh) robotMeshes.push(child);
        });
      });

      const intersects = raycaster.intersectObjects(robotMeshes, false);
      if (intersects.length > 0) {
        // Find parent AMR group
        let obj = intersects[0].object;
        while (obj && !obj.userData.isAMR) obj = obj.parent;
        if (obj && obj.userData.isAMR) {
          selectRobot(obj.userData.id);
        }
      }
    });
  }
}

const FLEET_INFO = {
  1: { name: '01 TITAN-X', type: 'Heavy-Duty AMR Vehicle', color: '#00f0ff' },
  2: { name: '02 ATLAS', type: 'Advanced Humanoid Logistics', color: '#2563eb' },
  3: { name: '03 VORTEX', type: 'Industrial Humanoid Sorter', color: '#ff6b00' },
  4: { name: '04 NOVA', type: 'Intelligent Inspection Humanoid', color: '#10b981' },
  5: { name: '05 SPECTRE', type: 'Autonomous Humanoid Assistant', color: '#06b6d4' },
};

function selectRobot(robotId) {
  state.selectedRobot = Number(robotId);
  const entry = state.robots.get(state.selectedRobot);
  if (!entry) return;

  const panel = document.getElementById('robot-panel');
  if (panel) panel.style.display = 'block';

  // Highlight active selector in dock
  document.querySelectorAll('.robot-select-btn').forEach(btn => {
    btn.classList.toggle('active', Number(btn.dataset.bot) === state.selectedRobot);
  });

  updateRobotPanel(entry.data);
}

function updateRobotPanel(data) {
  const rid = Number(data.id);
  const info = FLEET_INFO[rid] || { name: `ROBOT-${rid}`, type: 'Autonomous Agent', color: '#00f0ff' };

  const pid = document.getElementById('panel-id');
  const pstate = document.getElementById('panel-state');
  const pbatt = document.getElementById('panel-battery');
  const pbattBar = document.getElementById('panel-battery-bar');
  const ppos = document.getElementById('panel-pos');
  const ptask = document.getElementById('panel-task');
  const ptasks = document.getElementById('panel-tasks');
  const preplan = document.getElementById('panel-replan');

  if (pid) {
    pid.innerHTML = `<span style="color:${info.color};font-weight:700">${info.name}</span> <span style="font-size:10px;color:#94a3b8">(${info.type})</span>`;
  }
  if (pstate) {
    pstate.innerHTML = `<span class="badge" style="background:${STATE_COLORS[data.state] || info.color};color:#020617;font-weight:700;padding:2px 6px;border-radius:4px">${data.state || 'IDLE'}</span>`;
  }
  if (pbatt) {
    const batt = (data.battery !== undefined ? data.battery : 100).toFixed(1);
    pbatt.innerHTML = `<strong>${batt}%</strong>`;
  }
  if (pbattBar) {
    pbattBar.style.width = `${Math.max(0, Math.min(100, data.battery !== undefined ? data.battery : 100))}%`;
  }
  if (ppos) {
    ppos.innerHTML = `(${data.x !== undefined ? data.x : 0}, ${data.y !== undefined ? data.y : 0})`;
  }
  if (ptask) {
    ptask.innerHTML = `<strong>${data.task_id || data.current_task || 'Patrol & Ready'}</strong>`;
  }
  if (ptasks) {
    ptasks.innerHTML = `<strong>${data.tasks_done !== undefined ? data.tasks_done : (data.tasks_completed || 0)}</strong>`;
  }
  if (preplan) {
    preplan.innerHTML = `<strong>${data.replan_count || 0}</strong>`;
  }
}

/* ═══════════════════════════════════════════════════════════════
   §25  QUALITY TIERS
   ═══════════════════════════════════════════════════════════════ */

function setQuality(tier) {
  state.quality = tier;
  const renderer = state.renderer;

  if (tier === 'low') {
    renderer.shadowMap.enabled = false;
    renderer.setPixelRatio(1);
    state.keySun.castShadow = false;
  } else if (tier === 'med') {
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.BasicShadowMap;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    state.keySun.castShadow = true;
    state.keySun.shadow.mapSize.set(1024, 1024);
  } else {
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    state.keySun.castShadow = true;
    state.keySun.shadow.mapSize.set(2048, 2048);
  }
  renderer.shadowMap.needsUpdate = true;
}

function autoQualityCheck(fps) {
  if (fps < 25) {
    state.lowFpsCount++;
    if (state.lowFpsCount > 120) { // ~2 seconds of low fps
      if (state.quality === 'high') {
        setQuality('med');
        const qs = document.getElementById('quality-select');
        if (qs) qs.value = 'med';
      } else if (state.quality === 'med') {
        setQuality('low');
        const qs = document.getElementById('quality-select');
        if (qs) qs.value = 'low';
      }
      state.lowFpsCount = 0;
    }
  } else {
    state.lowFpsCount = Math.max(0, state.lowFpsCount - 1);
  }
}

/* ═══════════════════════════════════════════════════════════════
   §26  ANIMATION LOOP
   ═══════════════════════════════════════════════════════════════ */

function animate() {
  if (state.disposed) return;
  requestAnimationFrame(animate);

  const rawDt = state.clock.getDelta();
  const dt = Math.min(rawDt, 0.1) * state.simSpeed;
  state.animTime += dt;

  // FPS counter
  state.frameCount++;
  state.fpsAccum += rawDt;
  if (state.fpsAccum >= 0.5) {
    const fps = state.frameCount / state.fpsAccum;
    const fpsEl = document.getElementById('fps-counter');
    if (fpsEl) fpsEl.textContent = `${Math.round(fps)} FPS`;
    autoQualityCheck(fps);
    state.frameCount = 0;
    state.fpsAccum = 0;
  }

  if (state.simRunning) {
    // Update robots
    updateRobots(dt);

    // Animate robotic arms
    animateRoboticArms(dt);

    // Animate conveyors
    animateConveyors(dt);

    // Animate overlays
    animateOverlays(dt);

    // Animate charging rings
    animateChargingRings(dt);

    // Animate rack LEDs
    animateRackLEDs(dt);

    // Animate scanline (wireframe mode)
    if (state.activeTheme === 'wireframe' && state.scanlinePlane) {
      state.scanlinePlane.position.z = (state.animTime * 10) % TOTAL_D;
    }
  }

  // Update camera
  updateCamera(rawDt);

  // Update selected robot panel
  if (state.selectedRobot !== null) {
    const entry = state.robots.get(state.selectedRobot);
    if (entry) updateRobotPanel(entry.data);
  }

  // Render
  state.renderer.render(state.scene, state.camera);
}

function animateRoboticArms(dt) {
  const armGroup = state.groups.roboticArms;
  if (!armGroup) return;

  armGroup.children.forEach(child => {
    if (!child.userData.isRoboticArm) return;
    const phase = child.userData.animPhase || 0;
    const t = state.animTime + phase;

    // Pick/place cycle (smooth sinusoidal)
    const shoulderAngle = Math.sin(t * 0.8) * 0.4 - 0.3;
    const elbowAngle = Math.sin(t * 0.8 + 1) * 0.5 + 0.5;
    const wristAngle = Math.sin(t * 1.2) * 0.3;
    const gripOpen = Math.sin(t * 1.6) * 0.02 + 0.06;

    if (child.userData.shoulder) child.userData.shoulder.rotation.x = shoulderAngle;
    if (child.userData.elbow) child.userData.elbow.rotation.x = elbowAngle;
    if (child.userData.wrist) child.userData.wrist.rotation.z = wristAngle;
    if (child.userData.finger1) child.userData.finger1.position.x = -gripOpen;
    if (child.userData.finger2) child.userData.finger2.position.x = gripOpen;
  });
}

function animateConveyors(dt) {
  if (!state.conveyorActive) return;

  // Animate conveyor items
  const convGroup = state.groups.conveyors;
  if (convGroup) {
    convGroup.children.forEach(child => {
      if (child.userData.conveyorItem) {
        const dir = child.userData.dir;
        if (dir) {
          child.position.x += dir.x * child.userData.speed * dt;
          // Loop back
          if (child.position.x > child.userData.endX) {
            child.position.x = child.userData.startX;
          }
          child.matrixAutoUpdate = false;
          child.updateMatrix();
        }
      }
    });
  }

  // Rotate roller instances (via animation of rotation — visual only on the material or transform)
  // Since InstancedMesh can't rotate individually easily, we apply a subtle visual effect via the material
  if (state.rollerInstances && state.rollerInstances.material) {
    // Visual spinning effect isn't individually possible with InstancedMesh without updating matrices
    // We'll skip per-roller rotation for performance and rely on the tote movement for conveyor feel
  }
}

function animateOverlays(dt) {
  // Path ribbon chevron animation
  state.overlays.paths.forEach(tube => {
    if (tube.material && tube.material.map) {
      tube.userData.chevronOffset = (tube.userData.chevronOffset || 0) + dt * 0.5;
      tube.material.map.offset.x = tube.userData.chevronOffset;
    }
  });

  // Hazard zone pulsing
  state.overlays.hazards.forEach(hz => {
    if (hz.material) {
      hz.material.opacity = 0.3 + 0.3 * Math.sin(state.animTime * 4);
    }
  });

  // Task beacon pulsing
  state.overlays.taskBeacons.forEach(tb => {
    tb.position.y = 1.5 + 0.2 * Math.sin(state.animTime * 3);
    if (tb.material) {
      tb.material.opacity = 0.4 + 0.3 * Math.sin(state.animTime * 2);
    }
  });
}

function animateChargingRings(dt) {
  const chargeGroup = state.groups.charging;
  if (!chargeGroup) return;
  chargeGroup.traverse(child => {
    if (child.userData.chargingRing && child.material) {
      child.material.emissiveIntensity = 0.5 + 0.4 * Math.sin(state.animTime * 2.5);
      child.scale.setScalar(1.0 + 0.05 * Math.sin(state.animTime * 2.5));
    }
  });
}

function animateRackLEDs(dt) {
  const leds = state.groups.rackLEDs;
  if (!leds || !leds.material) return;
  leds.material.emissiveIntensity = 0.2 + 0.2 * Math.sin(state.animTime * 1.5);
}

/* ═══════════════════════════════════════════════════════════════
   §27  WINDOW RESIZE
   ═══════════════════════════════════════════════════════════════ */

function onResize() {
  const container = document.getElementById('canvas-container');
  if (!container || !state.renderer || !state.camera) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  state.camera.aspect = w / h;
  state.camera.updateProjectionMatrix();
  state.renderer.setSize(w, h);
}

/* ═══════════════════════════════════════════════════════════════
   §28  SCENE DISPOSAL
   ═══════════════════════════════════════════════════════════════ */

function dispose() {
  state.disposed = true;

  // Dispose all robots
  state.robots.forEach(entry => {
    state.scene.remove(entry.group);
    disposeGroup(entry.group);
  });
  state.robots.clear();

  // Dispose scene
  state.scene.traverse(child => {
    if (child.isMesh) disposeMesh(child);
    if (child.isLineSegments && child.geometry) child.geometry.dispose();
  });

  // Dispose renderer
  state.renderer.dispose();

  // Remove event listeners
  window.removeEventListener('resize', onResize);
}

/* ═══════════════════════════════════════════════════════════════
   §29  INITIALIZATION
   ═══════════════════════════════════════════════════════════════ */

async function init() {
  // Create renderer
  const container = document.getElementById('canvas-container');
  if (!container) { console.error('No canvas-container'); return; }

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);
  state.renderer = renderer;

  // Create scene
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(COL_DARK_BG);
  scene.fog = new THREE.FogExp2(COL_DARK_BG, 0.004);
  state.scene = scene;

  // Camera + controls
  const { camera, controls } = initCamera(renderer);
  state.camera = camera;
  state.controls = controls;

  // Initialize materials
  initMaterials();

  // ── Build scene in chunks ──
  buildFloor(scene);
  buildStructure(scene);
  buildLighting(scene);

  // Racking and inventory
  const rackPositions = buildRacking(scene);
  buildInventory(scene, rackPositions);

  // Equipment
  buildConveyors(scene);
  buildASRSCranes(scene);
  buildRoboticArms(scene);
  buildChargingStations(scene);

  // Mezzanine and infrastructure
  buildMezzanine(scene);
  buildSafetyInfra(scene);
  buildSignage(scene);
  buildKPIDisplay(scene);

  // Overlays
  buildOverlayGroup(scene);

  // Create default fleet of 5 distinct robots (TITAN-X, ATLAS, VORTEX, NOVA, SPECTRE)
  for (let i = 0; i < 5; i++) {
    const group = buildRobot(i + 1, { id: i + 1 });
    const pos = gridToWorld(CHARGING[i] ? CHARGING[i][0] : i * 3, CHARGING[i] ? CHARGING[i][1] : 0);
    group.position.set(pos.x, 0, pos.z);
    scene.add(group);
    state.robots.set(i + 1, {
      group,
      data: { id: i + 1, x: CHARGING[i] ? CHARGING[i][0] : i * 3, y: CHARGING[i] ? CHARGING[i][1] : 0, state: 'IDLE', battery: 100, carrying: false },
      prevData: { id: i + 1, x: CHARGING[i] ? CHARGING[i][0] : i * 3, y: CHARGING[i] ? CHARGING[i][1] : 0, state: 'IDLE', battery: 100 },
      lerpT: 1,
    });
  }

  // Apply default theme
  setTheme('realistic');
  setQuality('high');

  // HUD
  initHUD();

  // Bridge
  initBridge();

  // Resize handler
  window.addEventListener('resize', onResize);

  // Remove loader
  setTimeout(() => {
    const loader = document.getElementById('loader');
    if (loader) {
      loader.style.opacity = '0';
      setTimeout(() => loader.remove(), 600);
    }
  }, 500);

  // Start animation
  animate();
}

// ── Launch ──
init().catch(err => console.error('SmartWarehouse init failed:', err));
