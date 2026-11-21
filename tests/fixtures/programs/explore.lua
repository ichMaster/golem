-- explore.lua: maps a tier-one level into memory without pushing the box, then gives up "mapped".
-- It is the first half of a swap (v2.5): finish.lua, swapped in on that give-up, solves the level
-- from the map alone.
--
-- The robot explores depth-first from the start and never learns its absolute position, so the map
-- is kept relative to the start: (0, 0) is where it began. It never steps into the box, so exploring
-- pushes nothing, and it walks back along its path, so it ends where it began.
--
-- memory.map holds what finish.lua needs, all keyed "row,col":
--   floor  -- key -> true for every floor cell found (the box's cell included)
--   row, col -- key -> its row and column, for every cell looked at
--   box, goal -- the keys of the box and of the goal, or nil when not found
--   robot  -- the key of the robot's cell when it gave up

local DIRS = {"N", "E", "S", "W"}
local DR = {N = -1, E = 0, S = 1, W = 0}
local DC = {N = 0, E = 1, S = 0, W = -1}
local BACK = {N = "S", E = "W", S = "N", W = "E"}

local function key(r, c) return r .. "," .. c end

local floor, known, row, col = {}, {}, {}, {}
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
memory.map = {floor = floor, row = row, col = col, box = box, goal = goal, robot = key(r, c)}
give_up("mapped")
