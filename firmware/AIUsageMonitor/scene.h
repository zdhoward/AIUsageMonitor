#pragma once
// Generic scene engine: gradient sky, infinitely scrolling parallax layers,
// animated layers and reusable effects, all described by data generated from
// assets/library/<scene>/scene.json (see scripts/asset_convert.py).
#include "anim.h"

enum SceneFx : uint8_t { FX_STARS = 1, FX_RAIN, FX_SNOW, FX_LIGHTNING };

struct SceneLayer {
  const AnimAsset* asset;
  int16_t y;          // top of the layer's canvas on the 240-high scene
  int16_t speed16;    // scroll speed in px/s * 16; positive moves content left
  uint16_t period;    // horizontal repeat distance (canvas width + gap)
  uint16_t frameMs;   // 0: use the asset's own frame durations
};
struct SceneEffect {
  uint8_t type, density, color, front;  // front: draw above the layers
};
struct SceneDef {
  const char* id;
  const char* name;
  uint8_t top[3], bottom[3];  // sky gradient, RGB888
  const SceneLayer* layers;
  uint8_t layerCount;
  const SceneEffect* fx;
  uint8_t fxCount;
  const uint8_t* lut;  // theme palette remap, nullptr for original colours
};

void sceneDraw(const Canvas8& c, const SceneDef& s, uint32_t nowMs);
