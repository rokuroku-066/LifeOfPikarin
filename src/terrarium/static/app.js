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
let lastSnapshot = null;
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
  const viewHeight = worldSize;
  const viewWidth = viewHeight * aspect;
  camera = new THREE.OrthographicCamera(
    -viewWidth / 2,
    viewWidth / 2,
    viewHeight / 2,
    -viewHeight / 2,
    0.1,
    1000
  );
  camera.position.set(0, 0, worldSize * 1.5);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(width, height);
  container.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableRotate = false;
  controls.screenSpacePanning = true;
  controls.zoomSpeed = 1.2;
  controls.target.set(0, 0, 0);
  controls.update();

  const grid = new THREE.GridHelper(worldSize, 10, 0x333333, 0x222222);
  grid.rotation.x = Math.PI / 2;
  scene.add(grid);

  window.addEventListener('resize', handleResize);
  requestAnimationFrame(animate);
}

function handleResize() {
  if (!renderer || !camera) return;
  const { width, height } = container.getBoundingClientRect();
  const aspect = width / height;
  const viewHeight = worldSize;
  const viewWidth = viewHeight * aspect;
  camera.left = -viewWidth / 2;
  camera.right = viewWidth / 2;
  camera.top = viewHeight / 2;
  camera.bottom = -viewHeight / 2;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
}

function animate() {
  requestAnimationFrame(animate);
  if (controls) {
    controls.update();
  }
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

function connect() {
  socket = new WebSocket(`ws://${window.location.host}/ws`);
  socket.onmessage = (event) => {
    lastSnapshot = JSON.parse(event.data);
    updateView();
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
  if (instancedAgents && instancedAgents.count === count) {
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

  const material = new THREE.MeshBasicMaterial({ vertexColors: true });
  instancedAgents = new THREE.InstancedMesh(agentGeometry, material, count);
  instancedAgents.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  scene.add(instancedAgents);
  return instancedAgents;
}

function updateView() {
  if (!lastSnapshot || !scene) return;
  const { tick, metrics, agents } = lastSnapshot;
  tickSpan.textContent = `tick: ${tick}`;
  populationSpan.textContent = `pop: ${metrics.population ?? agents.length}`;

  const mesh = ensureInstancedAgents(agents.length);
  if (!mesh) return;

  const dummy = new THREE.Object3D();
  for (let i = 0; i < agents.length; i += 1) {
    const agent = agents[i];
    dummy.position.set(agent.x - halfWorld, agent.y - halfWorld, 0);
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
