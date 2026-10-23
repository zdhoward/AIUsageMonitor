#pragma once
#include <TFT_eSPI.h>

// Single loop-owned face. Unknown names select neutral content and return false.
bool faceSelectExpression(const char* name);
void faceNeutral();
// Call even while hidden; hidden time pauses animation, with no catch-up burst.
void faceUpdate(uint32_t nowMs, bool visible);
// Caller clears/presents its existing canvas; no allocation or panel push here.
void faceDraw(TFT_eSPI& canvas, int width, int height, uint16_t ink, uint16_t background);
