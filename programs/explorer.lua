-- Explores the room without pushing anything, then gives up with the map it saw.
--
-- The robot never learns its absolute position, so the map is kept relative to the start: (0, 0).
-- It looks in every direction from every floor cell it can reach, and steps only onto empty cells
-- and goals, never into a box. The map it reports, one row per "/":
--   # wall, $ box, * box on a goal, . goal, @ the start (+ on a goal), space floor, ? never seen.

local DIRS = {"N", "E", "S", "W"}
local DR = {N = -1, E = 0, S = 1, W = 0}
local DC = {N = 0, E = 1, S = 0, W = -1}
local BACK = {N = "S", E = "W", S = "N", W = "E"}

local function key(r, c) return r .. "," .. c end

local seen = {}  -- key -> one map character
local top, bottom, left, right = 0, 0, 0, 0
local r, c = 0, 0

local function mark(row, col, char)
  seen[key(row, col)] = char
  top, bottom = math.min(top, row), math.max(bottom, row)
  left, right = math.min(left, col), math.max(right, col)
end

mark(0, 0, here() == "goal" and "+" or "@")

local CHARS = {wall = "#", box = "$", box_on_goal = "*", goal = ".", empty = " "}

local function explore()
  for _, d in ipairs(DIRS) do
    local nr, nc = r + DR[d], c + DC[d]
    if seen[key(nr, nc)] == nil then
      local what = look(d)
      mark(nr, nc, CHARS[what])
      if what == "empty" or what == "goal" then
        move(d); r, c = nr, nc
        explore()
        move(BACK[d]); r, c = r - DR[d], c - DC[d]
      end
    end
  end
end

explore()

local rows = {}
for row = top, bottom do
  local line = {}
  for col = left, right do line[#line + 1] = seen[key(row, col)] or "?" end
  rows[#rows + 1] = table.concat(line)
end
give_up(table.concat(rows, "/"))
