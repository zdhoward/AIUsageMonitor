#include "anim.h"
#include <string.h>

void Canvas8::fill(int x, int y, int fw, int fh, uint8_t c) const {
  int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
  int x1 = x + fw > w ? w : x + fw, y1 = y + fh > h ? h : y + fh;
  for (int yy = y0; yy < y1; ++yy) memset(px + yy * w + x0, c, x1 > x0 ? x1 - x0 : 0);
}

uint16_t animFrameAt(const AnimAsset& a, uint32_t ms, const char* tag) {
  uint16_t from = 0, to = a.frameCount - 1;
  for (uint8_t i = 0; tag && i < a.tagCount; ++i)
    if (!strcmp(a.tags[i].name, tag)) from = a.tags[i].from, to = a.tags[i].to;
  uint32_t total = 0;
  for (uint16_t f = from; f <= to; ++f) total += a.frames[f].ms;
  if (!total) return from;
  ms %= total;
  for (uint16_t f = from; f <= to; ++f) {
    if (ms < a.frames[f].ms) return f;
    ms -= a.frames[f].ms;
  }
  return to;
}

void animBlit(const Canvas8& c, const AnimAsset& a, uint16_t frame, int x, int y, uint8_t scale, bool flipX,
              const uint8_t* lut) {
  if (frame >= a.frameCount || !scale) return;
  const int ox = x + a.x * scale, oy = y + a.y * scale;
  if (ox >= c.w || oy >= c.h || ox + a.w * scale <= 0 || oy + a.h * scale <= 0) return;  // off-screen
  const uint8_t* p = a.frames[frame].rle;
  const uint32_t total = (uint32_t)a.w * a.h;
  const bool fast = scale == 1 && !flipX;
  int sx = 0, sy = 0;  // source position, advanced incrementally (no division per pixel)
  uint32_t i = 0;
  auto advance = [&](uint32_t n) {
    sx += n;
    while (sx >= a.w) sx -= a.w, ++sy;
  };
  // Writes a run of `n` pixels starting at the current position; runs may wrap rows.
  auto run = [&](uint32_t n, const uint8_t* lit, uint8_t col) {
    while (n) {
      const uint32_t span = (uint32_t)(a.w - sx) < n ? (uint32_t)(a.w - sx) : n;
      const int dy = oy + sy * scale;
      if (fast && dy >= 0 && dy < c.h) {
        int dx = ox + sx, k0 = 0, k1 = (int)span;
        if (dx < 0) k0 = -dx;
        if (dx + k1 > c.w) k1 = c.w - dx;
        uint8_t* row = c.px + dy * c.w + dx;
        if (lit) for (int k = k0; k < k1; ++k) row[k] = lut ? lut[lit[k]] : lit[k];
        else if (k1 > k0) memset(row + k0, lut ? lut[col] : col, k1 - k0);
      } else if (!fast) {
        for (uint32_t k = 0; k < span; ++k) {
          const int fx = flipX ? a.w - 1 - (sx + (int)k) : sx + (int)k;
          uint8_t v = lit ? lit[k] : col;
          if (lut) v = lut[v];
          if (scale == 1) c.put(ox + fx, oy + sy, v);
          else c.fill(ox + fx * scale, oy + sy * scale, scale, scale, v);
        }
      }
      if (lit) lit += span;
      n -= span;
      advance(span);
    }
  };
  while (i < total) {
    const uint8_t op = *p++;
    const uint32_t n = (op & (op & 0x80 ? 0x7F : 0x3F)) + 1;
    if (op & 0x80) {
      advance(n);
    } else if (op & 0x40) {
      run(n, nullptr, *p++);
    } else {
      run(n, p, 0);
      p += n;
    }
    i += n;
    if (oy + sy * scale >= c.h) return;  // everything below is clipped
  }
}
