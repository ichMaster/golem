/* Golem — round 2 art directions. Layered canvas renderer, no libraries.
   <golem-scene direction="clay|lab|diorama" map="rows|joined|by|pipes" inset="t r b l" facing="N|E|S|W" cellmax="64" still>
   <golem-mini  direction="…" map="…" cell="7">
   Static layer (background, frame, floor, shadows, goals, walls, boxes) is built once per state;
   each frame blits it, then draws glows, Golem, the cells in front of Golem, particles and light. */
(function () {
  if (customElements.get('golem-scene')) return;
  const TAU = Math.PI * 2;
  const DIRV = { N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0] };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  function hash(x, y, k) {
    let h = Math.imul((x | 0) + 101, 374761393) ^ Math.imul((y | 0) + 211, 668265263) ^ Math.imul(((k || 0) | 0) + 7, 1274126177);
    h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  }
  const rowsOf = (m) => Array.isArray(m) ? m : (m ? String(m).split('|') : []);

  function model(input, floorMode) {
    const rows = rowsOf(input);
    const H = rows.length, W = Math.max(0, ...rows.map(r => r.length));
    const at = (x, y) => (rows[y] && rows[y][x]) || ' ';
    const isWall = (x, y) => at(x, y) === '#';
    const ins = rows.map(() => new Array(W).fill(false));
    let robot = null; const goals = [], boxes = [];
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const c = at(x, y);
      if (c === '.' || c === '*' || c === '+') goals.push({ x, y, lit: c === '*' });
      if (c === '$' || c === '*') boxes.push({ x, y, on: c === '*' });
      if (c === '@' || c === '+') robot = { x, y, on: c === '+' };
    }
    if (floorMode === 'all') rows.forEach((r, y) => { for (let x = 0; x < r.length; x++) if (r[x] !== '#') ins[y][x] = true; });
    else if (robot) {
      const st = [[robot.x, robot.y]];
      while (st.length) {
        const [x, y] = st.pop();
        if (y < 0 || y >= H || x < 0 || x >= W || ins[y][x]) continue;
        const c = rows[y][x]; if (c === undefined || c === '#') continue;
        ins[y][x] = true; st.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]);
      }
    } else rows.forEach((r, y) => { const a = r.indexOf('#'), b = r.lastIndexOf('#'); for (let x = a + 1; x < b; x++) if (r[x] !== '#') ins[y][x] = true; });
    const inside = (x, y) => !!(ins[y] && ins[y][x]);
    const boxAt = (x, y) => boxes.find(b => b.x === x && b.y === y);
    return { rows, W, H, at, isWall, inside, robot, goals, boxes, boxAt };
  }

  // ── helpers ──
  function rr(c, x, y, w, h, r) { c.beginPath(); if (c.roundRect) c.roundRect(x, y, w, h, r); else c.rect(x, y, w, h); }
  function lin(c, x0, y0, x1, y1, st) { const g = c.createLinearGradient(x0, y0, x1, y1); st.forEach(([o, k]) => g.addColorStop(o, k)); return g; }
  function rad(c, x, y, r, st, r0) { const g = c.createRadialGradient(x, y, r0 || 0, x, y, r); st.forEach(([o, k]) => g.addColorStop(o, k)); return g; }
  function circle(c, x, y, r) { c.beginPath(); c.arc(x, y, r, 0, TAU); }
  function ell(c, x, y, rx, ry, rot) { c.beginPath(); c.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), rot || 0, 0, TAU); }
  function castShadow(c, g, build, color, blur, dx, dy) {
    c.save(); c.shadowColor = color; c.shadowBlur = blur * g.dpr;
    c.shadowOffsetX = (dx + 6000) * g.dpr; c.shadowOffsetY = dy * g.dpr;
    c.translate(-6000, 0); c.beginPath(); build(c); c.fillStyle = '#000'; c.fill(); c.restore();
  }
  function speckle(c, x, y, w, h, n, seed, colors, a, b) {
    for (let i = 0; i < n; i++) {
      const r = a + hash(seed, i, 13) * (b - a);
      c.fillStyle = colors[i % colors.length];
      c.fillRect(x + hash(seed, i, 11) * w, y + hash(seed, i, 12) * h, r, r);
    }
  }
  function glow(c, g, color, blur) { c.shadowColor = color; c.shadowBlur = blur * g.dpr; c.shadowOffsetX = 0; c.shadowOffsetY = 0; }
  function noGlow(c) { c.shadowColor = 'transparent'; c.shadowBlur = 0; }
  function blink(t, period, seed) { const p = (t + seed) % period; return p < 0.15 ? Math.sin((p / 0.15) * Math.PI) : 0; }
  function ao(c, g, m, color, len) {
    const s = g.s;
    for (let y = 0; y < m.H; y++) for (let x = 0; x < m.W; x++) {
      if (!m.inside(x, y)) continue;
      const px = g.ox + x * s, py = g.oy + y * s;
      if (m.isWall(x, y - 1)) { c.fillStyle = lin(c, 0, py, 0, py + s * len, [[0, color], [1, 'rgba(0,0,0,0)']]); c.fillRect(px, py, s, s * len); }
      if (m.isWall(x - 1, y)) { c.fillStyle = lin(c, px, 0, px + s * len * 0.8, 0, [[0, color], [1, 'rgba(0,0,0,0)']]); c.fillRect(px, py, s * len * 0.8, s); }
    }
  }
  function shadowPath(m, g, wallH, boxInset, boxH) {
    const s = g.s;
    return (c) => {
      for (let y = 0; y < m.H; y++) for (let x = 0; x < m.W; x++) {
        const px = g.ox + x * s, py = g.oy + y * s;
        if (m.isWall(x, y)) c.rect(px, py - wallH, s, s + wallH);
        else if (m.boxAt(x, y)) c.rect(px + boxInset, py + boxInset - boxH, s - 2 * boxInset, s - 2 * boxInset + boxH);
      }
    };
  }
  function motes(c, g, t, n, color, area, speed, seed) {
    const { bx0, by0, bx1, by1, s } = g;
    const x0 = bx0 - s * area, y0 = by0 - s * area, w = bx1 - bx0 + 2 * s * area, h = by1 - by0 + 2 * s * area;
    for (let i = 0; i < n; i++) {
      const px = x0 + ((hash(i, seed, 1) * w + t * speed * (0.4 + hash(i, seed, 2)) * 14) % w);
      const py = y0 + (((hash(i, seed, 3) * h - t * speed * (0.3 + hash(i, seed, 4)) * 9) % h) + h) % h;
      const tw = 0.5 + 0.5 * Math.sin(t * (0.8 + hash(i, seed, 5) * 1.6) + i);
      const r = 0.6 + hash(i, seed, 6) * 1.5;
      c.globalAlpha = 0.12 + tw * 0.5; c.fillStyle = color; circle(c, px, py, r); c.fill();
    }
    c.globalAlpha = 1;
  }
  function vignette(c, g, color, strength) {
    const cx = (g.bx0 + g.bx1) / 2, cy = (g.by0 + g.by1) / 2;
    c.fillStyle = rad(c, cx, cy, Math.max(g.W, g.H) * 0.75, [[0, 'rgba(0,0,0,0)'], [0.45, 'rgba(0,0,0,0)'], [1, color]]);
    c.globalAlpha = strength; c.fillRect(0, 0, g.W, g.H); c.globalAlpha = 1;
  }

  // ════════════════ A · CLAY AND STONE ════════════════
  const clay = {
    hw: 0.34, margin: 0.55, thick: 0.4,
    mini: { floor: '#6c5e52', grid: '#5a4e45', wallTop: '#9a8a79', wallFront: '#54473d', goal: '#a68f69', goalLit: '#b5abfc', box: '#c4a580', boxFront: '#7a6249', mark: '#d2cefd', robot: '#c87a4e', eye: '#d2cefd' },
    bg(c, g) {
      const cx = (g.bx0 + g.bx1) / 2, cy = (g.by0 + g.by1) / 2;
      c.fillStyle = rad(c, cx - (g.bx1 - g.bx0) * 0.3, cy - (g.by1 - g.by0) * 0.45, Math.max(g.W, g.H) * 0.85,
        [[0, '#47352a'], [0.3, '#2a2022'], [0.65, '#18151d'], [1, '#0f1019']]);
      c.fillRect(0, 0, g.W, g.H);
      for (let i = 0; i < 26; i++) {
        const x = hash(i, 3, 1) * g.W, y = hash(i, 3, 2) * g.H, r = 60 + hash(i, 3, 3) * 180;
        c.fillStyle = rad(c, x, y, r, [[0, i % 2 ? 'rgba(255,190,140,0.025)' : 'rgba(0,0,0,0.08)'], [1, 'rgba(0,0,0,0)']]);
        c.fillRect(x - r, y - r, 2 * r, 2 * r);
      }
    },
    frame(c, g) {
      const s = g.s, mg = s * this.margin, d = s * this.thick;
      const x0 = g.bx0 - mg, y0 = g.by0 - mg - g.hw, x1 = g.bx1 + mg, y1 = g.by1 + mg, R = s * 0.28;
      castShadow(c, g, k => k.roundRect(x0, y0, x1 - x0, y1 - y0 + d, R), 'rgba(0,0,0,0.8)', s * 1.3, s * 0.3, s * 0.55);
      rr(c, x0, y0 + d, x1 - x0, y1 - y0, R); c.fillStyle = lin(c, 0, y1 - R, 0, y1 + d, [[0, '#2e2621'], [1, '#191512']]); c.fill();
      rr(c, x0, y0, x1 - x0, y1 - y0, R); c.fillStyle = lin(c, x0, y0, x1, y1, [[0, '#544840'], [0.55, '#3b322c'], [1, '#2b2420']]); c.fill();
      c.save(); rr(c, x0, y0, x1 - x0, y1 - y0, R); c.clip();
      speckle(c, x0, y0, x1 - x0, y1 - y0, Math.round((x1 - x0) * (y1 - y0) / (g.lod > 1 ? 60 : 160)), 77, ['rgba(255,235,210,0.07)', 'rgba(0,0,0,0.18)', 'rgba(0,0,0,0.1)'], 0.8, 2.2);
      c.restore();
      c.lineWidth = 1.5; c.strokeStyle = 'rgba(255,226,196,0.14)'; rr(c, x0 + 1, y0 + 1, x1 - x0 - 2, y1 - y0 - 2, R - 1); c.stroke();
      c.strokeStyle = 'rgba(255,226,196,0.08)'; c.beginPath(); c.moveTo(x0 + R, y1 + 1.5); c.lineTo(x1 - R, y1 + 1.5); c.stroke();
    },
    floor(c, g, px, py, x, y) {
      const s = g.s, r = hash(x, y, 1), r2 = hash(x, y, 2), gp = Math.max(1, s * 0.035), L = 30 + r * 9;
      c.fillStyle = '#29211d'; c.fillRect(px, py, s, s);
      rr(c, px + gp, py + gp, s - 2 * gp, s - 2 * gp, s * (0.05 + r2 * 0.09));
      c.fillStyle = lin(c, px, py, px + s, py + s, [[0, `hsl(28,15%,${L + 6}%)`], [1, `hsl(24,15%,${L - 5}%)`]]); c.fill();
      if (g.lod < 1) return;
      c.save(); c.clip();
      speckle(c, px, py, s, s, g.lod > 1 ? 30 : 10, x * 977 + y, ['rgba(255,240,220,0.11)', 'rgba(0,0,0,0.16)'], 0.8, 1.9);
      if (hash(x, y, 3) < 0.35) { const wx = px + s * (0.3 + 0.4 * hash(x, y, 31)), wy = py + s * (0.3 + 0.4 * hash(x, y, 32)); c.fillStyle = rad(c, wx, wy, s * 0.35, [[0, 'rgba(255,230,200,0.10)'], [1, 'rgba(255,230,200,0)']]); c.fillRect(px, py, s, s); }
      if (hash(x, y, 4) < 0.22) {
        c.strokeStyle = 'rgba(20,13,9,0.55)'; c.lineWidth = Math.max(0.8, s * 0.018); c.beginPath();
        let cx = px + s * (0.15 + 0.3 * hash(x, y, 41)), cy = py + s * (0.1 + 0.3 * hash(x, y, 42)); c.moveTo(cx, cy);
        for (let i = 0; i < 4; i++) { cx += s * (0.08 + 0.12 * hash(x, y, 50 + i)); cy += s * (0.06 + 0.14 * hash(x, y, 60 + i)); c.lineTo(cx, cy); }
        c.stroke();
      }
      c.restore();
      c.strokeStyle = 'rgba(255,236,210,0.09)'; c.lineWidth = 1; c.beginPath(); c.moveTo(px + gp + 2, py + gp + 0.5); c.lineTo(px + s - gp - 3, py + gp + 0.5); c.stroke();
    },
    goal(c, g, cx, cy, lit) {
      const s = g.s, R = s * 0.34;
      if (lit) { c.save(); c.globalCompositeOperation = 'lighter'; c.fillStyle = rad(c, cx, cy, R * 1.9, [[0, 'rgba(145,132,217,0.55)'], [0.5, 'rgba(145,132,217,0.18)'], [1, 'rgba(145,132,217,0)']]); c.fillRect(cx - R * 2, cy - R * 2, R * 4, R * 4); c.restore(); }
      const col = lit ? '#cfc8ff' : '#a68f69';
      c.lineWidth = Math.max(1.6, s * 0.05);
      c.strokeStyle = 'rgba(15,10,8,0.6)'; circle(c, cx, cy + 1, R); c.stroke();
      c.save(); if (lit) glow(c, g, '#9184d9', s * 0.25);
      c.strokeStyle = col; circle(c, cx, cy, R); c.stroke();
      c.lineWidth = Math.max(1, s * 0.024); circle(c, cx, cy, R * 0.64); c.stroke();
      if (g.lod >= 1) {
        for (let i = 0; i < 8; i++) {
          const a = (i / 8) * TAU + 0.39;
          if (i % 2) { c.beginPath(); c.moveTo(cx + Math.cos(a) * R * 0.72, cy + Math.sin(a) * R * 0.72); c.lineTo(cx + Math.cos(a) * R * 0.9, cy + Math.sin(a) * R * 0.9); c.stroke(); }
          else { c.fillStyle = col; circle(c, cx + Math.cos(a) * R * 0.81, cy + Math.sin(a) * R * 0.81, Math.max(0.8, s * 0.018)); c.fill(); }
        }
      }
      c.fillStyle = col; const d = s * 0.06; c.beginPath(); c.moveTo(cx, cy - d); c.lineTo(cx + d, cy); c.lineTo(cx, cy + d); c.lineTo(cx - d, cy); c.fill();
      c.restore();
    },
    shadows(c, g, m) { castShadow(c, g, shadowPath(m, g, g.hw, g.s * 0.11, g.s * 0.27), 'rgba(8,5,3,0.62)', g.s * 0.32, g.s * 0.2, g.s * 0.16); ao(c, g, m, 'rgba(10,6,4,0.35)', 0.28); },
    wall(c, g, px, py, x, y, m, front) {
      const s = g.s, h = g.hw, top = py - h;
      if (front) {
        c.fillStyle = lin(c, 0, py + s - h, 0, py + s, [[0, '#5b4d42'], [1, '#382e27']]); c.fillRect(px, py + s - h, s, h);
        if (g.lod >= 1) {
          c.fillStyle = 'rgba(18,12,9,0.5)'; c.fillRect(px, py + s - h * 0.5, s, Math.max(1, s * 0.02));
          const j1 = px + s * (0.25 + 0.3 * hash(x, y, 21)), j2 = px + s * (0.55 + 0.35 * hash(x, y, 22));
          c.fillRect(j1, py + s - h, Math.max(1, s * 0.02), h * 0.5); c.fillRect(j2, py + s - h * 0.5, Math.max(1, s * 0.02), h * 0.5);
        }
        c.fillStyle = 'rgba(255,226,196,0.13)'; c.fillRect(px, py + s - h, s, 1);
      }
      const r = hash(x, y, 5);
      c.fillStyle = lin(c, px, top, px + s, top + s, [[0, `hsl(31,13%,${51 + r * 6}%)`], [1, `hsl(27,12%,${38 + r * 5}%)`]]); c.fillRect(px, top, s, s);
      if (g.lod >= 1) {
        speckle(c, px, top, s, s, g.lod > 1 ? 34 : 12, x * 131 + y * 7, ['rgba(255,240,220,0.12)', 'rgba(0,0,0,0.15)', 'rgba(60,40,25,0.2)'], 0.8, 2);
        c.fillStyle = 'rgba(25,17,12,0.45)';
        if (m.isWall(x + 1, y)) c.fillRect(px + s - 1, top + s * 0.1 * hash(x, y, 23), Math.max(1, s * 0.022), s * (0.85 + 0.15 * hash(x, y, 24)));
        if (m.isWall(x, y + 1)) c.fillRect(px + s * 0.08 * hash(x, y, 25), top + s - 1, s * (0.9 + 0.1 * hash(x, y, 26)), Math.max(1, s * 0.022));
      }
      const bw = Math.max(1.5, s * 0.05);
      if (!m.isWall(x, y - 1)) { c.fillStyle = 'rgba(255,232,205,0.26)'; c.fillRect(px, top, s, bw); }
      if (!m.isWall(x - 1, y)) { c.fillStyle = 'rgba(255,232,205,0.15)'; c.fillRect(px, top, bw, s); }
      if (!m.isWall(x + 1, y)) { c.fillStyle = 'rgba(0,0,0,0.25)'; c.fillRect(px + s - bw, top, bw, s); }
      if (!m.isWall(x, y + 1)) { c.fillStyle = 'rgba(0,0,0,0.2)'; c.fillRect(px, top + s - bw, s, bw); }
    },
    box(c, g, px, py, x, y, on) {
      const s = g.s, b = s * 0.11, d = s - 2 * b, h = s * 0.27, x0 = px + b, y0 = py + b - h + s * 0.03, R = s * 0.07;
      rr(c, x0, y0 + d - R, d, h + R, [0, 0, R, R]); c.fillStyle = lin(c, 0, y0 + d, 0, y0 + d + h, [[0, '#86694d'], [1, '#56422f']]); c.fill();
      if (on) { c.save(); c.globalCompositeOperation = 'lighter'; c.fillStyle = lin(c, 0, y0 + d + h, 0, y0 + d, [[0, 'rgba(145,132,217,0.55)'], [1, 'rgba(145,132,217,0)']]); rr(c, x0, y0 + d - R, d, h + R, [0, 0, R, R]); c.fill(); c.restore(); }
      rr(c, x0, y0, d, d, R); c.fillStyle = lin(c, x0, y0, x0 + d, y0 + d, [[0, '#d2b48c'], [1, '#a08060']]); c.fill();
      if (g.lod >= 1) { c.save(); rr(c, x0, y0, d, d, R); c.clip(); speckle(c, x0, y0, d, d, g.lod > 1 ? 26 : 10, x * 53 + y * 3, ['rgba(255,245,225,0.16)', 'rgba(90,60,35,0.18)'], 0.8, 1.8); c.restore(); }
      c.strokeStyle = 'rgba(255,240,215,0.35)'; c.lineWidth = 1; c.beginPath(); c.moveTo(x0 + R, y0 + 0.5); c.lineTo(x0 + d - R, y0 + 0.5); c.moveTo(x0 + 0.5, y0 + R); c.lineTo(x0 + 0.5, y0 + d - R); c.stroke();
      const cx = x0 + d / 2, cy = y0 + d / 2, gr = d * 0.2;
      const path = () => { c.beginPath(); c.arc(cx, cy, gr, 0, TAU); c.moveTo(cx, cy - d * 0.32); c.lineTo(cx, cy + d * 0.32); c.moveTo(cx - d * 0.1, cy - d * 0.32); c.lineTo(cx + d * 0.1, cy - d * 0.32); };
      c.lineCap = 'round';
      if (on) {
        c.save(); glow(c, g, '#9184d9', s * 0.3); c.strokeStyle = '#e7e5fe'; c.lineWidth = Math.max(1.5, s * 0.045); path(); c.stroke(); c.restore();
      } else {
        c.strokeStyle = 'rgba(255,240,215,0.3)'; c.lineWidth = Math.max(1, s * 0.03); c.save(); c.translate(0.7, 0.9); path(); c.stroke(); c.restore();
        c.strokeStyle = 'rgba(70,46,28,0.65)'; c.lineWidth = Math.max(1.2, s * 0.04); path(); c.stroke();
      }
    },
    robot(c, g, px, py, t, facing) {
      const s = g.s, cx = px + s / 2, base = py + s * 0.86;
      const br = 0.5 + 0.5 * Math.sin(t * 1.9), sy = 1 + br * 0.035, sx = 1 - br * 0.015;
      const [fx, fy] = DIRV[facing] || [0, 0];
      c.save(); c.translate(cx + s * 0.07, base + s * 0.01); c.scale(1, 0.3); c.fillStyle = rad(c, 0, 0, s * 0.38, [[0, 'rgba(0,0,0,0.6)'], [1, 'rgba(0,0,0,0)']]); circle(c, 0, 0, s * 0.38); c.fill(); c.restore();
      c.save(); c.translate(cx, base); c.scale(sx, sy);
      const hgt = s * 0.64, bw = s * 0.27, tw = s * 0.22;
      c.fillStyle = '#7a3f27'; ell(c, -s * 0.13, -s * 0.015, s * 0.1, s * 0.055); c.fill(); ell(c, s * 0.13, -s * 0.015, s * 0.1, s * 0.055); c.fill();
      for (const side of [-1, 1]) {
        ell(c, side * s * 0.275, -hgt * 0.4, s * 0.075, s * 0.135, side * 0.28);
        c.fillStyle = lin(c, side * s * 0.2, -hgt * 0.6, side * s * 0.33, -hgt * 0.2, [[0, '#c27448'], [1, '#8c4a2c']]); c.fill();
      }
      c.beginPath(); c.moveTo(-bw, -s * 0.05);
      c.bezierCurveTo(-bw - s * 0.035, -hgt * 0.55, -tw - s * 0.02, -hgt, 0, -hgt);
      c.bezierCurveTo(tw + s * 0.02, -hgt, bw + s * 0.035, -hgt * 0.55, bw, -s * 0.05);
      c.quadraticCurveTo(0, s * 0.025, -bw, -s * 0.05);
      c.fillStyle = lin(c, -bw, -hgt, bw, 0, [[0, '#e09a6c'], [0.5, '#b8683f'], [1, '#7e4127']]); c.fill();
      c.save(); c.clip();
      c.fillStyle = rad(c, -s * 0.1, -hgt * 0.74, s * 0.26, [[0, 'rgba(255,228,200,0.5)'], [1, 'rgba(255,228,200,0)']]); c.fillRect(-bw * 1.2, -hgt, bw * 2.4, hgt);
      c.fillStyle = rad(c, 0, -hgt * 0.62, s * 0.3, [[0, 'rgba(145,132,217,0.18)'], [1, 'rgba(145,132,217,0)']]); c.fillRect(-bw * 1.2, -hgt, bw * 2.4, hgt);
      if (g.lod >= 2) {
        c.strokeStyle = 'rgba(255,225,195,0.13)'; c.lineWidth = 1;
        for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(s * 0.08, -hgt * 0.28, s * (0.04 + i * 0.025), Math.PI * 1.1, Math.PI * 1.75); c.stroke(); }
        c.strokeStyle = 'rgba(80,35,18,0.25)'; c.beginPath(); c.moveTo(-bw * 0.8, -hgt * 0.36); c.quadraticCurveTo(-bw * 0.4, -hgt * 0.32, -bw * 0.15, -hgt * 0.38); c.stroke();
      }
      c.restore();
      const ey = -hgt * 0.58 + fy * s * 0.02, ex = fx * s * 0.04, bl = blink(t, 3.7, 0.8);
      c.fillStyle = '#35180e';
      ell(c, -s * 0.095 + ex, ey, s * 0.06, s * 0.072 * (1 - bl * 0.85)); c.fill();
      ell(c, s * 0.095 + ex, ey, s * 0.06, s * 0.072 * (1 - bl * 0.85)); c.fill();
      if (bl < 0.6) {
        c.save(); glow(c, g, '#9184d9', s * 0.28); c.fillStyle = '#ece9ff';
        circle(c, -s * 0.095 + ex * 1.3, ey + fy * s * 0.01, s * 0.024); c.fill(); circle(c, s * 0.095 + ex * 1.3, ey + fy * s * 0.01, s * 0.024); c.fill(); c.restore();
      }
      const gy = -hgt * 0.84, pulse = 0.65 + 0.35 * Math.sin(t * 1.4);
      c.save(); glow(c, g, '#9184d9', s * 0.35 * pulse); c.strokeStyle = `rgba(214,208,255,${0.75 + 0.25 * pulse})`; c.lineWidth = Math.max(1.2, s * 0.028); c.lineCap = 'round';
      c.beginPath(); c.moveTo(0, gy - s * 0.05); c.lineTo(0, gy + s * 0.05); c.moveTo(-s * 0.045, gy - s * 0.025); c.lineTo(0, gy + s * 0.008); c.lineTo(s * 0.045, gy - s * 0.025); c.stroke(); c.restore();
      c.restore();
    },
    dyn(c, g, m, t) {
      c.save(); c.globalCompositeOperation = 'lighter';
      for (const q of m.goals) if (q.lit) {
        const cx = g.ox + q.x * g.s + g.s / 2, cy = g.oy + q.y * g.s + g.s / 2, a = 0.1 + 0.08 * Math.sin(t * 2 + q.x);
        c.fillStyle = rad(c, cx, cy, g.s * 0.8, [[0, `rgba(145,132,217,${a})`], [1, 'rgba(145,132,217,0)']]); c.fillRect(cx - g.s, cy - g.s, g.s * 2, g.s * 2);
      }
      c.restore();
    },
    post(c, g, t) {
      const fl = 1 + 0.06 * Math.sin(t * 6.3) * Math.sin(t * 2.7);
      c.save(); c.globalCompositeOperation = 'screen';
      const lx = g.bx0 + (g.bx1 - g.bx0) * 0.25, ly = g.by0 - g.s;
      c.fillStyle = rad(c, lx, ly, (g.bx1 - g.bx0) * 1.1, [[0, `rgba(255,180,120,${0.10 * fl})`], [1, 'rgba(255,180,120,0)']]); c.fillRect(0, 0, g.W, g.H);
      c.restore();
      if (g.lod >= 1) motes(c, g, t, 70, '#ffd9b0', 1.2, 0.6, 3);
      vignette(c, g, 'rgba(6,5,10,0.9)', 0.75);
    }
  };

  // ════════════════ B · PRECISION LABORATORY ════════════════
  const lab = {
    hw: 0.22, margin: 0.5, thick: 0.12,
    mini: { floor: '#232839', grid: '#2e3449', wallTop: '#3a4160', wallFront: '#141724', goal: '#6fe0c4', goalLit: '#6fe0c4', box: '#7b8197', boxFront: '#3a3e50', mark: '#6fe0c4', robot: '#d9dbe6', eye: '#9184d9' },
    bg(c, g) {
      c.fillStyle = lin(c, 0, 0, 0, g.H, [[0, '#0d0f19'], [1, '#141726']]); c.fillRect(0, 0, g.W, g.H);
      c.strokeStyle = 'rgba(145,132,217,0.05)'; c.lineWidth = 1; c.beginPath();
      for (let x = 0.5; x < g.W; x += 48) { c.moveTo(x, 0); c.lineTo(x, g.H); }
      for (let y = 0.5; y < g.H; y += 48) { c.moveTo(0, y); c.lineTo(g.W, y); }
      c.stroke();
      const cx = (g.bx0 + g.bx1) / 2;
      c.fillStyle = rad(c, cx, g.by0 - g.s * 2, (g.bx1 - g.bx0) * 1.2, [[0, 'rgba(145,132,217,0.16)'], [1, 'rgba(145,132,217,0)']]); c.fillRect(0, 0, g.W, g.H);
    },
    frame(c, g) {
      const s = g.s, mg = s * this.margin, x0 = g.bx0 - mg, y0 = g.by0 - mg - g.hw, x1 = g.bx1 + mg, y1 = g.by1 + mg, R = s * 0.22;
      castShadow(c, g, k => k.roundRect(x0, y0, x1 - x0, y1 - y0, R), 'rgba(0,0,0,0.85)', s * 1.2, 0, s * 0.4);
      c.save(); glow(c, g, 'rgba(145,132,217,0.35)', s * 0.9);
      rr(c, x0, y0, x1 - x0, y1 - y0, R); c.fillStyle = lin(c, 0, y0, 0, y1, [[0, '#151827'], [1, '#0d0f19']]); c.fill(); c.restore();
      c.save(); rr(c, x0, y0, x1 - x0, y1 - y0, R); c.clip();
      c.fillStyle = 'rgba(181,171,252,0.07)';
      for (let y = y0 + 8; y < y1; y += 12) for (let x = x0 + 8; x < x1; x += 12) c.fillRect(x, y, 1, 1);
      c.restore();
      c.lineWidth = 1; c.strokeStyle = 'rgba(181,171,252,0.32)'; rr(c, x0 + 0.5, y0 + 0.5, x1 - x0 - 1, y1 - y0 - 1, R); c.stroke();
      c.strokeStyle = 'rgba(255,255,255,0.08)'; c.beginPath(); c.moveTo(x0 + R, y0 + 1.5); c.lineTo(x1 - R, y0 + 1.5); c.stroke();
      const L = s * 0.35, k = s * 0.14; c.strokeStyle = 'rgba(181,171,252,0.7)'; c.lineWidth = 1.5; c.beginPath();
      [[x0 + k, y0 + k, 1, 1], [x1 - k, y0 + k, -1, 1], [x1 - k, y1 - k, -1, -1], [x0 + k, y1 - k, 1, -1]].forEach(([x, y, a, b]) => { c.moveTo(x, y + b * L); c.lineTo(x, y); c.lineTo(x + a * L, y); });
      c.stroke();
    },
    floor(c, g, px, py, x, y) {
      const s = g.s, v = hash(x, y, 1);
      c.fillStyle = '#0a0c13'; c.fillRect(px, py, s, s);
      rr(c, px + 1, py + 1, s - 2, s - 2, s * 0.05); c.fillStyle = lin(c, 0, py, 0, py + s, [[0, '#252a3d'], [1, '#1a1e2c']]); c.fill();
      if (g.lod >= 1) {
        for (let i = 0; i < 9; i++) { c.fillStyle = `rgba(255,255,255,${0.012 + 0.025 * hash(x * 7 + i, y, 3)})`; c.fillRect(px + 2, py + 2 + (i + 0.5) * (s - 4) / 9, s - 4, 1); }
        c.fillStyle = 'rgba(255,255,255,0.07)'; c.fillRect(px + 2, py + 1, s - 4, 1); c.fillRect(px + 1, py + 2, 1, s - 4);
        c.fillStyle = 'rgba(0,0,0,0.35)'; c.fillRect(px + 2, py + s - 2, s - 4, 1); c.fillRect(px + s - 2, py + 2, 1, s - 4);
        if (v < 0.12) { c.fillStyle = '#0c0e16'; for (let i = 0; i < 3; i++) { rr(c, px + s * 0.28, py + s * (0.36 + i * 0.12), s * 0.44, Math.max(1.5, s * 0.045), 2); c.fill(); } }
        else if (v < 0.24) { c.fillStyle = 'rgba(255,255,255,0.09)'; [[0.14, 0.14], [0.86, 0.14], [0.14, 0.86], [0.86, 0.86]].forEach(([a, b]) => { circle(c, px + s * a, py + s * b, Math.max(0.8, s * 0.022)); c.fill(); }); }
        else if (v < 0.29) { c.save(); glow(c, g, '#9184d9', s * 0.15); c.fillStyle = '#b5abfc'; circle(c, px + s * 0.82, py + s * 0.18, Math.max(1, s * 0.022)); c.fill(); c.restore(); }
      }
    },
    goal(c, g, cx, cy, lit) {
      const s = g.s;
      c.save(); c.globalCompositeOperation = 'lighter';
      c.fillStyle = rad(c, cx, cy, s * 0.42, [[0, `rgba(111,224,196,${lit ? 0.4 : 0.16})`], [1, 'rgba(111,224,196,0)']]); c.fillRect(cx - s / 2, cy - s / 2, s, s); c.restore();
      c.save(); glow(c, g, 'rgba(111,224,196,0.9)', s * 0.18);
      c.strokeStyle = 'rgba(111,224,196,0.85)'; c.lineWidth = Math.max(1.2, s * 0.025); circle(c, cx, cy, s * 0.2); c.stroke();
      c.fillStyle = '#9ff0dc'; circle(c, cx, cy, Math.max(1.2, s * 0.035)); c.fill();
      if (g.lod >= 1) { c.strokeStyle = 'rgba(111,224,196,0.35)'; c.lineWidth = 1; [[0, -1], [1, 0], [0, 1], [-1, 0]].forEach(([a, b]) => { c.beginPath(); c.moveTo(cx + a * s * 0.24, cy + b * s * 0.24); c.lineTo(cx + a * s * 0.3, cy + b * s * 0.3); c.stroke(); }); }
      c.restore();
    },
    shadows(c, g, m) { castShadow(c, g, shadowPath(m, g, g.hw, g.s * 0.12, g.s * 0.2), 'rgba(0,0,0,0.7)', g.s * 0.3, 0, g.s * 0.14); ao(c, g, m, 'rgba(0,0,0,0.4)', 0.22); },
    wall(c, g, px, py, x, y, m, front) {
      const s = g.s, h = g.hw, top = py - h;
      if (front) {
        c.fillStyle = lin(c, 0, py + s - h, 0, py + s, [[0, '#161927'], [1, '#0c0e17']]); c.fillRect(px, py + s - h, s, h);
        c.fillStyle = 'rgba(255,255,255,0.08)'; c.fillRect(px, py + s - h, s, 1);
        c.save(); glow(c, g, '#9184d9', s * 0.2); c.fillStyle = 'rgba(181,171,252,0.75)'; c.fillRect(px + (m.isWall(x - 1, y) ? 0 : s * 0.08), py + s - Math.max(2.5, h * 0.22), s - (m.isWall(x - 1, y) ? 0 : s * 0.08) - (m.isWall(x + 1, y) ? 0 : s * 0.08), Math.max(1, s * 0.022)); c.restore();
      }
      c.fillStyle = lin(c, px, top, px + s * 0.4, top + s, [[0, '#353c58'], [1, '#232739']]); c.fillRect(px, top, s, s);
      if (g.lod >= 1) {
        c.fillStyle = 'rgba(255,255,255,0.035)'; c.beginPath(); c.moveTo(px, top + s * 0.55); c.lineTo(px + s * 0.55, top); c.lineTo(px + s * 0.8, top); c.lineTo(px, top + s * 0.8); c.fill();
        c.fillStyle = 'rgba(0,0,0,0.45)'; if (m.isWall(x + 1, y)) c.fillRect(px + s - 0.5, top, 1, s); if (m.isWall(x, y + 1)) c.fillRect(px, top + s - 0.5, s, 1);
      }
      const N = !m.isWall(x, y - 1), Wd = !m.isWall(x - 1, y), E = !m.isWall(x + 1, y), S = !m.isWall(x, y + 1);
      c.fillStyle = 'rgba(181,171,252,0.6)'; if (N) c.fillRect(px, top, s, 1.5);
      c.fillStyle = 'rgba(181,171,252,0.38)'; if (Wd) c.fillRect(px, top, 1.5, s);
      c.fillStyle = 'rgba(181,171,252,0.22)'; if (E) c.fillRect(px + s - 1.5, top, 1.5, s); if (S) c.fillRect(px, top + s - 1.5, s, 1.5);
    },
    box(c, g, px, py, x, y, on) {
      const s = g.s, b = s * 0.12, d = s - 2 * b, h = s * 0.2, x0 = px + b, y0 = py + b - h + s * 0.03, R = s * 0.08;
      rr(c, x0, y0 + d - R, d, h + R, [0, 0, R, R]); c.fillStyle = lin(c, 0, y0 + d, 0, y0 + d + h, [[0, '#40455a'], [1, '#252836']]); c.fill();
      const lc = on ? '#6fe0c4' : '#e2a44c';
      c.save(); glow(c, g, lc, s * 0.22); c.fillStyle = lc; rr(c, x0 + d * 0.32, y0 + d + h * 0.38, d * 0.36, Math.max(2, s * 0.045), 2); c.fill(); c.restore();
      rr(c, x0, y0, d, d, R); c.fillStyle = lin(c, x0, y0, x0 + d * 0.6, y0 + d, [[0, '#949ab0'], [1, '#5a5f74']]); c.fill();
      c.fillStyle = 'rgba(255,255,255,0.3)'; c.fillRect(x0 + R, y0, d - 2 * R, 1); c.fillRect(x0, y0 + R, 1, d - 2 * R);
      c.fillStyle = '#4a4f63'; const k = d * 0.13;[[0, 0], [1, 0], [0, 1], [1, 1]].forEach(([a, q]) => { rr(c, x0 + a * (d - k) + (a ? -1 : 1) * 1.5, y0 + q * (d - k) + (q ? -1 : 1) * 1.5, k, k, 1.5); c.fill(); });
      const p = d * 0.24; rr(c, x0 + p, y0 + p, d - 2 * p, d - 2 * p, s * 0.04); c.fillStyle = on ? '#1d2a2c' : '#3e4255'; c.fill();
      c.strokeStyle = 'rgba(255,255,255,0.14)'; c.lineWidth = 1; c.stroke();
      const cx = x0 + d / 2, cy = y0 + d / 2;
      if (on) {
        c.save(); glow(c, g, '#6fe0c4', s * 0.2); c.strokeStyle = '#8ff0d6'; c.lineWidth = Math.max(1.4, s * 0.035); c.lineCap = 'round'; c.lineJoin = 'round';
        c.beginPath(); c.moveTo(cx - d * 0.13, cy + d * 0.01); c.lineTo(cx - d * 0.03, cy + d * 0.1); c.lineTo(cx + d * 0.14, cy - d * 0.09); c.stroke(); c.restore();
      } else { c.fillStyle = 'rgba(0,0,0,0.35)'; c.fillRect(cx - d * 0.14, cy - d * 0.05, d * 0.28, Math.max(1, s * 0.02)); c.fillRect(cx - d * 0.14, cy + d * 0.04, d * 0.28, Math.max(1, s * 0.02)); }
    },
    robot(c, g, px, py, t, facing) {
      const s = g.s, cx = px + s / 2, bob = Math.sin(t * 2.2) * s * 0.018, base = py + s * 0.84;
      const [fx, fy] = DIRV[facing] || [0, 0];
      c.save(); c.globalCompositeOperation = 'lighter'; c.translate(cx, base); c.scale(1, 0.35); c.fillStyle = rad(c, 0, 0, s * 0.5, [[0, 'rgba(145,132,217,0.35)'], [1, 'rgba(145,132,217,0)']]); circle(c, 0, 0, s * 0.5); c.fill(); c.restore();
      c.save(); c.translate(cx, base); c.scale(1, 0.28); c.fillStyle = rad(c, 0, 0, s * 0.32, [[0, 'rgba(0,0,0,0.7)'], [1, 'rgba(0,0,0,0)']]); circle(c, 0, 0, s * 0.32); c.fill(); c.restore();
      c.save(); c.translate(cx, base + bob);
      for (const side of [-1, 1]) {
        rr(c, side * s * 0.17 - s * 0.065, -s * 0.17, s * 0.13, s * 0.18, s * 0.04); c.fillStyle = '#1a1c27'; c.fill();
        if (g.lod >= 1) { c.fillStyle = 'rgba(255,255,255,0.08)'; for (let i = 0; i < 4; i++) c.fillRect(side * s * 0.17 - s * 0.055, -s * 0.15 + i * s * 0.04, s * 0.11, 1); }
      }
      c.strokeStyle = '#8f93a6'; c.lineWidth = Math.max(1.2, s * 0.03); c.lineCap = 'round';
      for (const side of [-1, 1]) { c.beginPath(); c.moveTo(side * s * 0.22, -s * 0.3); c.lineTo(side * s * 0.31, -s * 0.22); c.lineTo(side * s * 0.29, -s * 0.13); c.stroke(); c.fillStyle = '#c9ccd8'; circle(c, side * s * 0.29, -s * 0.12, s * 0.025); c.fill(); }
      rr(c, -s * 0.23, -s * 0.42, s * 0.46, s * 0.27, s * 0.08); c.fillStyle = lin(c, -s * 0.23, -s * 0.42, s * 0.23, -s * 0.15, [[0, '#eef0f6'], [0.6, '#b8bccb'], [1, '#7d8196']]); c.fill();
      c.fillStyle = '#2a2d3c'; rr(c, -s * 0.1, -s * 0.3, s * 0.2, s * 0.05, 2); c.fill();
      c.save(); glow(c, g, '#9184d9', s * 0.12); c.fillStyle = '#b5abfc'; rr(c, -s * 0.06, -s * 0.287, s * 0.12 * (0.5 + 0.5 * Math.sin(t * 3)), s * 0.024, 1); c.fill(); c.restore();
      c.fillStyle = '#5c6075'; c.fillRect(-s * 0.04, -s * 0.47, s * 0.08, s * 0.06);
      const hy = -s * 0.74;
      rr(c, -s * 0.21, hy, s * 0.42, s * 0.29, s * 0.13); c.fillStyle = lin(c, -s * 0.21, hy, s * 0.21, hy + s * 0.29, [[0, '#f4f5fa'], [0.55, '#c3c6d3'], [1, '#868aa0']]); c.fill();
      rr(c, -s * 0.16, hy + s * 0.07, s * 0.32, s * 0.15, s * 0.07); c.fillStyle = '#0b0c14'; c.fill();
      const bl = blink(t, 3.2, 1.3), ex = fx * s * 0.035, ey = hy + s * 0.145 + fy * s * 0.012;
      c.save(); glow(c, g, '#9184d9', s * 0.3); c.fillStyle = '#d8d2ff';
      for (const side of [-1, 1]) { const eh = s * 0.085 * (1 - bl * 0.85); rr(c, side * s * 0.065 - s * 0.028 + ex, ey - eh / 2, s * 0.056, eh, s * 0.028); c.fill(); }
      c.restore();
      c.fillStyle = 'rgba(255,255,255,0.65)'; ell(c, -s * 0.09, hy + s * 0.045, s * 0.07, s * 0.022, -0.2); c.fill();
      c.strokeStyle = '#8f93a6'; c.lineWidth = Math.max(1, s * 0.02); c.beginPath(); c.moveTo(s * 0.1, hy + s * 0.02); c.lineTo(s * 0.14, hy - s * 0.1); c.stroke();
      const ap = 0.5 + 0.5 * Math.sin(t * 2.6);
      c.save(); glow(c, g, '#9184d9', s * 0.25 * ap); c.fillStyle = `rgba(200,192,255,${0.5 + 0.5 * ap})`; circle(c, s * 0.14, hy - s * 0.11, Math.max(1.2, s * 0.03)); c.fill(); c.restore();
      c.restore();
    },
    dyn(c, g, m, t) {
      const s = g.s;
      for (const q of m.goals) {
        const cx = g.ox + q.x * s + s / 2, cy = g.oy + q.y * s + s / 2;
        if (q.lit) {
          c.save(); c.globalCompositeOperation = 'lighter';
          c.fillStyle = lin(c, 0, cy, 0, cy - s * 1.1, [[0, `rgba(111,224,196,${0.16 + 0.06 * Math.sin(t * 2.4 + q.x)})`], [1, 'rgba(111,224,196,0)']]);
          c.fillRect(cx - s * 0.3, cy - s * 1.1, s * 0.6, s * 1.1); c.restore();
        } else {
          c.save(); c.setLineDash([s * 0.07, s * 0.05]); c.lineDashOffset = -t * s * 0.25; c.strokeStyle = 'rgba(111,224,196,0.55)'; c.lineWidth = Math.max(1, s * 0.02);
          circle(c, cx, cy, s * 0.29); c.stroke(); c.restore();
        }
      }
    },
    post(c, g, t) {
      const bh = g.by1 - g.by0 + g.s * 3, y = g.by0 - g.s * 1.5 + ((t * 38) % bh);
      c.save(); c.globalCompositeOperation = 'lighter';
      c.fillStyle = lin(c, 0, y - 50, 0, y + 50, [[0, 'rgba(181,171,252,0)'], [0.5, 'rgba(181,171,252,0.05)'], [1, 'rgba(181,171,252,0)']]);
      c.fillRect(g.bx0 - g.s * 0.5, y - 50, g.bx1 - g.bx0 + g.s, 100); c.restore();
      if (g.lod >= 1) motes(c, g, t, 34, '#c9c1ff', 1, 0.35, 9);
      vignette(c, g, 'rgba(4,5,10,0.95)', 0.8);
    }
  };

  // ════════════════ C · TABLETOP DIORAMA ════════════════
  const diorama = {
    hw: 0.5, margin: 0.5, thick: 0.45,
    mini: { floor: '#6f9a55', grid: '#5e8848', wallTop: '#4c8040', wallFront: '#2c4a25', goal: '#ddd5c5', goalLit: '#b5abfc', box: '#cf955a', boxFront: '#8a5a30', mark: '#b5abfc', robot: '#a99ef0', eye: '#2a2540' },
    bg(c, g) {
      const cx = (g.bx0 + g.bx1) / 2, cy = (g.by0 + g.by1) / 2;
      c.fillStyle = rad(c, cx - g.s, cy - g.s * 1.5, Math.max(g.W, g.H) * 0.8, [[0, '#3a3540'], [0.4, '#22212d'], [1, '#101119']]); c.fillRect(0, 0, g.W, g.H);
      c.strokeStyle = 'rgba(255,230,200,0.018)'; c.lineWidth = 1;
      for (let y = 0; y < g.H; y += 7) { c.beginPath(); c.moveTo(0, y); for (let x = 0; x <= g.W; x += 80) c.lineTo(x, y + Math.sin(x * 0.01 + y * 0.3) * 2.5); c.stroke(); }
    },
    frame(c, g) {
      const s = g.s, mg = s * this.margin, d = s * this.thick, x0 = g.bx0 - mg, y0 = g.by0 - mg - g.hw, x1 = g.bx1 + mg, y1 = g.by1 + mg, R = s * 0.14;
      castShadow(c, g, k => k.roundRect(x0, y0, x1 - x0, y1 - y0 + d, R), 'rgba(0,0,0,0.7)', s * 1.1, s * 0.4, s * 0.55);
      rr(c, x0, y1 - R, x1 - x0, d + R, [0, 0, R, R]); c.fillStyle = lin(c, 0, y1, 0, y1 + d, [[0, '#6f4629'], [1, '#432914']]); c.fill();
      c.strokeStyle = 'rgba(30,15,5,0.35)'; c.lineWidth = 1;
      for (let i = 1; i < 4; i++) { c.beginPath(); const yy = y1 + d * i / 4; c.moveTo(x0 + 2, yy); for (let x = x0; x < x1; x += 30) c.lineTo(x, yy + Math.sin(x * 0.05 + i) * 1.2); c.stroke(); }
      rr(c, x0, y0, x1 - x0, y1 - y0, R); c.fillStyle = lin(c, x0, y0, x1, y1, [[0, '#a8744b'], [1, '#7a4c2c']]); c.fill();
      c.strokeStyle = 'rgba(255,225,190,0.25)'; c.beginPath(); c.moveTo(x0 + R, y0 + 1); c.lineTo(x1 - R, y0 + 1); c.stroke();
      const k = s * 0.16; rr(c, x0 + k, y0 + k, x1 - x0 - 2 * k, y1 - y0 - 2 * k, R * 0.6); c.fillStyle = '#3b2d23'; c.fill();
      c.save(); c.clip(); speckle(c, x0 + k, y0 + k, x1 - x0 - 2 * k, y1 - y0 - 2 * k, Math.round((x1 - x0) * (y1 - y0) / 90), 5, ['rgba(160,130,100,0.25)', 'rgba(0,0,0,0.25)', 'rgba(120,150,90,0.18)'], 1, 3);
      c.fillStyle = lin(c, 0, y0 + k, 0, y0 + k + s * 0.4, [[0, 'rgba(0,0,0,0.45)'], [1, 'rgba(0,0,0,0)']]); c.fillRect(x0, y0 + k, x1 - x0, s * 0.4); c.restore();
    },
    floor(c, g, px, py, x, y, m) {
      const s = g.s, r = hash(x, y, 1), chk = ((x + y) & 1) ? 2.5 : 0;
      c.fillStyle = `hsl(${95 + r * 12},${36 + r * 6}%,${37 + chk + r * 5}%)`; c.fillRect(px, py, s, s);
      if (g.lod >= 1) {
        const n = g.lod > 1 ? 22 : 9;
        for (const [col, k] of [['rgba(28,55,18,0.4)', 7], ['rgba(210,245,160,0.28)', 8]]) {
          c.strokeStyle = col; c.lineWidth = Math.max(0.8, s * 0.016); c.beginPath();
          for (let i = 0; i < n; i++) { const bx = px + hash(x * 31 + i, y, k) * s, by = py + s * 0.08 + hash(x, y * 17 + i, k + 1) * s * 0.9, l = s * (0.05 + 0.06 * hash(i, x, y + k)); c.moveTo(bx, by); c.lineTo(bx + (hash(i, y, x) - 0.5) * l * 0.7, by - l); }
          c.stroke();
        }
        if (hash(x, y, 9) < 0.2) { const cols = ['#f4f1e6', '#f6d36b', '#c9c1ff']; for (let i = 0; i < 3; i++) { c.fillStyle = cols[i]; circle(c, px + s * (0.2 + 0.6 * hash(x, y, 90 + i)), py + s * (0.2 + 0.6 * hash(x, y, 95 + i)), Math.max(0.9, s * 0.022)); c.fill(); } }
        if (hash(x, y, 10) < 0.08) { c.fillStyle = 'rgba(110,80,50,0.35)'; ell(c, px + s * 0.5, py + s * 0.6, s * 0.2, s * 0.1); c.fill(); }
      }
      c.fillStyle = 'rgba(20,45,12,0.2)';
      if (m.inside(x + 1, y)) c.fillRect(px + s - 0.5, py, 1, s);
      if (m.inside(x, y + 1)) c.fillRect(px, py + s - 0.5, s, 1);
    },
    goal(c, g, cx, cy, lit) {
      const s = g.s, R = s * 0.33;
      c.fillStyle = '#8c8372'; circle(c, cx, cy + s * 0.04, R); c.fill();
      c.fillStyle = rad(c, cx - R * 0.3, cy - R * 0.3, R * 1.4, [[0, '#efe9dc'], [1, '#b8ad98']]); circle(c, cx, cy, R); c.fill();
      c.save(); if (lit) glow(c, g, '#9184d9', s * 0.2);
      c.fillStyle = lit ? '#d2cefd' : '#9184d9';
      for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU; circle(c, cx + Math.cos(a) * R * 0.68, cy + Math.sin(a) * R * 0.68, Math.max(1, s * 0.03)); c.fill(); }
      circle(c, cx, cy, Math.max(1.4, s * 0.05)); c.fill(); c.restore();
      if (lit && g.lod >= 1) {
        const cols = ['#f2a7c3', '#f6d36b', '#c9c1ff', '#f4f1e6'];
        for (let i = 0; i < 9; i++) {
          const a = (i / 9) * TAU + 0.3, fx = cx + Math.cos(a) * R * 1.22, fy = cy + Math.sin(a) * R * 1.12, pr = Math.max(1, s * 0.03);
          c.fillStyle = cols[i % 4]; for (let p = 0; p < 5; p++) { const b = (p / 5) * TAU; circle(c, fx + Math.cos(b) * pr, fy + Math.sin(b) * pr, pr * 0.8); c.fill(); }
          c.fillStyle = '#f6d36b'; circle(c, fx, fy, pr * 0.6); c.fill();
        }
      }
    },
    shadows(c, g, m) { castShadow(c, g, shadowPath(m, g, g.hw * 0.6, g.s * 0.13, g.s * 0.3), 'rgba(12,30,8,0.6)', g.s * 0.3, g.s * 0.28, g.s * 0.3); ao(c, g, m, 'rgba(10,25,6,0.3)', 0.25); },
    wall(c, g, px, py, x, y, m, front) {
      const s = g.s, h = g.hw, top = py - h;
      const N = !m.isWall(x, y - 1), Wd = !m.isWall(x - 1, y), E = !m.isWall(x + 1, y), S = !m.isWall(x, y + 1), Rr = s * 0.2;
      const rad4 = [N && Wd ? Rr : 0, N && E ? Rr : 0, S && E ? Rr : 0, S && Wd ? Rr : 0];
      if (front) {
        rr(c, px, py + s - h - Rr, s, h + Rr, [0, 0, rad4[2], rad4[3]]); c.fillStyle = lin(c, 0, py + s - h, 0, py + s, [[0, '#365e2d'], [1, '#1f3a1a']]); c.fill();
        if (g.lod >= 1) speckle(c, px, py + s - h, s, h, g.lod > 1 ? 26 : 10, x * 17 + y * 3, ['rgba(120,180,90,0.25)', 'rgba(10,30,8,0.35)'], 1, 2.5);
      }
      rr(c, px, top, s, s, rad4); c.fillStyle = lin(c, px, top, px + s, top + s, [[0, '#5d9a4b'], [1, '#3e6f35']]); c.fill();
      if (g.lod >= 1) {
        c.save(); const ex = s * 0.14;
        rr(c, px - (Wd ? 0 : ex), top - (N ? 0 : ex), s + (Wd ? 0 : ex) + (E ? 0 : ex), s + (N ? 0 : ex) + (S ? 0 : ex), rad4); c.clip();
        const cols = ['#4a8540', '#6aa957', '#3d7036', '#5b9a49', '#78b862'];
        for (let i = 0; i < (g.lod > 1 ? 8 : 5); i++) {
          const qx = px + s * (0.1 + 0.8 * hash(x, y, 70 + i)), qy = top + s * (0.1 + 0.8 * hash(x, y, 80 + i)), qr = s * (0.12 + 0.09 * hash(x, y, 90 + i));
          c.fillStyle = cols[i % cols.length]; circle(c, qx, qy, qr); c.fill();
          c.fillStyle = 'rgba(230,255,190,0.16)'; circle(c, qx - qr * 0.3, qy - qr * 0.35, qr * 0.5); c.fill();
        }
        if (g.lod > 1) speckle(c, px, top, s, s, 18, x * 7 + y * 131, ['rgba(220,255,180,0.3)', 'rgba(15,40,10,0.35)'], 1, 2);
        c.restore();
      }
      c.save(); rr(c, px, top, s, s, rad4); c.clip(); c.lineWidth = Math.max(1.5, s * 0.05);
      c.strokeStyle = 'rgba(235,255,200,0.25)'; c.beginPath(); if (N) { c.moveTo(px, top + 1); c.lineTo(px + s, top + 1); } if (Wd) { c.moveTo(px + 1, top); c.lineTo(px + 1, top + s); } c.stroke();
      c.strokeStyle = 'rgba(10,30,8,0.3)'; c.beginPath(); if (S) { c.moveTo(px, top + s - 1); c.lineTo(px + s, top + s - 1); } if (E) { c.moveTo(px + s - 1, top); c.lineTo(px + s - 1, top + s); } c.stroke();
      c.restore();
    },
    box(c, g, px, py, x, y, on) {
      const s = g.s, b = s * 0.13, d = s - 2 * b, h = s * 0.36, x0 = px + b, y0 = py + b - h + s * 0.04;
      c.fillStyle = lin(c, 0, y0 + d, 0, y0 + d + h, [[0, '#a8713f'], [1, '#77491f']]); c.fillRect(x0, y0 + d, d, h);
      if (g.lod >= 1) {
        c.fillStyle = 'rgba(60,32,10,0.45)'; c.fillRect(x0, y0 + d + h * 0.5, d, 1);
        c.strokeStyle = '#8c5a2c'; c.lineWidth = Math.max(1.5, s * 0.05); c.beginPath(); c.moveTo(x0 + 2, y0 + d + h - 2); c.lineTo(x0 + d - 2, y0 + d + 2); c.stroke();
        c.strokeStyle = 'rgba(50,25,8,0.6)'; c.lineWidth = 1; c.strokeRect(x0 + 0.5, y0 + d + 0.5, d - 1, h - 1);
      }
      c.fillStyle = lin(c, x0, y0, x0 + d, y0 + d, [[0, '#e2ad6e'], [1, '#bb844a']]); c.fillRect(x0, y0, d, d);
      if (g.lod >= 1) {
        c.fillStyle = 'rgba(95,55,22,0.35)'; for (let i = 1; i < 4; i++) c.fillRect(x0 + d * i / 4, y0 + d * 0.1, 1, d * 0.8);
        c.strokeStyle = 'rgba(95,55,22,0.6)'; c.lineWidth = Math.max(1, s * 0.03); c.strokeRect(x0 + d * 0.06, y0 + d * 0.06, d * 0.88, d * 0.88);
        c.fillStyle = 'rgba(50,28,10,0.7)';[[0.12, 0.12], [0.88, 0.12], [0.12, 0.88], [0.88, 0.88]].forEach(([a, q]) => { circle(c, x0 + d * a, y0 + d * q, Math.max(0.8, s * 0.016)); c.fill(); });
      }
      c.fillStyle = 'rgba(255,240,210,0.4)'; c.fillRect(x0, y0, d, 1);
      if (on) {
        const fx = x0 + d * 0.72, ft = y0 - s * 0.36, fb = y0 + d * 0.4;
        c.strokeStyle = '#efe7d4'; c.lineWidth = Math.max(1.2, s * 0.028); c.lineCap = 'round'; c.beginPath(); c.moveTo(fx, fb); c.lineTo(fx, ft); c.stroke();
        c.fillStyle = '#b5abfc'; c.beginPath(); c.moveTo(fx, ft); c.lineTo(fx + s * 0.25, ft + s * 0.08); c.lineTo(fx, ft + s * 0.16); c.closePath(); c.fill();
        c.fillStyle = 'rgba(80,60,160,0.35)'; c.beginPath(); c.moveTo(fx, ft + s * 0.08); c.lineTo(fx + s * 0.25, ft + s * 0.08); c.lineTo(fx, ft + s * 0.16); c.closePath(); c.fill();
      }
    },
    robot(c, g, px, py, t, facing) {
      const s = g.s, cx = px + s / 2, base = py + s * 0.86, bob = Math.abs(Math.sin(t * 2.4)) * s * -0.015;
      const [fx, fy] = DIRV[facing] || [0, 0];
      c.save(); c.translate(cx + s * 0.14, base + s * 0.04); c.scale(1, 0.34); c.fillStyle = rad(c, 0, 0, s * 0.36, [[0, 'rgba(12,30,8,0.55)'], [1, 'rgba(12,30,8,0)']]); circle(c, 0, 0, s * 0.36); c.fill(); c.restore();
      c.fillStyle = '#bfb39a'; ell(c, cx, base, s * 0.25, s * 0.085); c.fill();
      c.fillRect(cx - s * 0.25, base - s * 0.045, s * 0.5, s * 0.045);
      c.fillStyle = lin(c, cx - s * 0.25, 0, cx + s * 0.25, 0, [[0, '#f6f0e2'], [1, '#d8ccb2']]); ell(c, cx, base - s * 0.045, s * 0.25, s * 0.085); c.fill();
      c.save(); c.translate(cx, base - s * 0.05 + bob);
      c.fillStyle = '#5d51a3'; rr(c, -s * 0.12, -s * 0.16, s * 0.09, s * 0.13, s * 0.03); c.fill(); rr(c, s * 0.03, -s * 0.16, s * 0.09, s * 0.13, s * 0.03); c.fill();
      const kx = s * 0.22, ky = -s * 0.31, rot = Math.cos(t * 3.2);
      c.fillStyle = '#9c7430'; c.fillRect(kx - s * 0.02, ky - s * 0.015, s * 0.08, s * 0.03);
      c.fillStyle = lin(c, kx, ky - s * 0.07, kx, ky + s * 0.07, [[0, '#f0cc6a'], [1, '#b8892e']]);
      ell(c, kx + s * 0.08, ky - s * 0.04, Math.max(0.6, s * 0.045 * Math.abs(rot)), s * 0.045); c.fill();
      ell(c, kx + s * 0.08, ky + s * 0.04, Math.max(0.6, s * 0.045 * Math.abs(rot)), s * 0.045); c.fill();
      for (const side of [-1, 1]) { rr(c, side * s * 0.255 - s * 0.04, -s * 0.42, s * 0.08, s * 0.2, s * 0.04); c.fillStyle = '#7f72cf'; c.fill(); }
      rr(c, -s * 0.2, -s * 0.45, s * 0.4, s * 0.31, s * 0.08); c.fillStyle = lin(c, -s * 0.2, -s * 0.45, s * 0.2, -s * 0.14, [[0, '#cfc7ff'], [0.55, '#9a8de6'], [1, '#6c5fb8']]); c.fill();
      rr(c, -s * 0.1, -s * 0.37, s * 0.2, s * 0.12, s * 0.03); c.fillStyle = '#efe7d4'; c.fill();
      c.fillStyle = '#e0675a'; circle(c, -s * 0.045, -s * 0.31, s * 0.022); c.fill(); c.fillStyle = '#f2c14e'; circle(c, s * 0.045, -s * 0.31, s * 0.022); c.fill();
      c.fillStyle = 'rgba(255,255,255,0.5)'; rr(c, -s * 0.16, -s * 0.43, s * 0.1, s * 0.035, s * 0.017); c.fill();
      c.fillStyle = '#6c5fb8'; c.fillRect(-s * 0.05, -s * 0.5, s * 0.1, s * 0.06);
      const hy = -s * 0.77;
      if (g.lod >= 1) { c.strokeStyle = '#6c5fb8'; c.lineWidth = Math.max(1, s * 0.02); c.beginPath(); c.moveTo(0, hy); c.lineTo(0, hy - s * 0.07); c.stroke(); c.fillStyle = '#e0675a'; circle(c, 0, hy - s * 0.08, Math.max(1.2, s * 0.03)); c.fill(); }
      rr(c, -s * 0.18, hy, s * 0.36, s * 0.28, s * 0.11); c.fillStyle = lin(c, -s * 0.18, hy, s * 0.18, hy + s * 0.28, [[0, '#d6cfff'], [0.6, '#9a8de6'], [1, '#6c5fb8']]); c.fill();
      const ex = fx * s * 0.03, ey = fy * s * 0.012;
      rr(c, -s * 0.125 + ex, hy + s * 0.06 + ey, s * 0.25, s * 0.17, s * 0.06); c.fillStyle = '#f3ecdc'; c.fill();
      const bl = blink(t, 4.1, 2.1);
      c.fillStyle = '#2a2540'; for (const side of [-1, 1]) { ell(c, side * s * 0.055 + ex * 1.5, hy + s * 0.13 + ey, s * 0.024, s * 0.03 * (1 - bl * 0.85)); c.fill(); }
      if (g.lod >= 1) { c.fillStyle = 'rgba(240,140,160,0.55)'; circle(c, -s * 0.09 + ex, hy + s * 0.18 + ey, s * 0.02); c.fill(); circle(c, s * 0.09 + ex, hy + s * 0.18 + ey, s * 0.02); c.fill(); }
      c.fillStyle = 'rgba(255,255,255,0.55)'; ell(c, -s * 0.08, hy + s * 0.04, s * 0.06, s * 0.022, -0.3); c.fill();
      c.restore();
    },
    dyn(c, g, m, t) {
      c.save(); c.globalCompositeOperation = 'lighter';
      for (const q of m.goals) if (q.lit) {
        const cx = g.ox + q.x * g.s + g.s / 2, cy = g.oy + q.y * g.s + g.s / 2, a = 0.08 + 0.05 * Math.sin(t * 2 + q.y);
        c.fillStyle = rad(c, cx, cy, g.s * 0.7, [[0, `rgba(181,171,252,${a})`], [1, 'rgba(181,171,252,0)']]); c.fillRect(cx - g.s, cy - g.s, g.s * 2, g.s * 2);
      }
      c.restore();
    },
    post(c, g, t) {
      c.save(); c.globalCompositeOperation = 'screen';
      c.fillStyle = rad(c, g.bx0, g.by0 - g.s * 2, (g.bx1 - g.bx0) * 1.3, [[0, 'rgba(255,236,200,0.10)'], [1, 'rgba(255,236,200,0)']]); c.fillRect(0, 0, g.W, g.H);
      c.restore();
      if (g.lod >= 1) motes(c, g, t, 30, '#fff1c8', 0.8, 0.45, 5);
      vignette(c, g, 'rgba(5,5,10,0.95)', 0.7);
    }
  };

  const DIRS = { clay, lab, diorama };

  // ── <golem-scene> ──
  const KEYS = ['direction', 'map', 'inset', 'facing', 'cellmax', 'still', 'pose', 'fx', 'focus', 'fog', 'phase', 'bare', 'floor'];
  const truthy = (v) => v === true || v === '' || v === 'true' || v === '1';
  class GolemScene extends HTMLElement {
    static get observedAttributes() { return KEYS; }
    constructor() { super(); this._p = {}; this._c = document.createElement('canvas'); this._c.style.cssText = 'display:block;width:100%;height:100%'; this._t0 = performance.now() - Math.random() * 4000; }
    _g(k) { return this._p[k] !== undefined ? this._p[k] : this.getAttribute(k); }
    connectedCallback() {
      if (!this._c.isConnected) this.appendChild(this._c);
      this.style.display = 'block'; if (!this.style.width) this.style.width = '100%'; if (!this.style.height) this.style.height = '100%';
      this._ro = new ResizeObserver(() => this._build()); this._ro.observe(this);
      this._io = new IntersectionObserver((e) => { this._vis = e[0].isIntersecting; this._loop(); }); this._io.observe(this);
      this._tries = 0; this._build();
      requestAnimationFrame(() => this._build());
    }
    _retry() { if ((this._tries = (this._tries || 0) + 1) <= 60) requestAnimationFrame(() => this._build()); }
    disconnectedCallback() { this._ro && this._ro.disconnect(); this._io && this._io.disconnect(); cancelAnimationFrame(this._raf); this._raf = 0; }
    attributeChangedCallback() { this._build(); }
    _build() {
      if (!this.isConnected) return;
      const w = this.clientWidth, h = this.clientHeight; if (!w || !h) return this._retry();
      const D = DIRS[this._g('direction')] || clay, m = model(this._g('map'), this._g('floor'));
      if (!m.H) return this._retry();
      const bare = truthy(this._g('bare')), MG = bare ? 0.2 : D.margin, TH = bare ? 0 : D.thick;
      this._tries = 0;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const [it, ir, ib, il] = String(this._g('inset') || '0 0 0 0').split(/\s+/).map(Number);
      const aw = w - (il || 0) - (ir || 0), ah = h - (it || 0) - (ib || 0);
      const s = clamp(Math.floor(Math.min(aw / (m.W + 2 * MG), ah / (m.H + 2 * MG + D.hw + TH))), bare ? 8 : 20, Number(this._g('cellmax')) || 64);
      const ox = Math.round((il || 0) + (aw - m.W * s) / 2), oy = Math.round((it || 0) + (ah - m.H * s) / 2 + (D.hw - TH) * s / 2);
      const g = { s, ox, oy, bx0: ox, by0: oy, bx1: ox + m.W * s, by1: oy + m.H * s, W: w, H: h, dpr, bare, hw: D.hw * s, lod: s >= 40 ? 2 : s >= 26 ? 1 : 0 };
      const c = this._c; c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
      const st = this._st || (this._st = document.createElement('canvas')); st.width = c.width; st.height = c.height;
      const k = st.getContext('2d'); k.setTransform(dpr, 0, 0, dpr, 0, 0); k.clearRect(0, 0, w, h);
      if (!bare) { D.bg(k, g); D.frame(k, g, m); }
      for (let y = 0; y < m.H; y++) for (let x = 0; x < m.W; x++) if (m.inside(x, y)) D.floor(k, g, ox + x * s, oy + y * s, x, y, m);
      for (const q of m.goals) D.goal(k, g, ox + q.x * s + s / 2, oy + q.y * s + s / 2, q.lit);
      D.shadows(k, g, m);
      for (let y = 0; y < m.H; y++) for (let x = 0; x < m.W; x++) {
        const px = ox + x * s, py = oy + y * s;
        if (m.isWall(x, y)) D.wall(k, g, px, py, x, y, m, !m.isWall(x, y + 1));
        else { const b = m.boxAt(x, y); if (b) D.box(k, g, px, py, x, y, b.on); }
      }
      this._D = D; this._m = m; this._geo = g;
      this._paint(); this._loop();
    }
    _paint() {
      const D = this._D, m = this._m, g = this._geo; if (!D) return;
      const c = this._c.getContext('2d'), t = this._still() ? 1.2 : (performance.now() - this._t0) / 1000;
      c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(this._st, 0, 0);
      c.setTransform(g.dpr, 0, 0, g.dpr, 0, 0);
      const f = String(this._g('focus') || '').split(',').map(Number);
      const o = { pose: this._g('pose') || 'idle', fx: this._g('fx') || '', dir: this._g('facing') || 'S', focus: f.length === 2 && !isNaN(f[0]) ? f : null, fog: this._g('fog') || '',
        p: this._still() ? Number(this._g('phase') ?? 0.5) : Math.min(1, (t % 1.8) / 1.1) };
      D.dyn(c, g, m, t, o);
      const r = m.robot;
      if (r) {
        D.robot(c, g, g.ox + r.x * g.s, g.oy + r.y * g.s, t, this._g('facing') || 'S', o);
        const y = r.y + 1;
        for (let x = r.x - 1; x <= r.x + 1; x++) {
          const px = g.ox + x * g.s, py = g.oy + y * g.s;
          if (m.isWall(x, y)) D.wall(c, g, px, py, x, y, m, !m.isWall(x, y + 1));
          else { const b = m.boxAt(x, y); if (b) D.box(c, g, px, py, x, y, b.on); }
        }
      }
      if (D.over) D.over(c, g, m, t, o);
      if (!g.bare) D.post(c, g, t, o);
    }
    _still() { return truthy(this._g('still')) || matchMedia('(prefers-reduced-motion: reduce)').matches; }
    _loop() {
      if (this._raf || this._still() || !this._vis || !this._D) return;
      const step = () => { if (!this.isConnected || !this._vis || this._still()) { this._raf = 0; return; } this._paint(); this._raf = requestAnimationFrame(step); };
      this._raf = requestAnimationFrame(step);
    }
  }
  KEYS.forEach((k) => Object.defineProperty(GolemScene.prototype, k, { get() { return this._p[k]; }, set(v) { this._p[k] = v; this._build(); }, configurable: true }));
  customElements.define('golem-scene', GolemScene);

  // ── <golem-mini> — flat miniature for picker cards ──
  const MKEYS = ['direction', 'map', 'cell'];
  class GolemMini extends HTMLElement {
    static get observedAttributes() { return MKEYS; }
    constructor() { super(); this._p = {}; this._c = document.createElement('canvas'); this._c.style.display = 'block'; }
    _g(k) { return this._p[k] !== undefined ? this._p[k] : this.getAttribute(k); }
    connectedCallback() { if (!this._c.isConnected) this.appendChild(this._c); this.style.display = 'inline-block'; this._draw(); requestAnimationFrame(() => this._draw()); }
    attributeChangedCallback() { this._draw(); }
    _draw() {
      if (!this.isConnected) return;
      const P = (DIRS[this._g('direction')] || clay).mini, m = model(this._g('map'));
      if (!m.H) { if ((this._tries = (this._tries || 0) + 1) <= 60) requestAnimationFrame(() => this._draw()); return; }
      const s = Number(this._g('cell')) || 7, dpr = Math.min(3, window.devicePixelRatio || 1), c = this._c;
      c.width = m.W * s * dpr; c.height = m.H * s * dpr; c.style.width = m.W * s + 'px'; c.style.height = m.H * s + 'px';
      this.style.width = m.W * s + 'px'; this.style.height = m.H * s + 'px';
      const k = c.getContext('2d'); k.setTransform(dpr, 0, 0, dpr, 0, 0); k.clearRect(0, 0, m.W * s, m.H * s);
      for (let y = 0; y < m.H; y++) for (let x = 0; x < m.W; x++) {
        const px = x * s, py = y * s;
        if (m.inside(x, y)) { k.fillStyle = ((x + y) & 1) ? P.floor : P.grid; k.fillRect(px, py, s, s); }
        if (m.isWall(x, y)) { k.fillStyle = P.wallTop; k.fillRect(px, py, s, s); if (!m.isWall(x, y + 1)) { k.fillStyle = P.wallFront; k.fillRect(px, py + s * 0.62, s, s * 0.38); } }
      }
      for (const q of m.goals) { k.strokeStyle = q.lit ? P.goalLit : P.goal; k.lineWidth = Math.max(1, s * 0.16); circle(k, q.x * s + s / 2, q.y * s + s / 2, s * 0.3); k.stroke(); }
      for (const b of m.boxes) { const i = s * 0.14; k.fillStyle = P.box; rr(k, b.x * s + i, b.y * s + i, s - 2 * i, s - 2 * i, s * 0.15); k.fill(); k.fillStyle = b.on ? P.mark : P.boxFront; k.fillRect(b.x * s + i, b.y * s + s * 0.62, s - 2 * i, s * 0.24); }
      if (m.robot) { k.fillStyle = P.robot; circle(k, m.robot.x * s + s / 2, m.robot.y * s + s / 2, s * 0.36); k.fill(); k.fillStyle = P.eye; k.fillRect(m.robot.x * s + s * 0.3, m.robot.y * s + s * 0.4, s * 0.4, Math.max(1, s * 0.14)); }
    }
  }
  MKEYS.forEach((k) => Object.defineProperty(GolemMini.prototype, k, { get() { return this._p[k]; }, set(v) { this._p[k] = v; this._draw(); }, configurable: true }));
  customElements.define('golem-mini', GolemMini);

  window.GolemArt = { DIRS, model, h: { rr, lin, rad, circle, ell, hash, glow, noGlow, blink, speckle, castShadow } };
  document.querySelectorAll('golem-scene').forEach(e => e._build && e._build());
})();
