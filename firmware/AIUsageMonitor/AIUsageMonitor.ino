// AI Usage Monitor: ESP32-2432S024C dashboard
//
// Receives a compact JSON payload from the aimon service on the PC (USB serial
// by default, optional Wi-Fi polling) and renders quota, activity and usage.
// Holds no credentials and makes no requests to AI providers.
//
// Protocol (USB serial, 115200 8N1): the PC sends one JSON object per line.
// The device replies "@HELLO ..." at boot and "@ACK <seq>" per accepted line.

#include <TFT_eSPI.h>
#include "config.h"
#include "model.h"
#include "ui.h"
#include "scenes_gen.h"
#include "tune.h"
#include "face.h"
#include <Wire.h>

#if AIMON_USE_WIFI
#include <WiFi.h>
#include <HTTPClient.h>
#include "secrets.h"
#endif

static TFT_eSPI tft;
static Model model;
static char lineBuf[4096];
static size_t lineLen = 0;
static bool overflow = false;
static uint32_t lastDraw = 0;
static uint32_t badLines = 0;
static bool touchReady = false;
static char selectedFace[10] = "content";

// CST820: a whole-screen button needs no coordinate calibration/rotation.
static void pollTouch() {
  static uint32_t lastPoll = 0, pressedAt = 0;
  static bool pressed = false;
  uint32_t now = millis();
  if (!touchReady || now - lastPoll < 25) return;
  lastPoll = now;
  Wire.beginTransmission(0x15);
  Wire.write(0x02);
  if (Wire.endTransmission(false) != 0) return;
  if (Wire.requestFrom(0x15, 1) != 1) return;
  bool down = (Wire.read() & 0x0f) != 0;
  static bool held = false;
  if (down && !pressed) { pressed = true; held = false; pressedAt = now; }
  // A hold jumps home as soon as it qualifies, so the finger can lift on the
  // home page; the release that follows is then not a tap.
  if (down && pressed && !held && now - pressedAt >= UI_HOLD_MS) {
    held = true;
    uiGoHome();
    lastDraw = 0;
  }
  if (!down && pressed) {
    pressed = false;
    if (!held && now - pressedAt >= 25) {
      uiNextView(model);
      lastDraw = 0;
    }
  }
}

static const char* linkInfo();

// Nonblocking linear interpolation, independent of page/activity state.
static uint8_t blCurrent = BACKLIGHT_LEVEL;

static void applyBacklight() {
  if (!model.hasBl) return;
  static uint8_t target = BACKLIGHT_LEVEL, from = BACKLIGHT_LEVEL;
  static uint32_t started = 0, duration = BACKLIGHT_SMOOTHING_MS;
  static bool active = false;
  uint32_t now = millis();
  // First advance the old ramp, so a retarget starts at the current level.
  uint32_t elapsed = now - started;
  uint8_t value = target;
  if (active) {
    if (!duration || elapsed >= duration) active = false;
    else value = (uint8_t)((int32_t)from + ((int32_t)target - from) * (int32_t)elapsed / (int32_t)duration);
  }
  if (target != model.bl || duration != model.blMs) {
    from = value;
    target = model.bl;
    duration = model.blMs;
    started = now;
    active = duration != 0 && from != target;
    if (!duration) value = target;
  }
  if (value != blCurrent) {
    blCurrent = value;
    ledcWrite(PIN_BACKLIGHT, blCurrent);
  }
}

static void acceptPayload(const char* json, size_t len) {
  if (parsePayload(json, len, model)) {
    selectedFace[0] = 0;  // payload authority also replaces a diagnostic !FACE
    Serial.printf("@ACK %lu\n", (unsigned long)model.seq);
    lastDraw = 0;  // redraw immediately
  } else {
    badLines++;
    Serial.printf("@ERR parse failed (%lu bad lines)\n", (unsigned long)badLines);
  }
}

static void printHello() {
  Serial.printf("@HELLO aimon-fw %s rot=%d w=%d h=%d fb=%d heap=%lu\n", FW_VERSION, tft.getRotation(), tft.width(),
                tft.height(), uiHasFramebuffer(), (unsigned long)ESP.getFreeHeap());
  setup_t s;
  tft.getSetup(s);  // proves which pin map was compiled in
  Serial.printf("@SETUP drv=%x mosi=%d miso=%d sclk=%d cs=%d dc=%d rst=%d bl=%d spi=%ld\n", s.tft_driver,
                s.pin_tft_mosi, s.pin_tft_miso, s.pin_tft_clk, s.pin_tft_cs, s.pin_tft_dc, s.pin_tft_rst,
                PIN_BACKLIGHT, (long)s.tft_spi_freq);
}

// Commands: "!HELLO" repeats the boot info, "!SHOT" dumps the frame buffer,
// "!ROT n" applies rotation n until reboot (test only), "!PERF" reports the
// last render time and free heap, "!SHOW name" shows a page or scene until
// the next tap, "!SCENES" lists compiled scene ids, "!TUNE <hex>|off" applies
// or clears a live scene edit from Scene Studio (see tune.h).
static void handleCommand(const char* cmd) {
  if (!strcmp(cmd, "!HELLO")) {
    printHello();
  } else if (!strcmp(cmd, "!SHOT")) {
    uiRender(model, millis(), linkInfo());
    if (!uiScreenshot(Serial)) Serial.print("@ERR no framebuffer\n");
  } else if (!strncmp(cmd, "!SHOW ", 6)) {
    const bool ok = uiShow(cmd + 6);
    Serial.print(ok ? "@SHOW ok\n" : "@ERR unknown page or scene\n");
    lastDraw = 0;
  } else if (!strcmp(cmd, "!TUNE off")) {
    sceneUntune();
    Serial.print("@TUNE off\n");
    lastDraw = 0;
  } else if (!strncmp(cmd, "!TUNE ", 6)) {
    // Live edit from Scene Studio: hex-encoded override, shown immediately.
    static uint8_t blob[2040];
    const char* h = cmd + 6;
    int n = 0;
    auto nib = [](char c) { return c <= '9' ? c - '0' : (c | 32) - 'a' + 10; };
    while (h[0] && h[1] && n < (int)sizeof(blob)) blob[n++] = (uint8_t)(nib(h[0]) << 4 | nib(h[1])), h += 2;
    if (sceneTune(blob, n)) {
      char name[40];
      strlcpy(name, SCENES[sceneTunedIndex()].id, sizeof name);
      uiShow(name);
      Serial.printf("@TUNE ok %s\n", name);
    } else {
      Serial.print("@ERR tune rejected (rebuild needed?)\n");
    }
    lastDraw = 0;
  } else if (!strcmp(cmd, "!SCENES")) {
    Serial.print("@SCENES");
    for (uint8_t i = 0; i < SCENE_COUNT; ++i) Serial.printf(" %s", SCENES[i].id);
    Serial.print("\n");
  } else if (!strcmp(cmd, "!PERF")) {
    Serial.printf("@PERF render_us=%lu heap=%lu\n", (unsigned long)uiLastRenderUs(), (unsigned long)ESP.getFreeHeap());
  } else if (!strcmp(cmd, "!NEXT")) {
    uiNextView(model);
    lastDraw = 0;
    Serial.print("@VIEW next\n");
  } else if (!strncmp(cmd, "!FACE ", 6)) {
    // Seven fixed names, no allocation. Oversized/unknown names select content.
    bool known = strlen(cmd + 6) <= 9 && faceSelectExpression(cmd + 6);
    if (!known) faceNeutral();
    Serial.print(known ? "@FACE ok\n" : "@ERR face; using content\n");
    lastDraw = 0;
  } else if (!strncmp(cmd, "!ROT ", 5)) {
    uiSetRotation((uint8_t)atoi(cmd + 5));
    Serial.printf("@ROT %d w=%d h=%d\n", atoi(cmd + 5) & 3, tft.width(), tft.height());
    lastDraw = 0;
  }
}

static void pollSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      lineBuf[lineLen] = 0;
      if (!overflow && lineLen > 0 && lineBuf[0] == '!') handleCommand(lineBuf);
      if (!overflow && lineLen > 0 && lineBuf[0] == '{') {
        if (!strncmp(lineBuf, "{\"t\":\"sys\"", 10)) parseSys(lineBuf, lineLen, gSys);  // no ACK
        else if (!strncmp(lineBuf, "{\"t\":\"proxy\"", 12)) parseProxy(lineBuf, lineLen, gProxy);  // no ACK
        else acceptPayload(lineBuf, lineLen);
      }
      lineLen = 0;
      overflow = false;
    } else if (c != '\r') {
      if (lineLen < sizeof(lineBuf) - 1) lineBuf[lineLen++] = c;
      else overflow = true;  // drop the oversized line, resync at next newline
    }
  }
}

#if AIMON_USE_WIFI
static uint32_t lastPoll = 0;
static void pollWifi() {
  if (WiFi.status() != WL_CONNECTED || millis() - lastPoll < WIFI_POLL_MS) return;
  lastPoll = millis();
  HTTPClient http;
  http.setTimeout(3000);
  if (http.begin(AIMON_URL)) {
    int code = http.GET();
    if (code == 200) {
      String body = http.getString();
      acceptPayload(body.c_str(), body.length());
    }
    http.end();
  }
}
#endif

static const char* linkInfo() {
#if AIMON_USE_WIFI
  static char b[48];
  if (WiFi.status() == WL_CONNECTED) snprintf(b, sizeof b, "Wi-Fi %s", WiFi.localIP().toString().c_str());
  else snprintf(b, sizeof b, "Wi-Fi connecting...");
  return b;
#else
  return "Link: USB serial";
#endif
}

void setup() {
  Serial.setRxBufferSize(4096);
  Serial.begin(SERIAL_BAUD);
  uiBegin(tft, DISPLAY_ROTATION);
  ledcAttach(PIN_BACKLIGHT, 5000, 8);  // ESP32 core 3.x: pin, Hz, bits
  ledcWrite(PIN_BACKLIGHT, BACKLIGHT_LEVEL);
  pinMode(25, OUTPUT);
  digitalWrite(25, LOW);
  delay(5);
  digitalWrite(25, HIGH);
  delay(50);
  Wire.begin(33, 32);
  Wire.setTimeOut(20);
  Wire.beginTransmission(0x15);
  touchReady = Wire.endTransmission() == 0;
  Serial.printf("@TOUCH ready=%d\n", touchReady);
  printHello();
#if AIMON_USE_WIFI
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
#endif
}

void loop() {
  pollSerial();
  pollTouch();
#if AIMON_USE_WIFI
  pollWifi();
#endif
  applyBacklight();
  uint32_t now = millis();
  // Retire an observed expiry permanently, including across a full millis cycle.
  // Keep the session/revision high-water so expired frames cannot replay.
  if (model.mintTtl && now - model.mintAt >= model.mintTtl) model.mintTtl = 0;
  const char* expression = model.mintTtl ? model.mintExpression : "content";
  if (strcmp(selectedFace, expression)) {
    faceSelectExpression(expression);
    strlcpy(selectedFace, expression, sizeof selectedFace);
  }
  if (lastDraw == 0 || now - lastDraw >= uiFrameIntervalMs()) {
    lastDraw = now ? now : 1;
    uiRender(model, now, linkInfo());
  }
  delay(5);
}
