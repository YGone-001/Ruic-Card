"""Re-title the first card from four characters to the two-character "隙光".

The title glyphs are baked into text.png, so this pass erases only the title
band and re-setts the new two-character title in the same face, size, colour
and position, leaving every other piece of card furniture untouched.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "cards" / "brick-gap" / "assets"
WEB_ASSETS = ROOT / "web" / "assets" / "cards" / "brick-gap"
CANVAS = (1024, 1536)
FONT = Path(r"C:\Windows\Fonts\simkai.ttf")
TITLE = "隙光"
IVORY = (255, 241, 206, 255)
TITLE_BOX = (66, 88, 420, 178)
INK_ORIGIN = (74, 94)


def title_sprite() -> Image.Image:
    font = ImageFont.truetype(str(FONT), size=90)
    scratch = Image.new("RGBA", (600, 240), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scratch)
    x = 20
    for char in TITLE:
        draw.text((x, 20), char, font=font, fill=IVORY)
        x += 100
    ink = np.asarray(scratch)[..., 3] > 40
    ys, xs = np.where(ink)
    return scratch.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def main() -> None:
    text = Image.open(ASSETS / "text.png").convert("RGBA")
    arr = np.asarray(text).copy()
    arr[TITLE_BOX[1]:TITLE_BOX[3], TITLE_BOX[0]:TITLE_BOX[2], 3] = 0
    text = Image.fromarray(arr, "RGBA")
    text.alpha_composite(title_sprite(), INK_ORIGIN)
    for directory in (ASSETS, WEB_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)
        text.save(directory / "text.png")
    print("Re-titled brick-gap text layer to", TITLE)


if __name__ == "__main__":
    main()
