"""Refine the second "暮途" card layers in place.

The GrabCut matte kept fragments of the car roof and window pillar as extra
alpha islands and left a semi-transparent veil over the person, so tilting
ghosted scene structure and hazed the face.  This pass intersects the matte
with a person-only segmentation of the composed scene, de-veils and
decontaminates the subject, strengthens the too-faint dust plane, and adds a
soft shadow under the typography so the ivory title reads on the bright sky.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import build_sunset_drive_assets as builder

builder.ImageChops = __import__("PIL.ImageChops", fromlist=["ImageChops"])


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "cards" / "sunset-drive"
ASSETS = CARD / "assets"
WEB_ASSETS = ROOT / "web" / "assets" / "cards" / "sunset-drive"
CANVAS = (1024, 1536)


def person_mask(scene: Image.Image) -> np.ndarray:
    from rembg import new_session, remove

    session = new_session("u2net_human_seg")
    mask = remove(scene.convert("RGB"), session=session, only_mask=True)
    return np.asarray(mask.convert("L"))


def clean_subject(subject: Image.Image, background: Image.Image) -> Image.Image:
    scene = background.convert("RGBA")
    scene.alpha_composite(subject)
    person = person_mask(scene)

    alpha = np.asarray(subject.getchannel("A"))
    rgb = np.asarray(subject.convert("RGB"))

    # Roof/pillar copies and the rectangular paste surplus sit outside the
    # person segmentation; a small dilation keeps hair wisps the matte caught.
    keep = ndimage.binary_dilation(person > 128, iterations=2)
    alpha = np.where((alpha > 0) & keep, alpha, 0).astype(np.uint8)

    # The matte veiled the person at ~89% opacity, bleeding the reconstructed
    # plate through the face; near-opaque pixels should be fully opaque.
    alpha = np.where(alpha >= 200, 255, alpha).astype(np.uint8)
    alpha = np.where(alpha < 12, 0, alpha).astype(np.uint8)

    comp, _ = ndimage.label(alpha > 32)
    sizes = np.bincount(comp.ravel())
    sizes[0] = 0
    for i in range(1, len(sizes)):
        if 0 < sizes[i] < 4:
            alpha = np.where(comp == i, 0, alpha).astype(np.uint8)

    interior = ndimage.binary_erosion(alpha >= 200, iterations=2)
    _, indices = ndimage.distance_transform_edt(~interior, return_indices=True)
    clean_rgb = rgb[tuple(indices)]
    clean_rgb = np.where(interior[..., None], rgb, clean_rgb).astype(np.uint8)

    out = Image.fromarray(clean_rgb, "RGB").convert("RGBA")
    out.putalpha(Image.fromarray(alpha, "L"))
    return out


def strengthen_effects(effects: Image.Image) -> Image.Image:
    arr = np.asarray(effects.convert("RGBA")).copy()
    arr[..., 3] = np.clip(arr[..., 3].astype(np.int16) * 155 // 100, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def shadowed_text(text: Image.Image) -> Image.Image:
    alpha = text.getchannel("A")
    shadow = alpha.filter(ImageFilter.GaussianBlur(2.5))
    shadow_arr = (np.asarray(shadow).astype(np.int16) * 55 // 100).astype(np.uint8)
    base = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    shade = Image.new("RGBA", CANVAS, (46, 28, 16, 0))
    shade.putalpha(Image.fromarray(shadow_arr, "L"))
    base.alpha_composite(shade, (0, 2))
    base.alpha_composite(text)
    return base


def save(image: Image.Image, name: str) -> None:
    for directory in (ASSETS, WEB_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)
        image.save(directory / name)


def main() -> None:
    subject_in = Image.open(ASSETS / "subject.png")
    background = Image.open(ASSETS / "background.png")
    subject = clean_subject(subject_in, background)
    lineart = builder.lineart_layer(subject)
    effects = strengthen_effects(Image.open(ASSETS / "effects.png"))
    text = shadowed_text(Image.open(ASSETS / "text.png"))
    for image, name in (
        (subject, "subject.png"),
        (lineart, "lineart.png"),
        (effects, "effects.png"),
        (text, "text.png"),
    ):
        save(image, name)

    preview = background.convert("RGBA")
    preview.alpha_composite(subject)
    preview.alpha_composite(effects)
    preview.alpha_composite(text)
    (ROOT / "verification" / "sunset-preview.png").parent.mkdir(exist_ok=True)
    preview.save(ROOT / "verification" / "sunset-preview.png")

    provenance = json.loads((CARD / "provenance.json").read_text(encoding="utf-8"))
    provenance["refinement_2026_09_25"] = (
        "Intersected the GrabCut matte with a person-only segmentation of the composed "
        "scene to drop car-roof and window-pillar alpha fragments, pushed the ~89% veil "
        "over the person to full opacity, decontaminated fringe RGB from the nearest "
        "interior pixel, raised the dust plane alpha by 55%, and added a soft dark shadow "
        "under the typography for contrast against the bright sunset sky."
    )
    (CARD / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Refined sunset-drive assets at", CARD)


if __name__ == "__main__":
    main()
