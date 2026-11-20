# Handoff: Golem — game screen, direction "Clay and stone"

## Overview
Golem is a private box-pushing research sandbox served from a local server (`http://127.0.0.1:8700/`). A person plays training levels with the arrow keys; later the same screen replays an AI agent's recorded runs. The page only **sends keys** and **draws the states** the server returns — it never decides whether a move is legal.

This package is the full visual design for the play screen in the chosen art direction **2a · Clay and stone**: a small clay golem in a lamp-lit stone workshop. It covers 12 required states + a replay sketch, the tile/sprite/effect art, an asset list, motion specs and the UI system. The original brief is included as `brief.md` — read it first; it is the source of truth for data formats and constraints.

## About the design files
The `.dc.html` files are **design references built in HTML** (a lightweight component format; open them in a browser — `support.js` must sit next to them). They show the intended look and behaviour; they are **not** the production page. Recreate them in the project's required stack:

- **Plain HTML + CSS + JavaScript. No framework, no build step, no library, no external URL** (brief, "technical frame").
- One page, `<canvas>` for the scene, HTML/CSS for the interface panels on top.

**Exception — the two renderer scripts are close to production code.** `golem-art.js` and `golem-clay-fx.js` are plain, dependency-free JS that already draw every frame in the mocks. Reuse them: keep the drawing functions, drop the custom-element wrappers if you prefer, and drop the unused `lab` and `diorama` directions from `golem-art.js`.

## Fidelity
**High-fidelity.** Colours, type, sizes, spacing, radii, shadows, copy and motion values below are final. Recreate pixel-accurately. Where this README and the mocks disagree, the README wins.

---

## Screen layout (1440 × 900 reference, "wide" ≥ 1200 px)

Everything is absolutely positioned over a full-window canvas.

| Layer | Position | Notes |
|---|---|---|
| Scene canvas | `inset: 0` | Draws room, tray, board, Golem, effects, lighting. |
| Level picker panel | `left 20; top 20; bottom 20; width 300` | Glass panel. |
| Level plate | `left 360; top 22` | Level name block. |
| Step gauge | `right 36; top 22; width 290` | |
| Key hints | `bottom 22`, centred in the area `left 340 → right 0` | |
| Result panel | `bottom 30`, centred in the same area, `width 680` | Only on solved / lost. |
| Error notice | `right 36; top 150; width 320` | |

**Board area (canvas inset, top right bottom left):**
- playing: `112 56 120 352`
- solved / lost (result panel visible): `112 56 214 352`
- title screen: `330 56 110 352`, max cell 60
- replay: `112 330 176 352`
- compact (< 1200 px): `96 28 86 96`

**Cell size:** `s = clamp(20, floor(min(aw / (W + 2·0.55), ah / (H + 2·0.55 + 0.34 + 0.40))), 64)`, where `aw/ah` is the inset area, `W/H` the map size in cells, `0.55` the tray margin, `0.34` the wall height and `0.40` the tray thickness (all in cells). Integer pixels. Canvas backing store = CSS size × `min(2, devicePixelRatio)`.

**Compact layout (< 1200 px, e.g. 1024 × 700):** picker folds into a rail `left 14; top 14; bottom 14; width 60; radius 14` (logo, Levels icon button 40 × 40, per-tier label `T1/T2/T3` with a column of 6 px dots, connection dot at the bottom). Plate `left 96; top 18`, name 30 px. Gauge `right 20; width 230`, number 30 px. Key hints area starts at `left 74`. A 20 × 20 board fits at ~21 px cells.

**< 900 px:** same as compact; the atlas (see below) is the full picker.

### Level picker panel
- Panel: radius 16; `background: rgba(30,24,26,0.64)`; `box-shadow: 0 0 0 1px rgba(255,214,170,0.10), 0 24px 60px rgba(0,0,0,0.45)`; `backdrop-filter: blur(20px) saturate(1.15)`.
- **Header** (padding 18 18 12, gap 9): logo 24 px (inline SVG clay dome with violet glyph), "Golem" 16 / 500 / −0.01em; right: connection status 11 px with a 7 px dot.
  - Connected: dot `#5cc49b`, halo `0 0 0 3px rgba(92,196,155,0.18), 0 0 8px #5cc49b`, text `#9397ab`.
  - Reconnecting: dot `#e2a44c`, halo `rgba(226,164,76,0.2)`, text `#f0c27e`, label "Reconnecting…".
- **Mode tabs** (padding 0 18 14): container padding 3, gap 3, radius 10, `background: rgba(0,0,0,0.25)`, inset ring `rgba(233,233,237,0.06)`. Tab height 28, radius 7, 12 / 500. Selected: `background: rgba(145,132,217,0.16)`, `box-shadow: inset 0 0 0 1px rgba(145,132,217,0.6)`, colour `#d2cefd`. "Replay" is disabled in play mode with a 10 px "later" suffix in `#75798c`.
- **Rule:** 1 px, margin 0 18, fading at both ends over 48 px: `linear-gradient(to right, transparent, rgba(255,214,170,0.14) 48px, rgba(255,214,170,0.14) calc(100% - 48px), transparent)`.
- **List** (padding 14 12, gap 6). The tier of the current level is expanded; other playable tiers collapse to a summary row; tier 3 is a placeholder.
  - *Collapsed tier row:* padding 9 10, radius 10, `background: rgba(255,255,255,0.025)`, inset ring `rgba(233,233,237,0.06)`. Label 11 / 500, caps, 0.1em, `#b2b6ca`. One 6 px dot per level: solved `#5cc49b` + `0 0 6px rgba(92,196,155,0.5)`; current `#b5abfc` + `0 0 6px #9184d9`; unsolved `rgba(233,233,237,0.18)`. Right: "5 of 5 solved" 11 px `#9397ab` + chevron. Hover `rgba(255,255,255,0.05)`.
  - *Expanded tier header:* label 11 / 500 caps `#cfd3e5`; right "2 of 5 solved".
  - *Level card:* `display: grid; grid-template-columns: 92px 1fr; gap 12; padding 7; radius 12`. Miniature well 92 × 66, radius 8, `#2a221f`, inset ring `rgba(255,214,170,0.07)`. Name 15 / 500; solved mark = 14 px circle-check `#5cc49b`; meta "10 × 8 · 300 steps" 12 px `#9397ab`, tabular numerals. Default `background: rgba(255,255,255,0.025)`, inset ring `rgba(233,233,237,0.06)`; hover `rgba(255,255,255,0.06)`.
  - *Current card:* `background: rgba(145,132,217,0.13)`; `box-shadow: inset 0 0 0 1px rgba(145,132,217,0.8), 0 0 24px rgba(145,132,217,0.22)`; name `#e7e5fe`; tag "PLAYING" 10 px caps 0.08em, padding 2 7, radius 5, `background: rgba(145,132,217,0.18)`, colour `#d2cefd`. `aria-current="true"`.
  - *Tier 3 placeholder:* header "TIER 3" + "arrives later"; a card outline `1px dashed rgba(255,214,170,0.14)` with a hatched well and two skeleton bars.
- **Footer** (padding 0 18 16): secondary button "All levels" (full width, height 34, border `rgba(255,214,170,0.16)`) with "3 tiers" right-aligned → opens the atlas.

**Miniatures:** flat top-down, cell = `floor(min(82 / W, 56 / H))` px (atlas: `min(150 / W, 92 / H)`). Palette: floor `#6c5e52` / `#5a4e45` checker, wall top `#9a8a79`, wall front `#54473d` (bottom 38 % of a wall cell when the cell below is open), goal ring `#a68f69` (lit `#b5abfc`), block `#c4a580` with a `#7a6249` strip (on goal: `#d2cefd` strip), Golem `#c87a4e` circle with a `#d2cefd` visor. See `GolemMini` in `golem-art.js`.

### Level plate
`left 360; top 22`, column gap 4. Kicker "TIER 2 · LEVEL 3 OF 5" 11 px caps 0.12em `#d9b48f`. Name "t2-03" 40 / 500 / −0.025em / line-height 1.05, `text-shadow: 0 2px 18px rgba(0,0,0,0.6)`. Sub "10 × 8 cells" 13 px `#b2b6ca`.

### Step gauge
Width 290, padding 10 12 12, radius 12, column gap 8.
- Row 1: "STEPS" 11 px caps 0.12em `#9397ab` · right "263 left" 12 px `#b2b6ca`.
- Row 2: count 40 / 500 / −0.03em, tabular; "/ 300" 18 px `#9397ab`.
- Row 3: **30 tiles**, flex, gap 3, height 16, radius 2. `spentTiles = round(steps / budget × 30)`.
  - Normal: spent `rgba(233,233,237,0.10)`; remaining `#9184d9` + `0 0 8px rgba(145,132,217,0.45)`; the last 3 tiles (the reserve 10 %) `rgba(226,164,76,0.5)` + `0 0 6px rgba(226,164,76,0.3)`.
  - **Warning (left ≤ 10 % of budget):** panel `background: rgba(60,40,20,0.35)`, `box-shadow: 0 0 0 1px rgba(226,164,76,0.35), 0 0 32px rgba(226,164,76,0.18)`; spent `rgba(233,233,237,0.06)`; remaining `#e2a44c` + `0 0 10px rgba(226,164,76,0.75)`; count `#f0c27e` with a 14 px glow; the "left" text becomes a pill: hourglass icon + "24 left", padding 2 8 2 6, radius 6, `background: rgba(226,164,76,0.16)`, `inset 0 0 0 1px rgba(226,164,76,0.5)`, `#f0c27e`, 11 / 500.
  - Lost on steps: every tile `rgba(233,233,237,0.06)` except the last, which is `rgba(236,125,138,0.5)` with a red glow; count `#f4a7b0`.
  - Solved: remaining tiles `#b5abfc`.
  - Bump: a "+1" chip next to "/ 300": 11 / 600, padding 2 6, radius 5, `background: rgba(255,214,170,0.16)`, `#ffd9b0`, visible 600 ms.

### Key hints
Panel padding 9 16 9 12, radius 14, `background: rgba(30,24,26,0.6)`, ring `rgba(255,214,170,0.10)`, `blur(16px)`. Contents (gap 14, 12 px `#b2b6ca`): an inverted-T of arrow keys (grid 3 × 28 px columns, 2 × 26 px rows, gap 3) · "move" · divider (1 × 22, `rgba(255,214,170,0.14)`) · `R` keycap 30 × 28 · "restart" · divider · focus status: 6 px dot (`#9184d9` "Board focused" / `#e2a44c` "Keys paused").
- **Keycap:** radius 6; `background: linear-gradient(#4a3d36, #33292a)`; `box-shadow: inset 0 1px 0 rgba(255,226,196,0.14), 0 2px 0 #140f0f, 0 0 0 1px #54473d`; text `#f3e6d8` 12 / 500. **Pressed / just used:** `linear-gradient(#7a5a48, #5a4033)` for 160 ms.
- Hidden while a result panel, the atlas or replay is showing; 45 % opacity while reconnecting.

### Result panel (solved / lost)
Width 680, padding 18, radius 20, row gap 18; `background: rgba(30,24,26,0.72)`; `backdrop-filter: blur(22px) saturate(1.2)`; `box-shadow: 0 0 0 1px <C>, 0 0 48px <G>, 0 24px 60px rgba(0,0,0,0.55)`.
- Medallion 64 px circle: `radial-gradient(circle at 40% 35%, <T>, rgba(0,0,0,0.2))`, `inset 0 0 0 2px <C>, 0 0 24px <G>`, icon colour `<C>`.
- Title 24 / 500 / −0.02em; sub 13 px `#b2b6ca`.
- Buttons: a column 170 px wide, gap 6, each 36 px high, label left and key/arrow right.

| State | C | G | T | Icon | Title | Sub | Primary | Secondary |
|---|---|---|---|---|---|---|---|---|
| Solved | `#b5abfc` | `rgba(145,132,217,0.45)` | `rgba(145,132,217,0.18)` | check | Solved in {steps} steps | All four blocks are home. Next up: t2-04. | Next level `t2-04 →` | Restart `R` |
| Lost — steps | `#ec7d8a` | `rgba(236,125,138,0.35)` | `rgba(236,125,138,0.14)` | hourglass | Lost — out of steps | Golem has spent all {budget} steps and powered down. | Restart `R` | Another level |
| Lost — deadlock | `#ec7d8a` | same | same | padlock | Lost — a box is stuck in a corner | The marked block can never move again. | Restart `R` | Another level |

The sub-copy counts boxes from the map ("All four blocks…" — use the real count). "Next level" = the next entry in the list; on a tier's last level it goes to the next tier; hide it on the very last level.

### Error notice
Width 320, padding 12 10 12 14, radius 12, `background: rgba(30,24,26,0.78)`, `box-shadow: 0 0 0 1px rgba(236,125,138,0.45), 0 16px 40px rgba(0,0,0,0.5)`, `blur(18px)`. Warning-circle icon 18 px `#ec7d8a`; title = server `detail`, capitalised ("Unknown level") 14 / 500; sub "The server sent an error. Play continues." 12 px `#b2b6ca`; × ghost button 26 × 26. `role="alert"`, never takes focus; × or Esc closes it; auto-hides after 8 s.

### Reconnecting
Scene `filter: grayscale(0.85) brightness(0.55)`. Centred over the board area: a 72 px SVG ring (track `rgba(255,214,170,0.14)`, arc `#e2a44c`, dash `40 150`, turning once per 1.6 s) with Golem's glyph inside in `#f0c27e`; "Reconnecting…" 22 / 500; "Keys are paused. The game resumes where it was as soon as the server is back." 13 px `#cfd3e5`; "attempt 3 · next try in 2 s" 11 px `#9397ab`.

### Title screen (no level loaded)
Map drawn: `["  #######  ","###     ###","#   . @   #","#    $    #","###     ###","  #######  "]`, max cell 60, Golem idle facing south. Over the board area, `top 70`, centred: kicker "A BOX-PUSHING SANDBOX" 12 px caps 0.24em `#d9b48f`; "Golem" 88 / 500 / −0.045em / line-height 0.95, `#f3e6d8`, `text-shadow: 0 0 40px rgba(255,180,120,0.25), 0 4px 24px rgba(0,0,0,0.7)`; tagline "A small clay worker, woken by a written word. Push every block onto its rune." 15 px `#cfd3e5` (max 460 px); primary button "Start with t1-01 →" (height 38, padding 0 16) with focus; hint "or pick any level on the left · `Tab` reaches the list" 12 px. Plate, gauge and key hints are hidden. The picker shows Tier 1 expanded and no current level.

### Atlas — "All levels"
Dialog `left 340; right 36; top 28; bottom 28`, padding 24 26, radius 20, `background: rgba(30,24,26,0.8)`, ring `rgba(255,214,170,0.14)`, `blur(24px) saturate(1.2)`. The scene behind gets `filter: blur(2px) brightness(0.5)`. Header: "All levels" 26 / 500 + "7 of 11 solved · Tab and arrows move between cards, Enter plays" 13 px `#9397ab` + close button 34 × 34. One section per tier (kicker in `#d9b48f` + summary), each a 5-column grid, gap 10. Card: padding 8, radius 12, miniature well 104 px high, name 15 / 500, meta 12 px; current = the same ring as in the panel plus "PLAYING"; keyboard focus = `0 0 0 2px #9184d9`. Tier 3: the `t3-01` sample + 4 dashed placeholders.

### Replay sketch (later — layout must already allow it)
Picker lists "Recent runs" (64 × 48 miniature, "#0142", "t2-03 · v7–v9", result tag Solved `#8fe0bd` on `rgba(92,196,155,0.16)` / Lost `#f4a7b0` on `rgba(236,125,138,0.16)` / Failed `#f0c27e` on `rgba(226,164,76,0.16)`, "212 steps"). Actions panel `right 20; top 128; bottom 176; width 290` with mono 12 px rows `#140  move S → true`, current row `rgba(145,132,217,0.2)` + ring, future rows at 50 %. Transport bar `left 340; right 20; bottom 20`: step back / pause (primary) / step forward, speed segmented control 1× 2× 4× 8×, a legend; timeline track 6 px with violet progress, stop markers (error ◆ red, deadlock ■ red, give-up ● grey, half budget ▮ amber, repeated position ● violet), program swaps as 2 px violet lines labelled `v7`, `v8`…, playhead a 14 × 22 cream handle. Board cells not yet seen are under drifting fog; a warm lantern lights Golem's five visible cells.

---

## The scene (canvas)

Draw order, every frame — **static layer cached once per state** (offscreen canvas), the rest redrawn per frame:
1. *(static)* Room background: radial gradient from the lamp (`#47352a` → `#2a2022` → `#18151d` → `#0f1019`) plus soft blotches.
2. *(static)* Stone tray: margin 0.55 cell, thickness 0.4 cell, radius 0.28 cell, drop shadow, speckle, warm edge highlight.
3. *(static)* Floor flagstones inside the walls (only where `inside` = 1).
4. *(static)* Goal runes.
5. *(static)* Cast shadows (walls and blocks, offset `(0.2, 0.16)` cell, blur `0.32` cell, `rgba(8,5,3,0.62)`) + ambient occlusion under north/west walls.
6. *(static)* Walls and blocks, row by row from top to bottom (later rows overlap earlier ones).
7. *(dynamic)* Glows of lit runes (slow pulse).
8. *(dynamic)* Golem, then **re-draw the three cells in the row below Golem** (walls/blocks) so they correctly overlap it.
9. *(dynamic)* Effects (`over`): bump, push dust, rune ignite, solved flares, lost dim, deadlock spotlight/crack/lock, replay fog.
10. *(dynamic)* Lamp (screen blend, flicker ±6 %), dust motes, vignette.

**Level of detail by cell size:** `lod 2` ≥ 40 px (all texture, Golem's clay rings); `lod 1` 26–39 px (less speckle); `lod 0` < 26 px (flat fills, no cracks/marks, no motes). Every kind remains distinct at 20 px — checked in the reference.

### Cell kinds (see `golem-art.js` → `clay.*`)
- **Wall `#`:** top face shifted up by 0.34 cell, `hsl(31,13%,51–57%)` → `hsl(27,12%,38–43%)` gradient + speckle. Front face (`#5b4d42` → `#382e27`, two mortar courses) only where the cell below is not a wall. Lips: lit `rgba(255,232,205,0.26)` on north and `0.15` on west where open; shade `rgba(0,0,0,0.25 / 0.2)` on east/south where open; mortar seams between two walls. 16 neighbour masks are shown in the reference.
- **Floor (inside):** grout `#29211d`, stone inset 0.035 cell, radius 0.05–0.14 cell, `hsl(28,15%,36–45%)` → `hsl(24,15%,25–34%)`; per-cell hash picks tone, wear spot (35 %), crack (22 %). Outside the walls nothing is drawn — only the room.
- **Goal `.`:** bronze `#a68f69` rune: ring r = 0.34 cell, inner ring 0.64 r, 8 marks, centre diamond, 1 px dark under-shadow.
- **Block `$`:** sandstone, inset 0.11 cell, 0.27 cell tall; top `#d2b48c` → `#a08060`, face `#86694d` → `#56422f`; carved seal (circle + stem) dark.
- **Block on goal `*`:** the rune underneath is lit violet; the seal glows `#e7e5fe` with a violet blur; the face gets a violet bottom glow. Different in mark and light, not just hue.
- **Golem `@`:** clay dome, `#e09a6c` → `#b8683f` → `#7e4127`, feet `#7a3f27`, arms; eyes dark ellipses with glowing `#ece9ff` pupils that look toward the last move; glyph on the brow (`#d6d0ff`, violet glow, brighter when acting). Facing north = back view (no eyes, a seam).
- **Golem on goal `+`:** the body is narrower than the rune ring, so the ring stays visible around the feet.
- **Stuck block (deadlock only):** see Motion.

---

## Interactions & behaviour

### Keys and focus
| Key | Where | Action |
|---|---|---|
| ← ↑ → ↓ | board focused | send a move. Ignore `event.repeat` (holding a key would burn ~30 steps/s). `preventDefault`. |
| R | board focused, any status | send restart |
| Enter / Space | on a card | load that level, return focus to the board |
| Esc | anywhere | close the atlas / error notice |
| Tab | — | order: mode tabs → level cards → All levels → board → result buttons |

- The board region is focusable (`tabindex="0"`, `aria-label="Board — arrow keys move Golem, R restarts"`), focused on load, after a level is picked and on click. Arrows only act while it has focus, so arrows inside the list never move Golem.
- Focus ring everywhere: Nocturne's `outline: 2px solid #9184d9; outline-offset: 2px` on `:focus-visible` only.
- Keys are sent immediately; never wait for a reply or an animation.

### Detecting moments (compare the previous and the new state — never decide legality)
- **Bump:** status still `playing`, every map row identical, `steps` = previous + 1. Direction = last key sent.
- **Move:** Golem's cell changed and no block moved.
- **Push:** Golem moved and exactly one `$`/`*` moved one cell in the same direction.
- **Block onto a rune:** a cell changed `.`→`*` (or `+`→`*`). **Off a rune:** `*`→`.`/`+`.
- **Deadlock box:** on `status: lost, reason: deadlock`, the stuck box is the one that moved in the last step (brief).
- **Warning:** the first state where `budget − steps ≤ 0.1 × budget`.

### Motion specs
Rule: **input never waits.** When a new state arrives mid-tween, snap the running tween to its end in one frame and start the next. With `prefers-reduced-motion: reduce`, keep only short fades (column 6).

| Moment | Trigger | Duration | Easing | What moves | Reduced motion |
|---|---|---|---|---|---|
| Idle | no new state for 600 ms | 3.3 s loop | sine | breathe (scale y +3.5 %), blink every 3.7 s, glyph pulse, dust motes, lamp flicker ±6 % | static pose, no motes |
| Move | Golem's cell changed | 140 ms | `cubic-bezier(.2,.7,.3,1)` | slide one cell, walk strip once, eyes turn | jump |
| Push | Golem + one block moved | 160 ms | `cubic-bezier(.3,.6,.35,1)` | Golem leans; the block follows 20 ms later; dust behind the block | jump, no dust |
| Bump | map same, steps + 1 | 200 ms | out 60 ms, then damped spring 140 ms | lunge 0.13 cell, squash, squint, recoil; impact burst + chips at the edge; keycap + "+1" flash 400 ms | amber outline on Golem, 300 ms fade |
| Block onto rune | `.`→`*` | 420 ms | `cubic-bezier(.16,1,.3,1)` | ring expands 0.34 → 0.9 cell and fades; 12 sparks; seal lights; rune settles to a slow pulse | lit state, 150 ms fade |
| Block off rune | `*`→`.` | 300 ms | ease-out | seal and rune glow fade to bronze | 150 ms fade |
| Solved | status → solved | 1.2 s | flare: out; panel `cubic-bezier(.2,.8,.2,1)` | runes flare in a 60 ms stagger (light pillar + ring + sparks); Golem celebrates; result panel rises 24 px + fades in at 300 ms | panel fades in |
| Lost — steps | reason = steps | 900 ms | ease-in-out | last gauge tile goes red; Golem powers down (grey, slump, eyes off); room dims 30 %; panel at 500 ms | grey pose, panel fades |
| Lost — deadlock | reason = deadlock | 1.0 s | crack linear; lock back-out | spotlight closes on the block; crack spreads; red lock pops; outline pulses 0.5 Hz; panel at 600 ms | static mark + outline |
| Steps warning | first state ≤ 10 % left | 600 ms | ease-out | remaining tiles turn amber (20 ms stagger), panel glow, pill appears | instant |
| Reconnecting | socket closed | 400 ms in / 600 ms out | ease | desaturate + dim; ring turns once per 1.6 s | fade only, ring static |
| Error notice | `{type:"error"}` | 220 ms in, 8 s hold | `cubic-bezier(.2,.8,.2,1)` | slides 8 px down + fades | fade |
| Atlas | click / Enter | 220 ms | `cubic-bezier(.2,.8,.2,1)` | scale 0.98 → 1 + fade; scene blurs 2 px, dims | fade |
| Replay fog | a cell seen first time | 500 ms | ease-out | fog puffs fade and drift outward | instant |

Sprite strip timings: idle 8 frames (loop), walk 6 × 4 dirs, push 6 × 4, bump 6 × 4, celebrate 12, power-down 10 (ends on a hold frame). Effects: dust 6, impact 5, ignite 8, sparks 8, flare 10, crack 6, lock 6.

### Reconnect behaviour
On close: status "Reconnecting…" immediately; keys ignored (not queued); after 300 ms the scene filter and centre indicator fade in (avoids flashing on a fast restart). Retries at 0.5, 1, 2, 4 s, then every 5 s; show the attempt and a countdown. After 30 s add "Check that the server is running on 127.0.0.1:8700." On open the server sends the current state → draw it, lift the filter, status "Connected". No toast.

### Solved memory
Solved levels are remembered in `localStorage` (key e.g. `golem.solved` = array of level ids) to draw the checks and tier dots.

## State management
- `socket` status: `connecting | open | reconnecting` + attempt count.
- `levels`: the level list (id, tier, width, height, budget, map).
- `prev`, `state`: last two states (`level, map, inside, steps, budget, status, reason`).
- `lastKey`: direction of the last key sent (bump direction, Golem facing).
- `facing`: N/E/S/W.
- `anim`: the current tween/effect { kind, start, duration } — replaced instantly by a new state.
- `ui`: `atlasOpen`, `error` { detail, until }, `solved` set.
- Derived each state: `warn`, `spentTiles`, `boxesOnGoals`, moment kind (above), deadlock box cell.

## Data contract (from the brief)
- State: `{type:"state", level, map: string[], inside: <mask, shape fixed in v2.2>, steps, budget, status, reason}`. Draw floor only where `inside` is set. Until it exists, the renderer falls back to a flood fill from Golem over non-wall cells (`model()` in `golem-art.js`).
- Level list entries include `map` so cards can draw miniatures.
- Error: `{type:"error", detail}`.

---

## Design tokens (one theme, dark)

**Ground and glass**
| Token | Value | Use |
|---|---|---|
| `--gm-room` | `#18151d` | room behind the tray |
| `--gm-room-lit` | `#47352a` | lamp pool |
| `--gm-panel` | `rgba(30,24,26,0.64)` | glass panels; blur 20 px, saturate 1.15 |
| `--gm-panel-edge` | `rgba(255,214,170,0.10)` | 1 px warm edge |
| `--gm-card` | `rgba(255,255,255,0.025)` | cards |
| `--gm-rule` | `rgba(255,214,170,0.14)` | fading rules |
| `--gm-text` | `#e9e9ed` | Nocturne text |
| `--gm-text-muted` | `#9397ab` | Nocturne neutral-500 |
| `--gm-kicker` | `#d9b48f` | warm labels |

**Game semantics**
| Token | Value | Use |
|---|---|---|
| `--gm-word` | `#9184d9` | Nocturne accent — Golem's glyph, lit runes, current level, primary buttons, focus |
| `--gm-word-hi` | `#d6d0ff` | glyph / seal at full burn |
| `--gm-solved` | `#5cc49b` | solved checks, connected dot (never on the board) |
| `--gm-warn` | `#e2a44c` | last 10 %, reconnecting |
| `--gm-danger` | `#ec7d8a` | lost, stuck block, error |
| `--gm-ember` | `#ffd9b0` | impact, motes, "+1" |

**Material and light (canvas)**
| Token | Value |
|---|---|
| `--gm-stone-top` | `#9a8a79` (±6 % per cell) |
| `--gm-stone-face` | `#54473d` |
| `--gm-flag` | `#6c5e52` (±5 %) |
| `--gm-grout` | `#29211d` |
| `--gm-sandstone` | `#c4a580` |
| `--gm-bronze` | `#a68f69` |
| `--gm-clay` | `#b8683f` |
| `--gm-shadow` | `rgba(8,5,3,0.62)`, offset (0.2, 0.16) cell, blur 0.32 cell |
| `--gm-lamp` | `rgba(255,180,120,0.10)` screen blend |
| `--gm-vignette` | `rgba(6,5,10,0.9)` at 75 % |

Nocturne ramps used for text: neutral-300 `#cfd3e5`, neutral-400 `#b2b6ca`, neutral-500 `#9397ab`, neutral-600 `#75798c`; accent-300 `#d2cefd`, accent-400 `#b5abfc`, accent-100 `#e7e5fe` (see `_ds/…/styles.css`).

**Type — Inter (self-hosted WOFF2, SIL OFL 1.1)**, tabular numerals for all counts.
| Token | Size / line / weight | Tracking | Example |
|---|---|---|---|
| `--gm-type-hero` | 88 / 0.95 / 500 | −0.045em | Golem |
| `--gm-type-plate` | 40 / 1.05 / 500 | −0.025em | t2-03 · 37 / 300 |
| `--gm-type-title` | 24 / 1.15 / 500 | −0.02em | Solved in 64 steps |
| `--gm-type-card` | 15 / 1.3 / 500 | −0.005em | t2-04 |
| `--gm-type-body` | 13 / 1.45 / 400 | 0 | All four blocks are home. |
| `--gm-type-meta` | 12 / 1.4 / 400 | 0 | 11 × 9 · 400 steps |
| `--gm-type-kicker` | 11 / 1.3 / 500, caps | 0.12em | TIER 2 · LEVEL 3 OF 5 |
| `--gm-type-key` | 12 / 1 / 500 | 0 | ← ↑ → ↓ R |

**Spacing** (Nocturne 0.7× density): 3, 6, 8, 11, 17, 22 px; panel insets 18 / 20 px. **Radii:** keycap 6, tag 5, card 12, panel 16, result 20, atlas 20, notice 12.

**Buttons** — Nocturne `.btn` (outlined; 14 / 500; radius 8):
- Primary: border + text `#9184d9`; hover `color-mix(in srgb, #9184d9 12%, transparent)`; pressed 22 % + border `#b5abfc`, text `#d2cefd`; disabled 45 % opacity. On glass the resting fill is `rgba(145,132,217,0.12)`.
- Secondary: border `rgba(255,214,170,0.18)`; hover `rgba(255,226,196,0.07)`; pressed `rgba(255,226,196,0.14)` + border `0.28`.
- Ghost / icon: 26–40 px squares.

**Icons:** Phosphor-style inline SVG, viewBox 256, stroke 16, round caps/joins, `currentColor`: restart, next, check, hourglass, lock, levels (grid), close, error, play, pause, step back, step forward, glyph, reconnect. The path data is in the reference (`Golem Clay.dc.html`, section 05).

## Assets
All art is **original** and generated by the two renderer scripts — no third-party images.
Two valid paths (pick one):
1. **Runtime drawing (zero image files):** ship `golem-art.js` + `golem-clay-fx.js` and draw everything each frame as the reference does.
2. **Baked sheets:** render the same functions into PNG strips at 1× and 2× and commit them. The asset list with file names, frame sizes, counts and sizes (≈ 2 MB total for both densities) is in section 03 of `Golem Clay.dc.html`. Golem frames are 64 × 80 (feet on the bottom 8 px); tiles 64 × 64; walls 64 × 86.

**Fonts:** Inter Regular / Medium / SemiBold as WOFF2 (from github.com/rsms/inter, OFL) — **not included**; add them under `static/fonts/`. Note: the bundled Nocturne `styles.css` contains an `@import` of Google Fonts — **remove it** in production (no external URLs allowed) and use `@font-face` with the local files.

## Files
| File | What it is |
|---|---|
| `brief.md` | The product brief — data formats, constraints, required states. |
| `Golem Clay.dc.html` | **Main reference**: intro, 13 frames, art sheets, asset list, motion specs, UI system. Open in a browser. |
| `GolemClayScreen.dc.html` | The screen used by every frame; prop `frame` = `title, playing, warn, bump, land, solved, lost-steps, deadlock, reconnecting, error, atlas, large, replay`. Its logic class holds exact maps, copy and state → style mappings. |
| `golem-art.js` | **Reusable renderer.** `model()` (map parsing, inside mask), `DIRS.clay` drawing functions, `<golem-scene>` (layered canvas with static-layer cache, IntersectionObserver, retry on zero size) and `<golem-mini>` (picker miniatures). Attributes: `direction map inset facing cellmax still pose fx focus fog phase bare floor`. |
| `golem-clay-fx.js` | **Reusable** poses (`idle walk push bump celebrate powerdown`), effects (`dust impact ignite sparks flare crack lock spotlight fog`) and `<golem-sheet>` (sprite strips). Installs onto `window.GolemArt.DIRS.clay`. |
| `support.js` | Runtime needed only to open the `.dc.html` references. Not for production. |
| `_ds/…/styles.css` | Nocturne design-system stylesheet (tokens + `.btn`, `.seg` classes). |

### Suggested production structure
```
static/
  index.html        – panels markup (picker, plate, gauge, keys, result, notice, atlas)
  style.css         – tokens above as custom properties + panel styles
  app.js            – socket, state diff → moments, input, focus, tween scheduler
  art/golem-art.js  – from this package (clay only)
  art/golem-fx.js   – from golem-clay-fx.js
  fonts/Inter-*.woff2
```
Budgets to keep: 60 fps on 20 × 20 boards (cache the static layer; redraw it only when the map changes), first screen < 1 s, assets ≈ 10 MB max.
