-- On t1-01: pushes the box into the top-right corner, so the level is lost on deadlock.
--
-- The box starts east of the robot. The robot goes round it, pushes it north against the wall,
-- then pushes it east along the wall into the corner, which is not a goal.

for _, d in ipairs({"S", "E", "N", "W", "N", "E", "E"}) do
  move(d)
end
give_up("the box did not reach a corner on this level")
