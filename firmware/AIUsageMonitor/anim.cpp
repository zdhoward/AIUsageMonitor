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

void animBlit(const Canvas8& c, const AnimAsset& a, uint16_t frame, int x, int y, uint8_t scale, bool flipX) {
  if (frame >= a.frameCount || !scale) return;
  const uint8_t* p = a.frames[frame].rle;
  const uint32_t total = (uint32_t)a.w * a.h;
  const int ox = x + a.x * scale, oy = y + a.y * scale;
  uint32_t i = 0;
  auto plot = [&](uint32_t idx, uint8_t col) {
    int sx = idx % a.w, sy = idx / a.w;
    if (flipX) sx = a.w - 1 - sx;
    int dx = ox + sx * scale, dy = oy + sy * scale;
    if (scale == 1) c.put(dx, dy, col);
    else c.fill(dx, dy, scale, scale, col);
  };
  while (i < total) {
    const uint8_t op = *p++;
    const uint32_t n = (op & (op & 0x80 ? 0x7F : 0x3F)) + 1;
    if (op & 0x80) {
      i += n;
    } else if (op & 0x40) {
      const uint8_t col = *p++;
      for (uint32_t k = 0; k < n; ++k) plot(i + k, col);
      i += n;
    } else {
      for (uint32_t k = 0; k < n; ++k) plot(i + k, p[k]);
      p += n;
      i += n;
    }
  }
}
