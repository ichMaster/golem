# Design brief — the Golem game screen

## The project in one paragraph

Golem is a private research sandbox. A robot pushes boxes onto goals on a grid, following classic box-pushing
rules: it pushes one box at a time and never pulls. Later an AI agent will write the Lua program that drives
the robot. This screen comes first: **a person plays the levels with the arrow keys**. The same screen will
later replay the robot's recorded runs. The game rules live on a local server; the page only sends keys and
draws the states the server sends back.

## Who uses it, and where

- One person, the project's owner, on a Mac. The browser opens `http://127.0.0.1:8700/`; the page is never
  on the internet.
- It is a working tool used often and for long stretches, not a product to sell. It should be legible at a
  glance and quiet, so that the board holds the attention.
- Typical window: about 1440 × 900. It must still work at about 1024 × 700 and at a narrow 800 px width.
  There is no phone or touch layout.
- All interface text is in English.

## What to deliver

1. **Frames** for every state listed under "States to show".
2. **A tile set** for the board's cell kinds (see the legend below), shown at 32 px and 64 px.
3. **Design tokens:** colours for a light and a dark theme (the page follows the system setting), a type
   scale, spacing and corner radii. Name them so that they can become CSS custom properties.
4. **Interaction notes:** keyboard focus, what happens on each key, the reconnect behaviour, and any motion.
5. **Optional:** a static HTML/CSS mock. If you make one, keep within the constraints below, so that it can
   be the starting point for the real page.
6. **An answer to the open question** at the end of this brief.

## Hard constraints (the implementation will follow them)

- **Three files:** one HTML page, one stylesheet and one plain JavaScript file. No framework, no build step,
  no package.
- **No external URLs at all:** no CDN, no web fonts, no remote images. Use the system font stack (e.g.
  `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`) and a system monospace for numbers and ids.
  Icons are inline SVG.
- **The board is drawn on a `<canvas>`.** Tiles must therefore be drawable with simple shapes or small
  inline images: flat fills, strokes, simple glyphs. Avoid effects that need heavy filters.
- **No game logic in the page.** The page never decides whether a move is legal. It may compare two states
  it received, for example to notice that the map didn't change.
- **An original look.** Don't copy the art, sprites or colours of any existing box-pushing game. The robot
  is called Golem; how it looks is yours to decide.

## What the page receives

**A state**, after every key and right after (re)connecting:

```json
{"type": "state", "level": "training/tier1/t1-02",
 "map": ["########", "#   .  #", "#  $   #", "#  @   #", "#      #", "########"],
 "steps": 1, "budget": 200, "status": "playing", "reason": null}
```

- `map` is the board as text, one string per row. Rows can differ in length, and spaces before the first
  wall belong to nothing. The legend:

  | Char | Cell | Notes |
  |---|---|---|
  | `#` | wall | |
  | space | floor, or empty space outside the walls | see the open question |
  | `.` | goal | |
  | `$` | box | |
  | `*` | box on a goal | must differ from `$` by more than colour |
  | `@` | robot | |
  | `+` | robot standing on a goal | the goal must stay visible under the robot |

- `steps` against `budget`: every key press costs one step, **even when nothing moves** (bumping a wall or
  pushing a blocked box). The level is lost when `steps` reaches `budget`.
- `status` is `playing`, `solved` or `lost`. When the level is lost, `reason` is `steps` (out of steps) or
  `deadlock` (a box was pushed into a corner that is not a goal, so it can never move again). The page does
  not know which box caused the deadlock.

**The level list:**

```json
{"levels": [{"id": "training/tier1/t1-01", "tier": "tier1", "width": 7, "height": 5,
             "budget": {"steps": 200, "instructions": 1000000}}]}
```

- Today there are three tier-1 levels, from 7 × 5 to 8 × 6 cells. With this screen comes a set of ten
  across tiers 1 and 2.
- Tier 3 arrives later. The later tiers bring more boxes, corridors and traps, and boards up to about
  20 × 20. The board must scale its cell size to fit, between about 20 and 64 px per cell.

**An error**, rarely: `{"type": "error", "detail": "unknown level"}`.

**The connection** can drop, for example when the server restarts. The page reconnects by itself, and the
server then sends the current state, so the game continues where it was.

## Screen anatomy (required now)

1. **The board:** the largest element, centred in its area. Show the grid clearly enough to count cells.
2. **The level header:** the level's name (`t1-02`), its tier, and its size.
3. **The step counter:** `37 / 200`, with a bar or another reading of how much is left. It must be hard to
   miss once the steps are almost spent, say in the last 10 %.
4. **The status banner:**
   - "Solved in 37 steps";
   - "Lost — out of steps";
   - "Lost — a box is stuck in a corner".

   Each comes with the next actions: `R` to restart, or picking another level. While playing, the banner is
   absent or neutral.
5. **The level picker:** the training levels grouped by tier. Each entry shows its name, size and step
   budget, and the current level is marked. It is always reachable, as a side panel or a drawer, and works
   with the mouse and with `Tab`.
6. **Key hints:** `← ↑ → ↓ move · R restart`.
7. **Bump feedback:** a key that cost a step but changed nothing (the map is the same, `steps` + 1) should
   show briefly, for example a small shake or flash on the robot. This tells the player why the counter
   rose.
8. **The connection indicator:** connected, or reconnecting. While reconnecting, the board is dimmed and
   keys are ignored.
9. **The error notice:** a small, dismissable message, such as "Unknown level".
10. **The empty state:** before any level is loaded, a prompt to pick one.

**Keyboard and focus:** the arrow keys always move the robot while the board area has focus, and `R`
restarts. The picker is reached with the mouse or `Tab`, so that arrows inside a list never fight the
board.

**Motion:** optional. A short slide of the robot and the box between states, 120 ms or less, is fine. Input
must never wait for an animation: a new state replaces the old one at once. Respect
`prefers-reduced-motion`.

## States to show (frames)

1. The empty state: no level loaded, picker visible.
2. Playing: mid-level, a few boxes, the robot next to a box.
3. Playing with few steps left: the counter's warning state.
4. A bump: the robot against a wall.
5. Solved.
6. Lost — out of steps.
7. Lost — a box stuck in a corner.
8. Reconnecting.
9. An error notice over a playing board.
10. The picker open with all three tiers (tiers 2–3 can be placeholders), the current level marked.
11. A large tier-3-sized board (about 20 × 20) at 1024 × 700, to show the scaling.
12. The same playing frame in the dark theme.

## Later, leave room for it: the replay mode

Not needed in this round, but the layout must have room for it without a redesign. One sketch frame is
welcome. Replay plays back a recorded run of the robot's program, frame by frame:

- **A run picker:** recent runs, each with its level, its result (solved, lost, failed) and its step count.
- **Transport:** play, pause, step back, step forward, and a speed setting.
- **A timeline across the run's steps**, with markers for:
  - **stops**, where the program paused on an event. The kinds: an error, a deadlock, a give-up, half the
    budget spent, and a repeated position;
  - **swaps**, where a new program version took over, labelled with its version number, e.g. `v7`.
- **An action list** in step order, with the current one highlighted: `#140 move E → true`,
  `#141 look N → "box"`. The commands are `move`, `look`, `here`, `boxes_left` and `give_up`.
- **The robot's view:** the robot sees only its own cell and the four next to it. Cells it has not seen
  yet in the run are greyed out on the board; seen cells draw normally.

## Out of scope

- The game rules and any logic.
- The server, the command-line tool, and the agent's own views.
- Accounts and settings.
- Sound.
- Phone layouts and touch input.
- Onboarding beyond the key hints.

## Open question for you

The `map` uses a space both for the floor inside the walls and for the empty area outside them. If your
design draws the floor differently from the background, say so. The server can then also send which cells
are inside the walls. If floor and background can look the same, nothing needs to change.
