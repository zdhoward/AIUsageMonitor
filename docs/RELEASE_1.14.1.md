# v1.14.1 — Third-party notices and optional scene pack

This documentation/tooling update retains Grobot's MIT notice, adds pinned MIT notices for procedural references, and records known third-party licenses and unresolved provenance in THIRD_PARTY_NOTICES.md and third_party/manifest.json.

- README now includes a 12-second animated native-renderer preview of Miami Drive, Neon Skyline, Rainy Street, Plasma and Warp Speed. It is not hardware footage. Ansimuz layers are CC0; unverified tiles/palettes are excluded.
- Optional **cc0-scenes.zip** contains exactly 16 referenced PNG layers, three copies of the packs' original license PDFs, and setup instructions. Extract at the source checkout's root, then build/send the Default profile in Studio. No profiles, personal configuration, music, unrelated art or compiled firmware are included.
- Neon Pulse 8 is removed from current Git tracking while preserving existing local copies. New palette acquisitions remain ignored; users explicitly acquire optional data upstream after reviewing rights/terms. Old public history/tags are not rewritten and still contain the earlier palette file.
- `scripts/third_party.py` lists/checks the declared inventory and supports bounded, allowlisted optional palette acquisition. It does not certify legality or perform exhaustive source provenance analysis.
- A visible SunriseSunset.io credit link is added to Studio brightness settings.

Verification: Python compilation, inventory/notice check, production GIF rendering and curated archive inspection passed; independent review found no concrete blockers. This task's automated tests remain deferred; the preceding v1.14.0 release had 49 service and 20 Studio tests passing. Installed firmware remains v1.14.0; this release contains no binary firmware update.

Known gaps: PixelPatterns tile source/license, exact earlier procedural reference revisions and derivation, and complete obligations for distributing compiled firmware/executables. Prebuilt binaries remain unpublished until those obligations are assembled. Source code MIT does not relicense third-party material.

Scene pack SHA-256: `b9a7b7f21cf1ef530343f23f1831c8cca1898492a45f1eac17d198a03da2a3b1`.
