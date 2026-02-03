local queue = require 'queue'

local BeatEvents = {}
BeatEvents.__index = BeatEvents

function BeatEvents.new()
  local events = {}
  events.queue = queue.new()
  setmetatable(events, BeatEvents)
  return events
end

function BeatEvents:emitBeatOnset(payload)
  self.queue:push('beat_onset', payload)
end

function BeatEvents:pollBeatOnset()
  return self.queue:poll('beat_onset')
end

return BeatEvents.new()
