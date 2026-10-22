#include "model.h"
#include <ArduinoJson.h>

static uint16_t hexTo565(const char* hex) {
  if (!hex || strlen(hex) < 6) return 0x8410;
  uint32_t v = strtoul(hex, nullptr, 16);
  uint8_t r = (v >> 16) & 0xFF, g = (v >> 8) & 0xFF, b = v & 0xFF;
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

static void copyStr(char* dst, size_t n, JsonVariantConst v) {
  const char* s = v | "";
  strlcpy(dst, s, n);
}

// Parses into a scratch model first so a malformed line never clobbers the
// last good data.
bool parsePayload(const char* json, size_t len, Model& out) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, json, len);
  if (err || (doc["v"] | 0) != 1) return false;

  static Model m;  // static: too big for the loop task stack
  m = Model();
  m.valid = true;
  m.rxMillis = millis();
  m.seq = doc["seq"] | 0;
  copyStr(m.hm, sizeof m.hm, doc["hm"]);
  m.ok = (doc["ok"] | 0) == 1;
  copyStr(m.err, sizeof m.err, doc["err"]);

  JsonObjectConst act = doc["act"];
  copyStr(m.actS, sizeof m.actS, act["s"]);
  if (!m.actS[0]) strcpy(m.actS, "na");
  copyStr(m.actP, sizeof m.actP, act["p"]);
  copyStr(m.actM, sizeof m.actM, act["m"]);
  m.actN = act["n"] | 1;
  m.actT = act["t"] | -1;

  JsonObjectConst hi = doc["hi"];
  m.hasHi = !hi.isNull();
  if (m.hasHi) {
    m.hiU = hi["u"] | -1;
    copyStr(m.hiP, sizeof m.hiP, hi["p"]);
    copyStr(m.hiW, sizeof m.hiW, hi["w"]);
  }

  for (JsonObjectConst a : doc["acc"].as<JsonArrayConst>()) {
    if (m.nacc >= 4) break;
    AccData& d = m.acc[m.nacc++];
    copyStr(d.p, sizeof d.p, a["p"]);
    copyStr(d.pl, sizeof d.pl, a["pl"]);
    copyStr(d.x, sizeof d.x, a["x"]);
    d.color = hexTo565(a["c"] | "888888");
    d.age = a["age"] | -1;
    d.stale = (a["st"] | 1) == 1;
    d.rc = a["rc"] | 0;
    d.nw = 0;
    for (JsonObjectConst w : a["w"].as<JsonArrayConst>()) {
      if (d.nw >= 3) break;
      WinData& wd = d.w[d.nw++];
      copyStr(wd.l, sizeof wd.l, w["l"]);
      wd.u = w["u"] | -1;
      wd.r = w["r"] | -1;
    }
  }

  JsonObjectConst use = doc["use"];
  if (!use.isNull()) {
    m.c1 = use["c1"] | -1;
    m.c7 = use["c7"] | -1;
    m.i1 = use["i1"] | 0;
    m.cr1 = use["cr1"] | 0;
    m.o1 = use["o1"] | 0;
    m.unp = (use["unp"] | 0) == 1;
    JsonArrayConst h = use["h"];
    m.hasH = h.size() == 24;
    for (size_t i = 0; i < 24 && i < h.size(); i++) m.h[i] = h[i] | 0;
  }
  for (JsonObjectConst b : doc["byp"].as<JsonArrayConst>()) {
    if (m.nbyp >= 4) break;
    copyStr(m.byp[m.nbyp].p, sizeof m.byp[0].p, b["p"]);
    m.byp[m.nbyp++].c1 = b["c1"] | 0;
  }

  JsonObjectConst fr = doc["free"];
  if (!fr.isNull()) {
    m.freeN = fr["n"] | -1;
    m.freeT = fr["t"] | 0;
    copyStr(m.freeM, sizeof m.freeM, fr["m"]);
  }
  m.nimN = doc["nim"]["n"] | -1;

  JsonObjectConst o = doc["or"];
  copyStr(m.orX, sizeof m.orX, o["x"]);
  m.orOk = !o.isNull() && !m.orX[0];
  m.orFu = o["fu"] | -1;
  m.orFl = o["fl"] | -1;
  m.orD = o["d"] | -1;
  m.orB = o["b"] | -1;
  m.orAge = o["age"] | -1;
  if (!m.orOk && out.orOk) {
    m.orOk = true;
    m.orFu = out.orFu; m.orFl = out.orFl;
    m.orD = out.orD; m.orB = out.orB;
    m.orAge = out.orAge < 0 ? -1 : out.orAge + (millis() - out.rxMillis) / 1000;
  }

  // Merge by account/window identity, never by array position. Missing values
  // are not measurements: retain the last reading and its reset countdown.
  const int32_t elapsed = (millis() - out.rxMillis) / 1000;
  for (int i = 0; i < out.nacc; ++i) {
    const AccData& old = out.acc[i];
    int index = -1;
    for (int j = 0; j < m.nacc; ++j)
      if (!strcmp(old.p, m.acc[j].p)) index = j;
    if (index < 0 && m.nacc < 4) {
      index = m.nacc++;
      m.acc[index] = old;
      if (old.age >= 0) m.acc[index].age = old.age + elapsed;
      m.acc[index].nw = 0;
      m.acc[index].stale = true;
    }
    if (index < 0) continue;
    AccData& dest = m.acc[index];
    for (int k = 0; k < old.nw; ++k) {
      int wi = -1;
      for (int j = 0; j < dest.nw; ++j)
        if (!strcmp(old.w[k].l, dest.w[j].l)) wi = j;
      if (wi < 0 && dest.nw < 3) {
        wi = dest.nw++;
        dest.w[wi] = old.w[k];
        dest.w[wi].u = -1;
        dest.w[wi].r = -1;
      }
      if (wi < 0) continue;
      if (dest.w[wi].u < 0) dest.w[wi].u = old.w[k].u;
      if (dest.w[wi].r < 0 && old.w[k].r >= 0)
        dest.w[wi].r = max<int32_t>(0, old.w[k].r - elapsed);
    }
  }
  out = m;
  return true;
}
