import * as THREE from 'https://unpkg.com/three@0.164.1/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.164.1/examples/jsm/controls/OrbitControls.js';
import { computeGroupHue } from './color.js';

const container = document.getElementById('view-container');
const tickSpan = document.getElementById('tick');
const populationSpan = document.getElementById('population');
const startBtn = document.getElementById('start');
const stopBtn = document.getElementById('stop');
const resetBtn = document.getElementById('reset');
const speedSlider = document.getElementById('speed');

const worldSize = 100;
const halfWorld = worldSize / 2;

let socket = null;
let prevSnapshot = null;
let nextSnapshot = null;
let prevSnapshotTime = 0;
let nextSnapshotTime = 0;
const fallbackSnapshotInterval = 100;
let renderer;
let scene;
let camera;
let controls;
let instancedAgents = null;
let agentGeometry = null;

function initThree() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0a0a);

  const { width, height } = container.getBoundingClientRect();
  const aspect = width / height;
  camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 2000);
  camera.position.set(worldSize, worldSize * 0.8, worldSize);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(width, height);
  renderer.shadowMap.enabled = true;
  container.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableRotate = true;
  controls.screenSpacePanning = true;
  controls.zoomSpeed = 1.2;
  controls.minPolarAngle = 0.4;
  controls.maxPolarAngle = Math.PI / 2.2;
  controls.target.set(0, 0, 0);
  controls.update();

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

  window.addEventListener('resize', handleResize);
  requestAnimationFrame(animate);
}

function handleResize() {
  if (!renderer || !camera) return;
  const { width, height } = container.getBoundingClientRect();
  const aspect = width / height;
  camera.aspect = aspect;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
}

function animate() {
  requestAnimationFrame(animate);
  const now = performance.now();
  updateView(now);
  if (controls) {
    controls.update();
  }
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  socket.onmessage = (event) => {
    const parsed = JSON.parse(event.data);
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
  return instancedAgents;
}

function updateView(now) {
  if (!nextSnapshot || !scene) return;

  const prevAgentsById = new Map();
  if (prevSnapshot) {
    for (const agent of prevSnapshot.agents) {
      prevAgentsById.set(agent.id, agent);
    }
  }

  const intervalMs = Math.max(nextSnapshotTime - prevSnapshotTime, fallbackSnapshotInterval);
  const alpha = THREE.MathUtils.clamp((now - prevSnapshotTime) / intervalMs, 0, 1);
  const interpTick = prevSnapshot
    ? THREE.MathUtils.lerp(prevSnapshot.tick, nextSnapshot.tick, alpha)
    : nextSnapshot.tick;
  const currentPopulation = nextSnapshot.metrics.population ?? nextSnapshot.agents.length;
  tickSpan.textContent = `tick: ${Math.round(interpTick)}`;
  populationSpan.textContent = `pop: ${currentPopulation}`;

  const mesh = ensureInstancedAgents(nextSnapshot.agents.length);
  if (!mesh) return;
  mesh.count = nextSnapshot.agents.length;

  const dummy = new THREE.Object3D();
  for (let i = 0; i < nextSnapshot.agents.length; i += 1) {
    const agent = nextSnapshot.agents[i];
    const prevAgent = prevAgentsById.get(agent.id) ?? agent;
    const x = THREE.MathUtils.lerp(prevAgent.x, agent.x, alpha) - halfWorld;
    const z = THREE.MathUtils.lerp(prevAgent.y, agent.y, alpha) - halfWorld;
    const vx = THREE.MathUtils.lerp(prevAgent.vx ?? 0, agent.vx ?? 0, alpha);
    const vy = THREE.MathUtils.lerp(prevAgent.vy ?? 0, agent.vy ?? 0, alpha);
    const yaw = Math.atan2(vx, vy || 0.0001);

    dummy.position.set(x, 0, z);
    dummy.rotation.set(0, yaw, 0);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
    mesh.setColorAt(i, groupColor(agent.group));
  }

  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) {
    mesh.instanceColor.needsUpdate = true;
  }
}

function groupColor(id) {
  const hue = computeGroupHue(id);
  return new THREE.Color(`hsl(${hue}, 70%, 60%)`);
}

initThree();
connect();
