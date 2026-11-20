/* Golem · Clay and stone — poses, effects, fog and sprite sheets.
   Extends window.GolemArt.DIRS.clay (from golem-art.js). Load after it, or anywhere: it waits. */
(function boot() {
  if (!window.GolemArt) return setTimeout(boot, 20);
  const A = window.GolemArt; if (A.clayFx) return;
  const clay = A.DIRS.clay, { rr, lin, rad, circle, ell, hash, glow, blink } = A.h;
  const TAU = Math.PI * 2, DV = { N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0] };
  const E = {
    out: p => 1 - Math.pow(1 - p, 3),
    inOut: p => p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2,
    back: p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); }
  };
  const cl = (v, a, b) => Math.max(a, Math.min(b, v));
  const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const mix = (a, b, k) => { const x = hex(a), y = hex(b); return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * k)).join(',')})`; };
  const VIOLET = '#9184d9', VIOLET_HI = '#e7e5fe', EMBER = '#ffd9b0', RED = '#ec7d8a';

  // ── poses: every value is in cell units ──
  function pose(name, f, p, t) {
    const [fx, fy] = DV[f] || [0, 0], br = 0.5 + 0.5 * Math.sin(t * 1.9);
    const P = { dx: 0, dy: 0, lean: 0, sx: 1 - br * 0.015, sy: 1 + br * 0.035, lift: 0, tilt: 0, arms: 'side', swing: 0, eyes: 'open', glyph: 0.55 + 0.25 * Math.sin(t * 1.4), grey: 0, droop: 0, blink: blink(t, 3.7, 0.8) };
    if (name === 'walk') {
      const h = Math.sin(Math.PI * p);
      Object.assign(P, { lean: fx * 0.1, lift: h * 0.06, sy: 1 + h * 0.05, sx: 1 - h * 0.03, swing: Math.sin(TAU * p), glyph: 1, blink: 0 });
    } else if (name === 'push') {
      const k = E.out(Math.min(1, p * 1.6));
      Object.assign(P, { dx: fx * 0.07 * k, dy: fy * 0.05 * k, lean: fx * 0.2 * k, sx: 1 + 0.06 * k, sy: 1 - 0.05 * k, arms: 'fwd', glyph: 1.3, eyes: p > 0.2 && p < 0.8 ? 'squint' : 'open', blink: 0 });
    } else if (name === 'bump') {
      const k = p < 0.3 ? E.out(p / 0.3) : Math.exp(-6 * (p - 0.3)) * Math.cos((p - 0.3) * 14);
      const sq = Math.max(0, k - 0.75) * 0.5;
      Object.assign(P, { dx: fx * 0.13 * k, dy: fy * 0.1 * k, lean: fx * 0.12 * k, sx: 1 - (fx ? sq : -sq * 0.5), sy: 1 - (fy ? sq : -sq * 0.4), eyes: p > 0.22 && p < 0.65 ? 'squint' : 'open', glyph: 1.2 * (1 - p) + 0.5 * p, blink: 0 });
    } else if (name === 'celebrate') {
      const h = p < 0.6 ? Math.sin(Math.PI * p / 0.6) : Math.abs(Math.sin(Math.PI * (p - 0.6) / 0.2)) * 0.25 * (1 - (p - 0.6) / 0.4);
      Object.assign(P, { lift: h * 0.2, sy: 1 + h * 0.08, sx: 1 - h * 0.04, arms: 'up', swing: Math.sin(TAU * 2 * p) * 0.3, eyes: 'happy', glyph: 1.6, blink: 0 });
    } else if (name === 'powerdown') {
      const k = E.inOut(p);
      Object.assign(P, { sy: 1 - 0.1 * k, sx: 1 + 0.03 * k, tilt: (fx || 1) * -0.1 * k, arms: 'down', eyes: k > 0.55 ? 'off' : 'open', glyph: 0.9 * (1 - k), grey: k, droop: k, blink: k > 0.3 && k < 0.55 ? 0.7 : 0 });
    }
    return P;
  }

  function robot(c, g, px, py, t, facing, o) {
    o = o || {};
    const s = g.s, f = facing || 'S', [fx, fy] = DV[f] || [0, 0], P = pose(o.pose || 'idle', f, o.p == null ? 0.5 : o.p, t);
    const cx = px + s / 2 + P.dx * s, foot = py + s * 0.86 + P.dy * s;
    const back = f === 'N';
    c.save(); c.translate(cx + s * 0.07, foot + s * 0.01); c.scale(1 - P.lift * 1.4, 0.3 * (1 - P.lift * 0.8));
    c.fillStyle = rad(c, 0, 0, s * 0.38, [[0, 'rgba(0,0,0,0.6)'], [1, 'rgba(0,0,0,0)']]); circle(c, 0, 0, s * 0.38); c.fill(); c.restore();
    c.save(); c.translate(cx, foot - P.lift * s); c.rotate(P.tilt); c.transform(1, 0, -P.lean, 1, 0, 0); c.scale(P.sx, P.sy);
    const hgt = s * 0.64, bw = s * 0.27, tw = s * 0.22, G = P.grey;
    const C = (a, b) => G ? mix(a, b, G) : a;
    c.fillStyle = C('#7a3f27', '#4a423d');
    const step = P.swing * s * 0.03;
    ell(c, -s * 0.13, -s * 0.015 - Math.max(0, step), s * 0.1, s * 0.055); c.fill();
    ell(c, s * 0.13, -s * 0.015 - Math.max(0, -step), s * 0.1, s * 0.055); c.fill();
    const arm = (side) => {
      let ax = side * s * 0.275, ay = -hgt * 0.4, rot = side * 0.28;
      if (P.arms === 'fwd') { if (fx) { ax = fx * s * 0.27 + side * s * 0.04; ay = -hgt * (0.42 + side * 0.06); rot = fx * 1.35; } else { ay = -hgt * (fy > 0 ? 0.35 : 0.5); rot = side * 0.12; } }
      if (P.arms === 'up') { ax = side * s * 0.33; ay = -hgt * (0.98 + P.swing * side * 0.05); rot = side * 0.65; }
      if (P.arms === 'down') { ax = side * s * 0.25; ay = -hgt * 0.3; rot = side * 0.08; }
      if (P.arms === 'side') ay += P.swing * side * s * 0.02;
      ell(c, ax, ay, s * 0.075, s * 0.135, rot);
      c.fillStyle = lin(c, ax - s * 0.07, ay - s * 0.13, ax + s * 0.07, ay + s * 0.13, [[0, C('#c27448', '#8a8079')], [1, C('#8c4a2c', '#57504b')]]); c.fill();
    };
    const armsBehind = P.arms === 'fwd' && fy < 0;
    if (armsBehind || back) { arm(-1); arm(1); }
    c.beginPath(); c.moveTo(-bw, -s * 0.05);
    c.bezierCurveTo(-bw - s * 0.035, -hgt * 0.55, -tw - s * 0.02, -hgt, 0, -hgt);
    c.bezierCurveTo(tw + s * 0.02, -hgt, bw + s * 0.035, -hgt * 0.55, bw, -s * 0.05);
    c.quadraticCurveTo(0, s * 0.025, -bw, -s * 0.05);
    c.fillStyle = lin(c, -bw, -hgt, bw, 0, [[0, C('#e09a6c', '#a59a92')], [0.5, C('#b8683f', '#7a706a')], [1, C('#7e4127', '#4c4540')]]); c.fill();
    c.save(); c.clip();
    c.fillStyle = rad(c, -s * 0.1, -hgt * 0.74, s * 0.26, [[0, `rgba(255,228,200,${0.5 - G * 0.35})`], [1, 'rgba(255,228,200,0)']]); c.fillRect(-bw * 1.3, -hgt, bw * 2.6, hgt);
    if (P.glyph > 0.05) { c.fillStyle = rad(c, 0, -hgt * 0.62, s * 0.3, [[0, `rgba(145,132,217,${0.12 * P.glyph})`], [1, 'rgba(145,132,217,0)']]); c.fillRect(-bw * 1.3, -hgt, bw * 2.6, hgt); }
    if (g.lod >= 2) {
      c.strokeStyle = 'rgba(255,225,195,0.13)'; c.lineWidth = 1;
      for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(s * 0.08, -hgt * 0.28, s * (0.04 + i * 0.025), Math.PI * 1.1, Math.PI * 1.75); c.stroke(); }
      c.strokeStyle = 'rgba(80,35,18,0.25)'; c.beginPath(); c.moveTo(-bw * 0.8, -hgt * 0.36); c.quadraticCurveTo(-bw * 0.4, -hgt * 0.32, -bw * 0.15, -hgt * 0.38); c.stroke();
      if (back) { c.strokeStyle = 'rgba(60,25,12,0.4)'; c.beginPath(); c.moveTo(0, -hgt * 0.92); c.quadraticCurveTo(s * 0.02, -hgt * 0.5, 0, -hgt * 0.12); c.stroke(); }
    }
    c.restore();
    if (!back) {
      const ey = -hgt * 0.58 + fy * s * 0.02 + P.droop * s * 0.04, ex = fx * s * 0.04, bl = P.blink;
      c.fillStyle = C('#35180e', '#2a2624');
      for (const sd of [-1, 1]) {
        const x = sd * s * 0.095 + ex;
        if (P.eyes === 'open' || P.eyes === 'off') { ell(c, x, ey, s * 0.06, s * 0.072 * (1 - bl * 0.85) * (P.eyes === 'off' ? 0.45 : 1)); c.fill(); }
      }
      c.lineCap = 'round'; c.lineJoin = 'round';
      if (P.eyes === 'open' && bl < 0.6) {
        c.save(); glow(c, g, VIOLET, s * 0.28); c.fillStyle = '#ece9ff';
        for (const sd of [-1, 1]) { circle(c, sd * s * 0.095 + ex * 1.3, ey + fy * s * 0.01, s * 0.024); c.fill(); }
        c.restore();
      } else if (P.eyes === 'squint') {
        c.save(); glow(c, g, VIOLET, s * 0.2); c.strokeStyle = '#ece9ff'; c.lineWidth = Math.max(1.2, s * 0.028);
        for (const sd of [-1, 1]) { const x = sd * s * 0.095 + ex; c.beginPath(); c.moveTo(x - sd * s * 0.045, ey - s * 0.03); c.lineTo(x + sd * s * 0.035, ey); c.lineTo(x - sd * s * 0.045, ey + s * 0.03); c.stroke(); }
        c.restore();
      } else if (P.eyes === 'happy') {
        c.save(); glow(c, g, VIOLET, s * 0.3); c.strokeStyle = '#ece9ff'; c.lineWidth = Math.max(1.4, s * 0.032);
        for (const sd of [-1, 1]) { c.beginPath(); c.arc(sd * s * 0.095 + ex, ey + s * 0.02, s * 0.045, Math.PI * 1.1, Math.PI * 1.9); c.stroke(); }
        c.restore();
      }
      const gy = -hgt * 0.84, on = cl(P.glyph, 0, 2);
      c.save(); c.lineWidth = Math.max(1.2, s * 0.028); c.lineCap = 'round';
      if (on > 0.05) { glow(c, g, VIOLET, s * 0.35 * on); c.strokeStyle = `rgba(214,208,255,${Math.min(1, 0.45 + 0.45 * on)})`; }
      else c.strokeStyle = 'rgba(70,40,28,0.7)';
      c.beginPath(); c.moveTo(0, gy - s * 0.05); c.lineTo(0, gy + s * 0.05); c.moveTo(-s * 0.045, gy - s * 0.025); c.lineTo(0, gy + s * 0.008); c.lineTo(s * 0.045, gy - s * 0.025); c.stroke();
      if (on > 1.2) { c.globalCompositeOperation = 'lighter'; c.fillStyle = rad(c, 0, gy, s * 0.22, [[0, 'rgba(181,171,252,0.5)'], [1, 'rgba(181,171,252,0)']]); circle(c, 0, gy, s * 0.22); c.fill(); }
      c.restore();
    }
    if (!(armsBehind || back)) { arm(-1); arm(1); }
    c.restore();
  }

  // ── effects: p is 0..1 through the effect ──
  function dust(c, x, y, s, p, dx, dy, seed, n) {
    for (let i = 0; i < (n || 5); i++) {
      const a = Math.atan2(dy, dx) + (hash(i, seed, 1) - 0.5) * 2.2, d = s * (0.05 + 0.3 * E.out(p) * (0.6 + 0.6 * hash(i, seed, 2)));
      const r = s * (0.05 + 0.11 * E.out(p) * (0.6 + 0.6 * hash(i, seed, 3)));
      c.fillStyle = `rgba(214,190,160,${0.5 * (1 - p) * (0.6 + 0.4 * hash(i, seed, 4))})`;
      circle(c, x + Math.cos(a) * d, y + Math.sin(a) * d - p * s * 0.08, r); c.fill();
    }
  }
  function impact(c, g, x, y, s, p, dir) {
    const [fx, fy] = DV[dir] || [1, 0], k = p < 0.25 ? p / 0.25 : 1 - (p - 0.25) / 0.75;
    c.save(); c.globalCompositeOperation = 'lighter';
    c.fillStyle = rad(c, x, y, s * 0.45, [[0, `rgba(255,214,170,${0.55 * k})`], [1, 'rgba(255,214,170,0)']]); circle(c, x, y, s * 0.45); c.fill();
    c.strokeStyle = `rgba(255,241,220,${k})`; c.lineWidth = Math.max(1.2, s * 0.03); c.lineCap = 'round';
    for (let i = 0; i < 6; i++) {
      const a = Math.atan2(-fy, -fx) + (i / 5 - 0.5) * 2.4, r0 = s * (0.06 + 0.12 * p), r1 = r0 + s * 0.12 * k;
      c.beginPath(); c.moveTo(x + Math.cos(a) * r0, y + Math.sin(a) * r0); c.lineTo(x + Math.cos(a) * r1, y + Math.sin(a) * r1); c.stroke();
    }
    c.restore();
    c.fillStyle = `rgba(150,128,105,${1 - p})`;
    for (let i = 0; i < 4; i++) { const a = Math.atan2(-fy, -fx) + (hash(i, 9, 1) - 0.5) * 2, d = s * 0.32 * E.out(p); c.fillRect(x + Math.cos(a) * d, y + Math.sin(a) * d + p * p * s * 0.25, Math.max(1.5, s * 0.035), Math.max(1.5, s * 0.035)); }
  }
  function sparks(c, x, y, s, p, n, seed, spread, colors) {
    c.save(); c.globalCompositeOperation = 'lighter';
    for (let i = 0; i < n; i++) {
      const q = cl(p * 1.25 - hash(i, seed, 1) * 0.25, 0, 1); if (q <= 0 || q >= 1) continue;
      const a = -Math.PI / 2 + (hash(i, seed, 2) - 0.5) * spread, d = s * (0.2 + 0.9 * hash(i, seed, 3)) * E.out(q);
      const px = x + Math.cos(a) * d, py = y + Math.sin(a) * d * 1.1 - q * s * 0.25, r = Math.max(1, s * 0.03 * (1 - q * 0.6));
      c.fillStyle = colors[i % colors.length]; c.globalAlpha = 1 - q;
      glow(c, g0, colors[i % colors.length], s * 0.15); circle(c, px, py, r); c.fill();
    }
    c.restore(); c.globalAlpha = 1;
  }
  let g0 = { dpr: 2 };
  function ignite(c, g, cx, cy, s, p) {
    const k = 1 - p;
    c.save(); c.globalCompositeOperation = 'lighter';
    c.fillStyle = rad(c, cx, cy, s * (0.5 + 0.6 * p), [[0, `rgba(181,171,252,${0.7 * k})`], [0.6, `rgba(145,132,217,${0.25 * k})`], [1, 'rgba(145,132,217,0)']]); circle(c, cx, cy, s * 1.1); c.fill();
    c.strokeStyle = `rgba(214,208,255,${k})`; c.lineWidth = Math.max(1.5, s * 0.045 * k + 1); glow(c, g, VIOLET, s * 0.3);
    circle(c, cx, cy, s * (0.34 + 0.55 * E.out(p))); c.stroke();
    c.restore();
    sparks(c, cx, cy, s, p, 12, 4, 2.6, [VIOLET_HI, '#b5abfc', EMBER]);
  }
  function flare(c, g, cx, cy, s, p, i) {
    const k = p < 0.2 ? p / 0.2 : 1 - (p - 0.2) / 0.8 * 0.6;
    c.save(); c.globalCompositeOperation = 'lighter';
    c.fillStyle = lin(c, 0, cy - s * 0.3, 0, cy - s * 2.6, [[0, `rgba(181,171,252,${0.26 * k})`], [1, 'rgba(181,171,252,0)']]);
    c.fillRect(cx - s * 0.2, cy - s * 2.6, s * 0.4, s * 2.3);
    c.fillStyle = rad(c, cx, cy, s * 0.95, [[0, `rgba(181,171,252,${0.22 * k})`], [0.5, `rgba(145,132,217,${0.12 * k})`], [1, 'rgba(145,132,217,0)']]); circle(c, cx, cy, s * 0.95); c.fill();
    c.strokeStyle = `rgba(214,208,255,${0.5 * k})`; c.lineWidth = Math.max(1.2, s * 0.03); circle(c, cx, cy, s * (0.4 + 0.25 * E.out(p))); c.stroke();
    c.restore();
    sparks(c, cx, cy - s * 0.2, s, cl(p * 1.1 - i * 0.06, 0, 1), 10, 20 + i, 1.4, [VIOLET_HI, EMBER, '#b5abfc']);
  }
  function boxTop(g, x, y) { const s = g.s; return { x0: g.ox + x * s + s * 0.11, y0: g.oy + y * s + s * 0.11 - s * 0.24, d: s * 0.78 }; }
  function crack(c, g, x0, y0, d, p, seed) {
    const s = g.s;
    c.save(); rr(c, x0, y0, d, d, s * 0.07); c.clip();
    c.fillStyle = `rgba(30,12,16,${0.42 * p})`; c.fillRect(x0, y0, d, d + s * 0.3);
    c.strokeStyle = 'rgba(25,10,8,0.9)'; c.lineWidth = Math.max(1.2, s * 0.035); c.lineCap = 'round'; c.lineJoin = 'round';
    const paths = [[[0.08, 0.3], [0.32, 0.42], [0.45, 0.36], [0.62, 0.58], [0.9, 0.66]], [[0.45, 0.36], [0.52, 0.12], [0.6, 0.02]], [[0.62, 0.58], [0.55, 0.8], [0.6, 0.98]]];
    paths.forEach((pts, j) => {
      const q = cl(p * 1.6 - j * 0.3, 0, 1); if (q <= 0) return;
      const n = Math.max(2, Math.ceil(pts.length * q)); c.beginPath();
      pts.slice(0, n).forEach(([a, b], i) => i ? c.lineTo(x0 + a * d, y0 + b * d) : c.moveTo(x0 + a * d, y0 + b * d)); c.stroke();
    });
    c.strokeStyle = 'rgba(255,220,190,0.18)'; c.lineWidth = 1; c.translate(0.8, 0.8);
    c.beginPath(); paths[0].slice(0, Math.max(2, Math.ceil(5 * cl(p * 1.6, 0, 1)))).forEach(([a, b], i) => i ? c.lineTo(x0 + a * d, y0 + b * d) : c.moveTo(x0 + a * d, y0 + b * d)); c.stroke();
    c.restore();
  }
  function lock(c, g, cx, cy, s, p) {
    const k = cl(E.back(cl(p * 1.4, 0, 1)), 0, 1.2), w = s * 0.34 * k, h = s * 0.27 * k;
    if (k <= 0.01) return;
    c.save(); c.translate(cx, cy);
    c.strokeStyle = '#2a1015'; c.lineWidth = Math.max(2, s * 0.07); c.beginPath(); c.arc(0, -h * 0.5, w * 0.32, Math.PI, 0); c.stroke();
    c.strokeStyle = RED; c.lineWidth = Math.max(1.4, s * 0.045); glow(c, g, RED, s * 0.3); c.beginPath(); c.arc(0, -h * 0.5, w * 0.32, Math.PI, 0); c.stroke();
    rr(c, -w / 2, -h * 0.5, w, h, s * 0.05); c.fillStyle = RED; c.fill();
    c.shadowBlur = 0; c.fillStyle = '#2a1015'; circle(c, 0, h * -0.05, Math.max(1, s * 0.035)); c.fill(); c.fillRect(-Math.max(0.6, s * 0.012), h * -0.05, Math.max(1.2, s * 0.024), h * 0.25);
    c.restore();
  }
  function spotlight(c, g, cx, cy, p) {
    const R = g.s * 1.4, k = E.out(cl(p * 1.5, 0, 1));
    c.save(); c.fillStyle = rad(c, cx, cy, Math.max(g.W, g.H) * 0.9, [[0, 'rgba(8,6,12,0)'], [R / (Math.max(g.W, g.H) * 0.9), 'rgba(8,6,12,0)'], [Math.min(1, R * 2.2 / (Math.max(g.W, g.H) * 0.9)), `rgba(8,6,12,${0.55 * k})`], [1, `rgba(8,6,12,${0.7 * k})`]]);
    c.fillRect(0, 0, g.W, g.H); c.restore();
  }
  function fog(c, g, m, mask, t) {
    const rows = String(mask).split('|'), s = g.s, r = m.robot;
    c.save();
    for (let y = 0; y < m.H; y++) for (let x = 0; x < m.W; x++) {
      if ((rows[y] || '')[x] !== '0' || !(m.inside(x, y) || m.isWall(x, y))) continue;
      const px = g.ox + x * s, py = g.oy + y * s - (m.isWall(x, y) ? g.hw : 0);
      c.fillStyle = 'rgba(14,12,18,0.9)'; c.fillRect(px - 1, py - 1, s + 2, s + 2 + (m.isWall(x, y) ? g.hw : 0));
      for (let i = 0; i < 3; i++) {
        const fx = px + s * (0.2 + 0.6 * hash(x, y, 60 + i)) + Math.sin(t * 0.3 + i + x) * s * 0.08, fy = py + s * (0.2 + 0.6 * hash(x, y, 70 + i)) + Math.cos(t * 0.25 + i + y) * s * 0.06;
        c.fillStyle = rad(c, fx, fy, s * 0.7, [[0, 'rgba(60,54,70,0.22)'], [1, 'rgba(60,54,70,0)']]); circle(c, fx, fy, s * 0.7); c.fill();
      }
    }
    for (let y = 0; y < m.H; y++) for (let x = 0; x < m.W; x++) {
      if ((rows[y] || '')[x] !== '0') continue;
      [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([dx, dy]) => {
        if ((rows[y + dy] || '')[x + dx] !== '1') return;
        const px = g.ox + x * s, py = g.oy + y * s;
        const ex = px + (dx > 0 ? s : 0), ey = py + (dy > 0 ? s : 0);
        const gr = dx ? lin(c, ex, 0, ex + dx * s * 0.45, 0, [[0, 'rgba(14,12,18,0.75)'], [1, 'rgba(14,12,18,0)']]) : lin(c, 0, ey, 0, ey + dy * s * 0.45, [[0, 'rgba(14,12,18,0.75)'], [1, 'rgba(14,12,18,0)']]);
        c.fillStyle = gr; if (dx) c.fillRect(dx > 0 ? ex : ex - s * 0.45, py, s * 0.45, s); else c.fillRect(px, dy > 0 ? ey : ey - s * 0.45, s, s * 0.45);
      });
    }
    if (r) {
      const cx = g.ox + r.x * s + s / 2, cy = g.oy + r.y * s + s / 2;
      c.globalCompositeOperation = 'screen';
      c.fillStyle = rad(c, cx, cy, s * 1.7, [[0, 'rgba(255,190,130,0.22)'], [0.55, 'rgba(255,190,130,0.08)'], [1, 'rgba(255,190,130,0)']]); circle(c, cx, cy, s * 1.7); c.fill();
      c.globalCompositeOperation = 'source-over'; c.strokeStyle = 'rgba(255,214,170,0.35)'; c.lineWidth = 1; c.setLineDash([3, 4]);
      c.beginPath(); const L = g.ox + (r.x - 1) * s, T = g.oy + (r.y - 1) * s;
      c.moveTo(L + s, T); c.lineTo(L + 2 * s, T); c.lineTo(L + 2 * s, T + s); c.lineTo(L + 3 * s, T + s); c.lineTo(L + 3 * s, T + 2 * s); c.lineTo(L + 2 * s, T + 2 * s); c.lineTo(L + 2 * s, T + 3 * s); c.lineTo(L + s, T + 3 * s); c.lineTo(L + s, T + 2 * s); c.lineTo(L, T + 2 * s); c.lineTo(L, T + s); c.lineTo(L + s, T + s); c.closePath(); c.stroke();
    }
    c.restore();
  }

  function over(c, g, m, t, o) {
    g0 = g; const s = g.s, p = o.p, r = m.robot, F = o.focus;
    if (o.fx === 'bump' && r) {
      const f = o.dir || 'W', [fx, fy] = DV[f], x = g.ox + r.x * s + s / 2 + fx * s * 0.5, y = g.oy + r.y * s + s * 0.55 + fy * s * 0.5;
      impact(c, g, x, y, s, p, f); dust(c, x, y + s * 0.2, s, p, -fx, -0.6, 3, 4);
    }
    if ((o.fx === 'land' || o.fx === 'push') && F) {
      const cx = g.ox + F[0] * s + s / 2, cy = g.oy + F[1] * s + s / 2, [fx, fy] = DV[o.dir || 'W'];
      dust(c, cx - fx * s * 0.45, cy + s * 0.32, s, Math.min(1, p * 1.3), -fx, -fy - 0.3, 7, 6);
      if (o.fx === 'land') ignite(c, g, cx, cy, s, p);
    }
    if (o.fx === 'solved') m.goals.forEach((q, i) => flare(c, g, g.ox + q.x * s + s / 2, g.oy + q.y * s + s / 2, s, p, i));
    if (o.fx === 'lost') { c.fillStyle = `rgba(10,10,22,${0.3 * E.out(p)})`; c.fillRect(0, 0, g.W, g.H); }
    if (o.fx === 'deadlock' && F) {
      const b = boxTop(g, F[0], F[1]), cx = b.x0 + b.d / 2, cy = b.y0 + b.d / 2;
      spotlight(c, g, cx, cy + s * 0.1, p);
      crack(c, g, b.x0, b.y0, b.d, cl(p * 1.3, 0, 1), 1);
      c.save(); c.strokeStyle = `rgba(236,125,138,${0.8 - 0.4 * Math.sin(t * 3) * 0.5})`; c.lineWidth = Math.max(1.5, s * 0.04); glow(c, g, RED, s * 0.4);
      rr(c, g.ox + F[0] * s + s * 0.03, g.oy + F[1] * s - s * 0.22, s * 0.94, s * 1.16, s * 0.14); c.stroke(); c.restore();
      lock(c, g, cx, b.y0 - s * 0.32, s, cl(p * 1.2 - 0.15, 0, 1));
    }
    if (o.fog) fog(c, g, m, o.fog, t);
  }

  clay.robot = robot; clay.over = over;

  // ── <golem-sheet anim frames cell facing> : a sprite strip drawn with the same code ──
  const ANIMS = { idle: 8, walk: 6, push: 6, bump: 6, celebrate: 12, powerdown: 10, dust: 6, impact: 5, ignite: 8, sparks: 8, crack: 6, lock: 6, flare: 10 };
  class GolemSheet extends HTMLElement {
    static get observedAttributes() { return ['anim', 'frames', 'cell', 'facing']; }
    constructor() { super(); this._p = {}; this._c = document.createElement('canvas'); this._c.style.display = 'block'; }
    _g(k) { return this._p[k] !== undefined ? this._p[k] : this.getAttribute(k); }
    connectedCallback() { if (!this._c.isConnected) this.appendChild(this._c); this.style.display = 'inline-block'; this._draw(); requestAnimationFrame(() => this._draw()); }
    attributeChangedCallback() { this._draw(); }
    _draw() {
      if (!this.isConnected) return;
      const anim = this._g('anim') || 'idle', n = Number(this._g('frames')) || ANIMS[anim] || 6, s = Number(this._g('cell')) || 48, f = this._g('facing') || 'S';
      const fw = s * 1.25, fh = s * 1.5, dpr = Math.min(3, window.devicePixelRatio || 1), cv = this._c;
      cv.width = Math.round(fw * n * dpr); cv.height = Math.round(fh * dpr); cv.style.width = fw * n + 'px'; cv.style.height = fh + 'px';
      const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, fw * n, fh);
      const g = { s, dpr, lod: s >= 40 ? 2 : s >= 26 ? 1 : 0, ox: 0, oy: 0, W: fw, H: fh, hw: s * clay.hw };
      g0 = g;
      for (let i = 0; i < n; i++) {
        const p = n > 1 ? i / (n - 1) : 0.5, x = i * fw, px = x + (fw - s) / 2, py = fh - s * 1.02, cx = x + fw / 2, cy = py + s / 2;
        c.strokeStyle = 'rgba(233,233,237,0.08)'; c.lineWidth = 1; c.strokeRect(x + 0.5, 0.5, fw - 1, fh - 1);
        if (['idle', 'walk', 'push', 'bump', 'celebrate', 'powerdown'].includes(anim)) {
          const t = anim === 'idle' ? (i === 5 ? 2.97 : (i / n) * (TAU / 1.9)) : 1.2;
          robot(c, g, px, py, t, f, { pose: anim, p: anim === 'idle' ? 0.5 : p });
          if (anim === 'bump') { const [fx, fy] = DV[f]; impact(c, g, cx + fx * s * 0.5, cy + s * 0.05 + fy * s * 0.5, s, p, f); }
        } else if (anim === 'dust') dust(c, cx, cy + s * 0.25, s, p, 0, -1, 7, 6);
        else if (anim === 'impact') impact(c, g, cx + s * 0.3, cy, s, p, 'E');
        else if (anim === 'ignite') ignite(c, g, cx, cy, s, p);
        else if (anim === 'sparks') sparks(c, cx, cy + s * 0.3, s, p, 14, 5, 2.2, [VIOLET_HI, EMBER, '#b5abfc']);
        else if (anim === 'flare') flare(c, g, cx, fh - s * 0.25, s * 0.55, p, 0);
        else if (anim === 'crack') { const d = s * 0.78, x0 = cx - d / 2, y0 = cy - d / 2; rr(c, x0, y0, d, d, s * 0.07); c.fillStyle = lin(c, x0, y0, x0 + d, y0 + d, [[0, '#d2b48c'], [1, '#a08060']]); c.fill(); crack(c, g, x0, y0, d, p, 1); }
        else if (anim === 'lock') lock(c, g, cx, cy + s * 0.1, s * 1.2, p);
      }
    }
  }
  if (!customElements.get('golem-sheet')) customElements.define('golem-sheet', GolemSheet);

  A.clayFx = { pose, robot, over, ANIMS, ease: E };
  document.querySelectorAll('golem-scene').forEach(e => e._build && e._build());
})();
