#include "city.h"
#include <math.h>
#include "assets_gen.h"

// Art is authored on a 320x240 canvas; other canvas sizes centre it.
static const int ART_W = 320, ART_H = 240, HORIZON = 168;

static constexpr uint8_t C8(int r, int g, int b) {
  return (uint8_t)((((r * 7 + 127) / 255) << 5) | (((g * 7 + 127) / 255) << 2) | ((b * 3 + 127) / 255));
}

static uint32_t hash(uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352d; x ^= x >> 15; x *= 0x846ca68b; x ^= x >> 16;
  return x;
}

// ------------------------------------------------------------------ sky + sun
struct Band { int16_t y; uint8_t c, flash; };
static const Band kSky[] = {
  {30, C8(0, 0, 0), C8(73, 73, 170)},       {62, C8(0, 0, 85), C8(109, 109, 170)},
  {94, C8(36, 0, 85), C8(146, 109, 255)},   {120, C8(73, 0, 85), C8(146, 146, 255)},
  {140, C8(109, 0, 170), C8(182, 146, 255)}, {156, C8(182, 0, 170), C8(219, 182, 255)},
  {HORIZON, C8(255, 36, 170), C8(255, 219, 255)},
};

static void drawSky(const Canvas8& c, int ox, int oy, bool flash) {
  c.fill(0, 0, c.w, oy, kSky[0].c);
  int y = 0;
  for (const Band& b : kSky) {
    c.fill(0, oy + y, c.w, b.y - y, flash ? b.flash : b.c);
    y = b.y;
  }
}

static void drawStars(const Canvas8& c, int ox, int oy, uint32_t now) {
  for (uint32_t i = 0; i < 46; ++i) {
    const uint32_t h = hash(i * 7919 + 1);
    const int x = ox + h % ART_W, y = oy + (h >> 12) % 100;
    const uint32_t tw = hash(i + (now + h % 900) / 900) % 10;
    if (tw > 2) c.put(x, y, tw > 7 ? C8(255, 255, 255) : C8(146, 146, 170));
  }
}

static void drawSun(const Canvas8& c, int ox, int oy, uint32_t now) {
  static const uint8_t kSun[] = {C8(255, 255, 85), C8(255, 219, 0), C8(255, 182, 0), C8(255, 146, 0),
                                 C8(255, 109, 0), C8(255, 73, 85), C8(255, 36, 170), C8(255, 0, 170)};
  const int cx = 160, cy = 120, r = 46;
  const int scroll = (now / 140) % 10;
  for (int y = cy - r; y < HORIZON; ++y) {
    const int dy = y - cy;
    if (dy > 0 && (y - scroll + 100) % 10 < 1 + dy * 5 / r) continue;  // retro stripes
    const int half = (int)sqrtf((float)(r * r - dy * dy));
    c.fill(ox + cx - half, oy + y, half * 2, 1, kSun[(y - (cy - r)) * 8 / (HORIZON - (cy - r) + 1)]);
  }
}

// ---------------------------------------------------------------- road + rain
static void drawRoad(const Canvas8& c, int ox, int oy, uint32_t now) {
  static const uint8_t kGround[] = {C8(36, 0, 85), C8(0, 0, 85), C8(0, 0, 0)};
  const int depth = ART_H - HORIZON;
  for (int y = 0; y < depth; ++y) c.fill(0, oy + HORIZON + y, c.w, 1, kGround[y * 3 / depth]);
  c.fill(0, oy + ART_H, c.w, c.h - oy - ART_H, kGround[2]);
  // Sun reflection on the wet road.
  for (int y = 2; y < depth; y += 3) {
    const int half = 30 - y / 3 + (int)(hash(y + now / 160) % 5);
    if (half > 0) c.fill(ox + 160 - half, oy + HORIZON + y, half * 2, 1, y < 24 ? C8(255, 73, 85) : C8(146, 0, 85));
  }
  const uint8_t grid = C8(255, 0, 170), gridFar = C8(146, 0, 170);
  const float phase = (now % 1400) / 1400.0f;
  for (int i = 0; i < 9; ++i) {
    const float t = (i + phase) / 9.0f;
    const int y = HORIZON + (int)(depth * t * t);
    c.fill(0, oy + y, c.w, 1, t < 0.25f ? gridFar : grid);
  }
  for (int k = -9; k <= 9; ++k) {
    for (int y = depth / 8; y < depth; ++y) {
      c.put(ox + 160 + k * 40 * y / depth, oy + HORIZON + y, y < depth / 4 ? gridFar : grid);
    }
  }
}

struct Drop { int16_t x, y; uint8_t speed, len; };
static Drop drops[110];
static bool rainInit = false;
static uint32_t rainLast = 0;

static void drawRain(const Canvas8& c, uint32_t now) {
  if (!rainInit) {
    for (uint16_t i = 0; i < 110; ++i) {
      const uint32_t h = hash(i * 31 + 7);
      drops[i] = {(int16_t)(h % (c.w + 60)), (int16_t)((h >> 10) % c.h), (uint8_t)(5 + (h >> 20) % 5),
                  (uint8_t)(3 + (h >> 24) % 5)};
    }
    rainInit = true;
    rainLast = now;
  }
  const uint32_t dt = now - rainLast > 200 ? 40 : now - rainLast;
  rainLast = now;
  const uint8_t near = C8(146, 146, 255), far = C8(73, 73, 170), splash = C8(182, 182, 255);
  for (uint16_t i = 0; i < 110; ++i) {
    Drop& d = drops[i];
    const int step = d.speed * (int)dt / 16;
    d.y += step;
    d.x -= step / 3;
    const int floor = c.h - 4 - (int)(hash(i) % 60);
    if (d.y > floor) {
      c.put(d.x - 1, floor, splash);
      c.put(d.x + 1, floor, splash);
      const uint32_t h = hash(i + now);
      d.y = -(int)(h % 40);
      d.x = h % (c.w + 60);
    }
    const uint8_t col = d.speed > 7 ? near : far;
    for (int k = 0; k < d.len; ++k) c.put(d.x + k / 3, d.y - k, col);
  }
}

// ------------------------------------------------------------- city + traffic
static void drawWindows(const Canvas8& c, int ox, int oy, uint32_t now) {
  const uint8_t off = C8(36, 0, 85);
  for (uint16_t i = 0; i < RECTS_city_windows.count; ++i) {
    const AnimRect& r = RECTS_city_windows.rects[i];
    const uint32_t period = 2500 + (hash(i) % 9) * 700;
    const bool lit = hash(i * 13 + (now + hash(i) % period) / period) % 100 > 7;
    c.fill(ox + r.x, oy + r.y, r.w, r.h, lit ? r.c : off);
  }
}

static void drawCar(const Canvas8& c, int ox, int oy, uint32_t now, int y, int speedPxS, bool left, uint32_t seed) {
  const int span = ART_W + 60;
  const int travel = (int)((now / 1000.0f * speedPxS + seed) ) % span;
  const int x = left ? ART_W + 30 - travel : travel - 30;
  const int bob = (int)((now / 300 + seed) % 4 == 0);
  animBlit(c, ASSET_city_car, animFrameAt(ASSET_city_car, now + seed, "fly"), ox + x, oy + y + bob, 1, left);
}

static uint32_t boltAt = 0, boltEnd = 0;

static bool lightning(uint32_t now) {
  if (boltAt == 0) boltAt = now + 6000;
  if (now >= boltAt) {
    boltEnd = now + 240;
    boltAt = now + 7000 + hash(now) % 14000;
  }
  // Two quick flickers inside the strike window.
  return now < boltEnd && ((boltEnd - now) > 170 || (boltEnd - now) < 90);
}

void cityDraw(const Canvas8& c, uint32_t now) {
  const int ox = (c.w - ART_W) / 2, oy = (c.h - ART_H) / 2;
  const bool flash = lightning(now);
  drawSky(c, ox, oy, flash);
  drawStars(c, ox, oy, now);
  drawSun(c, ox, oy, now);
  animBlit(c, ASSET_city_far, 0, ox, oy);
  drawCar(c, ox, oy, now, 92, 28, false, 0);
  drawCar(c, ox, oy, now, 74, 18, true, 170);
  animBlit(c, ASSET_city_near, 0, ox, oy);
  drawWindows(c, ox, oy, now);
  animBlit(c, ASSET_city_sign, animFrameAt(ASSET_city_sign, now, "flicker"), ox + 213, oy + 114);
  drawRoad(c, ox, oy, now);
  drawCar(c, ox, oy, now, 138, 64, true, 40);
  drawRain(c, now);
}
