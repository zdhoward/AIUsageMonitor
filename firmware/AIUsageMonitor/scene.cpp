#include "scene.h"

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
  drawSky(c, s, oy, lightning(bolt, now));
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
