# Settings review (2026-10-25)

This review covers the settings of every library scene and of the app, so that new users get the controls they need without clutter.

## How it was made

1. **Ground truth first:** `python scripts/settings_audit.py --json facts.json` reads `scene.cpp`, `scenes.py` and every `entry.json`. It lists which visible controls the engine actually uses.
2. **Per-scene review:** `python scripts/settings_review.py facts.json out/` asked a local Ollama model (`gemma4:e4b`, about 45 s per scene, no paid model) for recommendations on each of the 15 scenes. The input was those facts.
3. **Coordinator check:** each suggestion below was checked against the code. **Verdict**: ✅ do it, 💡 worth considering, ❌ reject (with the reason).

## Findings from the engine (facts, not opinions)

- **Dead control:** the **sky top/bottom colours** show on every scene but do nothing on the 12 generator scenes (aurora, campfire, digital-rain, fireworks, game-of-life, lava-lamp, pixel-patterns, plasma, ripples, spectre-patch, video-equations, warp-speed). In `sceneDraw`, the sky is only drawn when there is no generator. *These are the colour pickers that "change nothing".*
- **No other dead controls.** Every generator field the Studio shows is read by that generator, and so is its colour list. Effects and themes work on every scene.

## Recurring recommendations (all scenes)

| # | Recommendation (how many scenes) | Verdict | Notes |
|---|---|---|---|
| 1 | Hide sky colours on generator scenes (12/12) | ✅ | Matches the facts. Show the sky section only when there is no generator. |
| 2 | Move "Layers" to advanced on generator scenes (11) | ❌ | Already hidden when a scene has no layers. The model misread the panel description. |
| 3 | Global **speed multiplier** for the whole scene (6) | 💡 medium | One "Speed ×" slider scaling every layer, effect and generator speed. A strong creative knob; needs a field in the scene/tune format and firmware. |
| 4 | Palette / colour-stop **preview** (6) | 💡 small | Themes already show swatches. What is missing is a gradient bar for a generator's colour stops (the Studio draws a ramp). |
| 5 | Per-type section titles, e.g. "Plasma settings", and "Effects" → "Weather & sky effects" (13) | ✅ small | Clearer labels, no behaviour change. |
| 6 | Random **seed** (5) | ❌ | Generators are time-driven and endless on the display, so reproducibility gives a hobbyist little. Adds clutter. |
| 7 | Brightness/contrast per scene (4) | 💡 medium | Could be a LUT adjustment like themes. Overlaps with themes and backlight. Low priority. |
| 8 | Output resolution, fps, loop count, interpolation mode | ❌ | Fixed 320×240 hardware and fixed frame pacing; scenes loop forever and playlists already set the duration. Not supported and not useful. |

## Scene-specific notes

| Scene | Suggestion | Verdict |
|---|---|---|
| fireworks | Gravity control | ❌ exists ("Gravity" field) |
| fireworks | Particle size/spread | 💡 small, if the generator gains a size parameter |
| ripples | Ripple strength/amplitude | 💡 small: ripple only has cell size and drops/min today |
| warp-speed | Background colour picker | ❌ the first colour stop already is the background |
| pixel-patterns | "Interaction mode", speed curve | ❌ unclear value |
| image scenes (miami, neon, rainy) | Keep sky colours, layers prominent | ✅ already so |

## App-level (Studio and setup) — coordinator review

| # | Gap | Verdict |
|---|---|---|
| A | Service settings (serial port, brightness location and timezone, day/night levels, stale threshold) live only in `service/aimon.config.json`, with no UI. A new user must edit JSON to make automatic brightness right for their city. | ✅ add a small **Settings** tab (location, timezone, brightness levels, serial port) that writes the ignored config |
| B | First run with no art: the Images and City pages show hints, but the Studio Library is nearly empty | 💡 a short "Add your own art" card in the Library linking to the import flow |
| C | Advanced generator numbers have no units or ranges shown | 💡 add min/max and a one-line hint per field |
| D | Everything else (profiles, playlists, screensaver, display) | ✅ already covered by the v1.10.0 UX pass |

## Suggested action list

1. ✅ Hide sky colours for generator scenes (#1).
2. ✅ Per-type titles and clearer labels (#5).
3. ✅ Studio Settings tab for the service config (A).
4. 💡 Then decide: speed multiplier (#3), colour-stop gradient bar (#4), field ranges and hints (C), "add your art" card (B).
