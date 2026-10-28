"""Package only referenced PNG layers from the two verified Ansimuz CC0 packs.

Usage: python scripts/package_cc0_scenes.py --out build/cc0-scenes.zip
Run from a checkout with local art installed. No network requests. The archive
contains art layers and their original license PDFs, not firmware or personal
settings. Extract into the repository root after downloading it from a release.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PACKS = {
    'miami-drive': 'Miami-synth-files/Miami-synth-files/public-license.pdf',
    'neon-skyline': 'cyberpunk-street-files/cyberpunk-street-files/public-license.pdf',
    'rainy-street': 'cyberpunk-street-files/cyberpunk-street-files/public-license.pdf',
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    files = {}
    for sid, license_path in PACKS.items():
        directory = ROOT / 'assets/library' / sid
        entry = json.loads((directory / 'entry.json').read_text(encoding='utf-8'))
        for layer in entry['scene']['layers']:
            sources = layer['src'] if isinstance(layer['src'], list) else [layer['src']]
            for src in sources:
                path = (directory / src).resolve(strict=True)
                if not path.is_relative_to((directory / 'src').resolve()) or path.suffix.lower() != '.png':
                    raise ValueError('Only referenced scene-local PNG layers may be packaged')
                files[path.relative_to(ROOT).as_posix()] = path
        license_file = ROOT / 'assets/sprites' / license_path
        files[f'third_party/licenses/{sid}-public-license.pdf'] = license_file.resolve(strict=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.out, 'w', ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        archive.writestr('CC0-SCENES-README.txt',
            'Miami Drive, Neon Skyline and Rainy Street layers by Luis Zuno (Ansimuz).\n'
            'Downloaded pack license PDFs are included: CC0, redistribution permitted.\n'
            'Sources: https://ansimuz.itch.io/warped-miami-synth and\n'
            'https://ansimuz.itch.io/cyberpunk-street-environment\n'
            'Extract at the AIUsageMonitor repository root, then build/send your profile.\n'
            'This archive has no firmware, personal settings, optional palettes or PixelPatterns.\n')
    print(f'Packaged {len(files)} approved files; sha256={hashlib.sha256(args.out.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
