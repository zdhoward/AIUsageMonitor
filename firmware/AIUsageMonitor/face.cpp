#include "face.h"
#include "grobot/GrobotEyes.h"
#include <string.h>

namespace {
using grobot::MoodData;
struct Emotion {
  const char* name;
  MoodData left, right;
  float mouthWidth, smile, opening, sweat;
};
// Grobot's 45px eye / 30px pupil design units, with asymmetric custom moods.
const Emotion emotions[] = {
  {"content",   {0,0,0,30,45}, {0,0,0,30,45}, 26, 5, 0, 0},
  {"happy",     {0,50,0,30,45}, {0,50,0,30,45}, 35, 15, 4, 0},
  {"curious",   {5,0,-12,27,45}, {20,0,8,30,45}, 20, 2, 3, 0},
  {"bored",     {40,0,0,30,45}, {40,0,0,30,45}, 25, -2, 0, 0},
  {"sleepy",    {65,0,0,30,45}, {65,0,0,30,45}, 18, 0, 4, 0},
  {"surprised", {0,0,0,23,48}, {0,0,0,23,48}, 16, 0, 17, 0},
  {"stressed",  {10,0,-25,27,45}, {10,0,-25,27,45}, 29, -9, 2, 1},
};
const Emotion* target = &emotions[0];
grobot::Eye left, right;
grobot::Motion gazeX{0,0}, gazeY{0,0};
float gazeTargetX = 0, gazeTargetY = 0;
float mouthWidth = 26, smile = 5, opening = 0, sweat = 0;
float blinkAmount = 0;
uint32_t previous = 0, blinkClock = 0, gazeClock = 0, effectClock = 0;
uint32_t blinkWait = 3200, gazeWait = 1900;
bool wasVisible = false, clockReady = false;
void blend(float& value, float end, float alpha) { value += (end - value) * alpha; }
}

bool faceSelectExpression(const char* name) {
  if (name) for (const auto& emotion : emotions) {
    if (!strcmp(name, emotion.name)) { target = &emotion; return true; }
  }
  faceNeutral();
  return false;
}

void faceNeutral() { target = &emotions[0]; }

void faceUpdate(uint32_t now, bool visible) {
  uint32_t elapsed = now - previous;  // unsigned subtraction survives millis wrap
  previous = now;
  if (!clockReady || !visible || !wasVisible) elapsed = 0;
  clockReady = true;
  wasVisible = visible;
  // Drop excess wall time after a stall: no unbounded integration/catch-up.
  uint32_t dtMs = min(elapsed, (uint32_t)50);
  blinkClock += dtMs;
  gazeClock += dtMs;
  effectClock = (effectClock + dtMs) % 1400;
  float blink = 0;
  if (blinkClock >= blinkWait) {
    uint32_t phase = blinkClock - blinkWait;
    if (phase < 90) blink = phase / 90.0f;
    else if (phase < 140) blink = 1;
    else if (phase < 290) blink = 1 - (phase - 140) / 150.0f;
    else { blinkClock = 0; blinkWait = random(2800, 6500); }
  }
  blinkAmount = blink;
  if (gazeClock >= gazeWait) {
    gazeClock = 0;
    gazeWait = random(1700, 4200);
    gazeTargetX = random(-9, 10);
    gazeTargetY = random(-5, 6);
  }
  // Grobot's springs use small bounded steps for stability at low frame rates.
  for (uint32_t remaining = dtMs; remaining; ) {
    uint32_t step = min(remaining, (uint32_t)10);
    float dt = step / 1000.0f;
    left.update(target->left, dt);
    right.update(target->right, dt);
    gazeX.step(gazeTargetX, dt, 140, 18);
    gazeY.step(gazeTargetY, dt, 140, 18);
    remaining -= step;
  }
  float alpha = 1 - expf(-dtMs / 150.0f);
  blend(mouthWidth, target->mouthWidth, alpha);
  blend(smile, target->smile, alpha);
  blend(opening, target->opening, alpha);
  blend(sweat, target->sweat, alpha);
}

void faceDraw(TFT_eSPI& g, int width, int height, uint16_t ink, uint16_t bg) {
  float scale = min(width / 300.0f, height / 220.0f);
  int cx = width / 2 + lroundf(gazeX.value * scale);
  int cy = height / 2 - lroundf(24 * scale) + lroundf(gazeY.value * scale);
  left.draw(g, cx - lroundf(65 * scale), cy, scale, true, blinkAmount, ink, bg);
  right.draw(g, cx + lroundf(65 * scale), cy, scale, false, blinkAmount, ink, bg);
  // A sampled parabola blends continuously between smile, frown and open oval.
  int my = height / 2 + lroundf(57 * scale);
  int half = max(2, (int)lroundf(mouthWidth * scale));
  for (int x = -half; x <= half; ++x) {
    float u = (float)x / half;
    float curve = 1 - u * u;
    int y = my + lroundf(smile * scale * curve);
    int gap = lroundf(opening * scale * sqrtf(max(0.0f, curve)));
    g.drawFastVLine(cx + x, y - gap / 2, max(2, gap + 2), ink);
  }
  if (sweat > 0.02f) {
    float fall = effectClock / 1400.0f;
    int r = max(1, (int)lroundf(5 * scale * sweat));
    int x = width / 2 + lroundf(124 * scale);
    int y = cy - lroundf(28 * scale) + lroundf(fall * 35 * scale);
    g.fillCircle(x, y, r, ink);
    g.fillTriangle(x-r, y, x+r, y, x, y-2*r, ink);
  }
}
