# Third-party content and distribution

[Notices](../THIRD_PARTY_NOTICES.md) and the [inventory](../third_party/manifest.json) separate our MIT code from third-party rights. This scoped audit records what was checked; it does not prove every dependency/subcomponent or historical source derivation has been cleared.

## Recreate the scene setup

1. Get application source from GitHub. Dashboards, MINT and procedural generators need no third-party image packs.
2. Optionally download **cc0-scenes.zip** from the licensing/docs update release. Extract at the repository root. It adds only referenced PNG layers for Miami Drive, Neon Skyline and Rainy Street, plus Ansimuz's original license PDFs. It does not overwrite profiles or service settings.
3. Open Studio, select Default and choose **Send to display**. Existing scene definitions and playlist reference these layers. Build tools/libraries still need installation: [Setup](SETUP.md).
4. Pack sources: [Warped Miami Synth](https://ansimuz.itch.io/warped-miami-synth) and [Synth Cities / Cyberpunk Street](https://ansimuz.itch.io/cyberpunk-street-environment). Credit Luis Zuno / Ansimuz even though the included CC0 notice does not require attribution. Music and unrelated packs are excluded.

Maintainers build the optional archive from locally installed packs:

```powershell
python scripts/package_cc0_scenes.py --out build/cc0-scenes.zip
```

The script follows the three scene definitions' exact PNG references, rejects paths outside their `src` folders and includes original license PDFs. Review contents before upload. No entire personal assets directory is packaged. README animation uses `scripts/render_scene_demo.py`; it is labelled native preview, not device footage.

## Optional palettes and user-owned art

Neon Pulse 8 redistribution permission is unverified. It is no longer tracked; your existing local file is retained. Earlier public history/tags still contain it. We have not rewritten shared history or asserted that a palette is unlawful. Obtain an explicit grant before bundling it again.

To acquire optional palette data directly after reviewing source terms:

```powershell
python scripts/third_party.py fetch --palette neon-pulse-8 --ack-source-terms
```

This opt-in command uses an allowlisted HTTPS source, bounded/validated JSON, no overwrite without `--replace`, and `assets/themes/<slug>.json` where Studio already reads themes. Palette files are Git-ignored; acquisition receipts go under ignored logs. Acknowledgement **does not create use or redistribution rights**. Studio's existing Lospec import also works; review author/source terms yourself. No login, payment or remote code execution is automated.

Studio art imports go to ignored `assets/library/<id>/src/`. Record source URL, author, actual license/version and acquisition date; retain receipts/licenses. A free download, credit field or filename containing CC0 is not evidence. Users acquire paid/restricted packs themselves and import locally; never mirror them or silently fetch during builds.

## Release checks and gaps

```powershell
python scripts/third_party.py list --format markdown
python scripts/third_party.py check
```

The checker covers declared notices and tracked unverified assets, not undeclared files or deep source similarity. It uses Git's index so ignored local copies do not count as redistributed. Keep the public push guard too: it covers secrets/personal data/art, not license interpretation.

Known gaps: PixelPatterns tile provenance, exact earlier procedural-reference revisions/derivation, complete binary dependency obligations. Termflix/sysc-Go/matrix MIT snapshots are retained; that does not clear separately licensed assets. No claim that the entire build has no GPL code is made. Prebuilt firmware/executable publication remains gated on the full dependency/notice/relinking checklist.
