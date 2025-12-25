import * as THREE from 'https://unpkg.com/three@0.164.1/build/three.module.js';
import { GLTFLoader } from 'https://unpkg.com/three@0.164.1/examples/jsm/loaders/GLTFLoader.js';
import {
  computeGroupHue,
  elderScaleMultiplier,
  energyToLightness,
  pulseLightnessOffset,
  reproductionDesire,
} from './color.js';

const container = document.getElementById('view-container');
const tickSpan = document.getElementById('tick');
const populationSpan = document.getElementById('population');
const startBtn = document.getElementById('start');
const stopBtn = document.getElementById('stop');
const resetBtn = document.getElementById('reset');
const speedSlider = document.getElementById('speed');
const header = document.querySelector('header');
const connectionBadge = document.getElementById('connection');

const worldSize = 100;
const halfWorld = worldSize / 2;
const wallHeight = worldSize * 0.45;
const maxInstances = 700;
const modelBaseScale = 1.0;
const modelYawOffset = 0.0;
const floorRepeat = 8;
const colorSaturation = 0.75;
const energyVisual = { floor: 0.2, ceiling: 0.9, mid: 10.0, spread: 6.0 };
const reproductionVisual = {
  threshold: 12.0,
  softCap: 20.0,
  adultAge: 20.0,
  pulseAmplitude: 0.12,
  scalePulseAmplitude: 0.06,
  frequencyHz: 1.6,
};
const ageVisual = {
  adultAge: 20.0,
  maxAge: 80.0,
  elderShrink: 0.18,
  oldJitterAge: 38.0,
  jitterAmplitude: 0.035,
  jitterFrequency: 0.85,
};

const assetBase = window.location.protocol === 'file:' ? 'assets' : '/static/assets';
const assetUrl = (name) => `${assetBase}/${name}`;

let socket = null;
let prevSnapshot = null;
let nextSnapshot = null;
let prevSnapshotTime = 0;
let nextSnapshotTime = 0;
const fallbackSnapshotInterval = 34;

let renderer = null;
let scene = null;
let camera = null;
let layoutDirty = true;

let instancedBody = null;
let instancedFace = null;
let instancingReady = false;

const dummy = new THREE.Object3D();
const tmpColor = new THREE.Color();

const targetFps = 45;
const minFrameInterval = 1000 / targetFps;
let lastRenderTime = 0;
let lastRenderMs = 0;
let pendingPixelRatio = null;
let resizeObserver = null;
let headerObserver = null;

function setConnectionStatus(state, label) {
  if (!connectionBadge) return;
  connectionBadge.textContent = label;
  connectionBadge.classList.remove('ok', 'warn', 'error');
  connectionBadge.classList.add(state);
}

function updateEnergyVisual(snapshot) {
  const avg = snapshot?.metrics?.average_energy;
  if (!Number.isFinite(avg) || avg <= 0) return;
  const targetMid = avg;
  energyVisual.mid = THREE.MathUtils.lerp(energyVisual.mid, targetMid, 0.12);
  const targetSpread = Math.max(4.0, targetMid * 0.65);
  energyVisual.spread = THREE.MathUtils.lerp(energyVisual.spread, targetSpread, 0.12);
  reproductionVisual.threshold = Math.max(6.0, energyVisual.mid * 0.9);
  reproductionVisual.softCap = Math.max(reproductionVisual.threshold + 2.0, energyVisual.mid * 1.6);
}

function lerpHeading(a, b, t) {
  const start = Number.isFinite(a) ? a : 0;
  const end = Number.isFinite(b) ? b : start;
  let delta = end - start;
  delta = ((delta + Math.PI) % (Math.PI * 2)) - Math.PI;
  return start + delta * THREE.MathUtils.clamp(t, 0, 1);
}

function agentPhase(agent) {
  const seed = Number.isFinite(agent?.appearance_seed) ? agent.appearance_seed : agent?.id ?? 0;
  return seed * 0.47;
}

function reproductionScalePulse(now, desire, phase) {
  const amp = (reproductionVisual.scalePulseAmplitude ?? 0.05) * THREE.MathUtils.clamp(desire, 0, 1);
  if (amp <= 0) return 0;
  const omega = (reproductionVisual.frequencyHz ?? 1.4) * 2 * Math.PI;
  return amp * Math.sin(omega * (now / 1000) + phase);
}

function computeScale(agent, now, baseSizeOverride, desire) {
  const baseSize = Number.isFinite(baseSizeOverride)
    ? baseSizeOverride
    : Number.isFinite(agent.size)
      ? agent.size
      : 0.8;
  const elderFactor = elderScaleMultiplier(agent.age, ageVisual);
  let scale = baseSize * elderFactor;
  const oldStart = ageVisual.oldJitterAge ?? ageVisual.maxAge * 0.8;
  if (Number.isFinite(agent.age) && agent.age >= oldStart) {
    const jitterAmp = ageVisual.jitterAmplitude ?? 0.03;
    const jitterFreq = ageVisual.jitterFrequency ?? 0.9;
    const phase = agentPhase(agent);
    const wobble = jitterAmp * Math.sin((now / 1000) * jitterFreq * 2 * Math.PI + phase);
    scale *= 1 + wobble;
  }
  const phase = agentPhase(agent);
  scale *= 1 + reproductionScalePulse(now, desire ?? 0, phase);
  return THREE.MathUtils.clamp(scale, 0.1, 2.0);
}

function computeColor(agent, now, desire) {
  const baseHue = computeGroupHue(agent.group);
  const lineageHue = Number.isFinite(agent?.lineage_id) ? agent.lineage_id : 0;
  const hue = (baseHue + (lineageHue % 12) * 0.8) % 360;
  const baseLightness = energyToLightness(agent.energy, energyVisual);
  const speedTrait = Number.isFinite(agent?.trait_speed) ? agent.trait_speed : 1;
  const speedFactor = THREE.MathUtils.clamp(speedTrait, 0.5, 1.5);
  const computedDesire = desire ?? reproductionDesire(agent.energy, agent.age, agent.behavior_state, {
    reproductionThreshold: reproductionVisual.threshold,
    energySoftCap: reproductionVisual.softCap,
    adultAge: reproductionVisual.adultAge,
  });
  const pulse = pulseLightnessOffset(now, computedDesire, {
    amplitude: reproductionVisual.pulseAmplitude,
    frequencyHz: reproductionVisual.frequencyHz,
    phase: agentPhase(agent),
  });
  const speedLightness = THREE.MathUtils.clamp((speedFactor - 1) * 0.12, -0.12, 0.12);
  const finalLightness = THREE.MathUtils.clamp(baseLightness + pulse + speedLightness, 0.12, 0.92);
  const traitSaturation = THREE.MathUtils.clamp(colorSaturation * (1 + (speedFactor - 1) * 0.4), 0.4, 1.0);
  tmpColor.setHSL(hue / 360, traitSaturation, finalLightness);
  return tmpColor;
}

function updateLayoutMetrics() {
  if (!header) return;
  const { height } = header.getBoundingClientRect();
  document.documentElement.style.setProperty('--header-height', `${height}px`);
}

function measureContainer() {
  const width = Math.max(container.clientWidth ?? 0, 1);
  const height = Math.max(container.clientHeight ?? 0, 1);
  return { width, height };
}

function initThree() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0a0a);

  updateLayoutMetrics();
  const { width, height } = measureContainer();

  renderer = new THREE.WebGLRenderer({ antialias: true });
  const pixelRatio = Math.min(window.devicePixelRatio ?? 1, 1.3);
  renderer.setPixelRatio(pixelRatio);
  renderer.setSize(width, height, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = false;
  container.appendChild(renderer.domElement);

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 2000);
  camera.position.set(halfWorld * 0.55, worldSize * 0.22, halfWorld * 0.65);
  camera.lookAt(0, 0, 0);

  initBackground();
  initLights();
  initPikarinInstancing();

  window.addEventListener('resize', () => {
    layoutDirty = true;
    updateLayoutMetrics();
  });
  watchResize();

  requestAnimationFrame(animate);
}

function initBackground() {
  const textureLoader = new THREE.TextureLoader();

  const groundTexture = textureLoader.load(assetUrl('ground.png'));
  groundTexture.colorSpace = THREE.SRGBColorSpace;
  groundTexture.wrapS = THREE.RepeatWrapping;
  groundTexture.wrapT = THREE.RepeatWrapping;
  groundTexture.repeat.set(floorRepeat, floorRepeat);

  const wallBackTexture = textureLoader.load(assetUrl('wall_back.png'));
  wallBackTexture.colorSpace = THREE.SRGBColorSpace;

  const wallSideTexture = textureLoader.load(assetUrl('wall_side.png'));
  wallSideTexture.colorSpace = THREE.SRGBColorSpace;

  const groundGeo = new THREE.PlaneGeometry(worldSize, worldSize);
  const groundMat = new THREE.MeshStandardMaterial({ map: groundTexture, roughness: 0.9 });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotateX(-Math.PI / 2);
  ground.position.y = 0;
  scene.add(ground);

  const wallGeo = new THREE.PlaneGeometry(worldSize, wallHeight);
  const backMat = new THREE.MeshStandardMaterial({ map: wallBackTexture, roughness: 0.9 });
  const backWall = new THREE.Mesh(wallGeo, backMat);
  backWall.position.set(0, wallHeight / 2, -halfWorld - 0.001);
  scene.add(backWall);

  const sideMat = new THREE.MeshStandardMaterial({ map: wallSideTexture, roughness: 0.9 });
  const sideWall = new THREE.Mesh(wallGeo, sideMat);
  sideWall.position.set(-halfWorld - 0.001, wallHeight / 2, 0);
  sideWall.rotation.y = -Math.PI / 2;
  scene.add(sideWall);
}

function initLights() {
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.35);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.9);
  directionalLight.position.set(worldSize, worldSize * 1.5, worldSize);
  directionalLight.castShadow = false;
  scene.add(directionalLight);
}

function initPikarinInstancing() {
  const loader = new GLTFLoader();
  loader.load(
    assetUrl('pikarin.glb'),
    (gltf) => {
      const meshes = [];
      gltf.scene.traverse((child) => {
        if (child.isMesh) meshes.push(child);
      });

      const bodyMesh = meshes.find((mesh) => /body/i.test(mesh.name)) ?? meshes[0] ?? null;
      const faceMesh = meshes.find((mesh) => /face/i.test(mesh.name)) ?? meshes[1] ?? null;

      if (!bodyMesh || !faceMesh) {
        console.warn('pikarin.glb missing body/face meshes; using fallback geometry.');
        initFallbackInstancing();
        return;
      }

      const bodyGeometry = bodyMesh.geometry.clone();
      const faceGeometry = faceMesh.geometry.clone();
      const bodyMaterial = normalizeMaterial(bodyMesh.material, { vertexColors: true });
      const faceMaterial = normalizeMaterial(faceMesh.material, {
        vertexColors: false,
        transparent: true,
        alphaTest: 0.5,
      });

      initInstancedMeshes(bodyGeometry, bodyMaterial, faceGeometry, faceMaterial);
    },
    undefined,
    (error) => {
      console.warn('Failed to load pikarin.glb, falling back to dummy geometry.', error);
      initFallbackInstancing();
    },
  );
}

function normalizeMaterial(material, { vertexColors, transparent = false, alphaTest = 0 } = {}) {
  let mat = material;
  if (Array.isArray(mat)) {
    mat = mat[0];
  }
  let normalized = mat ? mat.clone() : new THREE.MeshStandardMaterial({ color: 0xffffff });
  if (!(normalized instanceof THREE.MeshStandardMaterial)) {
    normalized = new THREE.MeshStandardMaterial({ color: normalized.color ?? new THREE.Color(0xffffff) });
  }
  normalized.vertexColors = vertexColors;
  normalized.transparent = transparent;
  normalized.alphaTest = alphaTest;
  if (normalized.map) {
    normalized.map.colorSpace = THREE.SRGBColorSpace;
    normalized.map.needsUpdate = true;
  }
  return normalized;
}

function initFallbackInstancing() {
  const bodyGeometry = new THREE.BoxGeometry(0.8, 0.8, 0.8);
  const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.8 });

  const faceGeometry = new THREE.PlaneGeometry(0.45, 0.45);
  faceGeometry.translate(0, 0.1, 0.41);
  const faceMaterial = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.6,
    transparent: true,
    opacity: 0.9,
  });

  initInstancedMeshes(bodyGeometry, bodyMaterial, faceGeometry, faceMaterial);
}

function initInstancedMeshes(bodyGeometry, bodyMaterial, faceGeometry, faceMaterial) {
  instancedBody?.geometry.dispose();
  instancedBody?.material.dispose();
  instancedFace?.geometry.dispose();
  instancedFace?.material.dispose();
  if (instancedBody) scene.remove(instancedBody);
  if (instancedFace) scene.remove(instancedFace);

  instancedBody = new THREE.InstancedMesh(bodyGeometry, bodyMaterial, maxInstances);
  instancedBody.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  instancedBody.castShadow = false;

  const colorAttr = new THREE.InstancedBufferAttribute(new Float32Array(maxInstances * 3), 3);
  colorAttr.setUsage(THREE.DynamicDrawUsage);
  instancedBody.instanceColor = colorAttr;
  instancedBody.geometry.setAttribute('color', colorAttr);

  instancedFace = new THREE.InstancedMesh(faceGeometry, faceMaterial, maxInstances);
  instancedFace.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  instancedFace.castShadow = false;

  scene.add(instancedBody);
  scene.add(instancedFace);
  instancingReady = true;
}

function ensureLayout() {
  if (!renderer || !camera) return;
  if (!layoutDirty) return;
  updateLayoutMetrics();
  const { width, height } = measureContainer();
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  layoutDirty = false;
}

function animate(now) {
  requestAnimationFrame(animate);
  const appliedPixelRatio = applyPendingPixelRatio();
  const shouldRender = appliedPixelRatio || now - lastRenderTime >= minFrameInterval;
  if (!shouldRender) {
    return;
  }
  lastRenderTime = now;
  const frameStart = performance.now();
  updateView(now);
  lastRenderMs = performance.now() - frameStart;
  adjustPixelRatioIfNeeded();
}

function watchResize() {
  if (typeof ResizeObserver !== 'undefined') {
    if (container) {
      resizeObserver?.disconnect();
      resizeObserver = new ResizeObserver(() => {
        layoutDirty = true;
      });
      resizeObserver.observe(container);
    }
    if (header) {
      headerObserver?.disconnect();
      headerObserver = new ResizeObserver(() => {
        updateLayoutMetrics();
        layoutDirty = true;
      });
      headerObserver.observe(header);
    }
  }
  if (window.matchMedia) {
    const dprQuery = `(resolution: ${window.devicePixelRatio}dppx)`;
    const mq = window.matchMedia(dprQuery);
    if (mq?.addEventListener) {
      mq.addEventListener('change', () => {
        const pixelRatio = Math.min(window.devicePixelRatio ?? 1, 1.3);
        requestPixelRatio(pixelRatio);
      });
    }
  }
}

function connect() {
  if (window.location.protocol === 'file:') {
    setConnectionStatus('warn', 'offline preview (no server)');
    return;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  socket.onopen = () => setConnectionStatus('ok', 'connected');
  socket.onmessage = (event) => {
    const parsed = JSON.parse(event.data);
    parsed.agentsById = new Map(parsed.agents.map((agent) => [agent.id, agent]));
    prevSnapshot = nextSnapshot;
    prevSnapshotTime = nextSnapshotTime;
    nextSnapshot = parsed;
    nextSnapshotTime = performance.now();
    if (!prevSnapshot) {
      prevSnapshot = nextSnapshot;
      prevSnapshotTime = nextSnapshotTime;
    }
  };
  socket.onerror = () => setConnectionStatus('error', 'connection error');
  socket.onclose = () => {
    setConnectionStatus('warn', 'disconnected, retrying…');
    setTimeout(connect, 1000);
  };
}

function sendControl(path, body) {
  if (window.location.protocol === 'file:') {
    setConnectionStatus('warn', 'offline preview (no server)');
    return;
  }
  fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : null,
  });
}

startBtn.addEventListener('click', () => sendControl('/api/control/start'));
stopBtn.addEventListener('click', () => sendControl('/api/control/stop'));
resetBtn.addEventListener('click', () => sendControl('/api/control/reset'));
speedSlider.addEventListener('input', () => {
  sendControl('/api/control/speed', { multiplier: parseFloat(speedSlider.value) });
});

function updateView(now) {
  if (!scene || !renderer || !camera) return;
  ensureLayout();

  if (!nextSnapshot) {
    renderer.render(scene, camera);
    return;
  }

  updateEnergyVisual(nextSnapshot);
  const prevAgentsById = prevSnapshot?.agentsById ?? null;
  const intervalMs = nextSnapshotTime > prevSnapshotTime
    ? nextSnapshotTime - prevSnapshotTime
    : fallbackSnapshotInterval;
  const alpha = THREE.MathUtils.clamp((now - prevSnapshotTime) / intervalMs, 0, 1);
  const interpTick = prevSnapshot
    ? THREE.MathUtils.lerp(prevSnapshot.tick, nextSnapshot.tick, alpha)
    : nextSnapshot.tick;
  const currentPopulation = nextSnapshot.metrics.population ?? nextSnapshot.agents.length;
  tickSpan.textContent = `tick: ${Math.round(interpTick)}`;
  populationSpan.textContent = `pop: ${currentPopulation}`;

  if (!instancingReady || !instancedBody || !instancedFace) {
    renderer.render(scene, camera);
    return;
  }

  const visibleCount = Math.min(nextSnapshot.agents.length, maxInstances);
  instancedBody.count = visibleCount;
  instancedFace.count = visibleCount;

  const colorAttr = instancedBody.instanceColor;
  const colors = colorAttr.array;

  for (let i = 0; i < visibleCount; i += 1) {
    const agent = nextSnapshot.agents[i];
    const prevAgent = prevAgentsById?.get(agent.id) ?? agent;
    const x = THREE.MathUtils.lerp(prevAgent.x, agent.x, alpha) - halfWorld;
    const z = THREE.MathUtils.lerp(prevAgent.y, agent.y, alpha) - halfWorld;
    const prevHeading = prevAgent.heading ?? Math.atan2(prevAgent.vx ?? 0, prevAgent.vy ?? 0);
    const nextHeading = agent.heading ?? Math.atan2(agent.vx ?? 0, agent.vy ?? 0);
    const yaw = lerpHeading(prevHeading, nextHeading, alpha) + modelYawOffset;
    const desire = reproductionDesire(agent.energy, agent.age, agent.behavior_state, {
      reproductionThreshold: reproductionVisual.threshold,
      energySoftCap: reproductionVisual.softCap,
      adultAge: reproductionVisual.adultAge,
    });
    const prevSize = Number.isFinite(prevAgent.size) ? prevAgent.size : agent.size ?? 0.8;
    const nextSize = Number.isFinite(agent.size) ? agent.size : prevSize;
    const blendedSize = THREE.MathUtils.lerp(prevSize, nextSize, alpha);
    const scale = computeScale(agent, now, blendedSize, desire) * modelBaseScale;

    dummy.position.set(x, 0, z);
    dummy.scale.set(scale, scale, scale);
    dummy.rotation.set(0, yaw, 0);
    dummy.updateMatrix();
    instancedBody.setMatrixAt(i, dummy.matrix);
    instancedFace.setMatrixAt(i, dummy.matrix);

    const color = computeColor(agent, now, desire);
    const base = i * 3;
    colors[base] = color.r;
    colors[base + 1] = color.g;
    colors[base + 2] = color.b;
  }

  instancedBody.instanceMatrix.needsUpdate = true;
  instancedFace.instanceMatrix.needsUpdate = true;
  instancedBody.instanceColor.needsUpdate = true;

  renderer.render(scene, camera);
}

function requestPixelRatio(next) {
  if (!renderer) return;
  const clamped = Math.min(1.3, Math.max(1.0, next));
  const current = renderer.getPixelRatio();
  if (Math.abs(clamped - current) < 1e-4 && pendingPixelRatio === null) return;
  pendingPixelRatio = clamped;
  layoutDirty = true;
}

function applyPendingPixelRatio() {
  if (pendingPixelRatio === null || !renderer) return false;
  ensureLayout();
  const { width, height } = measureContainer();
  renderer.setPixelRatio(pendingPixelRatio);
  renderer.setSize(width, height, false);
  pendingPixelRatio = null;
  return true;
}

function adjustPixelRatioIfNeeded() {
  if (!renderer) return;
  const current = renderer.getPixelRatio();
  const tooSlow = lastRenderMs > 24 && current > 1.0;
  const plentyFast = lastRenderMs < 12 && current < 1.25;
  if (tooSlow) {
    const next = Math.max(1.0, current - 0.1);
    requestPixelRatio(next);
  } else if (plentyFast) {
    const next = Math.min(1.3, current + 0.05);
    requestPixelRatio(next);
  }
}

initThree();
connect();
