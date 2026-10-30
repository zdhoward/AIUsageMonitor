#pragma once
// Dashboard data model. Filled from the service JSON by parsePayload();
// rendered by ui.cpp. Values of -1 mean "not reported" and are shown as
// unavailable, never as zero.
#include <Arduino.h>

#include "config.h"

struct WinData {
  char l[5];      // window label: 5h, 7d
  int16_t u;      // used percent, -1 unknown
  int32_t r;      // seconds to reset at receive time; -1 unknown, 0 = reset already passed
};

struct AccData {
  char p[9];      // account display name (CL1, CL2, Codex)
  char pl[9];     // plan (Pro, Plus)
  char x[21];     // unavailable reason
  uint16_t color; // RGB565 accent
  int32_t age;    // seconds since the provider was last checked, -1 unknown
  bool stale;
  int16_t rc;     // banked limit resets available (0 = none or not reported)
  WinData w[3];
  uint8_t nw;
};

struct Model {
  char mintSid[17] = "";
  uint32_t mintN = 0, mintAt = 0, mintTtl = 0;
  char mintExpression[10] = "content";
  bool valid = false;
  uint32_t seq = 0;
  uint32_t rxMillis = 0;  // millis() when this payload arrived
  char hm[6] = "";        // PC local time of the payload
  bool ok = true;         // every source read cleanly
  char err[41] = "";

  // activity
  char actS[5] = "na";    // run | idle | na
  char actP[11] = "";
  char actM[23] = "";
  int16_t actN = 0;
  int32_t actT = -1;

  // highest fresh quota use
  bool hasHi = false;
  int16_t hiU = -1;
  char hiP[9] = "";
  char hiW[5] = "";

  AccData acc[6];
  uint8_t nacc = 0;

  // subscription usage today (API-equivalent estimate, cents)
  int32_t c1 = -1, c7 = -1;
  uint32_t i1 = 0, cr1 = 0, o1 = 0;
  bool unp = false;
  uint16_t h[24] = {0};
  bool hasH = false;
  struct { char p[9]; int32_t c1; } byp[4];
  uint8_t nbyp = 0;

  // free / other providers today
  int32_t freeN = -1;
  uint32_t freeT = 0;
  char freeM[23] = "";
  int32_t nimN = -1;

  // OpenRouter
  bool orOk = false;
  char orX[17] = "";
  int16_t orFu = -1, orFl = -1;
  int32_t orD = -1, orB = -1, orAge = -1;

  // Location-based automatic backlight level (0..255). Missing or invalid
  // keeps the last received level; explicit zero (backlight off) is valid.
  // Firmware applies it for USB and Wi-Fi payloads and retains last value on
  // disconnect, with BACKLIGHT_LEVEL at boot.
  uint8_t bl = 0;        // last accepted duty 0..255
  bool hasBl = false;    // any valid bl received since boot
  uint32_t blMs = BACKLIGHT_SMOOTHING_MS; // duration for the next target, 0 = instant

  // Service-provided warning interval (seconds before a reset). Absent or
  // negative keeps the original due-only behaviour. The real reset countdown
  // in WinData::r is never adjusted by this.
  int32_t warnS = -1;
};

bool parsePayload(const char* json, size_t len, Model& out);

// PC resources for the System page. Arrives as its own {"t":"sys"} line about
// once a second, independent of the usage payload. -1 means not reported.
struct SysData {
  bool valid = false;
  uint32_t rxMillis = 0;
  int8_t cpu = -1, gpu = -1;
  uint32_t memUsed = 0, memTotal = 0;                 // MiB
  uint32_t diskR = 0, diskW = 0, netR = 0, netS = 0;  // KiB/s
};
extern SysData gSys;

bool parseSys(const char* json, size_t len, SysData& out);

// CPAMC proxy groups for the Proxy page. Arrives as its own {"t":"proxy"} line
// about every 30 s (contract in .tickets/T-028.md). `r` is percent REMAINING,
// -1 unknown; `z` is the next reset epoch, 0 none. Epochs need a clock: the
// optional top-level "ts" (current epoch) anchors countdowns; without it they
// show "--".
struct ProxyWin {
  char l[5];   // window label: 5h, 7d, 30d
  int8_t r;    // remaining percent 0..100, -1 unknown
  uint32_t z;  // next reset epoch, 0 none
};
struct ProxyPool {
  char l[8];   // pool label (Flash, Cl/GPT, Argon)
  ProxyWin w[2];  // w[0] is the shorter window (outer ring), w[1] the longer
  uint8_t nw = 0;
};
struct ProxyGroup {
  char n[10];  // group name
  uint8_t c = 0;      // active accounts
  bool a = false;     // needs the owner's attention
  bool multi = false; // "m": double-wide tile, one mini ring set per pool
  ProxyPool p[3];
  uint8_t np = 0;
};
struct ProxyData {
  bool valid = false;
  uint32_t rxMillis = 0;
  bool up = false;     // proxy reachable
  int32_t age = -1;    // seconds since the last good poll, -1 unknown
  bool attn = false;   // global danger flag
  uint32_t ts = 0;     // epoch at receive time, 0 unknown
  ProxyGroup g[6];
  uint8_t ng = 0;
};
extern ProxyData gProxy;

bool parseProxy(const char* json, size_t len, ProxyData& out);
