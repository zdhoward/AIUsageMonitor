#pragma once
// Copy to secrets.h (git-ignored) only if you enable AIMON_USE_WIFI in config.h.
// The ESP32 supports 2.4 GHz networks only.
#define WIFI_SSID "your-2.4GHz-ssid"
#define WIFI_PASS "your-wifi-password"
// LAN address of the PC running the aimon service (bind_host must be 0.0.0.0 or this IP).
#define AIMON_URL "http://192.168.1.10:8797/v1/device"
