#pragma once
// Scene Studio / build.ps1 -Profile writes profile_gen.h; its defines win
// over every guarded default below.
#if __has_include("profile_gen.h")
#include "profile_gen.h"
#endif
// ============================================================================
// AI Usage Monitor: firmware settings
// Board: ESP32-2432S024C (ESP32-D0WD-V3, ILI9341 240x320 SPI, CH340 USB-serial)
// ============================================================================

#define FW_VERSION "1.4.2"

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
#ifndef BACKLIGHT_SMOOTHING_MS
#define BACKLIGHT_SMOOTHING_MS 1000
#endif
#if BACKLIGHT_SMOOTHING_MS < 0 || BACKLIGHT_SMOOTHING_MS > 60000
#error "BACKLIGHT_SMOOTHING_MS must be 0..60000"
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

// ---------------------------------------------------------------------------
// Optional visual pages. Console and Details are always available. Companion,
// Images and automatic Screensaver support default on and can be removed at
// build time with one switch each. Keep these macros guarded so a project-wide
// override wins.
// ---------------------------------------------------------------------------
#ifndef UI_COMPANION_ENABLED
#define UI_COMPANION_ENABLED 1
#endif
#ifndef UI_IMAGE_ENABLED
#define UI_IMAGE_ENABLED 1
#endif
#ifndef UI_CITY_ENABLED
#define UI_CITY_ENABLED 1
#endif
#ifndef UI_SCREENSAVER_ENABLED
#define UI_SCREENSAVER_ENABLED 1
#endif

// Stable page IDs. They are independent of which optional pages are compiled
// in, so persisted/serial references do not shift when a page is omitted.
#define UI_PAGE_CONSOLE 0
#define UI_PAGE_DETAILS 1
#define UI_PAGE_COMPANION 2
#define UI_PAGE_IMAGE 3
#define UI_PAGE_SCREENSAVER 4
#define UI_PAGE_CITY 5

// Tap order of the pages. Pages switched off above are skipped.
#ifndef UI_VIEW_ORDER
#define UI_VIEW_ORDER UI_PAGE_CONSOLE, UI_PAGE_DETAILS, UI_PAGE_COMPANION, UI_PAGE_IMAGE, UI_PAGE_CITY
#endif

// Screensaver target and automatic activation. This is presentation state,
// never a navigation entry. Either global switch disables automatic saving.
#ifndef UI_SCREENSAVER_PAGE
#define UI_SCREENSAVER_PAGE UI_PAGE_COMPANION
#endif
#ifndef UI_SCREENSAVER_AUTO_ENABLED
#define UI_SCREENSAVER_AUTO_ENABLED 1
#endif
#ifndef UI_SCREENSAVER_TIMEOUT_MS
#define UI_SCREENSAVER_TIMEOUT_MS 30000UL
#endif

// Per-view idle policy; Companion, Images and City are always exempt.
#ifndef UI_CONSOLE_SAVER_ENABLED
#define UI_CONSOLE_SAVER_ENABLED 1
#endif
#ifndef UI_DETAILS_SAVER_ENABLED
#define UI_DETAILS_SAVER_ENABLED 1
#endif
#ifndef UI_CONSOLE_SAVER_TIMEOUT_MS
#define UI_CONSOLE_SAVER_TIMEOUT_MS UI_SCREENSAVER_TIMEOUT_MS
#endif
#ifndef UI_DETAILS_SAVER_TIMEOUT_MS
#define UI_DETAILS_SAVER_TIMEOUT_MS UI_SCREENSAVER_TIMEOUT_MS
#endif
#ifndef UI_CONSOLE_WAKE_ON_USAGE
#define UI_CONSOLE_WAKE_ON_USAGE 1
#endif
#ifndef UI_DETAILS_WAKE_ON_USAGE
#define UI_DETAILS_WAKE_ON_USAGE 1
#endif

// A target must exist only when automatic saving is enabled.
#if UI_SCREENSAVER_ENABLED && UI_SCREENSAVER_AUTO_ENABLED
#if UI_SCREENSAVER_PAGE == UI_PAGE_SCREENSAVER
#error "Screensaver cannot target itself"
#endif
#if UI_SCREENSAVER_PAGE < UI_PAGE_CONSOLE || UI_SCREENSAVER_PAGE > UI_PAGE_CITY
#error "Unknown screensaver target page"
#endif
#if UI_SCREENSAVER_PAGE == UI_PAGE_COMPANION && !UI_COMPANION_ENABLED
#error "Screensaver target must be an enabled page"
#endif
#if UI_SCREENSAVER_PAGE == UI_PAGE_IMAGE && !UI_IMAGE_ENABLED
#error "Screensaver target must be an enabled page"
#endif
#if UI_SCREENSAVER_PAGE == UI_PAGE_CITY && !UI_CITY_ENABLED
#error "Screensaver target must be an enabled page"
#endif
#endif
#if UI_SCREENSAVER_AUTO_ENABLED
#if UI_SCREENSAVER_TIMEOUT_MS < 1UL || UI_SCREENSAVER_TIMEOUT_MS > 2147483647UL
#error "Screensaver timeout must be 1..2147483647 milliseconds"
#endif
#if UI_CONSOLE_SAVER_TIMEOUT_MS < 1UL || UI_CONSOLE_SAVER_TIMEOUT_MS > 2147483647UL || UI_DETAILS_SAVER_TIMEOUT_MS < 1UL || UI_DETAILS_SAVER_TIMEOUT_MS > 2147483647UL
#error "Per-view timeout must be 1..2147483647 milliseconds"
#endif
#endif
