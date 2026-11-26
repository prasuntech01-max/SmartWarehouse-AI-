/**
 * SmartWarehouse AI — Futuristic Robotics Lab & Alien-Inspired 3D Hero Robot
 * ═══════════════════════════════════════════════════════════════════════════
 * Interactive Three.js WebGL scene combining:
 *  - One highly detailed alien-inspired titanium/graphite humanoid Hero Robot
 *  - Futuristic glass research chambers & dark metallic lab architecture
 *  - Floating 3D warehouse digital-twin hologram above a control console
 *  - Receding holographic warehouse racks, glowing pathways & floating particles
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

function initLabBackdrop() {
  const container = document.getElementById('lab-canvas-wrap');
  if (!container) return;

  const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const w = container.clientWidth || 720;
  const h = container.clientHeight || 500;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
  } catch (err) {
    console.warn('Lab backdrop WebGL unavailable:', err);
    return;
  }

  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x050b16);
  scene.fog = new THREE.FogExp2(0x050b16, 0.036);

  const camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 120);
  camera.position.set(0.3, 2.35, 7.6);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0.2, 1.35, 0.0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.enablePan = false;
  controls.minDistance = 4.2;
  controls.maxDistance = 12.0;
  controls.maxPolarAngle = Math.PI / 2 - 0.05;
  controls.minPolarAngle = 0.25;
  controls.update();

  // ── Cinematic Lighting ──
  const hemi = new THREE.HemisphereLight(0x38bdf8, 0x050b16, 0.85);
  scene.add(hemi);

  const keyLight = new THREE.DirectionalLight(0xe0f2fe, 2.1);
  keyLight.position.set(4.5, 7.5, 5.5);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(1024, 1024);
  keyLight.shadow.camera.near = 1;
  keyLight.shadow.camera.far = 22;
  keyLight.shadow.camera.left = -6;
  keyLight.shadow.camera.right = 6;
  keyLight.shadow.camera.top = 6;
  keyLight.shadow.camera.bottom = -6;
  scene.add(keyLight);

  const rimCyan = new THREE.PointLight(0x00f0ff, 5.5, 14);
  rimCyan.position.set(2.4, 2.8, -1.8);
  scene.add(rimCyan);

  const rimViolet = new THREE.PointLight(0xa855f7, 3.8, 12);
  rimViolet.position.set(-3.2, 2.6, 1.2);
  scene.add(rimViolet);

  const holoLight = new THREE.PointLight(0x00e5ff, 3.2, 8);
  holoLight.position.set(-1.75, 1.65, 0.6);
  scene.add(holoLight);

  // ── Shared PBR Materials ──
  const matTitanium = new THREE.MeshStandardMaterial({ color: 0xdbe4ee, metalness: 0.84, roughness: 0.18 });
  const matSilver = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.88, roughness: 0.24 });
  const matGraphite = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.72, roughness: 0.36 });
  const matDarkWall = new THREE.MeshStandardMaterial({ color: 0x091120, metalness: 0.65, roughness: 0.42 });
  const matFloor = new THREE.MeshStandardMaterial({ color: 0x070e1c, metalness: 0.7, roughness: 0.22 });
  const matGlass = new THREE.MeshPhysicalMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.14,
    roughness: 0.08,
    metalness: 0.15,
    side: THREE.DoubleSide,
  });
  const matCyanGlow = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
  const matIceGlow = new THREE.MeshBasicMaterial({ color: 0x7dd3fc });
  const matVioletGlow = new THREE.MeshBasicMaterial({ color: 0xa855f7 });

  // ── 1. Reflective Lab Floor & Glowing Grid Pathways ──
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), matFloor);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  const grid = new THREE.GridHelper(32, 32, 0x00f0ff, 0x0c2747);
  grid.position.y = 0.01;
  grid.material.transparent = true;
  grid.material.opacity = 0.32;
  scene.add(grid);

  // Glowing floor energy pathways leading to Hero Robot & Holo Console
  const laneMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.55 });
  for (const lx of [-1.75, 0.0, 1.85]) {
    const lane = new THREE.Mesh(new THREE.PlaneGeometry(0.045, 16), laneMat);
    lane.rotation.x = -Math.PI / 2;
    lane.position.set(lx, 0.015, -2.5);
    scene.add(lane);
  }

  // ── 2. Glass Research Chambers & Lab Architecture ──
  const labGroup = new THREE.Group();
  scene.add(labGroup);

  // Rear glass partition separating the lab from the receding holographic warehouse
  for (const gx of [-3.6, -1.2, 1.2, 3.6]) {
    const pillar = new THREE.Mesh(new THREE.BoxGeometry(0.16, 4.4, 0.22), matGraphite);
    pillar.position.set(gx, 2.2, -3.2);
    labGroup.add(pillar);

    const strip = new THREE.Mesh(new THREE.BoxGeometry(0.03, 4.1, 0.04), matCyanGlow);
    strip.position.set(gx, 2.2, -3.08);
    labGroup.add(strip);
  }
  const glassWall = new THREE.Mesh(new THREE.PlaneGeometry(7.2, 4.2), matGlass);
  glassWall.position.set(0, 2.1, -3.2);
  labGroup.add(glassWall);

  // Side glass research chamber behind Hero Robot
  const chamberFrame = new THREE.Mesh(new THREE.CylinderGeometry(1.45, 1.45, 0.14, 36), matGraphite);
  chamberFrame.position.set(1.85, 0.07, 0.35);
  chamberFrame.receiveShadow = true;
  labGroup.add(chamberFrame);

  const chamberRing = new THREE.Mesh(
    new THREE.TorusGeometry(1.32, 0.025, 10, 48),
    matCyanGlow
  );
  chamberRing.rotation.x = Math.PI / 2;
  chamberRing.position.set(1.85, 0.15, 0.35);
  labGroup.add(chamberRing);

  const chamberRingViolet = new THREE.Mesh(
    new THREE.TorusGeometry(1.05, 0.016, 8, 40),
    matVioletGlow
  );
  chamberRingViolet.rotation.x = Math.PI / 2;
  chamberRingViolet.position.set(1.85, 0.16, 0.35);
  labGroup.add(chamberRingViolet);

  // Overhead lab light ribs
  for (const rz of [-2.4, 0.0, 2.4]) {
    const beam = new THREE.Mesh(new THREE.BoxGeometry(9.0, 0.12, 0.18), matDarkWall);
    beam.position.set(0, 4.35, rz);
    labGroup.add(beam);
    const led = new THREE.Mesh(new THREE.BoxGeometry(6.8, 0.03, 0.04), matIceGlow);
    led.position.set(0, 4.28, rz);
    labGroup.add(led);
  }

  // ── 3. Floating 3D Warehouse Digital-Twin Hologram & Control Console ──
  const consoleBase = new THREE.Mesh(new THREE.BoxGeometry(2.3, 0.88, 1.05), matGraphite);
  consoleBase.position.set(-1.75, 0.44, 0.55);
  consoleBase.castShadow = true;
  consoleBase.receiveShadow = true;
  scene.add(consoleBase);

  const consoleTop = new THREE.Mesh(new THREE.BoxGeometry(2.42, 0.06, 1.16), matSilver);
  consoleTop.position.set(-1.75, 0.9, 0.55);
  scene.add(consoleTop);

  const emitterPad = new THREE.Mesh(
    new THREE.RingGeometry(0.35, 0.52, 32),
    new THREE.MeshBasicMaterial({ color: 0x00f0ff, side: THREE.DoubleSide })
  );
  emitterPad.rotation.x = -Math.PI / 2;
  emitterPad.position.set(-1.75, 0.94, 0.55);
  scene.add(emitterPad);

  const holoTwin = new THREE.Group();
  holoTwin.position.set(-1.75, 1.65, 0.55);
  scene.add(holoTwin);

  // Translucent cyan holographic warehouse miniature
  const holoWireMat = new THREE.LineBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.72 });
  const holoFloorEdge = new THREE.EdgesGeometry(new THREE.BoxGeometry(1.75, 0.04, 1.15));
  holoTwin.add(new THREE.LineSegments(holoFloorEdge, holoWireMat));

  for (const rx of [-0.55, 0.0, 0.55]) {
    for (const rz of [-0.26, 0.26]) {
      const rackEdge = new THREE.EdgesGeometry(new THREE.BoxGeometry(0.24, 0.42, 0.34));
      const rack = new THREE.LineSegments(rackEdge, holoWireMat);
      rack.position.set(rx, 0.23, rz);
      holoTwin.add(rack);
    }
  }
  // Tiny glowing micro-AMRs inside hologram
  for (const [mx, mz] of [[-0.28, 0], [0.28, 0.12]]) {
    const mBot = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.05, 0.08), matIceGlow);
    mBot.position.set(mx, 0.05, mz);
    holoTwin.add(mBot);
  }

  // ── 4. Receding Holographic Warehouse Racks Behind the Glass ──
  const bgWireMat = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.22 });
  for (const bx of [-4.2, -2.2, 2.2, 4.2]) {
    for (const bz of [-5.2, -7.8, -10.4]) {
      const rEdge = new THREE.EdgesGeometry(new THREE.BoxGeometry(1.1, 3.6, 1.8));
      const rMesh = new THREE.LineSegments(rEdge, bgWireMat);
      rMesh.position.set(bx, 1.8, bz);
      scene.add(rMesh);
    }
  }

  // ── 5. THE HERO ALIEN-INSPIRED HUMANOID ROBOT (Prominent, PBR Metallic) ──
  const hero = new THREE.Group();
  hero.position.set(1.85, 0.14, 0.35);
  hero.rotation.y = -0.38;
  scene.add(hero);

  // Pelvis & waist mechanical core
  const pelvis = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.16, 0.22, 12), matGraphite);
  pelvis.position.y = 1.08;
  pelvis.castShadow = true;
  hero.add(pelvis);

  // Articulated legs
  for (const s of [-1, 1]) {
    const sx = s * 0.16;
    const hip = new THREE.Mesh(new THREE.SphereGeometry(0.09, 14, 14), matGraphite);
    hip.position.set(sx, 1.02, 0);
    hero.add(hip);

    const thigh = new THREE.Mesh(new THREE.CylinderGeometry(0.095, 0.075, 0.44, 14), matTitanium);
    thigh.position.set(sx, 0.78, 0);
    thigh.castShadow = true;
    hero.add(thigh);

    const thighCircuit = new THREE.Mesh(new THREE.BoxGeometry(0.018, 0.32, 0.025), matCyanGlow);
    thighCircuit.position.set(sx + s * 0.088, 0.78, 0.02);
    hero.add(thighCircuit);

    const knee = new THREE.Mesh(new THREE.CylinderGeometry(0.072, 0.072, 0.14, 14), matGraphite);
    knee.rotation.z = Math.PI / 2;
    knee.position.set(sx, 0.54, 0);
    hero.add(knee);

    const shin = new THREE.Mesh(new THREE.CylinderGeometry(0.076, 0.056, 0.46, 14), matSilver);
    shin.position.set(sx, 0.28, 0);
    shin.castShadow = true;
    hero.add(shin);

    const shinCircuit = new THREE.Mesh(new THREE.BoxGeometry(0.016, 0.32, 0.022), matVioletGlow);
    shinCircuit.position.set(sx + s * 0.07, 0.28, 0.02);
    hero.add(shinCircuit);

    const foot = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.08, 0.31), matGraphite);
    foot.position.set(sx, 0.04, 0.06);
    foot.castShadow = true;
    hero.add(foot);
  }

  // Torso (breathing + subtle rotation)
  const torso = new THREE.Group();
  torso.position.y = 1.22;
  hero.add(torso);

  const abdomen = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.13, 0.28, 14), matGraphite);
  abdomen.position.y = 0.08;
  torso.add(abdomen);

  // V-tapered titanium chest armor
  const chest = new THREE.Mesh(new THREE.CylinderGeometry(0.30, 0.19, 0.46, 10), matTitanium);
  chest.scale.set(1.0, 1.0, 0.68);
  chest.position.y = 0.38;
  chest.castShadow = true;
  torso.add(chest);

  // Powerful illuminated chest energy core
  const coreRing = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.018, 12, 28), matCyanGlow);
  coreRing.position.set(0, 0.40, 0.185);
  torso.add(coreRing);

  const coreCenter = new THREE.Mesh(new THREE.CircleGeometry(0.06, 20), matIceGlow);
  coreCenter.position.set(0, 0.40, 0.182);
  torso.add(coreCenter);

  const chestLight = new THREE.PointLight(0x00f0ff, 2.4, 3.5);
  chestLight.position.set(0, 0.40, 0.32);
  torso.add(chestLight);

  // Violet & cyan chest/shoulder circuits + layered arms & articulated hands
  const arms = [];
  for (const s of [-1, 1]) {
    const circuit = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.02, 0.02), matVioletGlow);
    circuit.position.set(s * 0.15, 0.50, 0.175);
    circuit.rotation.z = s * -0.28;
    torso.add(circuit);

    const pauldron = new THREE.Mesh(
      new THREE.SphereGeometry(0.13, 14, 12, 0, Math.PI * 2, 0, Math.PI * 0.6),
      matTitanium
    );
    pauldron.position.set(s * 0.34, 0.54, 0);
    pauldron.rotation.z = s * -0.35;
    pauldron.castShadow = true;
    torso.add(pauldron);

    const armGrp = new THREE.Group();
    armGrp.position.set(s * 0.35, 0.48, 0);
    torso.add(armGrp);
    arms.push({ grp: armGrp, side: s });

    armGrp.add(new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 12), matGraphite));

    const upperArm = new THREE.Mesh(new THREE.CylinderGeometry(0.062, 0.052, 0.32, 12), matSilver);
    upperArm.position.y = -0.18;
    upperArm.castShadow = true;
    armGrp.add(upperArm);

    const elbow = new THREE.Mesh(new THREE.SphereGeometry(0.058, 12, 12), matGraphite);
    elbow.position.y = -0.36;
    armGrp.add(elbow);

    const forearm = new THREE.Mesh(new THREE.CylinderGeometry(0.058, 0.044, 0.30, 12), matTitanium);
    forearm.position.set(0, -0.52, 0.04);
    forearm.rotation.x = -0.22;
    forearm.castShadow = true;
    armGrp.add(forearm);

    const armStrip = new THREE.Mesh(new THREE.BoxGeometry(0.016, 0.20, 0.02), matCyanGlow);
    armStrip.position.set(s * 0.054, -0.52, 0.05);
    armGrp.add(armStrip);

    // Articulated hand & 5 robotic fingers
    const palm = new THREE.Mesh(new THREE.BoxGeometry(0.072, 0.095, 0.042), matGraphite);
    palm.position.set(0, -0.70, 0.08);
    armGrp.add(palm);
    for (let f = -1.5; f <= 1.5; f += 0.75) {
      const finger = new THREE.Mesh(new THREE.BoxGeometry(0.013, 0.062, 0.016), matSilver);
      finger.position.set(f * 0.018, -0.77, 0.08);
      armGrp.add(finger);
    }
  }

  // Sculpted Alien-Inspired Head & Helmet
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.062, 0.085, 0.14, 14), matGraphite);
  neck.position.y = 0.66;
  torso.add(neck);

  const head = new THREE.Group();
  head.position.y = 0.82;
  torso.add(head);

  const cranium = new THREE.Mesh(new THREE.SphereGeometry(0.14, 20, 16), matTitanium);
  cranium.scale.set(0.86, 1.22, 1.08);
  cranium.castShadow = true;
  head.add(cranium);

  const visor = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.06, 0.04), matGraphite);
  visor.position.set(0, 0.015, 0.12);
  head.add(visor);

  const eyes = [];
  for (const es of [-1, 1]) {
    const eyeMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const eye = new THREE.Mesh(new THREE.BoxGeometry(0.048, 0.018, 0.02), eyeMat);
    eye.position.set(es * 0.046, 0.018, 0.142);
    eye.rotation.z = es * -0.16;
    head.add(eye);
    eyes.push(eyeMat);

    const earRing = new THREE.Mesh(new THREE.TorusGeometry(0.046, 0.011, 10, 24), matCyanGlow);
    earRing.rotation.y = Math.PI / 2;
    earRing.position.set(es * 0.122, 0.01, 0);
    head.add(earRing);
  }

  // ── 6. Floating Laboratory Particles ──
  const pCount = 85;
  const pPos = new Float32Array(pCount * 3);
  for (let i = 0; i < pCount; i++) {
    pPos[i * 3] = (Math.random() - 0.5) * 11;
    pPos[i * 3 + 1] = 0.2 + Math.random() * 4.0;
    pPos[i * 3 + 2] = -6 + Math.random() * 9;
  }
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
  const pMat = new THREE.PointsMaterial({ color: 0x38bdf8, size: 0.05, transparent: true, opacity: 0.65 });
  const particles = new THREE.Points(pGeo, pMat);
  scene.add(particles);

  // ── Resize & Animation Loop ──
  const onResize = () => {
    const nw = container.clientWidth || 720;
    const nh = container.clientHeight || 500;
    camera.aspect = nw / nh;
    camera.updateProjectionMatrix();
    renderer.setSize(nw, nh);
  };
  window.addEventListener('resize', onResize);

  let rafId = null;
  const clock = new THREE.Clock();

  function animate() {
    rafId = requestAnimationFrame(animate);
    const t = clock.getElapsedTime();

    if (!reducedMotion) {
      // Hero Robot natural mechanical idle animation
      torso.position.y = 1.22 + Math.sin(t * 1.4) * 0.014;
      torso.rotation.y = Math.sin(t * 0.45) * 0.06;
      head.rotation.y = Math.sin(t * 0.55) * 0.26;
      head.rotation.x = Math.sin(t * 0.85) * 0.045;

      for (const a of arms) {
        a.grp.rotation.x = Math.sin(t * 0.9 + a.side) * 0.06;
        a.grp.rotation.z = a.side * (0.07 + Math.sin(t * 0.7) * 0.02);
      }

      const pulse = 0.75 + 0.25 * Math.sin(t * 2.8);
      chestLight.intensity = 1.8 + 0.9 * Math.sin(t * 2.8);
      coreRing.scale.setScalar(0.96 + 0.05 * Math.sin(t * 2.8));
      for (const em of eyes) em.color.setRGB(0, 0.75 + 0.25 * pulse, 1.0);

      // Floating warehouse digital-twin hologram rotation & hover
      holoTwin.rotation.y = t * 0.28;
      holoTwin.position.y = 1.65 + Math.sin(t * 1.5) * 0.06;

      // Subtle chamber ring rotation & particle drift
      chamberRing.rotation.z = t * 0.25;
      particles.rotation.y = t * 0.03;
    }

    controls.update();
    renderer.render(scene, camera);
  }

  animate();

  window.addEventListener('pagehide', () => {
    if (rafId !== null) cancelAnimationFrame(rafId);
    window.removeEventListener('resize', onResize);
    controls.dispose();
    renderer.dispose();
  });
}

initLabBackdrop();
