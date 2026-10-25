#pragma once
// Live scene tuning: a compact binary override for one compiled scene's
// parameters (sky, layer speeds/positions, effects, theme, generator settings,
// theme cycle). Sent by Scene Studio as "!TUNE <hex>" so edits show on the
// device without reflashing; the Studio's native preview uses the same decoder.
// Art itself (layer pixels, tiles) always comes from the compiled scene.
//
// Format v1 (little-endian):
//   u8 version=1, u8 scene index
//   u8 top[3], u8 bottom[3]
//   u8 layerCount (must match the compiled scene); per layer: i16 y, i16 speed16, u16 period, u16 frameMs
//   u8 fxCount (<=8); per effect: u8 type, density, color, front
//   u8 flags: bit0 = 256-byte theme LUT follows, bit1 = generator settings follow
//   [256 bytes LUT]
//   [gen: u8 type, u8 scale, i16 vx16, i16 vy16, u16 seconds, u8 colorCount (<=32), colors]
//   u8 cycleCount (<=5), u16 holdS, u16 fadeDs, cycleCount x 256-byte LUTs
#include "scene.h"

bool sceneTune(const uint8_t* blob, int len);  // false: malformed or mismatched
void sceneUntune();
int sceneTunedIndex();                          // -1 when nothing is tuned
const SceneDef& sceneResolve(uint8_t index);    // tuned override or SCENES[index]
