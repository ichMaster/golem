-- Calls a nil value on line 6, so the run fails with a Lua error that names the line.

local plan = {"E", "E"}
move(plan[1])
local finish = nil
finish(plan)
