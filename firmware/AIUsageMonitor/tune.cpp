#include "tune.h"
#include <string.h>
#include "scenes_gen.h"

static const int MAX_LAYERS = 16, MAX_FX = 8, MAX_COLORS = 32, MAX_CYCLE = 5;
static SceneDef tDef;
static SceneLayer tLayers[MAX_LAYERS];
static SceneEffect tFx[MAX_FX];
static SceneGen tGen;
static uint8_t tGenColors[MAX_COLORS];
static uint8_t tLut[256];
static uint8_t tCycle[MAX_CYCLE][256];
static const uint8_t* tCycleRefs[MAX_CYCLE];
static int tIdx = -1;

namespace {
struct Reader {
  const uint8_t* b;
  int n, p = 0;
  bool bad = false;
  int u8() {
    if (p >= n) { bad = true; return 0; }
    return b[p++];
  }
  int16_t i16() {
    const int lo = u8(), hi = u8();
    return (int16_t)(lo | (hi << 8));
  }
  uint16_t u16() { return (uint16_t)i16(); }
  bool bytes(uint8_t* out, int k) {
    if (p + k > n) { bad = true; return false; }
    memcpy(out, b + p, k);
    p += k;
    return true;
  }
};
}  // namespace

bool sceneTune(const uint8_t* blob, int len) {
  Reader r{blob, len};
  if (r.u8() != 1) return false;
  const int idx = r.u8();
  if (idx >= SCENE_COUNT) return false;
  const SceneDef& base = SCENES[idx];
  SceneDef d = base;
  for (int k = 0; k < 3; ++k) d.top[k] = r.u8();
  for (int k = 0; k < 3; ++k) d.bottom[k] = r.u8();
  const int nl = r.u8();
  if (nl != base.layerCount || nl > MAX_LAYERS) return false;  // art changed: needs a rebuild
  for (int i = 0; i < nl; ++i) {
    tLayers[i] = base.layers[i];
    tLayers[i].y = r.i16();
    tLayers[i].speed16 = r.i16();
    tLayers[i].period = r.u16();
    tLayers[i].frameMs = r.u16();
    if (!tLayers[i].period) tLayers[i].period = base.layers[i].period;
  }
  d.layers = nl ? tLayers : nullptr;
  const int nf = r.u8();
  if (nf > MAX_FX) return false;
  for (int i = 0; i < nf; ++i) tFx[i] = {(uint8_t)r.u8(), (uint8_t)r.u8(), (uint8_t)r.u8(), (uint8_t)r.u8()};
  d.fx = nf ? tFx : nullptr;
  d.fxCount = nf;
  const int flags = r.u8();
  d.lut = nullptr;
  if ((flags & 1) && r.bytes(tLut, 256)) d.lut = tLut;
  if (flags & 2) {
    if (!base.gen) return false;
    tGen = *base.gen;  // tiles stay compiled
    tGen.type = r.u8();
    tGen.scale = r.u8();
    tGen.vx16 = r.i16();
    tGen.vy16 = r.i16();
    tGen.seconds = r.u16();
    const int nc = r.u8();
    if (nc < 1 || nc > MAX_COLORS) return false;
    for (int i = 0; i < nc; ++i) tGenColors[i] = r.u8();
    tGen.colors = tGenColors;
    tGen.colorCount = nc;
    if (tGen.type == GEN_PATTERNS && !tGen.tileCount) return false;
    d.gen = &tGen;
  }
  const int nc = r.u8();
  d.holdS = r.u16();
  d.fadeDs = r.u16();
  if (nc > MAX_CYCLE) return false;
  for (int i = 0; i < nc; ++i) {
    r.bytes(tCycle[i], 256);
    tCycleRefs[i] = tCycle[i];
  }
  d.cycle = nc > 1 ? tCycleRefs : nullptr;
  d.cycleCount = nc > 1 ? nc : 0;
  if (r.bad) return false;
  tDef = d;
  tIdx = idx;
  return true;
}

void sceneUntune() { tIdx = -1; }
int sceneTunedIndex() { return tIdx; }
const SceneDef& sceneResolve(uint8_t i) { return (int)i == tIdx ? tDef : SCENES[i]; }
