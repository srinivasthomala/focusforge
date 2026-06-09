"""Generate FocusForge Chrome extension icons.

Renders a teal rounded-square with a bold "FF" wordmark at the three sizes
the MV3 manifest expects. Run from the repo root:

    python scripts/generate_icons.py

Requires Pillow (`pip install Pillow`). Output: extension/icons/icon{16,48,128}.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "extension" / "icons"

SIZES = [16, 48, 128]
TEAL = (20, 184, 166, 255)        # primary brand color
DARK = (15, 23, 42, 255)          # wordmark color (slate-900)

FONT_CANDIDATES = [
    "arialbd.ttf",                                  # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
    "DejaVuSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = max(2, size // 6)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=TEAL)

    text = "FF" if size >= 32 else "F"
    font = load_font(int(size * 0.6))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - tw) // 2 - bbox[0], (size - th) // 2 - bbox[1]),
        text,
        fill=DARK,
        font=font,
    )
    return img


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in SIZES:
        path = OUT_DIR / f"icon{s}.png"
        make_icon(s).save(path)
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
