-- Assembles PNG layers/frames into an editable .aseprite file.
-- Params: spec=<json path>. Spec: {w,h,out,layers:[{name,frames:[png...]}],
-- durations:[ms...], tags:[{name,from,to}]} (frames are 1-based in tags).
local spec = json.decode(io.open(app.params["spec"]):read("a"))
local spr = Sprite(spec.w, spec.h, ColorMode.RGB)
local first = spr.layers[1]
local n = #spec.durations
for i = 2, n do spr:newEmptyFrame() end
for i = 1, n do spr.frames[i].duration = spec.durations[i] / 1000 end
for _, l in ipairs(spec.layers) do
  local layer = spr:newLayer()
  layer.name = l.name
  for i, f in ipairs(l.frames) do
    spr:newCel(layer, i, Image{ fromFile = f }, Point(0, 0))
  end
end
spr:deleteLayer(first)
for _, t in ipairs(spec.tags or {}) do
  local tag = spr:newTag(t.from, t.to)
  tag.name = t.name
end
spr:saveAs(spec.out)
