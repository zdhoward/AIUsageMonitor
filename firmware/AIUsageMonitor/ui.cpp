// Dashboard renderer. All positions derive from the canvas size after
// rotation, so the same code serves portrait (single column) and landscape
// (two columns) in any of the four orientations.
#include "ui.h"
#include "config.h"

static TFT_eSPI* tftp = nullptr;
static TFT_eSprite* spr = nullptr;  // full-frame 8-bit buffer when memory allows
static int W = 0, H = 0;
static bool dim = false;            // no fresh data: grey everything out
static uint8_t viewIndex = 0;       // overview, each account, detailed dashboard
static float eased[4][3] = {};
static char easedAccount[4][9] = {};
static char easedWindow[4][3][5] = {};
static uint32_t animationMillis = 0;

// Palette (RGB565)
// Chosen to survive the 8-bit (RGB332) frame buffer without tinting.
static const uint16_t C_BG = 0x0000, C_PANEL = 0x014B, C_TEXT = 0xFFFF, C_MUTED = 0x9CF3,
                      C_FAINT = 0x4208, C_GREEN = 0x2E66, C_AMBER = 0xFD20, C_RED = 0xF186,
                      C_BLUE = 0x5D7F, C_TRACK = 0x4A4A;

// Dimmed mode keeps two grey levels so bars stay readable against their track.
static uint16_t col(uint16_t c) {
  if (!dim || c == C_BG) return c;
  return (c == C_TRACK || c == C_FAINT || c == C_PANEL) ? C_FAINT : C_MUTED;
}

static uint16_t levelColor(int u) {
  if (u < 0) return C_MUTED;
  if (u >= 80) return C_RED;
  if (u >= 50) return C_AMBER;
  return C_GREEN;
}

// ---------------------------------------------------------------- formatting

static void fmtDur(char* b, size_t n, int32_t s) {
  if (s < 0) snprintf(b, n, "?");
  else if (s == 0) snprintf(b, n, "reset");
  else if (s < 3600) snprintf(b, n, "%ldm", (long)((s + 59) / 60));
  else if (s < 86400) snprintf(b, n, "%ldh%02ldm", (long)(s / 3600), (long)((s % 3600) / 60));
  else snprintf(b, n, "%ldd%ldh", (long)(s / 86400), (long)((s % 86400) / 3600));
}

static void fmtTok(char* b, size_t n, uint32_t t) {
  if (t < 1000) snprintf(b, n, "%lu", (unsigned long)t);
  else if (t < 1000000) snprintf(b, n, "%.1fK", t / 1e3);
  else if (t < 1000000000) snprintf(b, n, "%.1fM", t / 1e6);
  else snprintf(b, n, "%.1fB", t / 1e9);
}

static void fmtUsd(char* b, size_t n, int32_t cents) {
  if (cents < 0) snprintf(b, n, "--");
  else if (cents >= 10000) snprintf(b, n, "$%ld", (long)(cents / 100));
  else snprintf(b, n, "$%ld.%02ld", (long)(cents / 100), (long)(cents % 100));
}

// ---------------------------------------------------------------- primitives

static TFT_eSPI& G() { return spr ? (TFT_eSPI&)*spr : *tftp; }

// Draws text clipped to maxW pixels (adds '~' when cut). Returns width drawn.
static int text(const char* s, int x, int y, uint8_t font, uint16_t fg, uint8_t datum = TL_DATUM, int maxW = 0) {
  TFT_eSPI& g = G();
  g.setTextFont(font);
  g.setTextDatum(datum);
  g.setTextColor(col(fg));
  char buf[48];
  strlcpy(buf, s, sizeof buf);
  if (maxW > 0) {
    size_t len = strlen(buf);
    while (len > 1 && g.textWidth(buf) > maxW) {
      buf[--len] = 0;
      buf[len - 1] = '~';
    }
  }
  g.drawString(buf, x, y);
  return g.textWidth(buf);
}

// Quota values arrive as percent USED; SHOW_REMAINING flips what is displayed.
static int shown(int used) { return used < 0 ? -1 : (SHOW_REMAINING ? 100 - min(used, 100) : used); }

// `u` is percent used. The fill follows the display mode; the colour always
// follows usage, so red means nearly exhausted either way.
static void bar(int x, int y, int w, int h, int u) {
  TFT_eSPI& g = G();
  g.fillRoundRect(x, y, w, h, 2, col(C_TRACK));
  if (u < 0) {  // unknown: hatched outline, never an empty "0%" bar
    g.drawRoundRect(x, y, w, h, 2, col(C_MUTED));
    for (int i = x + 3; i < x + w - 2; i += 6) g.drawLine(i, y + h - 2, i + 3, y + 1, col(C_FAINT));
    return;
  }
  int fw = (int)((long)w * shown(u) / 100);
  if (fw > 0) g.fillRoundRect(x, y, max(fw, 3), h, 2, col(levelColor(u)));
}

// ---------------------------------------------------------------- sections

static int drawHeader(const Model& m, uint32_t now, int x, int y, int w) {
  TFT_eSPI& g = G();
  const int h = 20;
  g.fillRect(x, y, w, h, col(C_PANEL));
  text("AI USAGE", x + 4, y + 2, 2, C_TEXT);
  char b[24];
  uint16_t c;
  if (!m.valid) {
    snprintf(b, sizeof b, "WAITING");
    c = C_AMBER;
  } else if (now - m.rxMillis > DATA_TIMEOUT_MS) {
    char d[10];
    fmtDur(d, sizeof d, (now - m.rxMillis) / 1000);
    snprintf(b, sizeof b, "NO DATA %s", d);
    c = C_RED;
  } else {
    snprintf(b, sizeof b, "%s%s", m.ok ? "" : "! ", m.hm);
    c = m.ok ? C_GREEN : C_AMBER;
  }
  // Header status stays bright even when the body is dimmed.
  bool wasDim = dim;
  dim = false;
  int tw = text(b, x + w - 4, y + 2, 2, c, TR_DATUM);
  g.fillCircle(x + w - 12 - tw, y + h / 2, 4, c);
  dim = wasDim;
  return h + 2;
}

static int drawActivity(const Model& m, uint32_t now, int x, int y, int w) {
  const int h = 18;
  char b[64], d[10];
  if (!strcmp(m.actS, "run")) {
    bool on = (now / 500) % 2;
    G().fillCircle(x + 7, y + 8, 4, col(on ? C_GREEN : C_PANEL));
    G().drawCircle(x + 7, y + 8, 4, col(C_GREEN));
    fmtDur(d, sizeof d, m.actT < 0 ? -1 : m.actT + (int32_t)((now - m.rxMillis) / 1000));
    if (m.actN > 1) snprintf(b, sizeof b, "%s %s +%d  %s", m.actP, m.actM, m.actN - 1, d);
    else snprintf(b, sizeof b, "%s %s  %s", m.actP, m.actM, d);
    text(b, x + 16, y + 1, 2, C_TEXT, TL_DATUM, w - 18);
  } else if (!strcmp(m.actS, "idle")) {
    G().drawCircle(x + 7, y + 8, 4, col(C_MUTED));
    fmtDur(d, sizeof d, m.actT < 0 ? -1 : m.actT + (int32_t)((now - m.rxMillis) / 1000));
    if (m.actP[0]) snprintf(b, sizeof b, "idle  last %s %s %s", m.actP, m.actM, d);
    else snprintf(b, sizeof b, "idle");
    text(b, x + 16, y + 1, 2, C_MUTED, TL_DATUM, w - 18);
  } else {
    text("activity: unavailable", x + 4, y + 1, 2, C_MUTED, TL_DATUM, w - 6);
  }
  return h;
}

static int drawPeak(const Model& m, int x, int y, int w) {
  TFT_eSPI& g = G();
  const int h = 24;
  char b[40];
  if (m.hasHi) {
    uint16_t c = levelColor(m.hiU);
    g.fillRoundRect(x + 2, y, w - 4, h - 2, 4, col(c));
    if (SHOW_REMAINING) snprintf(b, sizeof b, "LOWEST %d%% left", shown(m.hiU));
    else snprintf(b, sizeof b, "PEAK %d%% used", m.hiU);
    text(b, x + 8, y + 3, 2, C_BG, TL_DATUM);
    snprintf(b, sizeof b, "%s %s", m.hiP, m.hiW);
    text(b, x + w - 8, y + 3, 2, C_BG, TR_DATUM);
  } else {
    g.drawRoundRect(x + 2, y, w - 4, h - 2, 4, col(C_MUTED));
    text(SHOW_REMAINING ? "LOWEST --  no fresh quota data" : "PEAK --  no fresh quota data", x + 8, y + 3, 2, C_MUTED, TL_DATUM, w - 14);
  }
  return h + 2;
}

static int drawAccounts(const Model& m, uint32_t now, int x, int y, int w, int maxH) {
  int used = 0;
  const int rowH = 16;
  int32_t elapsed = (now - m.rxMillis) / 1000;
  char b[32], d[12];
  for (int i = 0; i < m.nacc; i++) {
    const AccData& a = m.acc[i];
    int need = rowH + max<int>(a.nw, 1) * rowH + 3;
    if (used + need > maxH) break;
    int yy = y + used;
    G().fillRect(x + 4, yy + 4, 8, 8, col(a.color));
    int nw = text(a.p, x + 16, yy, 2, C_TEXT);
    if (a.pl[0] || a.rc > 0) {
      char pl[32];
      if (a.rc > 0) snprintf(pl, sizeof pl, "%s (%dx reset%s)", a.pl, a.rc, a.rc == 1 ? "" : "s");
      else snprintf(pl, sizeof pl, "%s", a.pl);
      text(pl, x + 20 + nw, yy + 4, 1, a.rc > 0 ? C_BLUE : C_MUTED, TL_DATUM, w - 70 - nw);
    }
    if (a.age < 0) snprintf(b, sizeof b, "age ?");
    else {
      fmtDur(d, sizeof d, a.age + elapsed);
      snprintf(b, sizeof b, a.stale ? "STALE %s" : "%s ago", d);
    }
    text(b, x + w - 4, yy + 4, 1, a.stale ? C_AMBER : C_MUTED, TR_DATUM);
    yy += rowH;
    if (a.nw == 0) {
      snprintf(b, sizeof b, "limits n/a: %s", a.x[0] ? a.x : "unknown");
      text(b, x + 16, yy + 4, 1, C_MUTED, TL_DATUM, w - 20);
      yy += rowH;
    }
    for (int k = 0; k < a.nw; k++) {
      const WinData& wd = a.w[k];
      const int labelW = 22, pctW = 34, rstW = (w >= 200) ? 50 : 40;
      text(wd.l, x + 16, yy, 2, C_MUTED);
      int bx = x + 16 + labelW, bw = w - 16 - labelW - pctW - rstW - 8;
      bar(bx, yy + 3, bw, 10, wd.u);
      if (wd.u < 0) snprintf(b, sizeof b, "--");
      else snprintf(b, sizeof b, "%d%%", shown(wd.u));
      text(b, bx + bw + pctW, yy, 2, a.stale ? C_MUTED : levelColor(wd.u), TR_DATUM);
      int32_t r = wd.r > 0 ? max<int32_t>(wd.r - elapsed, 0) : wd.r;
      fmtDur(d, sizeof d, r);
      text(d, x + w - 4, yy, 2, C_MUTED, TR_DATUM);
      yy += rowH;
    }
    used += need;
  }
  if (m.nacc == 0 && maxH >= rowH) {
    text("No subscription accounts found", x + 4, y + 2, 2, C_MUTED, TL_DATUM, w - 6);
    used += rowH + 2;
  }
  return used;
}

static void sparkline(const Model& m, int x, int y, int w, int h) {
  TFT_eSPI& g = G();
  uint16_t mx = 1;
  for (int i = 0; i < 24; i++) mx = max(mx, m.h[i]);
  int bw = max(1, (w - 23) / 24);
  int ox = x + (w - bw * 24 - 23) / 2;
  for (int i = 0; i < 24; i++) {
    int bh = m.h[i] ? max(1, (int)((long)m.h[i] * (h - 1) / mx)) : 0;
    int bx = ox + i * (bw + 1);
    g.drawFastHLine(bx, y + h - 1, bw, col(C_TRACK));
    if (bh) g.fillRect(bx, y + h - bh, bw, bh, col(i == 23 ? C_BLUE : C_MUTED));
  }
}

// Lays out short text items left to right, wrapping to new lines within
// width w, so the same content fits a wide portrait row or a narrow landscape
// column. Items flagged in `optional` (bit i) are dropped instead of wrapped.
// Stops at maxH. Returns the height used.
static int flow(const char* const* items, const uint16_t* colors, int n, int x, int y, int w, int maxH,
                uint8_t font, uint8_t optional = 0) {
  TFT_eSPI& g = G();
  g.setTextFont(font);
  const int lineH = font == 1 ? 10 : 17, gap = font == 1 ? 10 : 12;
  int cx = 0, cy = 0;
  for (int i = 0; i < n; i++) {
    if (!items[i] || !items[i][0]) continue;
    int iw = g.textWidth(items[i]);
    if (cx > 0 && cx + gap + iw > w) {  // wrap
      if (optional & (1 << i)) continue;
      cx = 0;
      cy += lineH;
    }
    if (cy + lineH > maxH) return cy;
    if (cx > 0) cx += gap;
    cx += text(items[i], x + cx, y + cy, font, colors[i], TL_DATUM, w - cx);
  }
  return cx > 0 || cy > 0 ? cy + lineH : 0;
}

static int drawUsage(const Model& m, int x, int y, int w, int maxH) {
  int yy = y;
  const int ix = x + 4, iw = w - 8;
  auto left = [&]() { return y + maxH - yy; };
  char s1[40], s2[40], s3[40], s4[40], a[16];

  // Subscription accounts: API-price estimate (never a bill)
  G().drawFastHLine(ix, yy, iw, col(C_FAINT));
  yy += 2;
  fmtUsd(a, sizeof a, m.c1);
  snprintf(s1, sizeof s1, "est %s today", a);
  fmtUsd(a, sizeof a, m.c7);
  snprintf(s2, sizeof s2, "7d %s", a);
  {
    const char* it[] = {s1, s2};
    const uint16_t cl[] = {C_TEXT, C_MUTED};
    yy += flow(it, cl, 2, ix, yy, iw, left(), 2);
  }
  fmtTok(a, sizeof a, m.i1);
  snprintf(s1, sizeof s1, "in %s", a);
  fmtTok(a, sizeof a, m.cr1);
  snprintf(s2, sizeof s2, "cache %s", a);
  fmtTok(a, sizeof a, m.o1);
  snprintf(s3, sizeof s3, "out %s%s", a, m.unp ? " +unpriced" : "");
  {
    const char* it[] = {s1, s2, s3};
    const uint16_t cl[] = {C_MUTED, C_MUTED, C_MUTED};
    yy += flow(it, cl, 3, ix, yy, iw, left(), 1);
  }
  if (m.nbyp) {
    static char bp[4][24];
    const char* it[4];
    uint16_t cl[4];
    for (int i = 0; i < m.nbyp; i++) {
      fmtUsd(a, sizeof a, m.byp[i].c1);
      snprintf(bp[i], sizeof bp[i], "%s %s", m.byp[i].p, a);
      it[i] = bp[i];
      cl[i] = C_MUTED;
    }
    yy += flow(it, cl, m.nbyp, ix, yy, iw, left(), 1);
  }
  if (m.hasH && left() >= 18) {  // hourly API-price estimate, last 24 h; current hour in blue
    sparkline(m, ix, yy + 1, iw, 15);
    yy += 18;
  }

  // Free and pay-as-you-go providers
  if (left() >= 12) {
    G().drawFastHLine(ix, yy, iw, col(C_FAINT));
    yy += 2;
  }
  if (m.freeN < 0) {
    const char* it[] = {"Free: unavailable"};
    const uint16_t cl[] = {C_MUTED};
    yy += flow(it, cl, 1, ix, yy, iw, left(), 1);
  } else {
    snprintf(s1, sizeof s1, "Free %ld req", (long)m.freeN);
    fmtTok(a, sizeof a, m.freeT);
    snprintf(s2, sizeof s2, "%s tok", a);
    const char* it[] = {s1, s2, m.freeM};
    const uint16_t cl[] = {C_TEXT, C_TEXT, C_MUTED};
    yy += flow(it, cl, 3, ix, yy, iw, left(), 1, 0b100);
  }
  if (m.orOk) {
    bool hot = m.orFl > 0 && m.orFu * 100 / m.orFl >= 80;
    if (m.orFl > 0) snprintf(s1, sizeof s1, "OpenRouter free %d/%d", m.orFu, m.orFl);
    else snprintf(s1, sizeof s1, "OpenRouter");
    fmtUsd(a, sizeof a, m.orD);
    snprintf(s2, sizeof s2, "%s/day", a);
    fmtUsd(a, sizeof a, m.orB);
    snprintf(s3, sizeof s3, "%s left", a);
    const char* it[] = {s1, s2, s3};
    const uint16_t cl[] = {hot ? C_AMBER : C_TEXT, C_MUTED, C_MUTED};
    yy += flow(it, cl, 3, ix, yy, iw, left(), 1, 0b100);
  } else {
    snprintf(s1, sizeof s1, "OpenRouter: %s", m.orX[0] ? m.orX : "unavailable");
    const char* it[] = {s1};
    const uint16_t cl[] = {C_MUTED};
    yy += flow(it, cl, 1, ix, yy, iw, left(), 1);
  }
  if (m.nimN < 0) snprintf(s1, sizeof s1, "NIM: unavailable");
  else snprintf(s1, sizeof s1, "NIM %ld req", (long)m.nimN);
  snprintf(s4, sizeof s4, "(no quota API)");
  {
    const char* it[] = {s1, s4};
    const uint16_t cl[] = {C_MUTED, C_FAINT};
    yy += flow(it, cl, 2, ix, yy, iw, left(), 1, 0b10);
  }
  {
    const char* it[] = {m.ok ? "est = API-price estimate," : m.err, m.ok ? "not billed" : ""};
    const uint16_t cl[] = {m.ok ? C_FAINT : C_AMBER, C_FAINT};
    yy += flow(it, cl, 2, ix, yy, iw, left(), 1);
  }
  return yy - y;
}

static void drawWaiting(uint32_t now, const char* linkInfo) {
  TFT_eSPI& g = G();
  char b[48];
  int cy = H / 2 - 30;
  text("Waiting for data", W / 2, cy, 4, C_TEXT, TC_DATUM);
  text(linkInfo, W / 2, cy + 32, 2, C_MUTED, TC_DATUM, W - 8);
  text("Start the aimon service on the PC", W / 2, cy + 52, 1, C_MUTED, TC_DATUM, W - 8);
  snprintf(b, sizeof b, "fw %s  rot %d  %dx%d", FW_VERSION, DISPLAY_ROTATION, W, H);
  text(b, W / 2, H - 14, 1, C_FAINT, TC_DATUM);
  // Orientation marker: arrow at the logical top-centre.
  g.fillTriangle(W / 2, 24, W / 2 - 8, 36, W / 2 + 8, 36, col(C_BLUE));
  (void)now;
}

// ---------------------------------------------------------------- public

void uiNextView(const Model& m) {
  viewIndex = (viewIndex + 1) % (m.nacc + 2);
}

// All visual tuning lives here; transport/model retain exact measured values.
// Ease bars only: percentages remain truthful and immediately readable.
static void animate(const Model& m, uint32_t now) {
  float alpha = UI_ANIMATION ? min(1.0f, (now - animationMillis) / 350.0f) : 1.0f;
  animationMillis = now;
  for (int i = 0; i < m.nacc; ++i) {
    bool changed = strcmp(easedAccount[i], m.acc[i].p);
    strlcpy(easedAccount[i], m.acc[i].p, sizeof easedAccount[i]);
    for (int k = 0; k < m.acc[i].nw; ++k) {
      int u = m.acc[i].w[k].u;
      bool reset = changed || strcmp(easedWindow[i][k], m.acc[i].w[k].l);
      strlcpy(easedWindow[i][k], m.acc[i].w[k].l, sizeof easedWindow[i][k]);
      if (reset || u < 0) eased[i][k] = u;
      else eased[i][k] += (u - eased[i][k]) * alpha;
    }
  }
}

static void drawQuotaView(const Model& m, uint32_t now, int y, int account) {
  bool focus = account >= 0;
  int count = focus ? 1 : m.nacc;
  int available = H - y - 24;
  if (!count) {
    text("Waiting for quota readings", W / 2, H / 2, 2, C_MUTED, MC_DATUM);
    return;
  }
  int rowH = available / count;
  for (int row = 0; row < count; ++row) {
    int i = focus ? account : row;
    const AccData& a = m.acc[i];
    int top = y + row * rowH;
    G().drawFastVLine(8, top + 8, rowH - 16, a.color);
    text(a.p, 18, top + 5, 4, C_TEXT);
    text(a.stale ? "CACHED" : a.pl, W - 10, top + 12, 1,
         a.stale ? C_AMBER : C_MUTED, TR_DATUM);
    int slots = max<int>(1, a.nw);
    int slotH = (rowH - 32) / slots;
    if (!a.nw) text("No readings yet", 18, top + 36, 2, C_MUTED);
    for (int k = 0; k < a.nw; ++k) {
      const WinData& wd = a.w[k];
      int yy = top + 32 + k * slotH;
      char pct[12], reset[20], dur[12];
      if (wd.u < 0) strcpy(pct, "--");
      else snprintf(pct, sizeof pct, "%d%%", shown(wd.u));
      int32_t remain = wd.r < 0 ? -1 : max<int32_t>(0, wd.r - (now - m.rxMillis) / 1000);
      fmtDur(dur, sizeof dur, remain);
      snprintf(reset, sizeof reset, remain == 0 ? "awaiting update" : "reset %s", dur);
      if (!focus) {
        int cellW = (W - 28) / slots;
        int xx = 18 + k * cellW;
        text(wd.l, xx, top + 32, 1, C_MUTED);
        text(pct, xx + cellW - 8, top + 29, 4, levelColor(wd.u), TR_DATUM);
        bar(xx, top + 57, cellW - 8, 5, wd.u < 0 ? -1 : (int)(eased[i][k] + 0.5f));
        text(remain == 0 ? "update due" : reset, xx, top + 65, 1, C_TEXT, TL_DATUM, cellW - 4);
        continue;
      }
      text(wd.l, 18, yy + (focus ? 3 : 0), 2, C_MUTED);
      text(pct, W - 10, yy, focus ? 4 : 2, levelColor(wd.u), TR_DATUM);
      int by = yy + (focus ? 34 : 18);
      bar(18, by, W - 28, focus ? 12 : 5, wd.u < 0 ? -1 : (int)(eased[i][k] + 0.5f));
      text(reset, 18, by + (focus ? 22 : 7), focus ? 4 : 1, C_TEXT, TL_DATUM, W - 28);
    }
  }
}

void uiSetRotation(uint8_t rotation) {
  tftp->setRotation(rotation & 3);
  tftp->fillScreen(C_BG);
  W = tftp->width();
  H = tftp->height();
  if (spr) {
    spr->deleteSprite();
  } else {
    spr = new TFT_eSprite(tftp);
    spr->setColorDepth(8);
  }
  if (!spr->createSprite(W, H)) {  // not enough RAM: draw straight to the panel
    delete spr;
    spr = nullptr;
  }
}

void uiBegin(TFT_eSPI& tft, uint8_t rotation) {
  tftp = &tft;
  tft.init();
  uiSetRotation(rotation);
}

bool uiHasFramebuffer() { return spr != nullptr; }

bool uiScreenshot(Stream& out) {
  if (!spr) return false;
  out.printf("@SHOT %d %d 8\n", W, H);  // RGB332, row-major, as sent to the panel
  out.write((const uint8_t*)spr->getPointer(), (size_t)W * H);
  out.print("\n@SHOTEND\n");
  return true;
}

void uiRender(const Model& m, uint32_t now, const char* linkInfo) {
  TFT_eSPI& g = G();
  g.fillScreen(C_BG);
  dim = false; // cached readings remain fully readable, regardless of link age
  animate(m, now);
  if (viewIndex >= m.nacc + 2) viewIndex = 0;
  int y = drawHeader(m, now, 0, 0, W);
  if (!m.valid) {
    drawWaiting(now, linkInfo);
  } else if (viewIndex <= m.nacc) {
    text(SHOW_REMAINING ? "ALLOWANCE LEFT" : "ALLOWANCE USED", 10, y + 4, 2, C_MUTED);
    drawQuotaView(m, now, y + 25, viewIndex == 0 ? -1 : viewIndex - 1);
  } else {
    y += drawActivity(m, now, 0, y, W);
    y += drawPeak(m, 0, y, W);
    if (W > H) {  // landscape: quotas left, usage right
      int cw = W / 2;
      drawAccounts(m, now, 0, y, cw - 2, H - y);
      G().drawFastVLine(cw, y, H - y, col(C_FAINT));
      drawUsage(m, cw + 2, y, W - cw - 2, H - y);
    } else {
      y += drawAccounts(m, now, 0, y, W, H - y);
      drawUsage(m, 0, y, W, H - y);
    }
  }
  if (m.valid) {
    G().fillRect(0, H - 18, W, 18, C_BG);
    text("tap to change view", 10, H - 13, 1, C_MUTED);
    for (int i = 0; i < m.nacc + 2; ++i)
      G().fillCircle(W - 10 - (m.nacc + 1 - i) * 10, H - 9, 2, i == viewIndex ? C_TEXT : C_FAINT);
  }
  if (spr) spr->pushSprite(0, 0);
}
