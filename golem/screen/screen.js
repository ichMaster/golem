// The text page (v2.2): the socket and its reconnect, the keys, and each state drawn as text.
// The page holds no rules. It sends keys and draws the states that the server sends back; v3.2
// replaces the drawing and keeps the socket and the reconnect.
"use strict";

const RETRY_DELAYS_MS = [500, 1000, 2000, 4000];
const RETRY_EVERY_MS = 5000;
const KEY_DIRECTIONS = { ArrowUp: "N", ArrowRight: "E", ArrowDown: "S", ArrowLeft: "W" };
const LOSS_REASONS = { steps: "out of steps", deadlock: "a box is stuck in a corner" };
const EMPTY_PROMPT = "Pick a level below.";

const view = {
  body: document.body,
  level: document.getElementById("level"),
  steps: document.getElementById("steps"),
  status: document.getElementById("status"),
  board: document.getElementById("board"),
  error: document.getElementById("error"),
  connection: document.getElementById("connection"),
  levels: document.getElementById("levels"),
};

let socket = null;
let failedAttempts = 0;
let levelsShown = false;

// --- The socket ---------------------------------------------------------------------------------

function socketUrl() {
  // The page's own host and port; only the scheme changes (http -> ws, https -> wss).
  const url = new URL("/ws", location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.href;
}

function connect() {
  socket = new WebSocket(socketUrl());
  socket.addEventListener("open", onOpen);
  socket.addEventListener("message", (event) => receive(event.data));
  socket.addEventListener("close", onClose);
}

function onOpen() {
  failedAttempts = 0;
  showConnected(true);
  // The server sends the current state at once when it holds a game; until then, nothing is loaded.
  showEmpty();
  if (!levelsShown) {
    loadLevels();
  }
}

function onClose() {
  showConnected(false);
  const delay = failedAttempts < RETRY_DELAYS_MS.length
    ? RETRY_DELAYS_MS[failedAttempts]
    : RETRY_EVERY_MS;
  failedAttempts += 1;
  setTimeout(connect, delay);
}

function send(message) {
  // Keys pressed while the socket is not open are dropped, never queued.
  if (socket !== null && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message));
  }
}

function receive(text) {
  let message;
  try {
    message = JSON.parse(text);
  } catch {
    return;
  }
  if (message.type === "state") {
    drawState(message);
  } else if (message.type === "error") {
    view.error.textContent = message.detail;
  }
}

// --- The keys -----------------------------------------------------------------------------------

function onKey(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) {
    return; // Cmd+R and the like keep their browser meaning
  }
  const direction = KEY_DIRECTIONS[event.key];
  if (direction !== undefined) {
    event.preventDefault();
    send({ type: "move", dir: direction });
  } else if (event.key === "r" || event.key === "R") {
    event.preventDefault();
    send({ type: "restart" });
  }
}

// --- The drawing --------------------------------------------------------------------------------

function statusText(state) {
  if (state.status === "solved") {
    return `solved in ${state.steps} steps`;
  }
  if (state.status === "lost") {
    return `lost — ${LOSS_REASONS[state.reason] ?? state.reason}`;
  }
  return state.status;
}

function drawState(state) {
  view.board.textContent = state.map.join("\n");
  view.level.textContent = state.level;
  view.steps.textContent = `${state.steps} / ${state.budget}`;
  view.status.textContent = statusText(state);
  view.status.className = state.status;
  view.error.textContent = "";
  markCurrentLevel(state.level);
}

function showEmpty() {
  view.board.textContent = EMPTY_PROMPT;
  view.level.textContent = "no level loaded";
  view.steps.textContent = "–";
  view.status.textContent = "–";
  view.status.className = "";
  markCurrentLevel(null);
}

function showConnected(connected) {
  view.body.classList.toggle("offline", !connected);
  view.connection.textContent = connected ? "connected" : "reconnecting…";
}

function markCurrentLevel(levelId) {
  for (const button of view.levels.querySelectorAll("button")) {
    button.setAttribute("aria-current", String(button.dataset.level === levelId));
  }
}

// --- The level list -----------------------------------------------------------------------------

async function loadLevels() {
  let levels;
  try {
    const response = await fetch("/api/levels");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    levels = (await response.json()).levels;
  } catch {
    view.error.textContent = "The level list did not load; it is fetched again on reconnect.";
    return;
  }
  view.levels.replaceChildren(...levelGroups(levels));
  levelsShown = true;
  markCurrentLevel(view.level.textContent);
}

function levelGroups(levels) {
  const tiers = new Map();
  for (const level of levels) {
    if (!tiers.has(level.tier)) {
      tiers.set(level.tier, []);
    }
    tiers.get(level.tier).push(level);
  }
  return [...tiers].map(([tier, members]) => {
    const group = document.createElement("div");
    group.className = "tier";
    const heading = document.createElement("h2");
    heading.textContent = tier;
    group.append(heading, ...members.map(levelButton));
    return group;
  });
}

function levelButton(level) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.level = level.id;
  button.textContent = `${level.id.split("/").pop()} · ${level.budget.steps} steps`;
  button.addEventListener("click", () => {
    send({ type: "load", level: level.id });
    button.blur(); // so that Space or Enter does not load the level again by accident
  });
  return button;
}

document.addEventListener("keydown", onKey);
connect();
