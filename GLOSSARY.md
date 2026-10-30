# AI Usage Monitor

The display combines usage information and optional ambient scenes for a configured place.

## Language

**Local weather**:
The latest provider-reported conditions for the configured location, with a measurement/valid time and freshness state. It is distinct from a scene's decorative effects or an on-site sensor reading.
_Avoid_: Live sensor weather

**Scene weather**:
The rain, snow, storm, cloud or clear-sky appearance selected for an ambient scene. Its source can be authored settings, random choice, manual selection or local weather.

**Daylight phase**:
The local dawn, day, dusk or night state associated with the configured place and date. It describes scene lighting rather than the display's backlight brightness.

**Ambient synchronization**:
Optional coordination of scene weather and daylight phase with the configured place. Weather and daylight can be enabled independently.

**Proxy group**:
All active CPAMC accounts of one provider (e.g. claude, codex). The Proxy view shows one tile per group, with quota pooled across its accounts.

**Provider profile**:
The once-per-provider mapping from its usage source to display windows: request, field paths, window labels, pools and tile layout. New providers are added as profiles, not code.
_Avoid_: Adapter, template

**Usage window**:
One limit with its own length and reset (5h, 7d, 30d). It is labelled from its actual length, never assumed.
