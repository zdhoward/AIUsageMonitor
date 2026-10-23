#pragma once
#include <TFT_eSPI.h>
#include <math.h>

// Adapted from tanmaywankar/Grobot_Animations, MIT (see LICENSE.txt).
// Pin: 858d8da648c9e71ff9b9f5e6f558ba85293a70fb
// Keeps MoodData, applySpring and drawEye geometry; removes sprite ownership,
// HUD and implicit clocks. MINT supplies bounded elapsed time and a canvas.
namespace grobot {
struct MoodData { float topH, botH, tilt, pR, radius; };
struct Motion {
  float value, velocity;
  void step(float target, float dt, float stiffness = 180, float damping = 15) {
    // Upstream applySpring: Hooke force with velocity damping.
    velocity += ((target - value) * stiffness - velocity * damping) * dt;
    value += velocity * dt;
  }
};
struct Eye {
  Motion top{0, 0}, bottom{0, 0}, tilt{0, 0}, pupil{30, 0}, radius{45, 0};
  void update(const MoodData& mood, float dt) {
    top.step(mood.topH, dt);
    bottom.step(mood.botH, dt);
    tilt.step(mood.tilt, dt);
    pupil.step(mood.pR, dt, 180, 22);
    radius.step(mood.radius, dt);
  }
  void draw(TFT_eSPI& canvas, int x, int y, float scale, bool left, float blink,
            uint16_t ink, uint16_t bg) const {
    int r = max(1, (int)lroundf(radius.value * scale));
    int p = constrain((int)lroundf(pupil.value * scale), 0, r - 1);
    float lidHeight = top.value + (2 * radius.value + 2 - top.value) * blink;
    int lid = constrain((int)lroundf(lidHeight * scale), 0, 2 * r + 2);
    int bot = constrain((int)lroundf(bottom.value * scale), 0, 2 * r + 2);
    int angle = (int)lroundf(tilt.value * scale);
    canvas.fillCircle(x, y, r, ink);
    canvas.fillCircle(x, y, p, bg);
    canvas.fillRect(x - r, y - r, 2 * r + 1, lid, bg);
    int pointX = ((angle < 0) == left) ? x - r : x + r;
    canvas.fillTriangle(x - r, y - r + lid, x + r, y - r + lid,
                        pointX, y - r + lid + abs(angle), bg);
    canvas.fillRect(x - r - 5, y + r + 5 - bot, 2 * r + 10, bot, bg);
  }
};
}  // namespace grobot
