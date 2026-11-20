# Design brief — the Golem game screen

The design made from this brief is "Clay and stone": [golem-clay/README.md](golem-clay/README.md). The
phases that build it are v3.1–v3.3 in [ROADMAP.md](../ROADMAP.md).

## The project in one paragraph

Golem is a private research sandbox. A robot pushes boxes onto goals on a grid, following classic box-pushing
rules: it pushes one box at a time, never pulls, and a box pushed into a corner that isn't a goal is stuck
for good. Later an AI agent will write the Lua program that drives the robot. This screen comes first: **a
person plays the levels with the arrow keys**. The same screen will later replay the robot's recorded runs.
The game rules live on a local server; the page sends keys and draws the states the server sends back.

## The ambition

**Make it beautiful.** This is the owner's own game, played often and for long sessions. It should look and
feel like a polished, award-quality indie puzzle game:
- rich, crafted art and a characterful robot hero;
- lighting and depth;
- satisfying motion on every action;
- an interface (HUD, panels, typography) designed with the same care as the board.

Two things are not negotiable:
- **Legibility:** at a glance, and at the smallest cell size, the player must tell every cell kind apart.
- **Speed:** a key press must feel instant.

The look must be **original**. Don't copy the art, sprites, palette or interface of any existing
box-pushing game.

## Who uses it, and where

- One person, the owner, on a MacBook with a Retina display. The browser opens `http://127.0.0.1:8700/`;
  the page is never on the internet.
- Typical window: about 1440 × 900. It must still work at about 1024 × 700 and at a narrow 800 px width.
  There is no phone or touch layout.
- All interface text is in English.

## Art directions to explore

Explore **three directions**, each as one key frame of the playing state, before developing one fully. Here
are three starting points; replace any of them with a stronger idea of your own.

**A. Clay and stone.**
- The idea comes from the golem of legend: a figure shaped from clay and brought to life by a written word.
  In this project, the agent's program is that word.
- The robot is a small sculpted clay golem, with a glyph on its forehead that glows when it acts.
- Walls are hewn stone, the floor is worn flagstone, and the boxes are carved stone blocks or heavy
  crates.
- Goals are inlaid rune circles that ignite when a block settles on them.
- Warm workshop light, soft shadows, and a tactile, hand-made, stop-motion feel.

**B. Precision laboratory.**
- A sleek experimental chamber: dark glass and brushed metal.
- The robot is a small articulated machine with expressive light "eyes".
- Goals are projected holographic pads, and boxes are cargo modules with status lights.
- Cool, cinematic lighting with restrained colour accents.

**C. Tabletop diorama.**
- The level is a tiny handcrafted miniature world, seen from a three-quarter top-down angle.
- Walls and objects have visible height, and they cast and receive soft shadows.
- The robot is a charming figurine.
- Depth comes from layering and draw order on the 2D canvas, not from a 3D engine.

## What to deliver

1. **Three direction key frames** (above), then the full set for the chosen one.
2. **Frames** for every state under "States to show".
3. **The art:** the tile set for every cell kind, with variants so that large floors and walls don't look
   repetitive. Walls need edge and corner pieces that join cleanly on ragged maps. Deliver the robot as a
   sprite set: idle, walking in four directions, pushing in four directions, bumping, celebrating and
   powering down. Effects sprites too. Everything at 1× and 2× (Retina).
4. **An asset list:** every image with its size, frame count and file name, ready to be committed as files.
5. **Motion specs:** for each animation, its duration, easing and what triggers it (see "Motion and
   effects").
6. **The UI system:** colour and lighting tokens, the type scale, panel styles, icons, and the button and
   focus states, named so that they can become CSS custom properties. Provide light and dark variants if
   the chosen direction supports both. Otherwise one theme is fine.
7. **Optional:** an HTML/CSS/canvas mock within the technical frame below. It can become the starting point
   for the real page.

## The technical frame (what makes rich graphics possible here)

The page is plain HTML, CSS and JavaScript served by the local server, and it is drawn on a `<canvas>`.
Within that, there is plenty of room.

**Allowed, and welcome:**
- Image assets (PNG sprite sheets at 1× and 2×, or SVG) and font files (WOFF2) committed to the
  repository and served by the same server. Their licences must allow a public MIT repository: your own
  art, or fonts under the OFL.
- Layered canvas rendering: background, floor, shadows, objects, the robot, effects, and lighting
  overlays drawn with gradients and blend modes.
- Sprite animation, particles, easing, and an ambient background animation at 60 fps.
- Crisp drawing at the device pixel ratio.
- CSS for the interface: gradients, shadows, `backdrop-filter`, transitions.

**Not allowed:**
- A framework or library: no React, no game engine, no three.js.
- A build step: every asset must be a ready-to-serve file.
- Any external URL: no CDN, no remote fonts or images.
- Game logic in the page. The page never decides whether a move is legal. It may compare two states it
  received, for example to see which box moved.

**Budgets:**
- 60 fps on boards up to about 20 × 20 cells on a MacBook;
- the first screen ready in under a second from the local server;
- assets reasonably small, around 10 MB in all.

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
  | space | floor inside the walls, or empty space outside them | the state says which (`inside`, below) |
  | `.` | goal | |
  | `$` | box | |
  | `*` | box on a goal | must differ from `$` by more than colour |
  | `@` | robot | |
  | `+` | robot standing on a goal | the goal must stay visible under the robot |

- `inside` says which cells lie inside the walls, so the floor can be drawn differently from the
  surroundings. Its exact shape is fixed when the screen is built (v3.1), for example a mask with the same
  rows as `map`.
- `steps` against `budget`: every key press costs one step, **even when nothing moves** (bumping a wall or
  pushing a blocked box). The level is lost when `steps` reaches `budget`.
- `status` is `playing`, `solved` or `lost`. When the level is lost, `reason` is `steps` (out of steps) or
  `deadlock` (a box was pushed into a corner that is not a goal). Which box got stuck is not sent, but it
  is always the box that moved in the last step. The page finds it by comparing the last two states.

**The level list:** each training level's id, tier, width, height and step budget, and its map in the same
text form as `map`, so the picker's cards can show a miniature of each level.
- Today there are three tier-1 levels, from 7 × 5 to 8 × 6 cells. With this screen comes a set of ten
  across tiers 1 and 2.
- Tier 3 arrives later. The later tiers bring more boxes, corridors and traps, and boards up to about
  20 × 20. The board scales its cell size to fit, between about 20 and 64 px per cell.

**An error**, rarely: `{"type": "error", "detail": "unknown level"}`.

**The connection** can drop, for example when the server restarts. The page reconnects by itself, and the
server then sends the current state, so the game continues where it was.

## Screen anatomy (required now)

1. **The board:** the hero of the screen, framed and lit.
2. **The level plate:** the level's name (`t1-02`), its tier and its size.
3. **The step gauge:** `37 / 200`, shown as a crafted gauge or meter. It changes character in the last
   10 % of the budget.
4. **The result moments:**
   - "Solved in 37 steps": a celebration;
   - "Lost — out of steps";
   - "Lost — a box is stuck in a corner", with the stuck box marked on the board.

   Each comes with the next actions: `R` to restart, or another level.
5. **The level picker:** the training levels grouped by tier, as designed cards. Each shows a miniature of
   the level's map in the chosen art, its name, size and step budget, and the current level is marked. If you want a "solved" mark, the page can
   remember solved levels locally in the browser. It is reachable at any time and works with the mouse and
   with `Tab`.
6. **Key hints:** `← ↑ → ↓ move · R restart`, styled as keycaps.
7. **The connection state:** connected, or reconnecting. While reconnecting, the scene dims or
   desaturates and keys are ignored.
8. **The error notice:** a small, dismissable message, such as "Unknown level".
9. **The empty state:** before any level is loaded, an inviting title scene (the robot waiting, idle) with
   a prompt to pick a level.

**Keyboard and focus:** the arrow keys always move the robot while the board has focus, and `R` restarts.
The picker is reached with the mouse or `Tab`, so that arrows inside a list never fight the board.

## Motion and effects

Every action should feel physical and rewarding, without slowing the player down.

| Moment | Suggested treatment |
|---|---|
| Idle | a gentle breathing or blinking loop; ambient light or dust in the scene |
| A move | a short walk to the next cell, 120–160 ms, eased |
| A push | the robot leans in, and the box slides with a little weight and dust |
| A bump (a step spent, nothing moved) | the robot nudges the wall or the blocked box and recoils, with a small impact, so the player sees why the counter rose |
| A box onto a goal | the goal ignites, with a light pulse and maybe a few particles; the box shows it is placed |
| A box off a goal | the glow fades |
| Solved | every goal flares; a short celebration under 1.5 s; the result panel rises |
| Lost on steps | the robot powers down or dims; the gauge empties dramatically |
| Lost on deadlock | the stuck box cracks, darkens or shows a lock mark, and the camera draws the eye to it |
| Reconnecting | the scene desaturates, with a calm waiting indicator |

**Rules for motion:**
- Input never waits for an animation. If a new state arrives mid-animation, finish quickly or jump to it.
- With `prefers-reduced-motion`, keep only short fades.

## States to show (frames)

1. The title or empty state: no level loaded, the picker visible.
2. Playing: mid-level, several boxes, one already on a goal, the robot next to a box.
3. Playing with few steps left: the gauge's warning state.
4. A bump against a wall, as a still from the motion.
5. A box landing on a goal, as a still from the motion.
6. Solved, the celebration.
7. Lost — out of steps.
8. Lost — a box stuck in a corner, with the box marked.
9. Reconnecting.
10. An error notice over a playing board.
11. The picker with all three tiers (tiers 2–3 can be placeholders), the current level marked.
12. A large tier-3-sized board (about 20 × 20) at 1024 × 700, to show the scaling.

## Later, leave room for it: the replay mode

Not needed in this round, but the layout must take it without a redesign, and one sketch frame is
welcome. Replay plays back a recorded run of the robot's program, frame by frame, in the same art:

- **A run picker:** recent runs, each with its level, its result (solved, lost, failed) and its step count.
- **Transport:** play, pause, step back, step forward, and a speed setting.
- **A timeline across the run's steps**, with markers for:
  - **stops**, where the program paused on an event. The kinds: an error, a deadlock, a give-up, half the
    budget spent, and a repeated position;
  - **swaps**, where a new program version took over, labelled with its version number, e.g. `v7`.
- **An action list** in step order, with the current one highlighted: `#140 move E → true`,
  `#141 look N → "box"`. The commands are `move`, `look`, `here`, `boxes_left` and `give_up`.
- **The robot's view:** the robot sees only its own cell and the four next to it. Cells it hasn't seen yet
  are hidden under fog or darkness, which lifts as the robot explores. This is a strong visual moment.

## Out of scope

- The game rules and any logic.
- The server, the command-line tool, and the agent's own views.
- Accounts and settings.
- Sound.
- Phone layouts and touch input.
