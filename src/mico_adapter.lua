-- mico_adapter.lua — Abstracted policy interface for ARIA agents
-- Swap: stub → Optuna → Qdrant → Production ARIA

local json = require 'hawk/json'

local MicoAdapter = {}
MicoAdapter.__index = MicoAdapter

local function append_lines(filename, lines)
  if love and love.filesystem and love.filesystem.append then
    for _, line in ipairs(lines) do
      love.filesystem.append(filename, line .. "\n")
    end
    return true
  end

  local file, err = io.open(filename, "a")
  if not file then
    return false, err
  end

  for _, line in ipairs(lines) do
    file:write(line .. "\n")
  end

  file:close()
  return true
end

function MicoAdapter.new(policy_name, seed)
  local self = setmetatable({}, MicoAdapter)
  self.policy_name = policy_name or "random"
  self.seed = seed or os.time()
  self.corrections_applied = 0
  self.episode_telemetry = {}

  math.randomseed(self.seed)
  print(string.format("MICO[%s] seeded=%d", self.policy_name, self.seed))
  return self
end

function MicoAdapter:observe(obs)
  self.last_obs = obs
end

function MicoAdapter:act(state)
  local action = { dx = 0, dy = 0, force = 0 }

  if self.policy_name == "random" then
    action.dx = (math.random() - 0.5) * 0.2
    action.dy = (math.random() - 0.5) * 0.2
    action.force = math.random() * 0.1
  elseif self.policy_name == "optuna" then
    -- ARIA policy weights (from your Optuna trials)
    local w_meditation = 0.62 -- best trial
    action.force = w_meditation * (15.0 - state.eccentricity) * 0.01
    action.dx = math.sin(state.han_eigenvalue) * 0.05
  elseif self.policy_name == "troy_abed" then
    -- Troy (planner) + Abed (critic) coordination
    action.force = self:troy_plan(state)
    action.dx = self:abed_critique(state)
  end

  table.insert(self.episode_telemetry, {
    step = #self.episode_telemetry + 1,
    seed = self.seed,
    obs = state,
    action = action,
    policy = self.policy_name
  })

  return action
end

function MicoAdapter:train_step(obs, action, reward)
  -- NDJSON training signal (Optuna compatible)
  local step_log = {
    step = #self.episode_telemetry,
    reward = reward,
    obs_eccentricity = obs.eccentricity,
    action_force = action.force,
    policy = self.policy_name
  }

  table.insert(self.episode_telemetry, step_log)
end

function MicoAdapter:apply_correction(name)
  self.corrections_applied = self.corrections_applied + 1
  print(string.format("MICO CORRECTION[%s]: %d total", name, self.corrections_applied))
end

function MicoAdapter:flush_telemetry(filename)
  if #self.episode_telemetry == 0 then
    return
  end

  local lines = {}
  for _, tel in ipairs(self.episode_telemetry) do
    table.insert(lines, json.encode(tel))
  end

  local ok, err = append_lines(filename or "mico_telemetry.ndjson", lines)
  if not ok then
    print(string.format("MICO telemetry flush failed: %s", err or "unknown error"))
    return
  end

  self.episode_telemetry = {}
end

-- Policy implementations
function MicoAdapter:troy_plan(state)
  return (15.0 - state.eccentricity) * 0.02
end

function MicoAdapter:abed_critique(state)
  local hausdorff_error = math.abs(state.eccentricity - 15.0)
  if hausdorff_error > 0.002 then
    return math.sin(state.han_eigenvalue) * 0.1
  end

  return 0
end

return MicoAdapter
