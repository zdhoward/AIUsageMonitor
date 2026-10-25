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
// Full-screen procedural backdrop drawn instead of the sky gradient.
enum SceneGenType : uint8_t {
  GEN_PATTERNS = 1, GEN_PLASMA, GEN_WARP, GEN_MATRIX,
  GEN_FIRE, GEN_LAVA, GEN_AURORA, GEN_LIFE, GEN_RIPPLE, GEN_FIREWORKS, GEN_VIDEOEQ, GEN_SPECTRE
};
// Simulation generators: scale = cell size, vx16 = speed * 16 (fire: wind),
// vy16 = density / intensity / count, or the pinned mode (video EQ, spectre).
struct SceneGen {
  uint8_t type, scale;      // scale: pattern tile zoom / plasma block size
  int16_t vx16, vy16;       // pattern scroll, px/s * 16; warp: speed in vx16;
                            // matrix: fall speed rows/s * 16, vy16 = % of columns raining
  uint16_t seconds;         // pattern hold time before the next tile
  const uint8_t* tiles;     // 16x16 1-bit tiles, 32 bytes each, MSB = left
  uint8_t tileCount;
  const uint8_t* colors;    // RGB332: pattern bg/fg pairs, or plasma/warp gradient stops
  uint8_t colorCount;
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
  const SceneGen* gen;  // optional procedural backdrop
  const uint8_t* const* cycle;  // optional theme cycle: palette maps to cross-fade through
  uint8_t cycleCount;
  uint16_t holdS;   // seconds each theme holds
  uint16_t fadeDs;  // cross-fade length, tenths of a second
};

void sceneDraw(const Canvas8& c, const SceneDef& s, uint32_t nowMs);
