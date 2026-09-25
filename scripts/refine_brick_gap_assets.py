"""Refine the first "隙光" card layers in place.

The committed subject matte kept five disconnected alpha islands and a bright
rim from the generator's light checkerboard. This pass keeps only the main
component, decontaminates the fringe RGB from the nearest interior pixel,
re-derives the registered line art, strengthens the too-faint effects plane,
and records provenance for the card.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "cards" / "brick-gap"
ASSETS = CARD / "assets"
WEB_ASSETS = ROOT / "web" / "assets" / "cards" / "brick-gap"
CANVAS = (1024, 1536)


def clean_subject(subject: Image.Image) -> Image.Image:
    alpha = np.asarray(subject.getchannel("A"))
    rgb = np.asarray(subject.convert("RGB"))

    comp, _ = ndimage.label(alpha > 32)
    sizes = np.bincount(comp.ravel())
    sizes[0] = 0
    main = comp == int(sizes.argmax())
    alpha = np.where(main, alpha, 0).astype(np.uint8)
    alpha = np.where(alpha < 12, 0, alpha).astype(np.uint8)

    # Bright neutral board patches that flood-fill trapped inside the figure
    # (between hair spikes) read as white flakes; drop small ones at the edge.
    mn = rgb.min(axis=2).astype(np.int16)
    mx = rgb.max(axis=2).astype(np.int16)
    board = (mn >= 219) & (mx - mn <= 12) & (alpha > 0)
    near_edge = ndimage.binary_dilation(alpha == 0, iterations=3) & (alpha > 0)
    lab, n = ndimage.label(board)
    for i in range(1, n + 1):
        piece = lab == i
        if piece.sum() < 400 and (piece & near_edge).any():
            alpha = np.where(piece, 0, alpha).astype(np.uint8)

    # Dimmer board remnants (flat gray clumps) cling to the hair silhouette
    # as torn white flakes; clear them in the head region only, where no
    # garment highlight can be mistaken for fringe. Hair reads dark and skin
    # reads warm, so a neutral mid-gray test isolates the board leftovers.
    lum = rgb.mean(axis=2)
    spread = rgb.max(axis=2) - rgb.min(axis=2)
    head = np.zeros(alpha.shape, dtype=bool)
    head[:680, :] = True
    fringe = (alpha > 0) & (lum > 150) & (spread <= 16) & head
    fringe &= ndimage.binary_dilation(alpha == 0, iterations=6)
    alpha = np.where(fringe, 0, alpha).astype(np.uint8)

    comp, _ = ndimage.label(alpha > 32)
    sizes = np.bincount(comp.ravel())
    sizes[0] = 0
    alpha = np.where(comp == int(sizes.argmax()), alpha, 0).astype(np.uint8)

    # Torn gray board fringe clings to thin hair spikes at the silhouette.
    # Real strands read dark and interior sheen sits on the thick head mass,
    # so neutral mid-gray pixels inside thin (opening-removed) alpha
    # structures are board leftovers; opening spares the thick sheen.
    yy, xx = np.mgrid[-3:4, -3:4]
    disk = (yy ** 2 + xx ** 2) <= 9
    opened = ndimage.binary_opening(alpha > 0, structure=disk)
    thin = (alpha > 0) & ~opened
    gray_thin = head & thin & (spread <= 16) & (lum > 60)
    alpha = np.where(gray_thin, 0, alpha).astype(np.uint8)

    # A bright board patch flood-filled between spikes reads as a white blob
    # fully enclosed by dark hair; drop small neutral components whose
    # surrounding ring is predominantly hair-dark (eye whites sit on skin).
    cand = head & (alpha > 0) & (lum > 120) & (spread <= 16)
    lab, n = ndimage.label(cand)
    for i in range(1, n + 1):
        piece = lab == i
        if piece.sum() > 200:
            continue
        ring = ndimage.binary_dilation(piece, iterations=4) & ~piece & (alpha > 0)
        if ring.sum() and (lum[ring] < 90).mean() > 0.7:
            alpha = np.where(piece, 0, alpha).astype(np.uint8)

    comp, _ = ndimage.label(alpha > 32)
    sizes = np.bincount(comp.ravel())
    sizes[0] = 0
    alpha = np.where(comp == int(sizes.argmax()), alpha, 0).astype(np.uint8)

    interior = ndimage.binary_erosion(alpha >= 200, iterations=2)
    _, indices = ndimage.distance_transform_edt(~interior, return_indices=True)
    clean_rgb = rgb[tuple(indices)]
    clean_rgb = np.where(interior[..., None], rgb, clean_rgb).astype(np.uint8)

    out = Image.fromarray(clean_rgb, "RGB").convert("RGBA")
    out.putalpha(Image.fromarray(alpha, "L"))
    return out


def lineart_layer(subject: Image.Image) -> Image.Image:
    """Dark contours on white, re-derived from the cleaned subject."""
    alpha_np = np.asarray(subject.getchannel("A")).astype(np.int16)
    sil = Image.fromarray(((alpha_np > 40) * 255).astype(np.uint8), "L")
    edge_a = sil.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.6))
    flat = Image.new("RGBA", CANVAS, (255, 255, 255, 255))
    flat.alpha_composite(subject)
    edge_g = flat.convert("L").filter(ImageFilter.GaussianBlur(1.4)).filter(
        ImageFilter.FIND_EDGES
    )
    ea = np.asarray(edge_a).astype(np.int16)
    eg = np.asarray(edge_g).astype(np.int16)
    combined = np.maximum(ea, eg // 2)
    strokes_np = np.where(combined > 34, 0, 255).astype(np.uint8)
    strokes_np[:4, :] = 255
    strokes_np[-4:, :] = 255
    strokes_np[:, :4] = 255
    strokes_np[:, -4:] = 255
    strokes = Image.fromarray(strokes_np, "L")
    strokes = strokes.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.MinFilter(3))
    return Image.merge("RGB", (strokes, strokes, strokes))


def effects_layer() -> Image.Image:
    """Warm dust with real presence: the old plane was nearly invisible."""
    random.seed(1239)
    fx = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(fx)
    warm = [(255, 226, 178), (255, 200, 140), (255, 240, 210), (244, 176, 122)]
    for _ in range(120):
        x = random.randint(60, CANVAS[0] - 60)
        y = random.randint(140, 1240)
        r = random.choice([2, 3, 3, 4, 4, 5, 6, 8, 9])
        color = random.choice(warm)
        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=color + (random.randint(120, 215),),
        )
    for _ in range(8):
        x = random.randint(90, CANVAS[0] - 90)
        y = random.randint(200, 1150)
        r = random.randint(24, 54)
        glow = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((4, 4, r * 2 - 4, r * 2 - 4), fill=(255, 224, 178, 64))
        glow = glow.filter(ImageFilter.GaussianBlur(9))
        fx.alpha_composite(glow, (x - r, y - r))
    return fx.filter(ImageFilter.GaussianBlur(0.5))


def save(image: Image.Image, name: str) -> None:
    for directory in (ASSETS, WEB_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)
        image.save(directory / name)


def main() -> None:
    subject = clean_subject(Image.open(ASSETS / "subject.png"))
    lineart = lineart_layer(subject)
    effects = effects_layer()
    for image, name in ((subject, "subject.png"), (lineart, "lineart.png"), (effects, "effects.png")):
        save(image, name)

    preview = Image.open(ASSETS / "background.png").convert("RGBA")
    preview.alpha_composite(subject)
    preview.alpha_composite(effects)
    preview.alpha_composite(Image.open(ASSETS / "text.png"))
    preview.save(ROOT / "verification" / "brick-gap-preview.png")

    provenance = {
        "reference_role": "Generated layer art from the original skill session; the generator sources were never archived in the repository.",
        "foreground_method": "Checkerboard keying with border flood and hole fill produced the original matte; the 2026-09-25 refinement keeps only the main alpha component and decontaminates fringe RGB from the nearest interior pixel, so silhouette edges no longer carry the board's white rim.",
        "lineart_method": "Edge/threshold pass re-derived from the cleaned subject, keeping contour registration.",
        "effects_method": "Sparse warm dust motes and soft glow discs with raised alpha so the floating plane reads while tilting.",
        "style": "Urban street photography against a weathered brick wall; ivory and antique-gold typography; foil remains a material effect.",
    }
    (CARD / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Refined brick-gap assets at", CARD)


if __name__ == "__main__":
    main()
