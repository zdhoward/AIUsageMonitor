// Dashboard renderer. Two tap-cycled views: a glanceable three-client console
// (default) and the original detailed dashboard. All positions derive from the
// canvas size after rotation, so the same code serves portrait and landscape.
#include "ui.h"
#include "config.h"
#include "face.h"
#include "anim.h"
#include "assets_gen.h"
#include "city.h"
#include "scenes_gen.h"
#include "tune.h"

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
  uint8_t id;
  void (*draw)(const Model&, uint32_t, const ViewDef&, int y);
};

static void drawConsole(const Model&, uint32_t, const ViewDef&, int y);
static void drawDetails(const Model&, uint32_t, const ViewDef&, int y);
static void drawCompanion(const Model&, uint32_t, const ViewDef&, int y);
static void drawImage(const Model&, uint32_t, const ViewDef&, int y);
static void drawCity(const Model&, uint32_t, const ViewDef&, int y);
static void drawScenes(const Model&, uint32_t, const ViewDef&, int y);
static void drawOneScene(const Model&, uint32_t, const ViewDef&, int y);
static void drawSystem(const Model&, uint32_t, const ViewDef&, int y);

static const ViewDef kAllViews[] = {
  {UI_PAGE_CONSOLE, drawConsole},
  {UI_PAGE_DETAILS, drawDetails},
  {UI_PAGE_COMPANION, drawCompanion},
  {UI_PAGE_IMAGE, drawImage},
  {UI_PAGE_CITY, drawCity},
  {UI_PAGE_SCENES, drawScenes},
  {UI_PAGE_SYSTEM, drawSystem},
};
// Tap order comes from UI_VIEW_ORDER; pages not compiled in are skipped.
static const uint8_t kAllCount = sizeof(kAllViews) / sizeof(kAllViews[0]);
static const uint8_t kOrder[] = {UI_VIEW_ORDER};
static ViewDef kStaticViews[kAllCount + 48];  // built-in pages plus single-scene pages
static const uint8_t kViewCap = sizeof(kStaticViews) / sizeof(kStaticViews[0]);
static uint8_t kViewCount = 0;
static uint8_t selView = 0;  // first page in UI_VIEW_ORDER
#define UI_MAX_DOTS 6  // more pages than this show an "n / m" counter instead

// Playlists rotate Roku-style. UI_PAGE_SCENES plays every compiled scene;
// pages from UI_PLAYLIST_PAGE_BASE play the profile's own playlists
// (playlists_gen.h, written by scripts/profile_gen.py).
struct Playlist {
  const uint8_t* scenes;  // indices into SCENES
  uint8_t count;
  uint16_t seconds;
  uint8_t weather;  // 0: each scene's own effects; 1: random weather per scene turn
};
#if __has_include("playlists_gen.h")
#include "playlists_gen.h"
#else
static const Playlist kPlaylists[1] = {};
static const uint8_t kPlaylistCount = 0;
#endif
static uint8_t playPos[17];      // slot 0: all scenes; 1+k: playlist k
static uint32_t playSince[17];
static uint8_t playWeather[17];  // 0: not picked yet, else 1 + WEATHER_*

// Random weather for playlists that ask for it: the scene keeps its stars,
// its own rain/snow/lightning is replaced. Clear skies are one of the picks.
enum { WEATHER_CLEAR, WEATHER_RAIN, WEATHER_SNOW, WEATHER_STORM, WEATHER_COUNT };
static const SceneDef& withWeather(const SceneDef& s, uint8_t weather) {
  static SceneDef out;
  static SceneEffect fx[10];
  uint8_t n = 0;
  for (uint8_t i = 0; i < s.fxCount && n < 8; ++i)
    if (s.fx[i].type == FX_STARS) fx[n++] = s.fx[i];
  if (weather == WEATHER_RAIN) fx[n++] = {FX_RAIN, 2, 0x93, 1};
  if (weather == WEATHER_SNOW) fx[n++] = {FX_SNOW, 2, 0xFF, 1};
  if (weather == WEATHER_STORM) {
    fx[n++] = {FX_RAIN, 3, 0x93, 1};
    fx[n++] = {FX_LIGHTNING, 1, 0xFF, (uint8_t)(s.layerCount > 1 ? 1 : 0)};
  }
  out = s;
  out.fx = fx;
  out.fxCount = n;
  return out;
}

// Every page is compiled in so the Studio can show any of them with !SHOW;
// the *_ENABLED switches only decide what a tap cycles through.
static bool inRotation(uint8_t id) {
  if (id >= UI_PLAYLIST_PAGE_BASE) return id - UI_PLAYLIST_PAGE_BASE < kPlaylistCount;
  if (id >= UI_SCENE_PAGE_BASE) return id - UI_SCENE_PAGE_BASE < SCENE_COUNT;
  return id == UI_PAGE_COMPANION ? UI_COMPANION_ENABLED : id == UI_PAGE_IMAGE ? UI_IMAGE_ENABLED :
         id == UI_PAGE_CITY ? UI_CITY_ENABLED : id == UI_PAGE_SCENES ? (UI_SCENES_ENABLED && SCENE_COUNT) : true;
}

// Pages from UI_SCENE_PAGE_BASE up show one scene each (index = id - base).
static const ViewDef* viewById(uint8_t id) {
  static ViewDef scenePage;
  if (id >= UI_SCENE_PAGE_BASE) {
    scenePage = {id, id >= UI_PLAYLIST_PAGE_BASE ? drawScenes : drawOneScene};
    return &scenePage;
  }
  for (const ViewDef& v : kAllViews)
    if (v.id == id) return &v;
  return &kAllViews[0];
}

static void buildViewOrder() {
  kViewCount = 0;
  for (uint8_t id : kOrder) {
    bool dup = false;
    for (uint8_t k = 0; k < kViewCount; ++k) dup |= kStaticViews[k].id == id;
    if (inRotation(id) && !dup && kViewCount < kViewCap) kStaticViews[kViewCount++] = *viewById(id);
  }
  if (!kViewCount) kStaticViews[kViewCount++] = kAllViews[0];
}
static bool saverActive = false;
static int16_t forcedId = -1;  // page shown by !SHOW until the next tap
static bool idleStarted = false;
static uint32_t lastActivity[2] = {};
static Model usageBaseline;
static bool haveUsageBaseline = false;

// Explicit measurements only: heartbeats, ages, countdowns and MINT updates
// must not hold the dashboard awake. Never compare struct padding.
static bool sameUsage(const Model& a, const Model& b) {
  if (a.valid != b.valid || a.ok != b.ok || strcmp(a.err, b.err) ||
      a.nacc != b.nacc || a.c1 != b.c1 || a.c7 != b.c7 ||
      a.i1 != b.i1 || a.cr1 != b.cr1 || a.o1 != b.o1 || a.unp != b.unp ||
      a.hasH != b.hasH || a.nbyp != b.nbyp || a.freeN != b.freeN ||
      a.freeT != b.freeT || strcmp(a.freeM, b.freeM) || a.nimN != b.nimN ||
      a.orOk != b.orOk || strcmp(a.orX, b.orX) || a.orFu != b.orFu ||
      a.orFl != b.orFl || a.orD != b.orD || a.orB != b.orB ||
      strcmp(a.actS, b.actS) || strcmp(a.actP, b.actP) ||
      strcmp(a.actM, b.actM) || a.actN != b.actN) return false;
  for (uint8_t i = 0; i < 24; ++i)
    if (a.h[i] != b.h[i]) return false;
  for (uint8_t i = 0; i < a.nbyp; ++i)
    if (strcmp(a.byp[i].p, b.byp[i].p) || a.byp[i].c1 != b.byp[i].c1) return false;
  for (uint8_t i = 0; i < a.nacc; ++i) {
    const AccData& x = a.acc[i];
    const AccData& y = b.acc[i];
    if (strcmp(x.p, y.p) || strcmp(x.pl, y.pl) || strcmp(x.x, y.x) ||
        x.rc != y.rc || x.nw != y.nw) return false;
    for (uint8_t j = 0; j < x.nw; ++j)
      if (strcmp(x.w[j].l, y.w[j].l) || x.w[j].u != y.w[j].u) return false;
  }
  return true;
}

static void updateSaver(const Model& m, uint32_t now) {
  if (!idleStarted) {
    lastActivity[0] = lastActivity[1] = now;
    idleStarted = true;
  }
  if (!haveUsageBaseline || !sameUsage(m, usageBaseline)) {
    usageBaseline = m;
    haveUsageBaseline = true;
    const uint8_t shown = kStaticViews[selView].id;
    for (uint8_t i = 0; i < 2; ++i) {
      const bool wake = i == 0 ? UI_CONSOLE_WAKE_ON_USAGE : UI_DETAILS_WAKE_ON_USAGE;
      if (i != shown || !saverActive || wake) lastActivity[i] = now;
      if (i == shown && wake) saverActive = false;
    }
  }
  const uint8_t id = kStaticViews[selView].id;
  const bool eligible = id == UI_PAGE_CONSOLE ? UI_CONSOLE_SAVER_ENABLED :
    id == UI_PAGE_DETAILS ? UI_DETAILS_SAVER_ENABLED : false;
  if (!UI_SCREENSAVER_ENABLED || !UI_SCREENSAVER_AUTO_ENABLED || !eligible) {
    saverActive = false;
    return;
  }
  const uint32_t timeout = id == UI_PAGE_CONSOLE ? UI_CONSOLE_SAVER_TIMEOUT_MS : UI_DETAILS_SAVER_TIMEOUT_MS;
  if ((uint32_t)(now - lastActivity[id]) >= timeout) saverActive = true;
}

// Palette (RGB565, quantized from the requested hex values).
// #101923 bg, #202C3B panel, #F3F6FA text, #AEBCCC secondary,
// #49D7A0 healthy, #F4BC52 warning, #FF6B6B critical.
// Snap the panel's blue up one RGB332 step: literal #202C3B truncates
// its blue to zero in the 8-bit sprite and produces an olive panel.
static const uint16_t C_BG = 0x10C4, C_PANEL = 0x216B, C_TEXT = 0xF7BF, C_MUTED = 0xADF9,
                      C_FAINT = 0x4ACD, C_GREEN = UI_COLOR_HEALTHY, C_AMBER = UI_COLOR_WARNING, C_RED = UI_COLOR_CRITICAL,
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

// Console ring: circular quota gauge filling clockwise from 12 o'clock with REMAINING quota.
// Underlying track is subdued C_TRACK. Outer radius r, stroke width, percent centered.
static void drawQuotaRing(int cx, int cy, int r, int stroke, int used, int easedUsed, uint16_t fillColor, const char* label) {
  TFT_eSPI& g = G();
  int ir = r - stroke;
  if (ir < 1) ir = 1;

  // Background track - full circle
  // C_TRACK and C_PANEL quantize to the same RGB332 shade. Use the next
  // subdued level so an empty 0% ring remains visible on this framebuffer.
  g.drawArc(cx, cy, r, ir, 0, 360, C_FAINT, C_BG, false);

  if (used < 0) {
    // Unknown quota: hatched or dashed track appearance with "--" inside
    for (int deg = 0; deg < 360; deg += 30) {
      g.drawArc(cx, cy, r, ir, deg, deg + 10, C_FAINT, C_BG, false);
    }
    text("--", cx, cy, 2, C_MUTED, MC_DATUM);
  } else {
    int left = 100 - min(used, 100);
    int easedLeft = 100 - min(easedUsed, 100);
    if (easedLeft > 0) {
      uint32_t endAngle = (uint32_t)((easedLeft * 360L + 50) / 100);
      if (endAngle > 360) endAngle = 360;
      if (endAngle > 0) {
        uint16_t col = fillColor ? fillColor : leftColor(left);
        // TFT_eSPI angles start at 6 o'clock. Start at 180 (12 o'clock)
        // and split at 360 so the visible remaining arc grows clockwise.
        if (endAngle <= 180) g.drawArc(cx, cy, r, ir, 180, 180 + endAngle, col, C_BG, false);
        else {
          g.drawArc(cx, cy, r, ir, 180, 360, col, C_BG, false);
          g.drawArc(cx, cy, r, ir, 0, endAngle - 180, col, C_BG, false);
        }
      }
    }
    char pct[8];
    snprintf(pct, sizeof pct, "%d%%", left);
    uint16_t numColor = fillColor ? fillColor : leftColor(left);
    text(pct, cx, cy, 2, numColor, MC_DATUM);
  }

  if (label && label[0]) {
    text(label, cx, cy + r + 2, 2, C_TEXT, TC_DATUM);
  }
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
// reorders accounts. Names that match no row (T3 display names such as "A")
// fill the free Claude rows in service order, which follows T3's cache files.
static int slotByName(const Model& m, int slot) {
  static const char* const ids[3] = {"cl1", "cl2", "codex"};
  static const char* const longs[3] = {"claude a", "claude b", "codex"};
  for (int i = 0; i < m.nacc; ++i)
    if (eqNoCase(m.acc[i].p, ids[slot])) return i;
  for (int i = 0; i < m.nacc; ++i)
    if (prefixNoCase(m.acc[i].p, longs[slot])) return i;
  return -1;
}

static int slotIndex(const Model& m, int slot) {
  const int named = slotByName(m, slot);
  if (named >= 0 || slot == 2) return named;
  int skip = 0;  // unnamed accounts to pass before this row's
  for (int s = 0; s < slot; ++s)
    if (slotByName(m, s) < 0) skip++;
  for (int i = 0; i < m.nacc; ++i) {
    bool claimed = false;
    for (int s = 0; s < 3; ++s) claimed |= slotByName(m, s) == i;
    if (!claimed && skip-- == 0) return i;
  }
  return -1;
}

static bool clientStale(const Model& m, const AccData& a, uint32_t now) {
  int32_t elapsed = (int32_t)((now - m.rxMillis) / 1000);
  return a.stale || (a.age >= 0 && a.age + elapsed > CLIENT_STALE_S) ||
         (now - m.rxMillis > DATA_TIMEOUT_MS);
}

// Windows are identified by their service label, never by urgency: the
// session window stays the main number and the weekly window sits beneath it.
static int windowIndex(const AccData* a, const char* label) {
  if (!a) return -1;
  for (int k = 0; k < a->nw; ++k)
    if (eqNoCase(a->w[k].l, label)) return k;
  return -1;
}

// Shared by column headings and every row so they stay aligned on rotation.
static int ringCenterX(int x, int w, bool weekly) {
  return x + (w >= 280 ? (weekly ? 257 : 173) : (weekly ? w - 38 : w - 100));
}

static void resetCaption(char* dst, size_t size, const WinData* window, int32_t elapsed) {
  if (!window || window->r < 0) strlcpy(dst, "--", size);
  else if (window->r <= elapsed) strlcpy(dst, "due", size);
  else fmtDur(dst, size, window->r - elapsed);
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
  // Title (font 2)
  int nameW = text(kClientName[slot], nx, y + 4, 2, a ? C_TEXT : C_MUTED, TL_DATUM, 110);
  bool stale = a && clientStale(m, *a, now);
  if (stale) text("STALE", nx + nameW + 6, y + 6, 1, C_AMBER);

  // Windows
  int si = windowIndex(a, "5h");
  int wi = windowIndex(a, "7d");
  const WinData* sw = si >= 0 ? &a->w[si] : nullptr;
  const WinData* ww = wi >= 0 ? &a->w[wi] : nullptr;

  // The space below the provider title is intentionally reserved and empty.
  char sReset[12], wReset[12];
  resetCaption(sReset, sizeof sReset, sw, elapsed);
  resetCaption(wReset, sizeof wReset, ww, elapsed);

  // Rings: Session on LEFT, Weekly on RIGHT
  // Landscape card width is ~300 (W=320, pad=10 -> w=300).
  // Recommended layout: left column x10..135, rings side by side in right region centered around x183 and x267.
  int ringR = 21;
  int ringStroke = 4;
  int ringCy = y + h / 2 - 8;

  int ring1Cx = ringCenterX(x, w, false), ring2Cx = ringCenterX(x, w, true);

  int sUsed = sw ? sw->u : -1;
  int sEased = (idx >= 0 && si >= 0) ? (int)(eased[idx][si] + 0.5f) : sUsed;
  drawQuotaRing(ring1Cx, ringCy, ringR, ringStroke, sUsed, sEased, 0, sReset);

  int wUsed = ww ? ww->u : -1;
  int wEased = (idx >= 0 && wi >= 0) ? (int)(eased[idx][wi] + 0.5f) : wUsed;
  drawQuotaRing(ring2Cx, ringCy, ringR, ringStroke, wUsed, wEased, UI_WEEKLY_COLOR, wReset);
}

static void drawConsole(const Model& m, uint32_t now, const ViewDef&, int) {
  TFT_eSPI& g = G();
  const int pad = W > H ? 10 : 8;

  int clients = 0;
  for (int slot = 0; slot < 3; ++slot)
    if (slotIndex(m, slot) >= 0) clients++;
  char b[28];
  snprintf(b, sizeof b, "AI USAGE (%d CLIENTS)", clients);
  bool portrait = H > W;
  text(b, pad, portrait ? 4 : 8, portrait ? 2 : 1, C_TEXT);
  int headingY = portrait ? 24 : 4;
  text("Session", ringCenterX(pad, W - 2 * pad, false), headingY,
       portrait ? 1 : 2, C_MUTED, TC_DATUM);
  text("Weekly", ringCenterX(pad, W - 2 * pad, true), headingY,
       portrait ? 1 : 2, C_MUTED, TC_DATUM);
  g.drawFastHLine(pad, portrait ? 36 : 22, W - 2 * pad, C_PANEL);

  // Landscape fits three 64px cards under the slim header; portrait spends its
  // extra height on wider row spacing instead of stretching the type.
  const int top = portrait ? 38 : 24, gap = portrait ? 4 : 2;
  int fy = H - 18;
  const int bottom = fy - 2;
  int ch = (bottom - top - 2 * gap) / 3;
  if (ch < 24) return;
  for (int slot = 0; slot < 3; ++slot)
    drawClientCard(m, now, slot, pad, top + slot * (ch + gap), W - 2 * pad, ch);

  // Footer: newest provider reading age (not the serial push age) + link
  // health. An idle account's reading ages on its own (T3 re-polls quota only
  // every few minutes); its card carries the STALE label, not the footer.
  int32_t elapsed = (int32_t)((now - m.rxMillis) / 1000);
  int32_t newest = -1;
  for (int i = 0; i < m.nacc; ++i)
    if (m.acc[i].age >= 0) {
      int32_t s = m.acc[i].age + elapsed;
      if (newest < 0 || s < newest) newest = s;
    }
  char d[10];
  if (newest < 0) strlcpy(b, "Updated --", sizeof b);
  else {
    if (newest < 60) snprintf(d, sizeof d, "%lds", (long)newest);
    else fmtDur(d, sizeof d, newest);
    snprintf(b, sizeof b, "Updated %s", d);
  }
  // Link health is a dot before the age: green ok, amber when no payload has
  // arrived for DATA_TIMEOUT_MS, red source error. Reserve the page
  // indicator's width (dots or the "n / m" counter).
  const bool linkLost = now - m.rxMillis > DATA_TIMEOUT_MS;
  const uint16_t sc = !m.ok ? C_RED : linkLost ? C_AMBER : C_GREEN;
  g.fillCircle(pad + 4, fy + 7, 4, col(sc));
  const int navSpace = (kViewCount <= UI_MAX_DOTS ? kViewCount * 10 : 56) + 8;
  text(b, pad + 14, fy, 2, C_MUTED, TL_DATUM, W - 2 * pad - 14 - navSpace);
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


// ---------------------------------------------------------------- system page
// Task Manager style view of the PC: CPU, RAM and GPU load as large readouts
// with bars, then disk read/write and network download/upload. Samples arrive
// about once a second; every number and bar eases toward the latest sample on
// each frame so the page moves smoothly instead of stepping.

static void fmtRate(char* num, size_t nn, char* unit, size_t nu, float kib) {
  if (kib < 1000) { snprintf(num, nn, "%.0f", kib); strlcpy(unit, "KB/s", nu); }
  else if (kib < 1024000) { snprintf(num, nn, kib < 10240 ? "%.1f" : "%.0f", kib / 1024); strlcpy(unit, "MB/s", nu); }
  else { snprintf(num, nn, "%.1f", kib / 1048576); strlcpy(unit, "GB/s", nu); }
}

// One load row: label (and optional detail) left, big percent right, bar below.
static void loadRow(int x, int y, int w, const char* label, const char* detail, float pct, bool known) {
  TFT_eSPI& g = G();
  char b[8];
  text(label, x, y + 6, 2, C_MUTED);
  if (detail) text(detail, x + 44, y + 10, 1, C_MUTED);
  const int p = (int)(pct + 0.5f);
  if (known) snprintf(b, sizeof b, "%d%%", p);
  else strlcpy(b, "--", sizeof b);
  text(b, x + w, y, 4, known ? C_TEXT : C_MUTED, TR_DATUM);
  const int by = y + 28, bh = 6;
  g.fillRoundRect(x, by, w, bh, 3, col(C_TRACK));
  const int fw = known ? (int)(w * min(pct, 100.0f) / 100) : 0;
  if (fw > 1) g.fillRoundRect(x, by, max(fw, bh), bh, 3, col(levelColor(p)));
}

// One I/O cell: small caption, big number with its unit.
static void rateCell(int x, int y, const char* label, uint16_t accent, float kib) {
  TFT_eSPI& g = G();
  char num[12], unit[6];
  g.fillCircle(x + 3, y + 4, 3, col(accent));
  text(label, x + 11, y, 1, C_MUTED);
  fmtRate(num, sizeof num, unit, sizeof unit, kib);
  const int nw = text(num, x, y + 12, 4, C_TEXT);
  text(unit, x + nw + 4, y + 22, 1, C_MUTED);
}

static float ease(float& v, float target, float alpha) { return v += (target - v) * alpha; }

static void drawSystem(const Model&, uint32_t now, const ViewDef&, int) {
  static float cpu, mem, gpu, dr, dw, nr, ns;
  static uint32_t last = 0;
  const SysData& s = gSys;
  char b[32];
  const int x = 12, w = W - 24;
  text("SYSTEM", x, 6, 2, C_TEXT);
  if (!s.valid) {
    text("Waiting for PC stats", W / 2, H / 2 - 8, 2, C_MUTED, TC_DATUM);
    text("needs aimon with psutil", W / 2, H / 2 + 12, 1, C_FAINT, TC_DATUM);
    return;
  }
  const uint32_t age = (now - s.rxMillis) / 1000;
  if (age > 5) {
    snprintf(b, sizeof b, "stale %lus", (unsigned long)age);
    text(b, x + w, 10, 1, C_AMBER, TR_DATUM);
  }

  // ~250 ms time constant: fast enough to track, slow enough to glide.
  const float a = last ? min(1.0f, (now - last) / 250.0f) : 1.0f;
  last = now;
  const float memPct = s.memTotal ? 100.0f * s.memUsed / s.memTotal : 0;
  ease(cpu, max<int8_t>(s.cpu, 0), a);
  ease(mem, memPct, a);
  ease(gpu, max<int8_t>(s.gpu, 0), a);
  ease(dr, s.diskR, a);
  ease(dw, s.diskW, a);
  ease(nr, s.netR, a);
  ease(ns, s.netS, a);

  int y = 26;
  loadRow(x, y, w, "CPU", nullptr, cpu, s.cpu >= 0);
  y += 40;
  snprintf(b, sizeof b, "%.1f / %.0f GB", s.memUsed / 1024.0, s.memTotal / 1024.0);
  loadRow(x, y, w, "RAM", s.memTotal ? b : nullptr, mem, s.memTotal > 0);
  y += 40;
  loadRow(x, y, w, "GPU", nullptr, gpu, s.gpu >= 0);
  y += 40;

  G().drawFastHLine(x, y, w, col(C_FAINT));
  y += 6;
  const int cx = x + w / 2 + 6;
  rateCell(x, y, "DISK READ", C_BLUE, dr);
  rateCell(cx, y, "DISK WRITE", C_AMBER, dw);
  y += 38;
  rateCell(x, y, "DOWNLOAD", C_GREEN, nr);
  rateCell(cx, y, "UPLOAD", C_BLUE, ns);
}

// ---------------------------------------------------------------- optional pages

static void drawCompanion(const Model&, uint32_t now, const ViewDef&, int) {
  faceDraw(G(), W, H, C_GREEN, C_BG);
}

// Frame-based pages need the RGB332 framebuffer; without it they explain why.
static bool canvas(Canvas8& c) {
  if (!spr) {
    text("Needs the frame buffer", W / 2, H / 2, 2, C_MUTED, MC_DATUM);
    return false;
  }
  c = {(uint8_t*)spr->getPointer(), W, H};
  return true;
}

static void drawImage(const Model&, uint32_t now, const ViewDef&, int) {
  Canvas8 c;
  if (!canvas(c)) return;
  // Rotates through the manifest's "image" assets; each frame time restarts
  // at its own turn so an animation always plays from the start.
#if IMAGE_ASSET_COUNT == 0  // art is personal and not in the repo
  text("Add images in assets/manifest.json", W / 2, H / 2, 2, C_MUTED, MC_DATUM);
  return;
#endif
  const uint32_t turn = UI_IMAGE_SECONDS * 1000UL;
  const AnimAsset& a = *IMAGE_ASSETS[(now / turn) % max(1, IMAGE_ASSET_COUNT)];
  now %= turn;
  const uint8_t scale = min(W / a.w, (H - 16) / a.h) ? min(W / a.w, (H - 16) / a.h) : 1;
  animBlit(c, a, animFrameAt(a, now), (W - a.w * scale) / 2 - a.x * scale,
           (H - 16 - a.h * scale) / 2 - a.y * scale, scale);
}

static void drawCity(const Model&, uint32_t now, const ViewDef&, int) {
  Canvas8 c;
  if (!canvas(c)) return;
#if CITY_ART
  cityDraw(c, now);
#else
  text("City art not installed (assets/scenes/city)", W / 2, H / 2, 2, C_MUTED, MC_DATUM);
#endif
}


static void drawScenes(const Model&, uint32_t now, const ViewDef& v, int) {
  Canvas8 c;
  if (!canvas(c)) return;
  const bool custom = v.id >= UI_PLAYLIST_PAGE_BASE;
  const uint8_t k = custom ? v.id - UI_PLAYLIST_PAGE_BASE : 0, slot = custom ? k + 1 : 0;
  const uint8_t len = custom ? (k < kPlaylistCount ? kPlaylists[k].count : 0) : SCENE_COUNT;
  if (!SCENE_COUNT || !len || slot >= sizeof(playPos)) {
    text("No scenes in this playlist", W / 2, H / 2, 2, C_MUTED, MC_DATUM);
    return;
  }
  const uint32_t hold = (custom ? kPlaylists[k].seconds : UI_SCENE_SECONDS) * 1000UL;
  if (!playSince[slot]) playSince[slot] = now;
  if (now - playSince[slot] >= hold) {
    playPos[slot] = (uint8_t)((playPos[slot] + 1) % len);
    playSince[slot] = now;
    playWeather[slot] = 0;
  }
  const uint8_t p = playPos[slot] % len;
  const SceneDef& s = sceneResolve((custom ? kPlaylists[k].scenes[p] : p) % SCENE_COUNT);
  if (custom && kPlaylists[k].weather) {
    if (!playWeather[slot]) playWeather[slot] = 1 + esp_random() % WEATHER_COUNT;
    sceneDraw(c, withWeather(s, playWeather[slot] - 1), now);
  } else {
    sceneDraw(c, s, now);
  }
}

static void drawOneScene(const Model&, uint32_t now, const ViewDef& v, int) {
  Canvas8 c;
  if (!canvas(c)) return;
  const uint8_t i = v.id - UI_SCENE_PAGE_BASE;
  if (i < SCENE_COUNT) sceneDraw(c, sceneResolve(i), now);
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
  buildViewOrder();
  tft.init();
  uiSetRotation(rotation);
}

bool uiHasFramebuffer() { return spr != nullptr; }

uint32_t uiFrameIntervalMs() {
  const uint8_t id = forcedId >= 0 ? forcedId : saverActive ? UI_SCREENSAVER_PAGE : kStaticViews[selView].id;
  if (id == UI_PAGE_CITY || id == UI_PAGE_SCENES || id >= UI_SCENE_PAGE_BASE) return 40UL;
  return id == UI_PAGE_COMPANION || id == UI_PAGE_IMAGE ? 33UL : REDRAW_MS;
}

bool uiScreenshot(Stream& out) {
  if (!spr) return false;
  out.printf("@SHOT %d %d 8\n", W, H);  // RGB332, row-major, as sent to the panel
  out.write((const uint8_t*)spr->getPointer(), (size_t)W * H);
  out.print("\n@SHOTEND\n");
  return true;
}

bool uiShow(const char* name) {
  static const struct { const char* name; uint8_t id; } kPages[] = {
    {"console", UI_PAGE_CONSOLE}, {"details", UI_PAGE_DETAILS}, {"companion", UI_PAGE_COMPANION},
    {"image", UI_PAGE_IMAGE}, {"city", UI_PAGE_CITY}, {"scenes", UI_PAGE_SCENES},
    {"system", UI_PAGE_SYSTEM}};
  for (const auto& p : kPages)
    if (!strcmp(name, p.name)) {
      forcedId = p.id;
      saverActive = false;
      return true;
    }
  if (!strncmp(name, "playlist-", 9)) {  // playlist-<index> in profile order
    const int k = atoi(name + 9);
    if (k < 0 || k >= kPlaylistCount) return false;
    forcedId = UI_PLAYLIST_PAGE_BASE + k;
    saverActive = false;
    return true;
  }
  for (uint8_t i = 0; i < SCENE_COUNT; ++i)
    if (!strcmp(name, SCENES[i].id)) {
      forcedId = UI_SCENE_PAGE_BASE + i;
      saverActive = false;
      return true;
    }
  return false;
}

void uiNextView(const Model&) {
  if (forcedId >= 0) forcedId = -1;
  else if (saverActive) saverActive = false;
  else selView = (uint8_t)((selView + 1) % kViewCount);
  if (kStaticViews[selView].id < 2) lastActivity[kStaticViews[selView].id] = millis();
}

void uiGoHome() {
  forcedId = -1;
  saverActive = false;
  for (uint8_t i = 0; i < kViewCount; ++i)
    if (kStaticViews[i].id == UI_HOME_PAGE) { selView = i; break; }
  if (kStaticViews[selView].id < 2) lastActivity[kStaticViews[selView].id] = millis();
}

// Page position, bottom right. A few pages get dots; past UI_MAX_DOTS the dots
// would run across the screen, so show a "3 / 14" counter over a thin track
// whose bright segment marks the current page.
static void drawDots(uint8_t current) {
  TFT_eSPI& g = G();
  if (kViewCount <= UI_MAX_DOTS) {
    for (uint8_t i = 0; i < kViewCount; ++i)
      g.fillCircle(W - 10 - (kViewCount - 1 - i) * 10, H - 9, 2, i == current ? C_TEXT : C_FAINT);
    return;
  }
  char b[12];
  snprintf(b, sizeof b, "%u / %u", current + 1, kViewCount);
  const int tw = 48, tx = W - 8 - tw, ty = H - 4;
  text(b, W - 8, H - 15, 1, C_MUTED, TR_DATUM);
  g.drawFastHLine(tx, ty, tw, col(C_FAINT));
  const int sw = max(3, tw / kViewCount), sx = tx + (tw - sw) * current / (kViewCount - 1);
  g.fillRect(sx, ty - 1, sw, 2, col(C_TEXT));
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

static uint32_t renderUs = 0;
uint32_t uiLastRenderUs() { return renderUs; }

void uiRender(const Model& m, uint32_t now, const char* linkInfo) {
  const uint32_t t0 = micros();
  updateSaver(m, now);
  TFT_eSPI& g = G();
  // The base TFT API can retain its portrait extent on a sprite. Clear the
  // actual rotated canvas so landscape's right edge has no startup remnants.
  g.fillRect(0, 0, W, H, C_BG);
  dim = false;  // cached readings remain fully readable, regardless of link age
  animate(m, now);
  const uint8_t current = selView < kViewCount ? selView : 0;
  const bool away = forcedId >= 0 || saverActive;  // showing a page outside the tap order
  const ViewDef& v = forcedId >= 0 ? *viewById(forcedId) : saverActive ? *viewById(UI_SCREENSAVER_PAGE)
                                                                         : kStaticViews[current];
  faceUpdate(now, v.id == UI_PAGE_COMPANION);
  const bool dashboard = v.id == UI_PAGE_CONSOLE || v.id == UI_PAGE_DETAILS;
  if (!m.valid && dashboard) {
    drawHeader(m, now, 0, 0, W);
    drawWaiting(now, linkInfo);
  } else {
    if (v.id == UI_PAGE_CONSOLE) {
      v.draw(m, now, v, 0);
    } else if (v.id == UI_PAGE_DETAILS) {
      int y = drawHeader(m, now, 0, 0, W);
      v.draw(m, now, v, y);
      text("tap to change view", 10, H - 13, 1, C_MUTED);
    } else {
      v.draw(m, now, v, 0);
    }
  }
  if (!away && v.id != UI_PAGE_COMPANION && v.id != UI_PAGE_CITY && v.id != UI_PAGE_SCENES && v.id < UI_SCENE_PAGE_BASE)
    drawDots(current);
  if (spr) spr->pushSprite(0, 0);
  renderUs = micros() - t0;
}
