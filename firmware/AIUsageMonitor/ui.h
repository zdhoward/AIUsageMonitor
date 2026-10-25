#pragma once
#include <TFT_eSPI.h>
#include "model.h"

// Initialises the panel at the configured rotation and allocates the frame buffer.
void uiBegin(TFT_eSPI& tft, uint8_t rotation);

// Re-applies a rotation at runtime (test command; the persistent setting is
// DISPLAY_ROTATION in config.h).
void uiSetRotation(uint8_t rotation);

bool uiHasFramebuffer();
uint32_t uiFrameIntervalMs();
void uiNextView(const Model& m);

// Shows a page (console, details, companion, image, city, scenes) or a scene id
// until the next tap, even when it is not in the tap rotation.
bool uiShow(const char* name);

// Duration of the last uiRender, including the panel transfer.
uint32_t uiLastRenderUs();

// Dumps the current frame (RGB332) to `out` for host-side screenshots.
bool uiScreenshot(Stream& out);

// Draws the full dashboard. `nowMs` drives countdowns and staleness.
void uiRender(const Model& m, uint32_t nowMs, const char* linkInfo);
