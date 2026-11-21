// The text page (v2.2): the socket and its reconnect, the keys, and each state drawn as text.
// The programs panel (v2.4): the programs from the server, their code, a run on a training level,
// and the playback of the run's frames. The page holds no rules: it sends keys and draws the states
// and frames that the server sends back. v3.2 replaces the drawing and keeps the socket.
"use strict";

const RETRY_DELAYS_MS = [500, 1000, 2000, 4000];
const RETRY_EVERY_MS = 5000;
const KEY_DIRECTIONS = { ArrowUp: "N", ArrowRight: "E", ArrowDown: "S", ArrowLeft: "W" };
const LOSS_REASONS = {
  steps: "out of steps",
  deadlock: "a box is stuck in a corner",
  instructions: "out of instructions",
};
const EMPTY_PROMPT = "Pick a level below.";
const PLAYBACK_MS = 150;
// Keys typed into these belong to them, never to the game (the arrows in the level select).
const FORM_CONTROLS = new Set(["SELECT", "INPUT", "TEXTAREA"]);

const view = {
  body: document.body,
  level: document.getElementById("level"),
  steps: document.getElementById("steps"),
  status: document.getElementById("status"),
  board: document.getElementById("board"),
  error: document.getElementById("error"),
  connection: document.getElementById("connection"),
  levels: document.getElementById("levels"),
  programList: document.getElementById("program-list"),
  programName: document.getElementById("program-name"),
  programCode: document.getElementById("program-code"),
  programError: document.getElementById("program-error"),
  runLevel: document.getElementById("run-level"),
  runButton: document.getElementById("run-button"),
  skipButton: document.getElementById("skip-button"),
  runBoard: document.getElementById("run-board"),
  runStep: document.getElementById("run-step"),
  runReport: document.getElementById("run-report"),
};

let socket = null;
let failedAttempts = 0;
let levelsShown = false;
let programsShown = false;
let selectedProgram = null;
let runLevelChosen = false; // the owner picked a level in the select; stop following the game
let playback = null; // {frames, index, report, timer} while a run is being played back
let running = false; // a run request is in flight; Run stays disabled until it answers

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
  if (!programsShown) {
    loadPrograms();
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
  if (event.target && FORM_CONTROLS.has(event.target.tagName)) {
    return;
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
  followGameLevel(state.level);
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
  view.runLevel.replaceChildren(...levels.map(levelOption));
  levelsShown = true;
  markCurrentLevel(view.level.textContent);
  followGameLevel(view.level.textContent);
  updateRunButton();
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
    const heading = document.createElement("h3");
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

function levelOption(level) {
  const option = document.createElement("option");
  option.value = level.id;
  option.textContent = level.id;
  return option;
}

function followGameLevel(levelId) {
  // The run's level follows the human game's level until the owner picks one in the select.
  if (!runLevelChosen && [...view.runLevel.options].some((option) => option.value === levelId)) {
    view.runLevel.value = levelId;
  }
}

// --- The programs (v2.4) ------------------------------------------------------------------------

async function loadPrograms() {
  let programs;
  try {
    const response = await fetch("/api/programs");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    programs = (await response.json()).programs;
  } catch {
    view.programError.textContent = "The program list did not load; it is fetched again on reconnect.";
    return;
  }
  view.programList.replaceChildren(...programs.map(programButton));
  programsShown = true;
  if (programs.length === 0) {
    view.programName.textContent = "No programs in the programs folder.";
  }
}

function programButton(program) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.program = program.name;
  const name = document.createElement("strong");
  name.textContent = program.name;
  const description = document.createElement("span");
  description.className = "program-description";
  description.textContent = program.description ? ` — ${program.description}` : "";
  button.append(name, description);
  button.addEventListener("click", () => {
    showProgram(program.name);
    button.blur();
  });
  return button;
}

async function showProgram(name) {
  view.programError.textContent = "";
  let body;
  try {
    const response = await fetch(`/api/programs/${encodeURIComponent(name)}`);
    body = await response.json();
    if (!response.ok) {
      view.programError.textContent = body.detail;
      return;
    }
  } catch {
    view.programError.textContent = "The program did not load.";
    return;
  }
  selectedProgram = body.name;
  view.programName.textContent = body.name;
  view.programCode.textContent = numberedLines(body.source);
  for (const button of view.programList.querySelectorAll("button")) {
    button.setAttribute("aria-current", String(button.dataset.program === body.name));
  }
  updateRunButton();
}

function numberedLines(source) {
  const lines = source.replace(/\n$/, "").split("\n");
  const width = String(lines.length).length;
  return lines.map((line, i) => `${String(i + 1).padStart(width)}  ${line}`).join("\n");
}

function updateRunButton() {
  view.runButton.disabled = running || selectedProgram === null || view.runLevel.value === "";
}

async function runProgram() {
  if (running || selectedProgram === null || view.runLevel.value === "") {
    return;
  }
  stopPlayback();
  view.programError.textContent = "";
  view.runReport.textContent = "";
  view.runReport.className = "line";
  running = true;
  updateRunButton();
  let body;
  try {
    const response = await fetch(`/api/programs/${encodeURIComponent(selectedProgram)}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: view.runLevel.value }),
    });
    body = await response.json();
    if (!response.ok) {
      view.programError.textContent = body.detail;
      return;
    }
  } catch {
    view.programError.textContent = "The run did not reach the server.";
    return;
  } finally {
    running = false;
    updateRunButton();
  }
  startPlayback(body.frames, body.report);
}

// --- The playback -------------------------------------------------------------------------------

function startPlayback(frames, report) {
  stopPlayback(); // one playback at a time: an earlier timer never keeps running (code review #1)
  playback = { frames, index: 0, report, timer: null };
  drawFrame(frames[0]);
  if (frames.length === 1) {
    finishPlayback();
    return;
  }
  view.skipButton.disabled = false;
  playback.timer = setInterval(nextFrame, PLAYBACK_MS);
}

function nextFrame() {
  playback.index += 1;
  drawFrame(playback.frames[playback.index]);
  if (playback.index === playback.frames.length - 1) {
    finishPlayback();
  }
}

function skipToEnd() {
  if (playback === null) {
    return;
  }
  playback.index = playback.frames.length - 1;
  drawFrame(playback.frames[playback.index]);
  finishPlayback();
}

function finishPlayback() {
  clearInterval(playback.timer);
  view.skipButton.disabled = true;
  view.runReport.textContent = reportText(playback.report);
  view.runReport.className = `line ${playback.report.status}`;
  playback = null;
}

function stopPlayback() {
  if (playback !== null) {
    clearInterval(playback.timer);
    playback = null;
  }
  view.skipButton.disabled = true;
}

function drawFrame(frame) {
  view.runBoard.textContent = frame.map.join("\n");
  view.runStep.textContent = frame.dir === null
    ? "start"
    : `step ${frame.step} · ${frame.moved ? "move" : "bump"} ${frame.dir}`;
}

function reportText(report) {
  let outcome;
  if (report.status === "solved") {
    outcome = `solved in ${report.steps} steps`;
  } else if (report.status === "lost") {
    outcome = `lost — ${LOSS_REASONS[report.reason] ?? report.reason}`;
  } else if (report.reason === "give_up") {
    outcome = `gave up: ${report.error}`;
  } else if (report.reason === "error") {
    outcome = `error: ${report.error}`;
  } else {
    outcome = report.error ?? report.status;
  }
  return `${outcome} · ${report.steps} steps · ${report.instructions} instructions`;
}

view.runLevel.addEventListener("change", () => {
  runLevelChosen = true;
  updateRunButton();
});
view.runButton.addEventListener("click", runProgram);
view.skipButton.addEventListener("click", skipToEnd);
document.addEventListener("keydown", onKey);
connect();
