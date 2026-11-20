-- Solves a tier-one level (one box, one goal, an open room) with the robot API alone.
-- It solves training/tier1/t1-01, t1-02 and t1-03.
--
-- 1. Explore the room depth-first from the start. The robot never learns its absolute position,
--    so the map is kept relative to the start: (0, 0) is where it began. It never steps into the
--    box while exploring, so exploring pushes nothing.
-- 2. Search the pushes breadth-first over (robot cell, box cell) states on the explored map.
--    Unknown cells count as walls, and a push into a corner that is not the goal is never tried.
-- 3. Play the moves of the shortest plan.

local DIRS = {"N", "E", "S", "W"}
local DR = {N = -1, E = 0, S = 1, W = 0}
local DC = {N = 0, E = 1, S = 0, W = -1}
local BACK = {N = "S", E = "W", S = "N", W = "E"}

local function key(r, c) return r .. "," .. c end

local floor = {}      -- key -> true for every known floor cell (the box's cell included)
local known = {}      -- key -> true for every cell looked at, wall or floor
local row, col = {}, {}
local goal, box
local r, c = 0, 0

local function note(k, nr, nc) known[k] = true; row[k], col[k] = nr, nc end

note(key(0, 0), 0, 0)
floor[key(0, 0)] = true
if here() == "goal" then goal = key(0, 0) end

local function explore()
  for _, d in ipairs(DIRS) do
    local nr, nc = r + DR[d], c + DC[d]
    local k = key(nr, nc)
    if not known[k] then
      note(k, nr, nc)
      local seen = look(d)
      if seen == "box" or seen == "box_on_goal" then
        floor[k] = true
        box = k
        if seen == "box_on_goal" then goal = k end
      elseif seen ~= "wall" then
        floor[k] = true
        if seen == "goal" then goal = k end
        move(d); r, c = nr, nc
        explore()
        move(BACK[d]); r, c = r - DR[d], c - DC[d]
      end
    end
  end
end

explore()
if box == nil or goal == nil then give_up("no box or no goal found") end
if box == goal then give_up("the box is already on the goal") end

local function next_cell(k, d)
  local nr, nc = row[k] + DR[d], col[k] + DC[d]
  local n = key(nr, nc)
  if not known[n] then note(n, nr, nc) end
  return n
end

local function dead_corner(k)
  if k == goal then return false end
  local walled = {}
  for _, d in ipairs(DIRS) do walled[d] = not floor[next_cell(k, d)] end
  return (walled.N or walled.S) and (walled.E or walled.W)
end

local start = {robot = key(r, c), box = box, from = nil, dir = nil}
local queue, head, visited = {start}, 1, {[start.robot .. "|" .. start.box] = true}
local found
while head <= #queue do
  local s = queue[head]
  head = head + 1
  if s.box == goal then found = s break end
  for _, d in ipairs(DIRS) do
    local target, moved_box = next_cell(s.robot, d), s.box
    local ok = floor[target]
    if ok and target == s.box then
      local beyond = next_cell(target, d)
      ok = floor[beyond] and not dead_corner(beyond)
      moved_box = beyond
    end
    local id = target .. "|" .. moved_box
    if ok and not visited[id] then
      visited[id] = true
      queue[#queue + 1] = {robot = target, box = moved_box, from = s, dir = d}
    end
  end
end
if found == nil then give_up("no plan reaches the goal") end

local plan, s = {}, found
while s.from do table.insert(plan, 1, s.dir); s = s.from end
for _, d in ipairs(plan) do move(d) end
