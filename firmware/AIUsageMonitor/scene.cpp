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

static void drawSky(const Canvas8& c, const SceneDef& s, int oy) {
  for (int y = 0; y < c.h; ++y) {
    int t = y - oy;
    t = t < 0 ? 0 : t >= SCENE_H ? SCENE_H - 1 : t;
    int r = s.top[0] + (s.bottom[0] - s.top[0]) * t / (SCENE_H - 1);
    int g = s.top[1] + (s.bottom[1] - s.top[1]) * t / (SCENE_H - 1);
    int b = s.top[2] + (s.bottom[2] - s.top[2]) * t / (SCENE_H - 1);
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
static uint32_t rampKey = 0;

// Identifies a generator's settings, so caches and simulations restart when
// live tuning changes them in place.
static uint32_t genKey(const SceneGen& g) {
  uint32_t k = hash(g.type * 2654435761u ^ g.scale * 40503u ^ (uint16_t)g.vx16 * 2246822519u ^
                    (uint16_t)g.vy16 * 3266489917u ^ g.seconds);
  for (uint8_t i = 0; i < g.colorCount; ++i) k = hash(k ^ g.colors[i]);
  return k ? k : 1;
}

static void buildRamp(const SceneDef& s, const SceneGen& g) {
  const bool cyclic = g.type <= GEN_MATRIX;  // older generators loop their gradient; simulations run dark -> bright
  if (rampKey == genKey(g)) return;
  for (int i = 0; i < 256; ++i) sin8[i] = (uint8_t)(128 + 127 * sinf(i * 6.2831853f / 256));
  const int n = g.colorCount > 1 ? g.colorCount : 2;
  for (int i = 0; i < 256; ++i) {
    const int span = cyclic ? n : n - 1;  // linear: last stop reached at 255
    const int pos = i * span * 256 / (cyclic ? 256 : 255);
    const int seg = (pos >> 8) < span ? pos >> 8 : span - 1, next = (seg + 1) % n;
    const int u = cyclic ? (i * n) % 256 : pos - seg * 256;
    const uint8_t a = g.colors[seg % g.colorCount], b = g.colors[next % g.colorCount];
    auto ch = [&](int shift, int bits) {
      const int m = (1 << bits) - 1, va = (a >> shift) & m, vb = (b >> shift) & m;
      return (va + ((vb - va) * u + 128) / 256) & m;
    };
    ramp[i] = (uint8_t)((ch(5, 3) << 5) | (ch(2, 3) << 2) | ch(0, 2));
  }
  rampKey = genKey(g);
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

// Digital rain: columns of procedurally generated glyphs fall with a bright
// head and a fading trail; characters flicker as they fall. The glyph set is
// generated from a hash, so there is no font asset.
static const int MX_COLS = 64, MX_ROWS = 40;
static uint8_t mxGlyph[64][7];  // 5-bit rows
static uint8_t mxCell[MX_COLS * MX_ROWS];
struct MxDrop { int32_t head16; uint8_t speed, len; };  // head row * 16, rows/s
static MxDrop mxDrop[MX_COLS];
static uint32_t mxKey = 0;
static uint32_t mxLast = 0;

static void mxRespawn(MxDrop& d, const SceneGen& g, uint32_t seed, int rows) {
  const uint32_t h = hash(seed);
  const int base = g.vx16 ? g.vx16 / 16 : 12;
  d.speed = (uint8_t)(base / 2 + h % (base + 1));
  d.len = (uint8_t)(6 + (h >> 8) % (rows * 2 / 3));
  // Columns outside the density share start far above the screen and wait.
  const bool active = (h >> 16) % 100 < (uint32_t)(g.vy16 ? g.vy16 : 70);
  d.head16 = -(int32_t)(((h >> 20) % (active ? rows : rows * 4)) * 16);
}

static void drawMatrix(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int sc = g.scale ? g.scale : 1, cw = 6 * sc, ch = 8 * sc;
  const int cols = c.w / cw < MX_COLS ? c.w / cw : MX_COLS, rows = c.h / ch < MX_ROWS ? c.h / ch : MX_ROWS;
  if (mxKey != genKey(g)) {
    for (int k = 0; k < 64; ++k)
      for (int r = 0; r < 7; ++r) {
        uint32_t h = hash(k * 131 + r * 7 + 9);
        uint8_t row = h & 0x1F;
        if (r == 0 || (h >> 5) % 4 == 0) row = (h >> 8) % 2 ? 0x1F : row | 0x11;  // strokes like kana
        mxGlyph[k][r] = row;
      }
    for (int i = 0; i < MX_COLS * MX_ROWS; ++i) mxCell[i] = hash(i + 77) & 63;
    for (int x = 0; x < MX_COLS; ++x) mxRespawn(mxDrop[x], g, x * 911 + 1, rows);
    mxKey = genKey(g);
    mxLast = now;
  }
  const uint32_t dt = now - mxLast > 200 ? 40 : now - mxLast;
  mxLast = now;
  c.fill(0, 0, c.w, c.h, themed(s, g.colors[0]));
  for (int n = cols * rows / 30; n > 0; --n) {  // flicker a few characters each frame
    const uint32_t h = hash(now * 31 + n);
    mxCell[h % (MX_COLS * MX_ROWS)] = (h >> 16) & 63;
  }
  const uint8_t head = themed(s, g.colors[g.colorCount - 1]);
  for (int x = 0; x < cols; ++x) {
    MxDrop& d = mxDrop[x];
    d.head16 += d.speed * (int32_t)dt * 16 / 1000;
    const int hr = d.head16 / 16;
    if (hr - d.len > rows) {
      mxRespawn(d, g, now + x * 7919, rows);
      continue;
    }
    for (int k = 0; k <= d.len; ++k) {
      const int r = hr - k;
      if (r < 0 || r >= rows) continue;
      const uint8_t col = k == 0 ? head : themed(s, ramp[200 - 190 * k / (d.len + 1)]);
      const uint8_t* gl = mxGlyph[mxCell[x * MX_ROWS + r]];
      for (int gy = 0; gy < 7; ++gy)
        for (int gx = 0; gx < 5; ++gx)
          if ((gl[gy] >> (4 - gx)) & 1) c.fill(x * cw + gx * sc, r * ch + gy * sc, sc, sc, col);
    }
  }
}

// ------------------------------------------------------------ simulation generators
// Fire, lava, aurora, life, ripples, fireworks, video equations and a
// Spectre-style patch. Original implementations of classic effects; ideas from
// termflix and sysc-Go (MIT), the Video EQ and the EMS Spectre / open_spectre.
// They share one scratch buffer: only one simulation runs at a time, and a
// change of settings (genKey) restarts it.
static uint8_t scratch[38400];
static uint32_t scratchKey = 0, simLast = 0;

static bool claim(const SceneGen& g, uint32_t now) {
  const uint32_t k = genKey(g);
  if (k == scratchKey) return false;
  scratchKey = k;
  memset(scratch, 0, sizeof scratch);
  simLast = now;
  return true;
}

// Fixed-rate simulation steps owed since the last frame (capped).
static int simSteps(uint32_t now, uint32_t stepMs, int cap = 4) {
  if (now < simLast) simLast = now;
  int n = (int)((now - simLast) / stepMs);
  if (n > cap) { simLast = now; return cap; }
  simLast += n * stepMs;
  return n;
}

static int gridScale(const SceneGen& g, const Canvas8& c, int def, int cellsMax) {
  int sc = g.scale ? g.scale : def;
  while ((c.w / sc) * (c.h / sc) > cellsMax) ++sc;
  return sc;
}

static void drawFire(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int sc = gridScale(g, c, 4, 19200), gw = c.w / sc, gh = c.h / sc;
  uint8_t* heat = scratch;
  claim(g, now);
  const int intensity = g.vy16 ? g.vy16 : 100;  // % of full heat at the source
  const int wind = g.vx16 / 16;                   // cells per row, signed
  const int drop = 1 + 255 * 100 / (gh * 80);     // flames reach most of the way up
  for (int n = simSteps(now, 30); n > 0; --n) {
    for (int x = 0; x < gw; ++x) {
      const uint32_t h = hash(now * 7 + x * 131 + n);
      heat[(gh - 1) * gw + x] = (uint8_t)((255 - (h & 63)) * intensity / 100);
    }
    for (int y = 1; y < gh; ++y)
      for (int x = 0; x < gw; ++x) {
        const uint8_t src = heat[y * gw + x];
        const uint32_t r = hash(y * 977 + x * 31 + now + n) & 3;
        int dx = x - (int)r + 1 + wind;
        dx = ((dx % gw) + gw) % gw;
        const int v = src - (int)(r * drop * 2 / 3);
        heat[(y - 1) * gw + dx] = (uint8_t)(v > 0 ? v : 0);
      }
  }
  for (int y = 0; y < gh; ++y)
    for (int x = 0; x < gw; ++x) c.fill(x * sc, y * sc, sc, sc, themed(s, ramp[heat[y * gw + x]]));
}

static void drawLava(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int sc = g.scale ? g.scale : 4, gw = c.w / sc, gh = c.h / sc;
  int n = g.vy16 ? g.vy16 : 6;
  n = n < 2 ? 2 : n > 12 ? 12 : n;
  const float t = now * (g.vx16 ? g.vx16 / 16.0f : 10.0f) / 10000.0f;
  int bx[12], by[12], r2[12];
  for (int i = 0; i < n; ++i) {
    const uint32_t h = hash(i * 7717 + 3);
    const float fa = 0.3f + (h % 100) / 140.0f, fb = 0.25f + ((h >> 8) % 100) / 160.0f;
    bx[i] = (int)(gw / 2 + gw * 0.4f * sinf(t * fa + (h >> 16) % 7));
    by[i] = (int)(gh / 2 + gh * 0.42f * sinf(t * fb + (h >> 20) % 5));
    const int r = gh / 7 + (int)((h >> 24) % (gh / 6 + 1));
    r2[i] = r * r;
  }
  for (int y = 0; y < gh; ++y)
    for (int x = 0; x < gw; ++x) {
      int f = 0;
      for (int i = 0; i < n; ++i) {
        const int dx = x - bx[i], dy = y - by[i];
        f += (r2[i] << 6) / (dx * dx + dy * dy + 1);
      }
      const int v = f > 255 * 2 ? 255 : f / 2;
      c.fill(x * sc, y * sc, sc, sc, themed(s, ramp[v < 110 ? v / 4 : v]));  // crisp blob edges
    }
}

static void drawAurora(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  c.fill(0, 0, c.w, c.h, themed(s, ramp[0]));
  for (uint32_t i = 0; i < 70; ++i) {  // still stars behind the curtains
    const uint32_t h = hash(i * 4441 + 1);
    c.put(h % c.w, (h >> 12) % c.h, themed(s, ramp[110 + (h >> 24) % 60]));
  }
  const int sc = g.scale ? g.scale : 2;
  const float t = now * (g.vx16 ? g.vx16 / 16.0f : 10.0f) / 10000.0f;
  const int bright = g.vy16 ? g.vy16 : 100;
  for (int x = 0; x < c.w; x += sc) {
    const float y0 = c.h * 0.36f + sinf(x * 0.021f + t * 0.7f) * c.h * 0.09f + sinf(x * 0.053f - t * 1.1f) * c.h * 0.05f;
    const float hgt = c.h * (0.3f + 0.12f * sinf(x * 0.031f + t * 0.9f));
    const float rays = 0.65f + 0.35f * sinf(x * 0.27f + t * 2.3f) * sinf(x * 0.071f - t);
    const float glow = (0.55f + 0.45f * sinf(x * 0.012f + t * 0.5f)) * rays * bright / 100.0f;
    const int top = (int)(y0 - hgt), bot = (int)(y0 + hgt * 0.25f);
    for (int y = top < 0 ? 0 : top; y < bot && y < c.h; y += sc) {
      // bright lower edge, long fade upwards
      const float u = y < y0 ? (y - top) / (y0 - top) : 1.0f - (y - y0) / (bot - y0 + 1);
      const int v = (int)(300 * glow * u);
      if (v > 24) c.fill(x, y, sc, sc, themed(s, ramp[v > 255 ? 255 : v]));
    }
  }
}

static void drawLife(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int sc = gridScale(g, c, 4, 19200), gw = c.w / sc, gh = c.h / sc;
  uint8_t *cur = scratch, *nxt = scratch + 19200;  // bit7 alive; low bits = age (alive) or fade (dead)
  const int density = g.vy16 ? g.vy16 : 28;
  const uint32_t reseedMs = (g.seconds ? g.seconds : 60) * 1000UL;
  static uint32_t seededAt = 0;
  if (claim(g, now) || now - seededAt > reseedMs) {
    for (int i = 0; i < gw * gh; ++i) cur[i] = (hash(i * 2654435761u + now) % 100 < (uint32_t)density) ? 0x81 : 0;
    seededAt = now;
  }
  const int gps = g.vx16 ? g.vx16 / 16 : 8;
  for (int n = simSteps(now, 1000 / (gps > 0 ? gps : 1), 2); n > 0; --n) {
    for (int y = 0; y < gh; ++y)
      for (int x = 0; x < gw; ++x) {
        int k = 0;
        for (int dy = -1; dy <= 1; ++dy)
          for (int dx = -1; dx <= 1; ++dx)
            if (dx || dy) k += cur[((y + dy + gh) % gh) * gw + (x + dx + gw) % gw] >> 7;
        const uint8_t v = cur[y * gw + x];
        const bool alive = v & 0x80;
        if (alive ? (k == 2 || k == 3) : k == 3) {
          const uint8_t age = alive ? (v & 0x7F) : 0;
          nxt[y * gw + x] = 0x80 | (age < 127 ? age + 1 : 127);
        } else {
          nxt[y * gw + x] = alive ? 24 : ((v & 0x7F) > 3 ? (v & 0x7F) - 3 : 0);  // fade after death
        }
      }
    memcpy(cur, nxt, gw * gh);
  }
  for (int y = 0; y < gh; ++y)
    for (int x = 0; x < gw; ++x) {
      const uint8_t v = cur[y * gw + x];
      const int idx = (v & 0x80) ? 255 - (v & 0x7F) : (v & 0x7F) * 3;
      c.fill(x * sc, y * sc, sc, sc, themed(s, ramp[idx]));
    }
}

static void drawRipple(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int sc = gridScale(g, c, 4, 9600), gw = c.w / sc, gh = c.h / sc;
  int16_t* a = (int16_t*)scratch;
  int16_t* b = a + 9600;
  static bool flip = false;
  claim(g, now);
  const int rate = g.vy16 ? g.vy16 : 40;  // drops per minute
  for (int n = simSteps(now, 30); n > 0; --n) {
    int16_t *h1 = flip ? b : a, *h2 = flip ? a : b;
    const uint32_t r = hash(now / 30 + n * 7);
    if (r % 2000 < (uint32_t)rate) {
      const int x = 2 + r % (gw - 4), y = 2 + (r >> 12) % (gh - 4);
      for (int dy = -1; dy <= 1; ++dy)
        for (int dx = -1; dx <= 1; ++dx) h1[(y + dy) * gw + x + dx] = -900;
    }
    for (int y = 1; y < gh - 1; ++y)
      for (int x = 1; x < gw - 1; ++x) {
        const int i = y * gw + x;
        int v = ((h1[i - 1] + h1[i + 1] + h1[i - gw] + h1[i + gw]) >> 1) - h2[i];
        v -= v >> 5;
        h2[i] = (int16_t)v;
      }
    flip = !flip;
  }
  const int16_t* h = flip ? b : a;
  for (int y = 0; y < gh; ++y)
    for (int x = 0; x < gw; ++x) {
      const int i = y * gw + x;
      const int slope = (x > 0 && x < gw - 1) ? h[i - 1] - h[i + 1] : 0;
      int v = 60 + slope / 3;
      v = v < 0 ? 0 : v > 255 ? 255 : v;
      c.fill(x * sc, y * sc, sc, sc, themed(s, ramp[v]));
    }
}

struct Spark { int32_t x, y, vx, vy; uint8_t life, color, rocket; };  // 1/256 px, per 30 ms step
static int32_t v0Brake(int grav) { return grav; }
static Spark sparks[260];

static void drawFireworks(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  if (claim(g, now)) memset(sparks, 0, sizeof sparks);
  // trails: darken the previous frame instead of clearing it
  static uint8_t dim[256];
  static bool dimInit = false;
  if (!dimInit) {
    for (int i = 0; i < 256; ++i) {
      const int r = (i >> 5) > 0 ? (i >> 5) - 1 : 0, gg = ((i >> 2) & 7) > 0 ? ((i >> 2) & 7) - 1 : 0, bl = (i & 3) > 0 ? (i & 3) - 1 : 0;
      dim[i] = (uint8_t)((r << 5) | (gg << 2) | bl);
    }
    dimInit = true;
  }
  for (int i = 0; i < c.w * c.h; ++i) c.px[i] = dim[c.px[i]];
  const int rate = g.vy16 ? g.vy16 : 40;                // launches per minute
  const int grav = 29 * (g.vx16 ? g.vx16 : 160) / 160;   // 1/256 px per step^2 (speed 10 = normal)
  for (int n = simSteps(now, 30); n > 0; --n) {
    if (hash(now / 30 + n) % 2000 < (uint32_t)rate)
      for (Spark& p : sparks)
        if (!p.life) {
          const uint32_t h = hash(now + n * 31);
          // rise ~45-75% of the height in ~1.5 s: v0 = 2h/T, with gravity braking it
          const int32_t v0 = (int32_t)(c.h * (45 + h % 30) / 100 * 2 * 256 / 50);
          p = {(int32_t)((c.w / 6 + h % (c.w * 2 / 3)) << 8), (int32_t)(c.h << 8), (int32_t)((h >> 8) % 120) - 60, -v0, 255,
               (uint8_t)(1 + (h >> 24) % (g.colorCount > 1 ? g.colorCount - 1 : 1)), 1};
          break;
        }
    for (Spark& p : sparks) {
      if (!p.life) continue;
      p.x += p.vx;
      p.y += p.vy;
      p.vy += p.rocket ? v0Brake(grav) : grav / 2;
      if (p.rocket) {
        if (p.vy >= 0) {  // apex: burst into sparks
          p.life = 0;
          const uint32_t h = hash(p.x + p.y);
          int made = 0;
          for (Spark& q : sparks)
            if (!q.life && made < 80) {
              const float a = made * 0.0785f + (h % 100) / 100.0f, sp = 256.0f * (0.6f + (hash(made + h) % 100) / 60.0f);
              q = {p.x, p.y, (int32_t)(cosf(a) * sp), (int32_t)(sinf(a) * sp), (uint8_t)(170 + hash(h + made) % 80), p.color, 0};
              ++made;
            }
        }
      } else {
        p.vx -= p.vx / 24;
        p.vy -= p.vy / 24;
        p.life = p.life > 2 ? p.life - 2 : 0;
      }
    }
  }
  for (const Spark& p : sparks)
    if (p.life) {
      const uint8_t col = g.colors[p.color % g.colorCount];
      const uint8_t shade = themed(s, p.life > 60 || p.rocket ? col : dim[col]);
      if (p.life > 140 && !p.rocket) c.fill((p.x >> 8) - 1, (p.y >> 8) - 1, 2, 2, shade);  // fresh sparks are bigger
      else c.put(p.x >> 8, p.y >> 8, shade);
      if (p.rocket) c.put(p.x >> 8, (p.y >> 8) + 1, themed(s, dim[col]));
    }
}

// Video equations: per-pixel integer formulas, one at a time (vy16 = 1..8 to
// pin one, 0 to cycle every `seconds`).
static void drawVideoEq(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int sc = g.scale ? g.scale : 2, gw = c.w / sc, gh = c.h / sc;
  const uint32_t hold = (g.seconds ? g.seconds : 12) * 1000UL;
  const int eq = g.vy16 ? (g.vy16 - 1) % 8 : (int)((now / hold) % 8);
  const int t = (int)((int64_t)now * (g.vx16 ? g.vx16 : 16 * 40) / 16000);
  for (int y = 0; y < gh; ++y)
    for (int x = 0; x < gw; ++x) {
      const int dx = x - gw / 2, dy = y - gh / 2;
      int v;
      switch (eq) {
        case 0: v = (x ^ y) + t; break;                                          // XOR lattice
        case 1: v = ((x * y) >> 4) + t; break;                                   // hyperbolic bands
        case 2: v = ((x ^ y) & 255) < (t & 255) ? 255 : 0; break;                // munching squares
        case 3: v = ((dx * dx + dy * dy) >> 3) - t; break;                       // rings
        case 4: v = (((dx * dx + dy * dy) >> 4) ^ ((x ^ y) >> 1)) + t; break;    // moire
        case 5: v = ((abs(dx) + abs(dy) + t) ^ (x >> 2)) & 255; break;           // diamonds
        case 6: v = sin8[(uint8_t)(x * 3 + t)] + sin8[(uint8_t)(y * 2 - t)]; break;  // plaid
        default: v = ((x | y) ^ (t >> 1)) * 3; break;                            // OR weave
      }
      c.fill(x * sc, y * sc, sc, sc, themed(s, ramp[(uint8_t)v]));
    }
}

// Spectre-style patch: two oscillators, a moving shape and a ramp comparator
// produce four 1-bit signals; a patch (vy16 = 1..6, 0 cycles) wires them into
// three colour bits that pick one of the scene's colours.
static void drawSpectre(const Canvas8& c, const SceneDef& s, const SceneGen& g, uint32_t now) {
  buildRamp(s, g);
  const int sc = g.scale ? g.scale : 2, gw = c.w / sc, gh = c.h / sc;
  const uint32_t hold = (g.seconds ? g.seconds : 10) * 1000UL;
  const int patch = g.vy16 ? (g.vy16 - 1) % 6 : (int)((now / hold) % 6);
  const float t = now * (g.vx16 ? g.vx16 / 16.0f : 10.0f) / 10000.0f;
  const int fa = 6 + (int)(4 * sinf(t * 0.37f)), fb = 5 + (int)(3 * sinf(t * 0.23f));
  const int pa = (int)(t * 40), pb = (int)(t * 27);
  const int cx = (int)(gw / 2 + gw * 0.3f * sinf(t * 0.61f)), cy = (int)(gh / 2 + gh * 0.3f * cosf(t * 0.47f));
  const int rad = (int)(gh * (0.25f + 0.12f * sinf(t * 0.8f)));
  for (int y = 0; y < gh; ++y)
    for (int x = 0; x < gw; ++x) {
      const int A = ((x * fa + pa) >> 5) & 1;                          // horizontal oscillator
      const int B = ((y * fb - pb) >> 5) & 1;                          // vertical oscillator
      const int dx = x - cx, dy = y - cy;
      const int C = (patch & 1) ? (abs(dx) + abs(dy) < rad) : (dx * dx + dy * dy < rad * rad);  // shape
      const int D = sin8[(uint8_t)((x + y) / 2 + pa)] > 128;          // ramp comparator
      int bits;
      switch (patch) {
        case 0: bits = A << 2 | B << 1 | C; break;
        case 1: bits = (A ^ C) << 2 | (B & D) << 1 | (C ^ D); break;
        case 2: bits = (A & B) << 2 | (C ^ B) << 1 | (D & ~C & 1); break;
        case 3: bits = (A ^ B ^ C) << 2 | (D ^ A) << 1 | C; break;
        case 4: bits = C ? (A << 2 | D << 1 | B) : (B << 2 | A); break;
        default: bits = (D ^ C) << 2 | (A | B) << 1 | (A ^ D); break;
      }
      c.fill(x * sc, y * sc, sc, sc, themed(s, g.colors[bits % g.colorCount]));
    }
}

static bool lightning(const SceneEffect* e, uint32_t now) {
  if (!e) return false;
  const uint32_t period = 14000 / e->density;
  const uint32_t t = now % period;
  const uint32_t at = hash(now / period) % (period - 400);
  return (t > at && t < at + 70) || (t > at + 160 && t < at + 230);
}

// Theme cycle: hold each palette map, then cross-fade to the next by blending
// the two maps channel by channel (256 entries per frame).
static uint8_t blendLut[256];

static const uint8_t* cycleLut(const SceneDef& s, uint32_t now) {
  const uint32_t hold = s.holdS * 1000UL, fade = s.fadeDs * 100UL, period = hold + fade;
  const uint32_t t = now % (period * s.cycleCount);
  const uint8_t k = t / period;
  const uint32_t u = t % period;
  const uint8_t* a = s.cycle[k];
  if (u < hold || !fade) return a;
  const uint8_t* b = s.cycle[(k + 1) % s.cycleCount];
  const int f = (int)((u - hold) * 256 / fade);  // 0..255
  for (int i = 0; i < 256; ++i) {
    const int r = (a[i] >> 5) * (256 - f) + (b[i] >> 5) * f;
    const int g = ((a[i] >> 2) & 7) * (256 - f) + ((b[i] >> 2) & 7) * f;
    const int bl = (a[i] & 3) * (256 - f) + (b[i] & 3) * f;
    blendLut[i] = (uint8_t)((((r + 128) >> 8) << 5) | (((g + 128) >> 8) << 2) | ((bl + 128) >> 8));
  }
  return blendLut;
}

void sceneDraw(const Canvas8& c, const SceneDef& def, uint32_t now) {
  SceneDef s = def;
  if (def.cycleCount > 1) s.lut = cycleLut(def, now);
  const int oy = (c.h - SCENE_H) / 2;
  const SceneEffect* bolt = nullptr;
  for (uint8_t i = 0; i < s.fxCount; ++i)
    if (s.fx[i].type == FX_LIGHTNING) bolt = &s.fx[i];
  const bool flash = lightning(bolt, now);
  if (!s.gen) drawSky(c, s, oy);
  else if (s.gen->type == GEN_PATTERNS) drawPatterns(c, s, *s.gen, now);
  else if (s.gen->type == GEN_PLASMA) drawPlasma(c, s, *s.gen, now);
  else if (s.gen->type == GEN_WARP) drawWarp(c, s, *s.gen, now);
  else if (s.gen->type == GEN_MATRIX) drawMatrix(c, s, *s.gen, now);
  else if (s.gen->type == GEN_FIRE) drawFire(c, s, *s.gen, now);
  else if (s.gen->type == GEN_LAVA) drawLava(c, s, *s.gen, now);
  else if (s.gen->type == GEN_AURORA) drawAurora(c, s, *s.gen, now);
  else if (s.gen->type == GEN_LIFE) drawLife(c, s, *s.gen, now);
  else if (s.gen->type == GEN_RIPPLE) drawRipple(c, s, *s.gen, now);
  else if (s.gen->type == GEN_FIREWORKS) drawFireworks(c, s, *s.gen, now);
  else if (s.gen->type == GEN_VIDEOEQ) drawVideoEq(c, s, *s.gen, now);
  else if (s.gen->type == GEN_SPECTRE) drawSpectre(c, s, *s.gen, now);
  for (uint8_t pass = 0; pass < 2; ++pass) {
    for (uint8_t i = 0; i < s.fxCount; ++i) {
      const SceneEffect& e = s.fx[i];
      if (e.front != pass) continue;
      if (e.type == FX_STARS) drawStars(c, s, e, oy, now);
      else if (e.type == FX_RAIN || e.type == FX_SNOW) drawFall(c, s, e, now, e.type == FX_SNOW);
    }
    if (pass) break;
    for (uint8_t i = 0; i <= s.layerCount; ++i) {
      // Lightning lights the sky behind the layers from bolt->front onwards.
      if (flash && i == (bolt->front < s.layerCount ? bolt->front : s.layerCount)) c.fill(0, 0, c.w, c.h, themed(s, bolt->color));
      if (i == s.layerCount) break;
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
