#include "scene.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static const int SCENE_H = 240;

static uint32_t hash(uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352d; x ^= x >> 15; x *= 0x846ca68b; x ^= x >> 16;
  return x;
}
static uint8_t rgb332(int r, int g, int b) {
  return (uint8_t)((((r * 7 + 127) / 255) << 5) | (((g * 7 + 127) / 255) << 2) | ((b * 3 + 127) / 255));
}
static uint8_t themed(const SceneDef& s, uint8_t c) { return s.lut ? s.lut[c] : c; }

static void drawSky(const Canvas8& c, const SceneDef& s, int oy, bool flash) {
  for (int y = 0; y < c.h; ++y) {
    int t = y - oy;
    t = t < 0 ? 0 : t >= SCENE_H ? SCENE_H - 1 : t;
    int r = s.top[0] + (s.bottom[0] - s.top[0]) * t / (SCENE_H - 1);
    int g = s.top[1] + (s.bottom[1] - s.top[1]) * t / (SCENE_H - 1);
    int b = s.top[2] + (s.bottom[2] - s.top[2]) * t / (SCENE_H - 1);
    if (flash) r = (r + 255) / 2, g = (g + 255) / 2, b = (b + 255) / 2;
    c.fill(0, y, c.w, 1, themed(s, rgb332(r, g, b)));
  }
}

static void drawStars(const Canvas8& c, const SceneDef& s, const SceneEffect& e, int oy, uint32_t now) {
  const uint32_t n = 20u * e.density;
  for (uint32_t i = 0; i < n; ++i) {
    const uint32_t h = hash(i * 7919 + 1);
    const uint32_t tw = hash(i + (now + h % 1100) / 1100) % 10;
    if (tw > 2) c.put(h % c.w, oy + (h >> 12) % 150, themed(s, tw > 7 ? 0xFF : e.color));
  }
}

// Falling particles: rain streaks or drifting snow. Stateless: positions are a
// function of time, so switching scenes needs no reset.
static void drawFall(const Canvas8& c, const SceneDef& s, const SceneEffect& e, uint32_t now, bool snow) {
  const uint32_t n = (snow ? 30u : 40u) * e.density;
  const uint8_t col = themed(s, e.color);
  for (uint32_t i = 0; i < n; ++i) {
    const uint32_t h = hash(i * 2654435761u + 3);
    const uint32_t speed = snow ? 18 + h % 22 : 160 + h % 140;  // px/s
    const uint32_t span = c.h + 20;
    const int y = (int)((now * speed / 1000 + (h >> 8)) % span) - 10;
    if (snow) {
      const int x = (int)((h % c.w) + 6 * (int)((now / 700 + h) % 3) - 6);
      c.put(x, y, col);
      if (h & 1) c.put(x + 1, y, col);
    } else {
      const int x = (int)((h % (c.w + 40)) - y / 4);
      const int len = 3 + h % 5;
      for (int k = 0; k < len; ++k) c.put(x + k / 4, y - k, col);
    }
  }
}

// ------------------------------------------------------------ generators
static bool tileBit(const SceneGen& g, uint8_t t, int x, int y) {
  const uint8_t* row = g.tiles + t * 32 + (y & 15) * 2;
  return (row[(x & 15) >> 3] >> (7 - (x & 7))) & 1;
}

// Scrolling 1-bit tiles in two colours; every `seconds` a diagonal wipe moves
// to the next tile and colour pair.
static void drawPatterns(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  const uint32_t hold = g.seconds * 1000UL, wipe = 900;
  const uint32_t step = now / hold, into = now % hold;
  const uint8_t pairs = g.colorCount / 2 ? g.colorCount / 2 : 1;
  const uint8_t cur = step % g.tileCount, prev = (step + g.tileCount - 1) % g.tileCount;
  const uint8_t* pc = g.colors + (step % pairs) * 2;
  const uint8_t* pp = g.colors + ((step + pairs - 1) % pairs) * 2;
  const uint8_t c0 = themed(s, pc[0]), c1 = themed(s, pc[1]), p0 = themed(s, pp[0]), p1 = themed(s, pp[1]);
  const int edge = into < wipe && step ? (int)((c.w + c.h) * into / wipe) : 1 << 30;
  const int sc = g.scale ? g.scale : 1;
  const int ox = (int)((int64_t)now * g.vx16 / 16000), oy = (int)((int64_t)now * g.vy16 / 16000);
  for (int y = 0; y < c.h; ++y) {
    uint8_t* row = c.px + y * c.w;
    const int ty = ((y + oy) / sc) & 15;
    for (int x = 0; x < c.w; ++x) {
      const int tx = ((x + ox) / sc) & 15;
      row[x] = x + y < edge ? (tileBit(g, cur, tx, ty) ? c1 : c0) : (tileBit(g, prev, tx, ty) ? p1 : p0);
    }
  }
}

static uint8_t sin8[256];
static uint8_t ramp[256];
static const SceneGen* rampFor = nullptr;

static void buildRamp(const SceneDef& s, const SceneGen& g) {
  if (rampFor == &g) return;
  for (int i = 0; i < 256; ++i) sin8[i] = (uint8_t)(128 + 127 * sinf(i * 6.2831853f / 256));
  const int n = g.colorCount > 1 ? g.colorCount : 2;
  for (int i = 0; i < 256; ++i) {  // cyclic gradient through the colour stops
    const int seg = i * n / 256, next = (seg + 1) % n;
    const int u = (i * n) % 256;
    const uint8_t a = g.colors[seg % g.colorCount], b = g.colors[next % g.colorCount];
    auto ch = [&](int shift, int bits) {
      const int m = (1 << bits) - 1, va = (a >> shift) & m, vb = (b >> shift) & m;
      return (va + ((vb - va) * u + 128) / 256) & m;
    };
    ramp[i] = (uint8_t)((ch(5, 3) << 5) | (ch(2, 3) << 2) | ch(0, 2));
  }
  rampFor = &g;
}

static void drawPlasma(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int b = g.scale ? g.scale : 2;
  const uint8_t t1 = now / 23, t2 = now / 37, t3 = now / 61;
  for (int y = 0; y < c.h; y += b)
    for (int x = 0; x < c.w; x += b) {
      const uint8_t v = sin8[(uint8_t)(x + t1)] / 4 + sin8[(uint8_t)(y * 2 - t2)] / 4 +
                        sin8[(uint8_t)((x + y) + t3)] / 4 + sin8[(uint8_t)(sin8[(uint8_t)(x / 2 + t2)] / 2 + y - t1)] / 4;
      c.fill(x, y, b, b, themed(s, ramp[(uint8_t)(v + now / 40)]));
    }
}

// Classic warp-speed starfield: stars fly out of the centre, streaking as they near.
struct Star { int32_t x, y; uint16_t z; };
static Star stars[150];
static bool starsInit = false;
static uint32_t warpLast = 0;

static void drawWarp(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  c.fill(0, 0, c.w, c.h, themed(s, g.colors[0]));
  if (!starsInit) {
    for (uint16_t i = 0; i < 150; ++i) {
      const uint32_t h = hash(i * 977 + 5);
      stars[i] = {(int32_t)(h % 2000) - 1000, (int32_t)((h >> 11) % 1500) - 750, (uint16_t)(1 + (h >> 22) % 1000)};
    }
    starsInit = true;
    warpLast = now;
  }
  const uint32_t dt = now - warpLast > 200 ? 40 : now - warpLast;
  warpLast = now;
  const int speed = (g.vx16 ? g.vx16 : 16 * 300) * (int)dt / 16000;
  const int cx = c.w / 2, cy = c.h / 2;
  for (uint16_t i = 0; i < 150; ++i) {
    Star& st = stars[i];
    const int pz = st.z;
    st.z = st.z > speed + 1 ? st.z - speed : 0;
    if (!st.z) {
      const uint32_t h = hash(i + now);
      st = {(int32_t)(h % 2000) - 1000, (int32_t)((h >> 11) % 1500) - 750, 1000};
      continue;
    }
    const int x = cx + st.x * 128 / st.z, y = cy + st.y * 128 / st.z;
    const int px = cx + st.x * 128 / pz, py = cy + st.y * 128 / pz;
    const uint8_t col = themed(s, ramp[255 - st.z / 4]);
    const int steps = abs(x - px) > abs(y - py) ? abs(x - px) : abs(y - py);
    for (int k = 0; k <= steps; ++k) c.put(px + (x - px) * k / (steps ? steps : 1), py + (y - py) * k / (steps ? steps : 1), col);
  }
}

static bool lightning(const SceneEffect* e, uint32_t now) {
  if (!e) return false;
  const uint32_t period = 14000 / e->density;
  const uint32_t t = now % period;
  const uint32_t at = hash(now / period) % (period - 400);
  return (t > at && t < at + 70) || (t > at + 160 && t < at + 230);
}

void sceneDraw(const Canvas8& c, const SceneDef& s, uint32_t now) {
  const int oy = (c.h - SCENE_H) / 2;
  const SceneEffect* bolt = nullptr;
  for (uint8_t i = 0; i < s.fxCount; ++i)
    if (s.fx[i].type == FX_LIGHTNING) bolt = &s.fx[i];
  if (!s.gen) drawSky(c, s, oy, lightning(bolt, now));
  else if (s.gen->type == GEN_PATTERNS) drawPatterns(c, s, *s.gen, now);
  else if (s.gen->type == GEN_PLASMA) drawPlasma(c, s, *s.gen, now);
  else if (s.gen->type == GEN_WARP) drawWarp(c, s, *s.gen, now);
  for (uint8_t pass = 0; pass < 2; ++pass) {
    for (uint8_t i = 0; i < s.fxCount; ++i) {
      const SceneEffect& e = s.fx[i];
      if (e.front != pass) continue;
      if (e.type == FX_STARS) drawStars(c, s, e, oy, now);
      else if (e.type == FX_RAIN || e.type == FX_SNOW) drawFall(c, s, e, now, e.type == FX_SNOW);
    }
    if (pass) break;
    for (uint8_t i = 0; i < s.layerCount; ++i) {
      const SceneLayer& L = s.layers[i];
      const AnimAsset& a = *L.asset;
      const uint16_t frame = L.frameMs ? (now / L.frameMs) % a.frameCount : animFrameAt(a, now);
      if (!L.speed16) {  // static: centre it
        animBlit(c, a, frame, (c.w - L.period) / 2, oy + L.y, 1, false, s.lut);
        continue;
      }
      const int64_t travel = (int64_t)now * L.speed16 / 16000;
      int off = (int)(travel % L.period);
      if (off < 0) off += L.period;
      for (int x = -off; x < c.w; x += L.period) animBlit(c, a, frame, x, oy + L.y, 1, false, s.lut);
    }
  }
}
