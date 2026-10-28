"""Render a README GIF with the native firmware preview engine, not USB footage.

Usage: python scripts/render_scene_demo.py --out build/scene-demo.gif
Requires Pillow and a built Scene Studio native DLL. Only procedural scenes and
the locally verified CC0 Ansimuz packs are allowlisted; Pixel Patterns is omitted
until its imported tile provenance is verified. No downloads or config writes.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw
from studio.native_host import NativeHost

SCENES = ('miami-drive', 'neon-skyline', 'rainy-street', 'plasma', 'warp-speed')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--scene', choices=SCENES, action='append')
    ap.add_argument('--fps', type=int, default=10, choices=range(5, 21))
    ap.add_argument('--seconds', type=float, default=2.4)
    args = ap.parse_args()
    if not 1 <= args.seconds <= 5:
        ap.error('--seconds must be 1..5')
    host = NativeHost()
    frames = []
    palette = []
    for v in range(256):
        palette.extend((((v >> 5) & 7) * 255 // 7,
                        ((v >> 2) & 7) * 255 // 7, (v & 3) * 85))
    for sid in args.scene or SCENES:
        entry = json.loads((ROOT / 'assets/library' / sid / 'entry.json').read_text(encoding='utf-8'))
        scene = entry['scene']
        scene['theme'] = 'original'
        scene.pop('cycle', None)
        host.render(sid, 6000, scene, warm=150)
        for n in range(round(args.fps * args.seconds)):
            pixels, status = host.render(sid, 6000 + round(n * 1000 / args.fps), scene)
            if status != 'ok':
                raise RuntimeError(f'{sid}: {status}')
            frame = Image.frombytes('P', (320, 240), pixels)
            frame.putpalette(palette)
            canvas = Image.new('RGB', (320, 260), 'black')
            canvas.paste(frame.convert('RGB'))
            ImageDraw.Draw(canvas).text((6, 243), entry['name'] + ' | native preview', fill='white')
            frames.append(canvas.resize((640, 520), Image.Resampling.NEAREST))
        print('rendered', sid)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(args.out, save_all=True, append_images=frames[1:],
                   duration=round(1000 / args.fps), loop=0, optimize=True)
    print(f'Saved {args.out}: {len(frames)} input frames, {args.out.stat().st_size} bytes')


if __name__ == '__main__':
    main()
