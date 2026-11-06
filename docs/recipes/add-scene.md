# Add a screensaver scene

Scenes are art compiled into the firmware. Raw art is personal and git-ignored, so adding a scene never touches tracked files except your own profile. Background: [ASSETS.md](../ASSETS.md) and [STUDIO.md](../STUDIO.md).

Do not use art you are not allowed to use. Having a download is not permission to redistribute; keep art local.

## Easiest path: Scene Studio

1. Double-click `Scene Studio.cmd`.
2. **Import art**: drop one image for a still scene, or several files ordered back to front for a parallax scene. Procedural scenes (plasma, fire, aurora and others) need no art.
3. Open the new card, adjust speeds and sky, **Save scene**.
4. Add the scene to a playlist in your profile (Studio's profile editor, or edit `profiles/my.json` under `playlists[].scenes`).
5. **Send to display**, or build and flash. Check: the scene plays in Studio's preview.

## By hand

1. Put the art under `assets/` and describe it in `assets/manifest.json` (copy `assets/manifest.example.json` to start).
2. Run `python scripts\asset_convert.py`. Check: it prints a size for each asset and no error.
3. Add the scene id to `playlists[].scenes` in `profiles/my.json`. Check: `python scripts\profile_gen.py my` passes.
4. `.\scripts\build.ps1 -Profile my`, then `.\scripts\flash.ps1`.
5. Capture with `python scripts\screenshot.py --feed --next N --out build\scene.png` (raise `N` until the scene page appears) and look at it.

## Limits to know

- Scene art is authored at 320x240. On other sizes, see [resize](resize-display.md).
- Flash is limited. `asset_convert.py` reports encoded sizes; if the build fails to fit, use fewer or smaller layers.
- Colours are snapped to 8-bit RGB332, so gradients band. Use flat pixel art or accept the banding.
