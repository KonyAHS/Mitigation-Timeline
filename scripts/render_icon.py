"""Rasterise assets/icon.svg into the PNG/ICO files used by the apps and the .exe builds.

Usage:  uv run --no-project --with resvg-py --with pillow python scripts/render_icon.py
"""

from __future__ import annotations

import io
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "assets" / "icon.svg"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(size: int) -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_string=SVG.read_text("utf-8"), width=size, height=size)
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


def main() -> None:
    big = render(256)
    big.save(ROOT / "assets" / "icon.png")
    big.save(ROOT / "src" / "mitigation_timeline" / "assets" / "icon.png")
    frames = [render(s) for s in ICO_SIZES]
    frames[-1].save(ROOT / "assets" / "icon.ico", sizes=[(s, s) for s in ICO_SIZES],
                    append_images=frames[:-1])
    print("icon.png / icon.ico written")


if __name__ == "__main__":
    main()
