# Hardware report

Verified 2026-10-21. Facts come from the device itself (esptool) and from Arduino sketches you previously ran on it.

## Identity

| Item | Value | Evidence |
| --- | --- | --- |
| MCU | ESP32-D0WD-V3, revision v3.1, dual core 240 MHz, Wi-Fi + BT | `esptool chip-id` on COM6 |
| MAC | `ac:15:18:d4:4c:dc` | esptool |
| Flash | 4 MB (manufacturer 0x68, device 0x4016), 3.3 V | `esptool flash-id` |
| PSRAM | none reported (D0WD has no in-package PSRAM) | chip type |
| USB | Separate USB-serial bridge: WCH **CH340** (`VID_1A86&PID_7523`), currently **COM6**. No native USB, and USB is not a network interface. | Windows PnP |
| Board | **ESP32-2432S024C** "Cheap Yellow Display" clone (2.4", capacitive) | Matches every sketch in `Documents/Arduino` (`MonDeck2/README.txt`: "ESP32-2432S024 board with ILI9341 (TFT_eSPI) and CST820 capacitive touch") |
| Display | **ILI9341**, 240×320, SPI | `libraries/TFT_eSPI/User_Setup.h` (`ILI9341_DRIVER`), used by all sketches |
| Touch | CST820 capacitive, I²C at 0x15 | `MonDeck2/touch_driver.h`, `tft_example.ino` |

## Pinout (from the working `TFT_eSPI/User_Setup.h` and the sketches)

| Signal | GPIO |
| --- | --- |
| TFT MISO | 12 |
| TFT MOSI | 13 |
| TFT SCLK | 14 |
| TFT CS | 15 |
| TFT DC | 2 |
| TFT RST | not connected (-1, shared with EN) |
| TFT backlight | 27 (active high) |
| Touch SDA / SCL | 33 / 32 |
| Touch INT / RST | 21 / 25 |

SPI is 40 MHz for writes and 20 MHz for reads.

The firmware build passes these same values as compiler flags (`USER_SETUP_LOADED`), so it doesn't depend on, or modify, the shared `User_Setup.h`. The values are identical to the ones you already used.

## Toolchain found

- Arduino IDE 2, bundled `arduino-cli` 1.2.0.
- Board package `esp32:esp32` 3.3.1, target `esp32:esp32:esp32` (ESP32 Dev Module), 4 MB flash.
- Libraries in the sketchbook: TFT_eSPI 2.5.43, ArduinoJson 7.4.2, bb_captouch.
- Sketchbook: `C:\Users\ZECHS\Documents\Arduino`. The IDE keeps no custom sketchbook path, so this default applies.

## Orientation

Every earlier sketch (`MonDeck`, `MonDeck2`, `TouchDeck`, `blank`, `tft_example`, `OldMakerMon`) used `setRotation(1)`. That landscape view is how the board is "traditionally" held.

From the ILI9341 rotation table in TFT_eSPI:

- `0` = MX
- `1` = MV
- `2` = MY
- `3` = MX|MY|MV

In rotation 1, the right edge of the landscape image is the bottom edge of the rotation 0 portrait. So "portrait with the traditional right-hand edge facing up" is **rotation 2**. Version 1.2 defaults to **rotation 0**, traditional left edge up, for the requested clockwise remount. See the README to change it.

## Remaining uncertainty

- Physical markings were not inspected. ILI9341 vs ST7789 variants exist for this board family; the earlier sketches show ILI9341 worked on this unit.
- v1.2 uses CST820 touch on SDA 33 / SCL 32, reset 25, address 0x15, for whole-screen tap cycling. Physical tap reliability still needs user confirmation.
- The flash held TickrTrackr/older test firmware. You said it was disposable, so no backup was kept.
