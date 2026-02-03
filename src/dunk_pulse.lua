local window = require 'window'

local DunkPulse = {}
DunkPulse.__index = DunkPulse

local TTL_FRAMES = 18
local PULSE_BEAT_INDEX = 15

local SHADER_CODE = [[
uniform float u_pulse_intensity;
uniform float u_pulse_progress;
uniform int u_pulse_beatIndex;
uniform int u_time_frame;
uniform float u_seed;

float rand(float x) {
  return fract(sin(x) * 43758.5453123);
}

vec4 effect(vec4 color, Image texture, vec2 texture_coords, vec2 screen_coords) {
  vec3 base = vec3(0.05, 0.05, 0.06);

  float p = 1.0 - pow(1.0 - u_pulse_progress, 3.0);
  float intensity = u_pulse_intensity * p;

  vec3 pulseColor = vec3(1.0, 0.91, 0.22) * intensity;

  float shake = (rand(float(u_pulse_beatIndex) + u_seed) - 0.5) * 0.02 * intensity;
  vec2 uv = texture_coords + vec2(shake, shake);

  float vignette = smoothstep(0.8, 0.4, length(uv - vec2(0.5)));
  vec3 colorOut = mix(base, pulseColor, intensity * (1.0 - vignette));

  return vec4(colorOut, intensity);
}
]]

function DunkPulse.new()
  local pulse = {}
  setmetatable(pulse, DunkPulse)
  pulse.frameIndex = 0
  pulse.lastBeatIndex = nil
  pulse.visualPulseRef = { current = nil }
  pulse.shader = nil
  pulse.whitePixel = nil
  return pulse
end

function DunkPulse:load()
  if self.shader then
    return
  end

  self.shader = love.graphics.newShader(SHADER_CODE)

  local imageData = love.image.newImageData(1, 1)
  imageData:setPixel(0, 0, 1, 1, 1, 1)
  self.whitePixel = love.graphics.newImage(imageData)
end

function DunkPulse:tick()
  self.frameIndex = self.frameIndex + 1

  if not self.visualPulseRef.current then
    return
  end

  local pulse = self.visualPulseRef.current
  local progress = (self.frameIndex - pulse.startFrame) / pulse.ttlFrames

  if progress >= 1 then
    self.visualPulseRef.current = nil
  end
end

function DunkPulse:onBeatOnset(beatIndex, frameIndex)
  if beatIndex ~= PULSE_BEAT_INDEX then
    return
  end

  if self.lastBeatIndex == beatIndex then
    return
  end

  self.lastBeatIndex = beatIndex

  self.visualPulseRef.current = {
    beatIndex = beatIndex,
    startFrame = frameIndex or self.frameIndex,
    ttlFrames = TTL_FRAMES,
    intensity = 1.0,
  }
end

function DunkPulse:applyUniforms()
  if not self.shader then
    return
  end

  local pulse = self.visualPulseRef.current
  local intensity = 0.0
  local progress = 0.0
  local beatIndex = self.lastBeatIndex or -1

  if pulse then
    progress = math.min(1, (self.frameIndex - pulse.startFrame) / pulse.ttlFrames)
    intensity = pulse.intensity
    beatIndex = pulse.beatIndex
  end

  self.shader:send('u_pulse_intensity', intensity)
  self.shader:send('u_pulse_progress', progress)
  self.shader:send('u_pulse_beatIndex', math.floor(beatIndex))
  self.shader:send('u_time_frame', math.floor(self.frameIndex))
  self.shader:send('u_seed', (beatIndex % 997) / 997)
end

function DunkPulse:draw()
  if not self.shader or not self.whitePixel then
    return
  end

  self:applyUniforms()

  local blendMode, alphaMode = love.graphics.getBlendMode()
  local currentShader = love.graphics.getShader()

  love.graphics.setShader(self.shader)
  love.graphics.setBlendMode('add', 'alphamultiply')
  love.graphics.setColor(1, 1, 1, 1)
  love.graphics.draw(self.whitePixel, 0, 0, 0, window.width, window.height)

  love.graphics.setBlendMode(blendMode, alphaMode)
  love.graphics.setShader(currentShader)
end

return DunkPulse.new()
