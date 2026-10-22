// Dashboard renderer. Two tap-cycled views: a glanceable three-client console
// (default) and the original detailed dashboard. All positions derive from the
// canvas size after rotation, so the same code serves portrait and landscape.
#include "ui.h"
#include "config.h"

static TFT_eSPI* tftp = nullptr;
static TFT_eSprite* spr = nullptr;  // full-frame 8-bit buffer when memory allows
static int W = 0, H = 0;
static bool dim = false;            // legacy detail dimming; console stays bright
static float eased[4][3] = {};
static char easedAccount[4][9] = {};
static char easedWindow[4][3][5] = {};
static uint32_t animationMillis = 0;

// ---------------------------------------------------------------- view registry
// Every tap stop is one static descriptor with a render callback. Navigation
// and pagination dots read this list, so a new page needs one entry plus its
// renderer. Generated overview/focus pages are intentionally gone.
struct ViewDef {
  void (*draw)(const Model&, uint32_t, const ViewDef&, int y);
};

static void drawConsole(const Model&, uint32_t, const ViewDef&, int y);
static void drawDetails(const Model&, uint32_t, const ViewDef&, int y);

static const ViewDef kStaticViews[] = {
  {drawConsole},
  {drawDetails},
};
static const uint8_t kViewCount = sizeof(kStaticViews) / sizeof(kStaticViews[0]);
static uint8_t selView = 0;  // console is the default view

// Palette (RGB565, quantized from the requested hex values).
// #101923 bg, #202C3B panel, #F3F6FA text, #AEBCCC secondary,
// #49D7A0 healthy, #F4BC52 warning, #FF6B6B critical.
// Snap the panel's blue up one RGB332 step: literal #202C3B truncates
// its blue to zero in the 8-bit sprite and produces an olive panel.
static const uint16_t C_BG = 0x10C4, C_PANEL = 0x216B, C_TEXT = 0xF7BF, C_MUTED = 0xADF9,
                      C_FAINT = 0x4ACD, C_GREEN = 0x4EB4, C_AMBER = 0xF5EA, C_RED = 0xFB4D,
                      C_BLUE = 0x5D5F, C_TRACK = 0x29E9;

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

// Threshold colour for a REMAINING percentage.
static uint16_t leftColor(int left) {
  if (left < 0) return C_MUTED;
  if (left <= UI_CRITICAL_LEFT) return C_RED;
  if (left <= UI_WARNING_LEFT) return C_AMBER;
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
static int text(const char* s, int x, int y, uint8_t font, uint16_t fg, uint8_t datum = TL_DATUM, int maxW = 0,
                uint8_t size = 1) {
  TFT_eSPI& g = G();
  g.setTextFont(font);
  g.setTextDatum(datum);
  g.setTextSize(size);
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
  int w = g.textWidth(buf);
  g.drawString(buf, x, y);
  g.setTextSize(1);
  return w;
}

// Quota values arrive as percent USED; SHOW_REMAINING flips the detail view.
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

// Console bar: always fills with REMAINING quota, coloured by the thresholds.
static void leftBar(int x, int y, int w, int h, int used, int easedUsed) {
  TFT_eSPI& g = G();
  g.fillRoundRect(x, y, w, h, 2, C_TRACK);
  if (used < 0) {
    g.drawRoundRect(x, y, w, h, 2, C_MUTED);
    for (int i = x + 3; i < x + w - 2; i += 6) g.drawLine(i, y + h - 2, i + 3, y + 1, C_FAINT);
    return;
  }
  int left = 100 - min(used, 100);
  int easedLeft = 100 - min(easedUsed, 100);
  int fw = (int)((long)w * easedLeft / 100);
  if (fw > 0) g.fillRoundRect(x, y, max(fw, 3), h, 2, leftColor(left));
}

// ---------------------------------------------------------------- console

static const char* const kClientName[3] = {"CLAUDE A", "CLAUDE B", "CODEX"};
static const char* const kClientId[3] = {"CL1", "CL2", "Codex"};

static bool eqNoCase(const char* a, const char* b) {
  while (*a && *b) {
    if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return false;
    ++a;
    ++b;
  }
  return !*a && !*b;
}

static bool prefixNoCase(const char* s, const char* prefix) {
  while (*prefix) {
    if (!*s || tolower((unsigned char)*s) != tolower((unsigned char)*prefix)) return false;
    ++s;
    ++prefix;
  }
  return true;
}

// Stable slot mapping: CL1, CL2, Codex keep their rows even when the service
// reorders accounts. Unknown names leave the row at "--" rather than guess.
static int slotIndex(const Model& m, int slot) {
  static const char* const ids[3] = {"cl1", "cl2", "codex"};
  static const char* const longs[3] = {"claude a", "claude b", "codex"};
  for (int i = 0; i < m.nacc; ++i)
    if (eqNoCase(m.acc[i].p, ids[slot])) return i;
  for (int i = 0; i < m.nacc; ++i)
    if (prefixNoCase(m.acc[i].p, longs[slot])) return i;
  return -1;
}

static bool clientStale(const Model& m, const AccData& a, uint32_t now) {
  int32_t elapsed = (int32_t)((now - m.rxMillis) / 1000);
  return a.stale || (a.age >= 0 && a.age + elapsed > CLIENT_STALE_S) ||
         (now - m.rxMillis > DATA_TIMEOUT_MS);
}

static void drawClientCard(const Model& m, uint32_t now, int slot, int x, int y, int w, int h) {
  TFT_eSPI& g = G();
  g.fillRoundRect(x, y, w, h, 5, C_PANEL);

  int idx = slotIndex(m, slot);
  const AccData* a = idx >= 0 ? &m.acc[idx] : nullptr;
  int32_t elapsed = (int32_t)((now - m.rxMillis) / 1000);

  const int ix = x + 8;
  int nx = ix;
  bool running = a && !strcmp(m.actS, "run") && eqNoCase(m.actP, a->p);
  if (running) {
    g.fillCircle(ix + 3, y + 11, 3, C_GREEN);  // only a measured running account
    nx += 10;
  }
  int nameW = text(kClientName[slot], nx, y + 4, 2, a ? C_TEXT : C_MUTED, TL_DATUM, w - 20);
  int idW = text(kClientId[slot], nx + nameW + 5, y + 8, 1, C_MUTED);
  bool stale = a && clientStale(m, *a, now);
  if (stale) text("STALE", nx + nameW + idW + 11, y + 6, 1, C_AMBER);

  // The largest number is the exact remaining percentage of the most urgent
  // measured window (highest used). Quotas are never averaged.
  const WinData* uw = nullptr;
  int uk = -1;
  if (a) {
    int best = -1;
    for (int k = 0; k < a->nw; ++k)
      if (a->w[k].u >= 0 && a->w[k].u > best) {
        best = a->w[k].u;
        uk = k;
      }
    if (uk < 0 && a->nw > 0) uk = 0;
    if (uk >= 0) uw = &a->w[uk];
  }
  int left = uw && uw->u >= 0 ? 100 - min((int)uw->u, 100) : -1;
  char pct[8];
  if (left < 0) strcpy(pct, "--");
  else snprintf(pct, sizeof pct, "%d%%", left);

  // Grow the percentage when the card is tall enough for it.
  uint8_t pctSize = (h >= 96 && w >= 210) ? 2 : 1;
  int pw = text(pct, x + w - 8, y + 2, 4, leftColor(left), TR_DATUM, 0, pctSize);
  if (uw) text(uw->l, x + w - 12 - pw, y + 7, 2, C_MUTED, TR_DATUM, 24);
  text("REMAINING", ix, y + 21, 1, C_MUTED);

  bool tall = h >= 72;
  int barY = y + (tall ? 40 : 30);
  int barH = tall ? 6 : 4;
  int easedUsed = (idx >= 0 && uk >= 0) ? (int)(eased[idx][uk] + 0.5f) : (uw ? uw->u : -1);
  leftBar(ix, barY, w - 16, barH, uw ? uw->u : -1, easedUsed);

  char rst[24];
  if (!uw || uw->r < 0) strlcpy(rst, "Reset unavailable", sizeof rst);
  else {
    int32_t rem = max<int32_t>(0, uw->r - elapsed);
    if (rem == 0) strlcpy(rst, "Update due", sizeof rst);
    else {
      char d[10];
      fmtDur(d, sizeof d, rem);
      snprintf(rst, sizeof rst, "Reset %s", d);
    }
  }
  int resetY = barY + barH + 2;
  int rw = text(rst, ix, resetY, 2, left < 0 ? C_MUTED : C_TEXT);

  // Second (and third) quota, smaller but legible. Space decides the line.
  char sec[48] = "";
  if (a) {
    for (int k = 0; k < a->nw; ++k) {
      if (k == uk) continue;
      const WinData& wd = a->w[k];
      char p2[8];
      if (wd.u < 0) strcpy(p2, "--");
      else snprintf(p2, sizeof p2, "%d%%", 100 - min((int)wd.u, 100));
      char d[10] = "";
      if (wd.r >= 0) fmtDur(d, sizeof d, max<int32_t>(0, wd.r - elapsed));
      char item[24];
      if (d[0]) snprintf(item, sizeof item, "%s %s %s", wd.l, p2, d);
      else snprintf(item, sizeof item, "%s %s", wd.l, p2);
      if (sec[0]) strlcat(sec, "  ", sizeof sec);
      strlcat(sec, item, sizeof sec);
      break;  // one secondary quota keeps the card calm
    }
  }
  if (sec[0]) {
    if (tall) text(sec, ix, resetY + 18, 1, C_MUTED, TL_DATUM, w - 16);
    else text(sec, x + w - 8, resetY + 4, 1, C_MUTED, TR_DATUM, w - 16 - rw - 6);
  }
}

static void drawConsole(const Model& m, uint32_t now, const ViewDef&, int) {
  TFT_eSPI& g = G();
  const int pad = W > H ? 10 : 8;

  text("AI USAGE", pad, 8, 2, C_TEXT);
  int clients = 0;
  for (int slot = 0; slot < 3; ++slot)
    if (slotIndex(m, slot) >= 0) clients++;
  char b[20];
  snprintf(b, sizeof b, "%d CLIENTS", clients);
  text(b, W - pad, 8, 2, C_MUTED, TR_DATUM);

  g.drawFastHLine(pad, 32, W - 2 * pad, C_PANEL);

  const int top = 37, bottom = H - 38, gap = 3;
  int ch = (bottom - top - 2 * gap) / 3;
  if (ch < 24) return;
  for (int slot = 0; slot < 3; ++slot)
    drawClientCard(m, now, slot, pad, top + slot * (ch + gap), W - 2 * pad, ch);

  // Footer: oldest provider source age (not the serial push age) + link health.
  int fy = H - 26;
  int32_t elapsed = (int32_t)((now - m.rxMillis) / 1000);
  int32_t oldest = -1;
  bool anyStale = now - m.rxMillis > DATA_TIMEOUT_MS;
  for (int i = 0; i < m.nacc; ++i) {
    if (m.acc[i].stale) anyStale = true;
    if (m.acc[i].age >= 0) {
      int32_t s = m.acc[i].age + elapsed;
      if (s > oldest) oldest = s;
      if (s > CLIENT_STALE_S) anyStale = true;
    }
  }
  char d[10];
  if (oldest < 0) strlcpy(b, "Updated --", sizeof b);
  else {
    if (oldest < 60) snprintf(d, sizeof d, "%lds", (long)oldest);
    else fmtDur(d, sizeof d, oldest);
    snprintf(b, sizeof b, "Updated %s", d);
  }
  text(b, pad, fy, 2, C_MUTED);

  const char* st;
  uint16_t sc;
  if (!m.ok) {
    st = "SOURCE ERROR";
    sc = C_RED;
  } else if (anyStale) {
    st = "STALE";
    sc = C_AMBER;
  } else {
    st = "CONNECTED";
    sc = C_GREEN;
  }
  text(st, W - pad - 28, fy, 2, sc, TR_DATUM, W - 80);
}

// ---------------------------------------------------------------- detail sections

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
  } else if (m.hiU >= 0) {  // retained window, not a fresh measurement
    uint16_t c = levelColor(m.hiU);
    g.drawRoundRect(x + 2, y, w - 4, h - 2, 4, col(c));
    if (SHOW_REMAINING) snprintf(b, sizeof b, "CACHED LOW %d%% left", shown(m.hiU));
    else snprintf(b, sizeof b, "CACHED PEAK %d%%", m.hiU);
    text(b, x + 8, y + 3, 2, c, TL_DATUM, w - 70);
    snprintf(b, sizeof b, "%s %s", m.hiP, m.hiW);
    text(b, x + w - 8, y + 3, 2, c, TR_DATUM);
  } else {
    g.drawRoundRect(x + 2, y, w - 4, h - 2, 4, col(C_MUTED));
    text(SHOW_REMAINING ? "LOWEST --  no quota data" : "PEAK --  no quota data", x + 8, y + 3, 2, C_MUTED, TL_DATUM, w - 14);
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
  // Cached OpenRouter numbers stay visible even when the latest read failed:
  // show whatever numbers exist plus a short error indicator. Never fake clean.
  bool orNumbers = m.orFu >= 0 || m.orFl >= 0 || m.orD >= 0 || m.orB >= 0;
  if (m.orOk || orNumbers) {
    bool hot = m.orFl > 0 && m.orFu * 100 / m.orFl >= 80;
    if (m.orFl > 0) snprintf(s1, sizeof s1, "OpenRouter free %d/%d", m.orFu, m.orFl);
    else snprintf(s1, sizeof s1, "OpenRouter");
    if (!m.orOk) strlcat(s1, " !", sizeof s1);
    fmtUsd(a, sizeof a, m.orD);
    snprintf(s2, sizeof s2, "%s/day", a);
    fmtUsd(a, sizeof a, m.orB);
    snprintf(s3, sizeof s3, "%s left", a);
    const char* it[] = {s1, s2, s3};
    const uint16_t cl[] = {!m.orOk ? C_AMBER : (hot ? C_AMBER : C_TEXT), C_MUTED, C_MUTED};
    yy += flow(it, cl, 3, ix, yy, iw, left(), 1, 0b100);
    if (!m.orOk) {
      snprintf(s1, sizeof s1, "OpenRouter: %s", m.orX[0] ? m.orX : "unavailable");
      const char* e[] = {s1};
      const uint16_t ec[] = {C_AMBER};
      yy += flow(e, ec, 1, ix, yy, iw, left(), 1);
    }
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

static void drawDetails(const Model& m, uint32_t now, const ViewDef&, int y) {
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

// ---------------------------------------------------------------- public

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

void uiNextView(const Model&) {
  selView = (uint8_t)((selView + 1) % kViewCount);
}

static void drawDots(uint8_t current) {
  for (uint8_t i = 0; i < kViewCount; ++i)
    G().fillCircle(W - 10 - (kViewCount - 1 - i) * 10, H - 9, 2, i == current ? C_TEXT : C_FAINT);
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

void uiRender(const Model& m, uint32_t now, const char* linkInfo) {
  TFT_eSPI& g = G();
  g.fillScreen(C_BG);
  dim = false;  // cached readings remain fully readable, regardless of link age
  animate(m, now);
  uint8_t current = selView < kViewCount ? selView : 0;
  if (!m.valid) {
    drawHeader(m, now, 0, 0, W);
    drawWaiting(now, linkInfo);
  } else {
    const ViewDef& v = kStaticViews[current];
    if (v.draw == drawConsole) {
      v.draw(m, now, v, 0);
    } else {
      int y = drawHeader(m, now, 0, 0, W);
      v.draw(m, now, v, y);
      text("tap to change view", 10, H - 13, 1, C_MUTED);
    }
    drawDots(current);
  }
  if (spr) spr->pushSprite(0, 0);
}
