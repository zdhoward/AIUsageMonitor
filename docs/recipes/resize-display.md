# Fit a different screen size or aspect ratio

Status: the shipped layout is verified only on the 320x240 ESP32-2432S024C. Other sizes are **untested**. Say so to the user and show them captures.

## The approach

Stretch the containers, not the content. The header, footer and cards take their size from the screen, and each card lays its own content out inside whatever rectangle it is given. Slightly stretched proportions on near-standard boards are acceptable.

Most of the UI already works this way. `drawProxy` computes the grid from `W` and `H`, and each card receives `(x, y, w, h)`. What does not scale automatically is listed below.

## Steps

1. **Set the driver.** The display driver, resolution and pins are the `$tft` flags in `scripts/build.ps1` (for example `-DILI9341_DRIVER=1`, the SPI pins, backlight pin). A different controller needs the matching TFT_eSPI driver define and pins from the board's documentation. Do not guess pins; if you cannot find them, stop and ask the user.
2. **Build and look first.** Build, flash and capture (`python scripts\screenshot.py --feed --out build\size.png`). The framebuffer capture records the real width and height. Check what already fits before changing anything.
3. **Fix the header and footer.** In `ui.cpp`, `drawProxy` uses fixed offsets: header rule at y=20, footer at `H - 18`, and a status dot at `W - pad - 4`. These follow `W` and `H`, so they usually need no change. Raise them only if the text looks cramped on a taller screen.
4. **Fix the grid.** In `drawProxy`, `cols` and `rows` are 3x2 (landscape) and 2x3 (portrait). On a larger screen you may raise them, which also adds cell slots. Each card's size then comes from `cw`/`ch` automatically.
5. **Fix card content.** For each `drawProxy*` function that overflows or leaves large gaps, change only its internal layout: positions from `w` and `h`, and fonts (font 1 small, 2 medium). Keep fixed offsets for padding only. Check each card in a capture.
6. **Fix other pages.** Console grid, Details, Companion and Images use the same `W`/`H`. Capture each page (`--next N`) and fix overflow the same way.
7. **Scenes and city art.** These are authored at 320x240: `firmware/AIUsageMonitor/city.cpp` (`ART_W`, `ART_H`), `firmware/AIUsageMonitor/scene.cpp` (`SCENE_H`), and `studio/web/scene.js`, `scripts/scenes.py` and `scripts/render_scene_demo.py` (preview and conversion). On a different size, scenes render at their native size, leaving borders or cropping. Prefer re-exporting art at the new size, or accept the border. Do not change these constants unless you also regenerate the art.
8. **Check portrait and landscape.** Build with `-Rotation 0`, `1`, `2` and `3` as needed and capture each. Rebuild with your normal rotation at the end.
9. **Record it.** Log every tracked file you changed in `docs/MY_CHANGES.md`, and tell the user which pages you verified.

## Common mistakes

- Changing resolution constants without regenerating art.
- Hard-coding the new size inside a card instead of using `w` and `h`.
- Trusting a build that compiles: always look at the capture.
