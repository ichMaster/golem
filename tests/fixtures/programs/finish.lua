-- Solves a tier-one level from the map explore.lua left in memory, without looking around.
-- It is the second half of a swap (v2.5). Run alone, it finds no map and gives up.
--
-- It searches the pushes breadth-first over (robot cell, box cell) states on the map in memory.
-- Unknown cells count as walls, and a push into a corner that is not the goal is never tried. Then it
-- plays the moves of the shortest plan, and no other move.

local map = memory.map
if map == nil then give_up("no map in memory") end

local DIRS = {"N", "E", "S", "W"}
local DR = {N = -1, E = 0, S = 1, W = 0}
local DC = {N = 0, E = 1, S = 0, W = -1}

local floor, row, col, box, goal = map.floor, map.row, map.col, map.box, map.goal
if box == nil or goal == nil then give_up("no box or no goal on the map") end
if box == goal then give_up("the box is already on the goal") end

local function key(r, c) return r .. "," .. c end

local function next_cell(k, d)
  local nr, nc = row[k] + DR[d], col[k] + DC[d]
  local n = key(nr, nc)
  if row[n] == nil then row[n], col[n] = nr, nc end
  return n
end

local function dead_corner(k)
  if k == goal then return false end
  local walled = {}
  for _, d in ipairs(DIRS) do walled[d] = not floor[next_cell(k, d)] end
  return (walled.N or walled.S) and (walled.E or walled.W)
end

local start = {robot = map.robot, box = box, from = nil, dir = nil}
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
