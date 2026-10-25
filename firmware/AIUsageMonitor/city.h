#pragma once
#include "anim.h"
#include "assets_gen.h"

// The art is personal and git-ignored; without it the City page shows a hint.
#if defined(ASSET_HAS_city_far) && defined(ASSET_HAS_city_near) && defined(ASSET_HAS_city_windows) && \
    defined(ASSET_HAS_city_sign) && defined(ASSET_HAS_city_car)
#define CITY_ART 1
#else
#define CITY_ART 0
#endif

// Synthwave city: Aseprite art layers (assets/scenes/city) plus code-driven
// life — sky, sun, neon road, rain, window blinks, traffic and lightning.
void cityDraw(const Canvas8& c, uint32_t nowMs);
