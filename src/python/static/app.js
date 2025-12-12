const canvas = document.getElementById('view');
const ctx = canvas.getContext('2d');
const tickSpan = document.getElementById('tick');
const populationSpan = document.getElementById('population');
const startBtn = document.getElementById('start');
const stopBtn = document.getElementById('stop');
const resetBtn = document.getElementById('reset');
const speedSlider = document.getElementById('speed');

let socket = null;
let lastSnapshot = null;
const worldSize = 100;

function connect() {
  socket = new WebSocket(`ws://${window.location.host}/ws`);
  socket.onmessage = (event) => {
    lastSnapshot = JSON.parse(event.data);
    render();
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

function render() {
  if (!lastSnapshot) return;
  const { tick, metrics, agents } = lastSnapshot;
  tickSpan.textContent = `tick: ${tick}`;
  populationSpan.textContent = `pop: ${metrics.population ?? agents.length}`;

  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const scale = canvas.width / worldSize;
  for (const agent of agents) {
    const x = agent.x * scale;
    const y = agent.y * scale;
    const size = 4;
    const color = agent.group >= 0 ? groupColor(agent.group) : '#7dc9ff';
    ctx.fillStyle = color;
    ctx.fillRect(x, y, size, size);
  }
}

function groupColor(id) {
  const hue = (id * 47) % 360;
  return `hsl(${hue}, 70%, 60%)`;
}

connect();
