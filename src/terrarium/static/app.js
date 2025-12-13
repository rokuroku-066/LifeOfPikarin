import * as THREE from 'https://unpkg.com/three@0.164.1/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.164.1/examples/jsm/controls/OrbitControls.js';
import { computeGroupHue } from './color.js';

const container = document.getElementById('view-container');
const tickSpan = document.getElementById('tick');
const populationSpan = document.getElementById('population');
const trackedSpan = document.getElementById('tracked');
const startBtn = document.getElementById('start');
const stopBtn = document.getElementById('stop');
const resetBtn = document.getElementById('reset');
const speedSlider = document.getElementById('speed');
const header = document.querySelector('header');

const worldSize = 100;
const halfWorld = worldSize / 2;

const leftSplitRatio = 0.55;
const rightRowSplit = 0.5;
document.documentElement.style.setProperty('--left-split', `${leftSplitRatio * 100}%`);
document.documentElement.style.setProperty('--right-row-split', `${rightRowSplit * 100}%`);

let socket = null;
let prevSnapshot = null;
let nextSnapshot = null;
let prevSnapshotTime = 0;
let nextSnapshotTime = 0;
const fallbackSnapshotInterval = 34;

let renderer = null;
let scene = null;
const cameras = { top: null, angle: null, pov: null };
let angleControls = null;
let viewports = null;
let layoutDirty = true;

let instancedAgents = null;
let agentGeometry = null;
const dummy = new THREE.Object3D();
const colorCache = new Map();
const tmpDir = new THREE.Vector3();
const tmpPos = new THREE.Vector3();
const tmpLook = new THREE.Vector3();

let trackedAgentId = null;
let lastTrackedYaw = 0;

function updateLayoutMetrics() {
  if (!header) return;
  const { height } = header.getBoundingClientRect();
  document.documentElement.style.setProperty('--header-height', `${height}px`);
}

function measureContainer() {
  const { width, height } = container.getBoundingClientRect();
  return {
    width: Math.max(width, 1),
    height: Math.max(height, 1),
  };
}

function computeViewports() {
  const { width, height } = measureContainer();
  const leftWidth = Math.max(width * leftSplitRatio, 1);
  const rightWidth = Math.max(width - leftWidth, 1);
  const rightTopHeight = Math.max(height * rightRowSplit, 1);
  const rightBottomHeight = Math.max(height - rightTopHeight, 1);
  return {
    full: { width, height },
    topDown: { x: 0, y: 0, width: leftWidth, height },
    angle: { x: leftWidth, y: height - rightTopHeight, width: rightWidth, height: rightTopHeight },
    pov: { x: leftWidth, y: 0, width: rightWidth, height: rightBottomHeight },
  };
}

function initThree() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0a0a);

  updateLayoutMetrics();
  const { width, height } = measureContainer();

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(width, height);
  renderer.autoClear = false;
  renderer.setScissorTest(true);
  container.appendChild(renderer.domElement);

  cameras.top = new THREE.OrthographicCamera(-halfWorld, halfWorld, halfWorld, -halfWorld, 0.1, 2000);
  cameras.top.position.set(0, worldSize * 1.1, 0);
  cameras.top.up.set(0, 0, -1);
  cameras.top.lookAt(0, 0, 0);

  cameras.angle = new THREE.PerspectiveCamera(60, 1, 0.1, 2000);
  const edgeViewHeight = worldSize * 0.08;
  const edgeViewDepth = halfWorld + worldSize * 0.1;
  cameras.angle.position.set(0, edgeViewHeight, edgeViewDepth);
  cameras.angle.lookAt(0, 0, 0);

  cameras.pov = new THREE.PerspectiveCamera(70, 1, 0.05, 500);
  cameras.pov.position.set(0, 3, -halfWorld * 0.2);
  cameras.pov.lookAt(0, 0, 0);

  angleControls = new OrbitControls(cameras.angle, renderer.domElement);
  angleControls.enableRotate = true;
  angleControls.screenSpacePanning = true;
  angleControls.zoomSpeed = 1.1;
  angleControls.minPolarAngle = 0.35;
  angleControls.maxPolarAngle = Math.PI / 2.1;
  angleControls.target.set(0, 0, 0);
  angleControls.update();

  const grid = new THREE.GridHelper(worldSize, 10, 0x333333, 0x222222);
  scene.add(grid);

  const groundGeo = new THREE.PlaneGeometry(worldSize, worldSize);
  const groundMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.8 });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotateX(-Math.PI / 2);
  ground.receiveShadow = true;
  scene.add(ground);

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.35);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.9);
  directionalLight.position.set(worldSize, worldSize * 1.5, worldSize);
  directionalLight.castShadow = true;
  directionalLight.shadow.mapSize.width = 2048;
  directionalLight.shadow.mapSize.height = 2048;
  directionalLight.shadow.camera.near = 10;
  directionalLight.shadow.camera.far = worldSize * 4;
  directionalLight.shadow.camera.left = -worldSize;
  directionalLight.shadow.camera.right = worldSize;
  directionalLight.shadow.camera.top = worldSize;
  directionalLight.shadow.camera.bottom = -worldSize;
  scene.add(directionalLight);

  window.addEventListener('resize', () => {
    layoutDirty = true;
    updateLayoutMetrics();
  });

  requestAnimationFrame(animate);
}

function ensureLayout() {
  if (!renderer) return;
  if (!layoutDirty) return;
  viewports = computeViewports();
  renderer.setSize(viewports.full.width, viewports.full.height, false);
  setTopCameraProjection(viewports.topDown);
  setAngleCameraProjection(viewports.angle);
  layoutDirty = false;
}

function setTopCameraProjection(viewport) {
  if (!cameras.top) return;
  const aspect = viewport.width / viewport.height;
  const viewHeight = worldSize * 1.2;
  const viewWidth = viewHeight * aspect;
  cameras.top.left = -viewWidth / 2;
  cameras.top.right = viewWidth / 2;
  cameras.top.top = viewHeight / 2;
  cameras.top.bottom = -viewHeight / 2;
  cameras.top.updateProjectionMatrix();
}

function setAngleCameraProjection(viewport) {
  if (!cameras.angle) return;
  cameras.angle.aspect = viewport.width / viewport.height;
  cameras.angle.updateProjectionMatrix();
}

function setPovCameraProjection(viewport) {
  if (!cameras.pov) return;
  cameras.pov.aspect = viewport.width / viewport.height;
  cameras.pov.updateProjectionMatrix();
}

function animate() {
  requestAnimationFrame(animate);
  const now = performance.now();
  updateView(now);
  if (angleControls) {
    angleControls.update();
  }
}

function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
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
  socket.onclose = () => {
    setTimeout(connect, 1000);
  };
}

function sendControl(path, body) {
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

function ensureInstancedAgents(count) {
  if (instancedAgents && instancedAgents.count >= count) {
    instancedAgents.count = count;
    ensureInstanceColor(instancedAgents, count);
    return instancedAgents;
  }

  if (instancedAgents) {
    scene.remove(instancedAgents);
    instancedAgents.material.dispose();
    instancedAgents = null;
  }

  if (count === 0) {
    return null;
  }

  if (!agentGeometry) {
    agentGeometry = new THREE.BoxGeometry(0.8, 0.8, 0.8);
  }

  const material = new THREE.MeshStandardMaterial({ vertexColors: true, metalness: 0.1, roughness: 0.8 });
  instancedAgents = new THREE.InstancedMesh(agentGeometry, material, count);
  instancedAgents.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  instancedAgents.castShadow = true;
  scene.add(instancedAgents);
  ensureInstanceColor(instancedAgents, count);
  return instancedAgents;
}

function ensureInstanceColor(mesh, count) {
  const existing = mesh.instanceColor;
  if (existing && existing.count >= count) {
    mesh.geometry.setAttribute('color', existing);
    return existing;
  }

  const colorAttr = new THREE.InstancedBufferAttribute(new Float32Array(count * 3), 3);
  colorAttr.setUsage(THREE.DynamicDrawUsage);
  mesh.instanceColor = colorAttr;
  mesh.geometry.setAttribute('color', colorAttr);
  mesh.material.needsUpdate = true;
  return colorAttr;
}

function selectTrackedAgent(snapshot) {
  if (!snapshot || snapshot.agents.length === 0) {
    trackedAgentId = null;
    return null;
  }
  if (trackedAgentId) {
    const current = snapshot.agentsById.get(trackedAgentId);
    if (current) return current;
  }
  const idx = Math.floor(Math.random() * snapshot.agents.length);
  const choice = snapshot.agents[idx];
  trackedAgentId = choice?.id ?? null;
  return choice ?? null;
}

function updateTrackedUi(agent) {
  if (!trackedSpan) return;
  if (!agent) {
    trackedSpan.textContent = 'POV: --';
    return;
  }
  trackedSpan.textContent = `POV: #${agent.id}`;
}

function updateView(now) {
  if (!scene || !renderer) return;
  ensureLayout();

  if (!nextSnapshot) {
    renderViews(null);
    return;
  }

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

  const previousTrackedId = trackedAgentId;
  const trackedAgent = selectTrackedAgent(nextSnapshot);
  const trackedChanged = previousTrackedId !== trackedAgentId;
  if (trackedChanged && trackedAgent) {
    lastTrackedYaw = Math.atan2(trackedAgent.vx ?? 0, trackedAgent.vy ?? 0);
  }
  let trackedPose = null;

  const mesh = ensureInstancedAgents(nextSnapshot.agents.length);
  if (mesh) {
    mesh.count = nextSnapshot.agents.length;
    const colorAttr = ensureInstanceColor(mesh, mesh.count);
    const colors = colorAttr.array;

    for (let i = 0; i < nextSnapshot.agents.length; i += 1) {
      const agent = nextSnapshot.agents[i];
      const prevAgent = prevAgentsById?.get(agent.id) ?? agent;
      const x = THREE.MathUtils.lerp(prevAgent.x, agent.x, alpha) - halfWorld;
      const z = THREE.MathUtils.lerp(prevAgent.y, agent.y, alpha) - halfWorld;
      const vx = THREE.MathUtils.lerp(prevAgent.vx ?? 0, agent.vx ?? 0, alpha);
      const vy = THREE.MathUtils.lerp(prevAgent.vy ?? 0, agent.vy ?? 0, alpha);
      const yaw = Math.atan2(vx, vy);

      dummy.position.set(x, 0, z);
      dummy.rotation.set(0, yaw, 0);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);

      const color = groupColor(agent.group);
      const base = i * 3;
      colors[base] = color.r;
      colors[base + 1] = color.g;
      colors[base + 2] = color.b;

      if (trackedAgent && agent.id === trackedAgent.id) {
        const speed = Math.hypot(vx, vy);
        const stableYaw = speed > 0.0001 ? yaw : lastTrackedYaw;
        lastTrackedYaw = stableYaw;
        trackedPose = {
          x,
          z,
          yaw: stableYaw,
        };
      }
    }

    mesh.instanceMatrix.needsUpdate = true;
    mesh.instanceColor.needsUpdate = true;
  }

  updateTrackedUi(trackedAgent);
  renderViews(trackedPose);
}

function renderViews(trackedPose) {
  if (!renderer || !scene || !viewports) return;

  renderer.setScissorTest(true);
  renderer.autoClear = false;
  renderer.setViewport(0, 0, viewports.full.width, viewports.full.height);
  renderer.setScissor(0, 0, viewports.full.width, viewports.full.height);
  renderer.clear();

  const views = [
    { camera: cameras.top, viewport: viewports.topDown },
    { camera: cameras.angle, viewport: viewports.angle },
  ];

  setAngleCameraProjection(viewports.angle);

  if (trackedPose) {
    setPovCameraProjection(viewports.pov);
    updatePovCamera(trackedPose, viewports.pov);
    views.push({ camera: cameras.pov, viewport: viewports.pov });
  } else {
    setPovCameraProjection(viewports.pov);
    cameras.pov.position.set(0, worldSize * 0.35, worldSize * 0.25);
    cameras.pov.lookAt(0, 0, 0);
    views.push({ camera: cameras.pov, viewport: viewports.pov });
  }

  for (const view of views) {
    renderer.setViewport(view.viewport.x, view.viewport.y, view.viewport.width, view.viewport.height);
    renderer.setScissor(view.viewport.x, view.viewport.y, view.viewport.width, view.viewport.height);
    renderer.clearDepth();
    renderer.render(scene, view.camera);
  }

  renderer.setScissorTest(false);
}

function updatePovCamera(pose, viewport) {
  setPovCameraProjection(viewport);
  const dir = tmpDir.set(Math.sin(pose.yaw), 0, Math.cos(pose.yaw));
  const followDistance = 6;
  const eyeHeight = 1.8;
  const lookAhead = 3;

  const position = tmpPos.set(pose.x, 0.4, pose.z);
  position.addScaledVector(dir, -followDistance);
  position.y += eyeHeight;

  const lookTarget = tmpLook.set(pose.x, 0.6, pose.z).addScaledVector(dir, lookAhead);

  cameras.pov.position.copy(position);
  cameras.pov.up.set(0, 1, 0);
  cameras.pov.lookAt(lookTarget);
}

function groupColor(id) {
  const cached = colorCache.get(id);
  if (cached) return cached;
  const hue = computeGroupHue(id);
  const color = new THREE.Color();
  color.setHSL(hue / 360, 0.7, 0.6);
  colorCache.set(id, color);
  return color;
}

initThree();
connect();
