-- Looks around once and gives up, with what it saw as the reason.

local seen = {}
for _, d in ipairs({"N", "E", "S", "W"}) do
  seen[#seen + 1] = d .. "=" .. look(d)
end
give_up(table.concat(seen, " ") .. " here=" .. here() .. " boxes_left=" .. boxes_left())
