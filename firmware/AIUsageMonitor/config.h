#pragma once
// ============================================================================
// AI Usage Monitor: firmware settings
// Board: ESP32-2432S024C (ESP32-D0WD-V3, ILI9341 240x320 SPI, CH340 USB-serial)
// ============================================================================

#define FW_VERSION "1.0.0"

// ---------------------------------------------------------------------------
// DISPLAY_ROTATION: the one setting to change when you remount the screen.
// Values are TFT_eSPI rotations for the ILI9341 on this board. "Traditional"
// means landscape rotation 1, the orientation all your earlier sketches used.
//
//   2 = Portrait, traditional RIGHT edge facing UP      (default)
//   0 = Portrait, traditional LEFT edge facing up       (upside-down portrait)
//   1 = Landscape, traditional orientation
//   3 = Landscape, upside down
//
// Rotations 1/3 make the screen 320x240 (two-column layout); 0/2 make it
// 240x320 (single column). The layout is computed from tft.width()/height()
// at runtime, so changing this value and reflashing is all that's needed.
// ---------------------------------------------------------------------------
#ifndef DISPLAY_ROTATION
#define DISPLAY_ROTATION 2
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

// Show "NO DATA" and dim the dashboard when no payload arrives for this long.
#define DATA_TIMEOUT_MS 30000UL

// Screen refresh period (countdowns and the activity pulse).
#define REDRAW_MS 1000UL
