# MINT face (T-009A)

Companion is a full-canvas face: Grobot eyes, a blending mouth and optional
sweat. Tap still advances through the existing page registry. Companion has
no labels, enclosure or pagination dots. Other pages retain their navigation
and rendering; the existing Screensaver preview still wraps its selected page.
No personality, CPU policy, service protocol or automatic saver behavior is
introduced here.

## Upstream and adaptation

Source: [tanmaywankar/Grobot_Animations](https://github.com/tanmaywankar/Grobot_Animations),
commit **858d8da648c9e71ff9b9f5e6f558ba85293a70fb** (MIT, Tanmay Wankar).
Inspected `src/Grobot_Animations.h`, `src/Grobot_Animations .cpp`, `src/Moods.h`,
`src/Animation_config.h`, both BasicEyes and CustomEyes examples, and LICENSE.
To reproduce the source, clone the repository and `git checkout` that full SHA.
The upstream C++ filename contains a space before `.cpp`.

`firmware/AIUsageMonitor/grobot/GrobotEyes.h` is the small vendored adaptation;
the adjacent `LICENSE.txt` retains upstream's MIT notice. It retains Grobot's
MoodData fields, circular eye/pupil rendering, rectangular and triangular lid
masks, mirrored tilt and Hooke spring integration. There is no GPL code.

Adapter changes: explicit caller-owned canvas and dimensions, no sprite
allocation/push or HUD, no implicit micros/millis clocks, clamped geometry,
and at most five 10ms spring steps per update. A timed blink overlays the
animated lid geometry so it fully closes without spring lag; expression
springs continue underneath. The mouth and emotion table are
MINT additions. Grobot gaze motion moves feature coordinates instead of
moving/pushing a separate sprite. Expression selection changes targets and
retains current values and velocities, including during a blink.

## Integration API

Include `face.h`; use these functions from the firmware loop thread:

- `faceSelectExpression(name)` selects one of `content`, `happy`, `curious`,
  `bored`, `sleepy`, `surprised`, `stressed`. Names are case sensitive.
  Unknown names or null select content and return false.
- `faceNeutral()` selects content, without snapping the current pose.
- `faceUpdate(nowMs, visible)` advances independent blink, gaze, mouth and
  effect channels. Call it even when hidden. `uiRender` already does this.
- `faceDraw(canvas, width, height, ink, background)` draws features only;
  the caller clears and presents the frame. `uiRender` already handles that.

The later PC integration only needs to validate/map its expression name and
call `faceSelectExpression`; quota/activity data does not currently pick moods.
There is no automatic emotion cycling or service policy in the firmware.

Developer serial commands at 115200 baud, newline terminated:

```text
!NEXT
!NEXT
!FACE happy
!FACE stressed
!FACE content
!SHOT
```

From the default Console, two NEXTs select Companion when the default optional
pages are enabled. `!FACE` accepts a fixed name of at most nine characters and
replies `@FACE ok`, or `@ERR face; using content`. It uses the existing 4096-byte
bounded line receiver; oversized lines are discarded until the next newline.
It does not change the selected page. Ordinary touch remains navigation.

To add an emotion, append one row in `face.cpp`'s `emotions`: name, left and
right Grobot `{topH, botH, tilt, pR, radius}`, mouth half-width, signed smile
depth, opening, sweat amount (0..1). Stay near the existing 45px radius design
and use names of at most nine characters for the developer command. No switch
statement or renderer changes are needed. Update the documented name list.

## Resources and timing limits

Uses the existing RGB332 framebuffer (76,800 bytes on this panel), with no
additional frame buffer, per-frame allocation, String construction or dynamic
containers. Face state is fixed-size scalars and a static seven-row table.
The existing screenshot byte format and runtime rotation are unchanged.
Coordinates scale to the current width/height in both orientations. The same
primitives draw directly to the panel when framebuffer allocation fails;
that fallback can visibly flicker because clearing/presentation is unbuffered.

Companion requests frames every 33ms; other pages keep REDRAW_MS. Actual FPS
depends on SPI transfer, serial traffic and loop work; this is a cadence target,
not measured hardware performance. Unsigned elapsed subtraction handles millis
wrap. Hidden time pauses all channels; the first visible update has zero delta.
Stalls consume at most 50ms of animation time without catch-up loops. This
deliberately slows animation during sustained overload. Blink and gaze clocks
are independent, mouth uses elapsed exponential blending, sweat uses a bounded
1400ms phase. Screenshot commands may block serial while emitting frame bytes.

## Verification and hardware follow-up

Production acceptance: `powershell -NoProfile -File scripts/build.ps1` and
`git diff --check`. Results and routing evidence are in `.tickets/T-009A.md`.
Tests remain deferred until the owner declares sprint end. No hardware was
flashed for this ticket; smoothness, touch behavior, visible rotation and
fallback flicker require device review and are not claimed as verified.

After owner authorization to flash, with the ESP32-2432S024C connected via USB,
Arduino ESP32 toolchain installed and a successful build in `build/`:

```powershell
powershell -NoProfile -File scripts/flash.ps1 -Port COM6
```

Replace COM6 with the actual CH340 port. The flash script pauses/resumes the
local service to release serial. For manual serial commands, also stop/pause
the service and use a 115200-baud terminal with newline endings. Review all
seven emotions, interrupted transitions, blink/gaze overlap, both rotations,
hide/return, and `!SHOT` before accepting the visual result.
