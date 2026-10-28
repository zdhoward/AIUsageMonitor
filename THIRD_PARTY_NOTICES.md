# Third-party notices

Our code is [MIT](LICENSE); that does not relicense other authors' code, artwork, fonts or data. The scoped [inventory](third_party/manifest.json) records evidence and remaining gaps. Run `python scripts/third_party.py list` or `check`; the checker is not a legal certification or an exhaustive code-provenance scanner.

## Companion face

MINT's eye geometry and spring motion adapt [Grobot Animations](https://github.com/tanmaywankar/Grobot_Animations), Tanmay Wankar, revision `858d8da648c9e71ff9b9f5e6f558ba85293a70fb`. The adaptation changes canvas ownership, timing, blending and bounds. Preserve the **complete** [upstream MIT notice](firmware/AIUsageMonitor/grobot/LICENSE.txt) with copies, including binary distribution documentation. Attribution is also in [MINT](docs/MINT.md).

## Scene packs and demonstrations

| Content | Author/source | Evidence and handling |
| --- | --- | --- |
| Miami Drive layers | Luis Zuno / Ansimuz, [Warped Miami Synth](https://ansimuz.itch.io/warped-miami-synth) | Downloaded archive's `public-license.pdf` explicitly permits CC0 use, modification and redistribution. License PDF accompanies the optional scene archive. |
| Neon Skyline and Rainy Street layers | Luis Zuno / Ansimuz, [Synth Cities / Cyberpunk Street](https://ansimuz.itch.io/cyberpunk-street-environment) | Official storefront lists CC0; downloaded archive's `public-license.pdf` agrees. License PDFs accompany the optional scene archive. |
| Pixel Patterns tiles | Exact author/source unresolved | Existing metadata says CC0, but that is not sufficient evidence. Raw tiles remain local and are excluded from the distributed pack and public GIF. |
| Neon Pulse 8 palette | pablokld, [Lospec](https://lospec.com/palette-list/neon-pulse-8) | No specific redistribution grant verified. Removed from current tracking; existing local copies remain ignored. Earlier public tags/history still contain the old palette. No historical rewrite or legal conclusion is implied. |

Screenshots and GIFs also distribute visual content; rendering an asset does not exempt it from its terms. The public README GIF contains only verified CC0 layers and original Plasma/Warp scenes in original themes. It is a native-renderer preview, not a hardware recording. The optional palette is not embedded in it.

## Procedural references

Scene metadata cites visual/algorithmic inspiration from these projects. Retained license snapshots preserve notices without asserting that the exact earlier implementation reference revision is known:

- [termflix](https://github.com/paulrobello/termflix), Paul Robello: [complete MIT notice](third_party/licenses/termflix-MIT.txt), snapshot `f2f2a3abe818bc0f85986c66de5750ef13cd1e59`.
- [sysc-Go](https://github.com/Nomadcxx/sysc-Go), Nomadcxx: [complete MIT notice](third_party/licenses/sysc-Go-MIT.txt), snapshot `84db16784091c310d21814bd0f244993b5cfb83b`. Its separately licensed upstream models/assets are **not** included here; MIT code does not clear those assets.
- [matrix](https://github.com/Rezmason/matrix), Rezmason: [complete MIT notice](third_party/licenses/matrix-MIT.txt), snapshot `5ba90490453ceceb6812d6b1bc658a99a92411d0`. No upstream fonts are packaged here.

Historical EMS Spectre / Video EQ concepts are not a public-domain software license. Source-copy provenance for those reference implementations remains unverified; do not import code/assets from GPL/unlicensed references assuming that a similar visual is sufficient permission. Existing source describes procedural implementations; this audit is not an exhaustive derivation analysis.

## Installed dependencies and binaries

Installed separately, not vendored: ESP32 Arduino core (LGPL-2.1 family and component-specific terms), TFT_eSPI (BSD-2-Clause), ArduinoJson (MIT), pyserial (BSD-3-Clause), tzdata (Apache-2.0 wrapper plus timezone database terms), psutil (BSD-3-Clause). Consult each exact installed version and its notices; currently unrecorded firmware library versions are not pinned by the inventory. Optional authoring/export tools such as Pillow, FFmpeg, resvg and Aseprite retain their own licenses and are not bundled by these scripts.

We publish source and the verified CC0 image pack, **not prebuilt firmware or frozen desktop executables**. Before distributing binaries: inventory every linked/bundled component, preserve full licenses/notices, provide corresponding source and relinking materials where required, include build instructions/versions, and verify asset permissions. The ESP32 core's root license is not an audit of every toolchain subcomponent. MIT application code does not remove those obligations.

## External service

Automatic brightness uses [SunriseSunset.io](https://sunrisesunset.io). Its [current API terms](https://sunrisesunset.io/api/#attribution-required) require a visible link wherever data is displayed. Attribution: **Powered by [SunriseSunset.io](https://sunrisesunset.io)**. This is a service requirement, not a CC-BY assertion. The app reports provider/link in brightness status; clients displaying solar data must preserve visible attribution.
