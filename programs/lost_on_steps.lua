-- Finds a wall next to it and bumps into it until the step budget runs out: lost on steps.
--
-- Every move costs a step, even one that moves nothing.

local DIRS = {"N", "W", "S", "E"}

local function wall_next_to_me()
  for _, d in ipairs(DIRS) do
    if look(d) == "wall" then return d end
  end
  return nil
end

local target = wall_next_to_me()
while target == nil do
  -- step onto a free neighbour, never into a box, and look again
  for _, d in ipairs(DIRS) do
    local what = look(d)
    if what == "empty" or what == "goal" then
      move(d)
      break
    end
  end
  target = wall_next_to_me()
end

while true do
  move(target)
end
