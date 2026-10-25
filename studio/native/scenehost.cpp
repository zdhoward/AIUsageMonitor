// Scene Studio's native preview: the firmware scene engine (scene.cpp,
// anim.cpp, tune.cpp and the generated scenes_gen.cpp) built for Windows, so
// previews are the device's own pixels. Built by studio/native/build.ps1.
#include "scenes_gen.h"
#include "tune.h"

#define API extern "C" __declspec(dllexport)

API int sh_count() { return SCENE_COUNT; }

API const char* sh_id(int i) { return i >= 0 && i < SCENE_COUNT ? SCENES[i].id : ""; }

// Renders scene `i` at `ms` into `out` (w*h RGB332). A non-empty tune blob
// applies live edits first (same decoder as the device's !TUNE). Returns 0 on
// a bad index, -1 when the tune blob was rejected (the scene renders untuned).
API int sh_render(int i, unsigned ms, const unsigned char* tune, int tuneLen, unsigned char* out, int w, int h) {
  if (i < 0 || i >= SCENE_COUNT || w <= 0 || h <= 0) return 0;
  int rc = 1;
  if (tuneLen > 0) {
    if (!sceneTune(tune, tuneLen)) {
      sceneUntune();
      rc = -1;
    }
  } else {
    sceneUntune();
  }
  Canvas8 c{out, w, h};
  sceneDraw(c, sceneResolve((uint8_t)i), ms);
  return rc;
}
