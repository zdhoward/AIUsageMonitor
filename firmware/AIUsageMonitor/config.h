#pragma once
// ============================================================================
// AI Usage Monitor: firmware settings
// Board: ESP32-2432S024C (ESP32-D0WD-V3, ILI9341 240x320 SPI, CH340 USB-serial)
// ============================================================================

#define FW_VERSION "1.3.1"

// ---------------------------------------------------------------------------
// DISPLAY_ROTATION: the one setting to change when you remount the screen.
// Values are TFT_eSPI rotations for the ILI9341 on this board. "Traditional"
// means landscape rotation 1, the orientation all your earlier sketches used.
//
//   2 = Portrait, traditional RIGHT edge facing UP
//   0 = Portrait, traditional LEFT edge facing up
//   1 = Landscape, traditional orientation             (default)
//   3 = Landscape, upside down
//
// Rotations 1/3 make the screen 320x240 (two-column layout); 0/2 make it
// 240x320 (single column). The layout is computed from tft.width()/height()
// at runtime, so changing this value and reflashing is all that's needed.
// ---------------------------------------------------------------------------
#ifndef DISPLAY_ROTATION
#define DISPLAY_ROTATION 1
#endif

// SHOW_REMAINING: 1 = bars and percentages show quota LEFT (default),
//                 0 = show quota USED. The top banner follows the same mode
//                 ("LOWEST 7% left" vs "PEAK 93% used"). Colours always mean the
//                 same thing: red = nearly exhausted.
#ifndef SHOW_REMAINING
#define SHOW_REMAINING 1
#endif

// Backlight pin (active high) on this board. TFT pins are passed as build
// flags by scripts/build.ps1 (identical to your TFT_eSPI User_Setup.h).
#define PIN_BACKLIGHT 27

// ---------------------------------------------------------------------------
// Transport. USB serial is the default: the service on the PC pushes one JSON
// line every few seconds over the CH340 bridge (COM port), so no Wi-Fi
// credentials or LAN exposure are needed.
//
// Optional Wi-Fi polling: set AIMON_USE_WIFI to 1 and create secrets.h (see
// secrets.example.h). The service must then bind to the LAN (see README).
// ---------------------------------------------------------------------------
#define SERIAL_BAUD 115200
#ifndef AIMON_USE_WIFI
#define AIMON_USE_WIFI 0
#endif
#define WIFI_POLL_MS 5000

// Backlight PWM level, 0..255 (ESP32 LEDC on PIN_BACKLIGHT).
#ifndef BACKLIGHT_LEVEL
#define BACKLIGHT_LEVEL 255
#endif

// Show "NO DATA" in the header; cached readings keep their normal brightness.
#define DATA_TIMEOUT_MS 30000UL

// Console thresholds, in percent quota REMAINING. <= critical is red,
// <= warning is amber, everything else healthy green.
#ifndef UI_CRITICAL_LEFT
#define UI_CRITICAL_LEFT 20
#endif
#ifndef UI_WARNING_LEFT
#define UI_WARNING_LEFT 50
#endif

// A console client is marked STALE when its provider source is older than
// this many seconds (or the link timed out, or the service flagged it).
#ifndef CLIENT_STALE_S
#define CLIENT_STALE_S 1200
#endif

// Screen refresh period (countdowns and the activity pulse).
#define REDRAW_MS 50UL

// Set to 0 for immediate value changes and a slower, static display.
#define UI_ANIMATION 1
