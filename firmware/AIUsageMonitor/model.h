#pragma once
// Dashboard data model. Filled from the service JSON by parsePayload();
// rendered by ui.cpp. Values of -1 mean "not reported" and are shown as
// unavailable, never as zero.
#include <Arduino.h>

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

  AccData acc[4];
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
};

bool parsePayload(const char* json, size_t len, Model& out);
