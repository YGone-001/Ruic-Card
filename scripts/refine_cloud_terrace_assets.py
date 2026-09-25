"""Refine the third "云阶" card layers in place.

The corrected full-photo card shipped a degenerate line art (only a border
ring, so the holographic ink glints had nothing to drive them) and a
too-sparse dust plane.  This pass re-derives the line art from a person-only
segmentation so the glints follow the figure and densifies the dust; the
subject plane keeps its transparent rim, which the layer contract requires.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "cards" / "cloud-terrace"
ASSETS = CARD / "assets"
WEB_ASSETS = ROOT / "web" / "assets" / "cards" / "cloud-terrace"
CANVAS = (1024, 1536)


def person_mask(photo: Image.Image) -> np.ndarray:
    from rembg import new_session, remove

    session = new_session("u2net_human_seg")
    mask = remove(photo.convert("RGB"), session=session, only_mask=True)
    return np.asarray(mask.convert("L"))


def lineart_layer(photo: Image.Image, person: np.ndarray) -> Image.Image:
    """Dark contours on white, focused on the figure instead of a border ring."""
    sil = Image.fromarray(((person > 128) * 255).astype(np.uint8), "L")
    outline = sil.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.6))
    detail_source = photo.convert("L").filter(ImageFilter.GaussianBlur(1.0))
    details = detail_source.filter(ImageFilter.FIND_EDGES)
    oa = np.asarray(outline).astype(np.int16)
    da = np.asarray(details).astype(np.int16)
    inside = ndimage.binary_dilation(person > 128, iterations=1)
    strokes = np.full(CANVAS[::-1], 255, dtype=np.uint8)
    edge = oa > 18
    detail = (da > 42) & inside
    strokes[edge | detail] = 0
    strokes[:4, :] = 255
    strokes[-4:, :] = 255
    strokes[:, :4] = 255
    strokes[:, -4:] = 255
    img = Image.fromarray(strokes, "L")
    img = img.filter(ImageFilter.MinFilter(3))
    return Image.merge("RGB", (img, img, img))


def effects_layer(existing: Image.Image) -> Image.Image:
    """Denser, brighter dust in the palette the card already uses."""
    arr = np.asarray(existing.convert("RGBA"))
    sel = arr[..., 3] > 120
    colors = [tuple(int(v) for v in row) for row in arr[..., :3][sel][:: max(1, sel.sum() // 4000)]]
    colors = colors or [(255, 246, 220), (196, 232, 240), (255, 214, 150)]
    random.seed(7703)
    fx = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(fx)
    quiet = ((40, 40, 440, 310), (260, 1255, 760, 1425))

    def in_quiet(x: int, y: int) -> bool:
        return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in quiet)

    placed = 0
    while placed < 170:
        x = random.randint(50, CANVAS[0] - 50)
        y = random.randint(140, 1400)
        if in_quiet(x, y):
            continue
        placed += 1
        r = random.choice([2, 2, 3, 3, 4, 5, 6, 7, 9])
        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=random.choice(colors) + (random.randint(110, 225),),
        )
    glows = 0
    while glows < 7:
        x = random.randint(100, CANVAS[0] - 100)
        y = random.randint(220, 1250)
        if in_quiet(x, y):
            continue
        glows += 1
        r = random.randint(22, 48)
        glow = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((4, 4, r * 2 - 4, r * 2 - 4), fill=random.choice(colors) + (52,))
        fx.alpha_composite(glow.filter(ImageFilter.GaussianBlur(8)), (x - r, y - r))
    return fx.filter(ImageFilter.GaussianBlur(0.4))


def save(image: Image.Image, name: str) -> None:
    for directory in (ASSETS, WEB_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)
        image.save(directory / name)


def main() -> None:
    subject_in = Image.open(ASSETS / "subject.png")
    person = person_mask(subject_in)
    lineart = lineart_layer(subject_in, person)
    effects = effects_layer(Image.open(ASSETS / "effects.png"))
    for image, name in ((lineart, "lineart.png"), (effects, "effects.png")):
        save(image, name)

    preview = Image.open(ASSETS / "background.png").convert("RGBA")
    preview.alpha_composite(subject_in)
    preview.alpha_composite(effects)
    preview.alpha_composite(Image.open(ASSETS / "text.png"))
    (ROOT / "verification").mkdir(exist_ok=True)
    preview.save(ROOT / "verification" / "cloud-preview.png")

    provenance = json.loads((CARD / "provenance.json").read_text(encoding="utf-8"))
    provenance["refinement_2026_09_25"] = (
        "Re-derived the line art from a person-only segmentation (silhouette plus "
        "interior detail edges) so the holographic ink glints follow the figure instead "
        "of an empty border ring, and densified and brightened the dust plane while "
        "keeping the typography zones quiet. The subject plane keeps its transparent "
        "border rim on purpose: the layer contract requires a genuinely transparent "
        "subject, and the full-photo card has no other transparent region."
    )
    (CARD / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Refined cloud-terrace assets at", CARD)


if __name__ == "__main__":
    main()
