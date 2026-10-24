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

// A present measurement replaces the cached one, including an explicit zero.
// -1 keeps its "not reported" meaning, so it falls back to the cached reading.
static void keepNum(JsonVariantConst v, int32_t& dst) {
  if (v.isNull()) return;
  int32_t n = v | (int32_t)-1;
  if (n >= 0) dst = n;
}

static void keepI16(JsonVariantConst v, int16_t& dst) {
  if (v.isNull()) return;
  int32_t n = v | (int32_t)-1;
  if (n >= 0) dst = (int16_t)n;
}

// Counts and flags have no "unknown" sentinel; presence alone decides.
static void keepU32(JsonVariantConst v, uint32_t& dst) {
  if (v.isNull()) return;
  dst = v | (uint32_t)0;
}

static void keepBool(JsonVariantConst v, bool& dst) {
  if (v.isNull()) return;
  dst = (v | 0) == 1;
}

// Parses into a scratch model first so a malformed line never clobbers the
// last good data. Sections and fields that are absent (or explicitly
// unavailable) are carried over from `out`, with countdowns aged by the time
// since the previous payload.
bool parsePayload(const char* json, size_t len, Model& out) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, json, len);
  if (err || (doc["v"] | 0) != 1) return false;

  static Model m;  // static: too big for the loop task stack
  m = Model();
  m.valid = true;
  m.rxMillis = millis();
  const int32_t elapsed = out.valid ? (int32_t)((m.rxMillis - out.rxMillis) / 1000) : 0;
  m.seq = doc["seq"] | 0;
  // Lease identity survives missing fields and expiry. Invalid input clears the
  // expression without erasing the high-water mark, so replay cannot renew it.
  strlcpy(m.mintSid, out.mintSid, sizeof m.mintSid);
  m.mintN = out.mintN;
  JsonObjectConst mint = doc["mint"];
  const char* sid = mint["sid"] | "";
  const char* expression = mint["e"] | "";
  bool sidValid = strlen(sid) == 16;
  for (size_t i = 0; sidValid && i < 16; ++i)
    sidValid = (sid[i] >= '0' && sid[i] <= '9') || (sid[i] >= 'a' && sid[i] <= 'f');
  bool expressionValid = false;
  const char* names[] = {"content", "happy", "curious", "bored", "sleepy", "surprised", "stressed"};
  for (const char* name : names) if (!strcmp(name, expression)) expressionValid = true;
  uint32_t n = mint["n"] | (uint32_t)0;
  uint32_t ttl = mint["ttl"] | (uint32_t)0;
  int order = strcmp(sid, out.mintSid);
  if (sidValid && expressionValid && mint["n"].is<uint32_t>() && n > 0 &&
      mint["ttl"].is<uint32_t>() && ttl > 0 && ttl <= 15000 &&
      (order > 0 || (order == 0 && n > out.mintN))) {
    strlcpy(m.mintSid, sid, sizeof m.mintSid);
    strlcpy(m.mintExpression, expression, sizeof m.mintExpression);
    m.mintN = n;
    m.mintAt = m.rxMillis;
    m.mintTtl = ttl;
  }
  if (!doc["hm"].isNull()) copyStr(m.hm, sizeof m.hm, doc["hm"]);
  else strlcpy(m.hm, out.hm, sizeof m.hm);

  // Status flags: an explicit clean payload clears the old error, while an
  // omitted flag keeps the last one instead of pretending everything is fine.
  if (!doc["ok"].isNull()) {
    m.ok = (doc["ok"] | 0) == 1;
    if (!doc["err"].isNull()) copyStr(m.err, sizeof m.err, doc["err"]);
    else if (!m.ok) strlcpy(m.err, out.err, sizeof m.err);
  } else {
    m.ok = out.ok;
    if (!doc["err"].isNull()) copyStr(m.err, sizeof m.err, doc["err"]);
    else strlcpy(m.err, out.err, sizeof m.err);
  }

  // Activity. "na" is unavailable, not a measurement, so keep the last known
  // run/idle state and age its duration by the elapsed time.
  JsonObjectConst act = doc["act"];
  const char* actState = act["s"] | "";
  if (actState[0] && strcmp(actState, "na")) {
    copyStr(m.actS, sizeof m.actS, act["s"]);
    copyStr(m.actP, sizeof m.actP, act["p"]);
    copyStr(m.actM, sizeof m.actM, act["m"]);
    m.actN = act["n"] | 1;
    m.actT = act["t"] | -1;
  } else if (out.valid && strcmp(out.actS, "na")) {
    strlcpy(m.actS, out.actS, sizeof m.actS);
    strlcpy(m.actP, out.actP, sizeof m.actP);
    strlcpy(m.actM, out.actM, sizeof m.actM);
    m.actN = out.actN;
    m.actT = out.actT < 0 ? -1 : out.actT + elapsed;
  }

  // Quota accounts: merge by account name, then windows by label.
  for (JsonObjectConst a : doc["acc"].as<JsonArrayConst>()) {
    if (m.nacc >= 4) break;
    AccData d = AccData();
    copyStr(d.p, sizeof d.p, a["p"]);
    const AccData* old = nullptr;
    for (int i = 0; i < out.nacc; ++i)
      if (!strcmp(out.acc[i].p, d.p)) old = &out.acc[i];

    copyStr(d.pl, sizeof d.pl, a["pl"]);
    if (a["pl"].isNull() && old) strlcpy(d.pl, old->pl, sizeof d.pl);

    // The unavailable reason is current status, not metadata: absence clears it.
    copyStr(d.x, sizeof d.x, a["x"]);

    JsonVariantConst c = a["c"];
    const char* cs = c | "";
    if (cs[0]) d.color = hexTo565(cs);
    else d.color = old ? old->color : 0x8410;

    JsonVariantConst age = a["age"];
    if (!age.isNull() && (age | -1) >= 0) d.age = age | -1;
    else if (old && old->age >= 0) d.age = old->age + elapsed;
    else d.age = -1;

    JsonVariantConst st = a["st"];
    d.stale = st.isNull() ? true : ((st | 1) == 1);

    JsonVariantConst rc = a["rc"];
    if (!rc.isNull()) d.rc = rc | 0;  // explicit zero clears banked resets
    else d.rc = old ? old->rc : 0;

    d.nw = 0;
    for (JsonObjectConst w : a["w"].as<JsonArrayConst>()) {
      if (d.nw >= 3) break;
      WinData& wd = d.w[d.nw++];
      copyStr(wd.l, sizeof wd.l, w["l"]);
      wd.u = w["u"] | -1;
      wd.r = w["r"] | -1;
    }
    if (old) {
      for (int k = 0; k < old->nw; ++k) {
        const WinData& ow = old->w[k];
        int wi = -1;
        for (int j = 0; j < d.nw; ++j)
          if (!strcmp(d.w[j].l, ow.l)) wi = j;
        if (wi < 0) {
          if (d.nw >= 3) continue;
          wi = d.nw++;
          d.w[wi] = ow;
          // Retained window: age its reset countdown like every other cached
          // field instead of presenting the old value as freshly measured.
          if (d.w[wi].r >= 0) d.w[wi].r = max<int32_t>(0, d.w[wi].r - elapsed);
          continue;
        }
        if (d.w[wi].u < 0) d.w[wi].u = ow.u;  // explicit zero stays zero
        if (d.w[wi].r < 0) d.w[wi].r = ow.r >= 0 ? max<int32_t>(0, ow.r - elapsed) : -1;
      }
    }
    m.acc[m.nacc++] = d;
  }

  // Accounts missing from this payload stay visible as cached, with their
  // age and reset countdown advanced by the elapsed time.
  for (int i = 0; i < out.nacc && m.nacc < 4; ++i) {
    const AccData& oa = out.acc[i];
    bool seen = false;
    for (int j = 0; j < m.nacc; ++j)
      if (!strcmp(oa.p, m.acc[j].p)) seen = true;
    if (seen) continue;
    AccData d = oa;
    if (d.age >= 0) d.age += elapsed;
    for (int k = 0; k < d.nw; ++k)
      if (d.w[k].r >= 0) d.w[k].r = max<int32_t>(0, d.w[k].r - elapsed);
    d.stale = true;
    m.acc[m.nacc++] = d;
  }

  // Peak banner. A fresh `hi` wins; otherwise summarize the retained windows
  // so the line reports the cached worst quota instead of going blank. UI
  // labels this case CACHED, since hasHi stays false.
  JsonObjectConst hi = doc["hi"];
  if (!hi.isNull() && (hi["u"] | -1) >= 0) {
    m.hasHi = true;
    m.hiU = hi["u"] | -1;
    copyStr(m.hiP, sizeof m.hiP, hi["p"]);
    copyStr(m.hiW, sizeof m.hiW, hi["w"]);
  } else {
    int best = -1;
    const AccData* bestA = nullptr;
    const WinData* bestW = nullptr;
    for (int i = 0; i < m.nacc; ++i)
      for (int k = 0; k < m.acc[i].nw; ++k)
        if (m.acc[i].w[k].u >= 0 && m.acc[i].w[k].u > best) {
          best = m.acc[i].w[k].u;
          bestA = &m.acc[i];
          bestW = &m.acc[i].w[k];
        }
    if (bestA) {
      m.hiU = (int16_t)best;
      strlcpy(m.hiP, bestA->p, sizeof m.hiP);
      strlcpy(m.hiW, bestW->l, sizeof m.hiW);
    }
  }

  // Subscription usage. Start from the cached section, then let present
  // fields (including zero) replace it.
  m.c1 = out.c1;
  m.c7 = out.c7;
  m.i1 = out.i1;
  m.cr1 = out.cr1;
  m.o1 = out.o1;
  m.unp = out.unp;
  memcpy(m.h, out.h, sizeof m.h);
  m.hasH = out.hasH;
  m.nbyp = out.nbyp;
  memcpy(m.byp, out.byp, sizeof m.byp);

  JsonObjectConst use = doc["use"];
  if (!use.isNull()) {
    keepNum(use["c1"], m.c1);
    keepNum(use["c7"], m.c7);
    keepU32(use["i1"], m.i1);
    keepU32(use["cr1"], m.cr1);
    keepU32(use["o1"], m.o1);
    keepBool(use["unp"], m.unp);
    JsonArrayConst h = use["h"];
    if (h.size() == 24) {  // all-zero hour is a real reading
      m.hasH = true;
      for (size_t i = 0; i < 24; i++) m.h[i] = h[i] | 0;
    }
  }
  JsonArrayConst byp = doc["byp"];
  if (!byp.isNull()) {  // an empty array is a valid "no usage" reading
    m.nbyp = 0;
    for (JsonObjectConst b : byp) {
      if (m.nbyp >= 4) break;
      auto& e = m.byp[m.nbyp];
      copyStr(e.p, sizeof e.p, b["p"]);
      JsonVariantConst cv = b["c1"];
      if (!cv.isNull()) {
        e.c1 = cv | 0;
      } else {
        e.c1 = 0;
        for (int i = 0; i < out.nbyp; ++i)
          if (!strcmp(out.byp[i].p, e.p)) e.c1 = out.byp[i].c1;
      }
      m.nbyp++;
    }
  }

  // Free provider stats and NIM counts. Zero is valid; -1 means unavailable.
  m.freeN = out.freeN;
  m.freeT = out.freeT;
  strlcpy(m.freeM, out.freeM, sizeof m.freeM);
  JsonObjectConst fr = doc["free"];
  if (!fr.isNull()) {
    keepNum(fr["n"], m.freeN);
    keepU32(fr["t"], m.freeT);
    if (!fr["m"].isNull()) copyStr(m.freeM, sizeof m.freeM, fr["m"]);
    else if (m.freeN == 0) m.freeM[0] = 0;  // no requests: old model no longer applies
  }
  m.nimN = out.nimN;
  JsonObjectConst nim = doc["nim"];
  if (!nim.isNull()) keepNum(nim["n"], m.nimN);

  // OpenRouter. A present section updates status and any reported numbers;
  // an absent section keeps the last status and values, with only its age
  // moving forward.
  m.orOk = out.orOk;
  strlcpy(m.orX, out.orX, sizeof m.orX);
  m.orFu = out.orFu;
  m.orFl = out.orFl;
  m.orD = out.orD;
  m.orB = out.orB;
  m.orAge = out.orAge >= 0 ? out.orAge + elapsed : -1;

  JsonObjectConst o = doc["or"];
  if (!o.isNull()) {
    copyStr(m.orX, sizeof m.orX, o["x"]);
    m.orOk = !m.orX[0];
    keepI16(o["fu"], m.orFu);
    keepI16(o["fl"], m.orFl);
    keepNum(o["d"], m.orD);
    keepNum(o["b"], m.orB);
    JsonVariantConst age = o["age"];
    if (!age.isNull() && (age | -1) >= 0) m.orAge = age | -1;
  }

  // Location-based automatic backlight level (0..255). Missing or invalid
  // keeps the last received level; explicit zero (backlight off) is valid.
  m.bl = out.bl;
  m.hasBl = out.hasBl;
  m.blMs = out.blMs;
  JsonVariantConst blv = doc["bl"];
  if (!blv.isNull() && blv.is<int>() && blv.as<int>() >= 0 && blv.as<int>() <= 255) {
    m.bl = (uint8_t)blv.as<int>();
    m.hasBl = true;
    JsonVariantConst duration = doc["bl_ms"];
    if (duration.is<int>() && duration.as<int>() >= 0 && duration.as<int>() <= 60000)
      m.blMs = (uint32_t)duration.as<int>();
  }

  out = m;
  return true;
}
