# Hardware and pinout

The verified target is an **ESP32-2432S024C** integrated 2.4-inch display board with an **ILI9341** TFT and **CST820** capacitive touch. This is one tested variant of a board family often called “Cheap Yellow Display”; a similar product name does not prove matching hardware.

## Bill of materials

| Item | Purpose |
| --- | --- |
| ESP32-2432S024C, ILI9341 + CST820 variant | MCU, display, touch and USB-UART bridge on one board |
| USB data cable matching the board connector | Firmware upload, power and telemetry |
| PC with Windows and a USB port | Tested host for the Python service and PowerShell helpers |
| Optional mount/enclosure | Position the screen beneath a monitor; design not supplied |

No external wiring is needed on the integrated board. USB supplies board power; GPIO signal levels are 3.3 V. A measured power/current budget and external-power wiring have not been established here. Do not infer connector positions or power-input ratings from the GPIO table.

## Verified identity

| Component | Tested unit |
| --- | --- |
| MCU | ESP32-D0WD-V3, revision v3.1, dual-core 240 MHz |
| Flash | 4 MB, reported by esptool |
| PSRAM | Not used; none reported on the tested unit |
| USB-UART | WCH CH340, VID `1A86`, PID `7523` |
| TFT | ILI9341, native 240×320, SPI |
| Touch | CST820, I²C address `0x15` |
| Default orientation | Rotation 1, landscape 320×240 |

MCU/flash identity was read using esptool. Display pin mapping was established from an existing working configuration and confirmed by this project's successful build, flash and framebuffer output. Touch initialization reports a device at `0x15`; physical tap reliability remains a user acceptance check. No physical board schematic or connector survey is claimed.

## Implemented GPIO mapping

These are ESP32 **GPIO numbers**, not connector pin numbers.

| Function | GPIO / value | Firmware behavior |
| --- | --- | --- |
| TFT MISO | 12 | SPI data input |
| TFT MOSI | 13 | SPI data output |
| TFT SCLK | 14 | SPI clock |
| TFT CS | 15 | TFT chip select |
| TFT DC | 2 | Command/data select |
| TFT RST | `-1` | No dedicated reset GPIO configured in TFT_eSPI |
| TFT backlight | 27 | Active high, LEDC PWM at 5 kHz, 8-bit duty |
| Touch SDA | 33 | I²C data, `Wire.begin(33, 32)` |
| Touch SCL | 32 | I²C clock; default Wire bus frequency, no explicit override |
| Touch reset | 25 | Driven low then high at startup |
| Touch interrupt | 21 | Historical board mapping; **unused by this firmware**, which polls |

The TFT pin definitions are supplied by [scripts/build.ps1](../scripts/build.ps1) using `USER_SETUP_LOADED`; building with that script does not edit a shared TFT_eSPI `User_Setup.h`.

SPI write frequency is **40 MHz**, with **20 MHz** configured for reads. The build also defines `SPI_TOUCH_FREQUENCY=2.5 MHz`, but this is not the CST820 bus: touch is read over I²C directly through Wire. TFT_eSPI's `TOUCH_CS` warning is expected because no SPI touch controller is used.

The application polls touch register `0x02` every 25 ms. A release after a press of 25 ms to under 1.5 seconds switches views. Coordinates are unnecessary because the whole screen acts as one button. The firmware does not require `bb_captouch`.

## USB and display memory

USB connects through the CH340 to the ESP32 UART; it is not native USB or a network adapter. Serial uses **115200 baud, 8N1**, one JSON payload per line. The host opens the port with DTR/RTS deasserted to avoid an automatic reset during normal service operation.

The renderer normally uses an 8-bit RGB332 framebuffer: 320×240 = **76,800 bytes**, independent of orientation. TFT_eSPI converts it for display output; screenshots capture those quantized colors. If allocation fails, the renderer falls back to direct drawing and framebuffer capture is unavailable.

## Orientation and brightness

Set `DISPLAY_ROTATION` in [config.h](../firmware/AIUsageMonitor/config.h), then rebuild and flash:

| Rotation | Logical size | Orientation |
| --- | --- | --- |
| 0 | 240×320 | Portrait |
| 1 | 320×240 | Landscape, default |
| 2 | 240×320 | Opposite portrait |
| 3 | 320×240 | Opposite landscape |

For a temporary preview, `python scripts/screenshot.py --rot 3 --feed --out build/rotation3.png` changes rotation until reboot. Rotation numbers describe this driver/panel combination; confirm upright text on your own mount.

`BACKLIGHT_LEVEL` is an 8-bit PWM duty from 0 to 255, default 255. It is not a calibrated brightness measurement.

## Adapting another board

Check its display controller, resolution, GPIO assignments, touch controller, reset behavior and backlight polarity first. ST7789 and resistive-touch variants require changes; this pinout is not a generic ESP32 wiring recipe. The validated software baseline is in [SETUP.md](SETUP.md), and test scope is in [TEST_REPORT.md](TEST_REPORT.md).
