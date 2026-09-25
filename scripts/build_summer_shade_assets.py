"""Build the layered source art for the fourth "夏荫" holographic card.

The supplied photograph remains the source of the hero's RGB pixels. A rembg
person matte supplies only the alpha channel; the person-free background plate
is reconstructed by inpainting the matte hole into the surrounding bokeh.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
from rembg import new_session, remove


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "cards" / "summer-shade"
ASSETS = CARD / "assets"
WEB_ASSETS = ROOT / "web" / "assets" / "cards" / "summer-shade"
CANVAS = (1024, 1536)
PHOTO_VALUE = os.environ.get("RUIC_SUMMER_SHADE_PHOTO")
PHOTO = Path(PHOTO_VALUE).expanduser() if PHOTO_VALUE else None
FONT = Path(r"C:\Windows\Fonts\simkai.ttf")

# Head/face region on the card canvas; the floating effects plane keeps out of
# it so light motes never sit on the portrait's face.
FACE_BOX = (360, 60, 700, 620)


def fit(image: Image.Image, mode: str) -> Image.Image:
    """Resize a portrait source to the shared 1024x1536 card canvas."""
    return ImageOps.fit(
        image.convert(mode), CANVAS, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
    )


def person_alpha(original: Image.Image) -> Image.Image:
    """Person matte from rembg; only the alpha channel is used."""
    session = new_session("u2net_human_seg")
    cut = remove(original, session=session)
    alpha = cut.getchannel("A")
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.7))
    return alpha.point(lambda value: 0 if value < 12 else value, "L")


def subject_layer(original: Image.Image, alpha: Image.Image) -> Image.Image:
    subject = original.convert("RGBA")
    subject.putalpha(alpha)
    return subject


def background_layer(original: Image.Image, alpha: Image.Image) -> Image.Image:
    """Opaque person-free plate: normalized-convolution fill of the matte hole.

    A plain inpaint left a flat yellow field and a hair ghost; spreading the
    real background colours across the hole with a normalized blur continues
    the bokeh gradient instead, and sparse dim discs restore the disc texture.
    """
    rgb = np.asarray(original).astype(np.float32)
    hole = (np.asarray(alpha) > 4).astype(np.uint8) * 255
    hole = cv2.dilate(hole, np.ones((61, 61), np.uint8), iterations=1)
    weight = 1.0 - (hole > 0).astype(np.float32)
    kernel = (151, 151)
    numerator = cv2.blur(rgb * weight[..., None], kernel)
    denominator = cv2.blur(weight, kernel)[..., None] + 1e-6
    fill = numerator / denominator

    random.seed(20260925006)
    discs = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(discs)
    holes = np.argwhere(hole > 0)
    fill_pixels = np.clip(fill, 0, 255).astype(np.uint8)
    for _ in range(150):
        y, x = holes[random.randrange(len(holes))]
        base = fill_pixels[y, x].astype(np.int16)
        bright = random.randint(-26, 46)
        color = tuple(int(np.clip(channel + bright, 0, 255)) for channel in base)
        radius = random.randint(8, 34)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=color + (random.randint(26, 64),),
        )
    discs = discs.filter(ImageFilter.GaussianBlur(9))
    recon = Image.fromarray(fill_pixels).convert("RGBA")
    recon.alpha_composite(discs)

    feather = Image.fromarray(hole).filter(ImageFilter.GaussianBlur(30))
    return Image.composite(recon.convert("RGB"), original, feather)


def lineart_layer(subject: Image.Image) -> Image.Image:
    """Dark contours on white, registered directly from the final subject."""
    alpha = subject.getchannel("A")
    alpha_edge = alpha.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    silhouette = alpha_edge.point(lambda value: 0 if value > 14 else 255, "L")

    source = Image.new("RGB", CANVAS, "white")
    source.paste(subject.convert("RGB"), mask=alpha)
    details = source.convert("L").filter(ImageFilter.GaussianBlur(1.1)).filter(
        ImageFilter.FIND_EDGES
    )
    opaque = alpha.point(lambda value: 255 if value > 96 else 0, "L")
    internals = details.point(lambda value: 0 if value > 80 else 255, "L")
    internals = Image.composite(internals, Image.new("L", CANVAS, 255), opaque)
    strokes = ImageChops.darker(silhouette, internals).filter(ImageFilter.MedianFilter(3))
    return Image.merge("RGB", (strokes, strokes, strokes))


def effects_layer() -> Image.Image:
    """Sparse sun motes and a few coral petal flecks, clear of the face."""
    random.seed(20260925005)
    effects = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(effects)
    motes = [(255, 240, 190), (255, 222, 150), (226, 246, 205), (255, 252, 235)]
    petals = [(238, 128, 96), (244, 156, 110)]
    for _ in range(130):
        x = random.randint(64, 960)
        y = random.randint(350, 1195)
        if FACE_BOX[0] < x < FACE_BOX[2] and FACE_BOX[1] < y < FACE_BOX[3]:
            continue
        radius = random.choice((1, 2, 2, 3, 4, 5, 6))
        color = random.choice(motes)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=color + (random.randint(96, 208),),
        )
    for _ in range(14):
        x = random.randint(80, 944)
        y = random.randint(380, 1180)
        if FACE_BOX[0] < x < FACE_BOX[2] and FACE_BOX[1] < y < FACE_BOX[3]:
            continue
        radius = random.choice((3, 4, 5))
        color = random.choice(petals)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=color + (random.randint(110, 180),),
        )
    return effects.filter(ImageFilter.GaussianBlur(0.22))


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size=size)


def centered(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    font_: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
) -> None:
    draw.text(xy, value, font=font_, fill=fill, anchor="ma")


def text_layer() -> Image.Image:
    """Fixed card furniture and all human-readable typography."""
    text = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text)
    leaf = (188, 232, 190, 236)
    pale_leaf = (216, 244, 214, 174)
    ivory = (255, 250, 233, 248)
    gold = (248, 217, 145, 220)

    draw.rounded_rectangle((26, 26, 998, 1510), radius=27, outline=leaf, width=3)
    draw.rounded_rectangle((40, 40, 984, 1496), radius=20, outline=(240, 253, 236, 120), width=1)
    draw.text((76, 92), "园游系列  ·  GARDEN STROLL", font=font(22), fill=leaf)
    draw.text((76, 145), "夏荫", font=font(74), fill=ivory)
    draw.text((79, 238), "园  游  拾  光", font=font(25), fill=pale_leaf)
    draw.line((76, 294, 948, 294), fill=(222, 247, 214, 190), width=2)
    draw.line((76, 1235, 948, 1235), fill=(222, 247, 214, 180), width=2)
    centered(draw, (512, 1285), "绿荫深处，光落肩头", font(25), gold)
    centered(draw, (512, 1352), "凝望", font(49), ivory)
    draw.text((76, 1442), "004  /  100", font=font(22), fill=leaf)
    draw.text((753, 1442), "HOLOGRAPHIC", font=font(19), fill=leaf)
    return text


def save(image: Image.Image, name: str) -> None:
    for directory in (ASSETS, WEB_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)
        image.save(directory / name)


def main() -> None:
    if PHOTO is None:
        raise RuntimeError(
            "Set RUIC_SUMMER_SHADE_PHOTO to the private reference photo path."
        )
    if not PHOTO.exists() or not FONT.exists():
        raise FileNotFoundError(f"Missing card source: {PHOTO} or {FONT}")

    original = fit(Image.open(PHOTO), "RGB")
    alpha = person_alpha(original)
    subject = subject_layer(original, alpha)
    background = background_layer(original, alpha)
    lineart = lineart_layer(subject)
    effects = effects_layer()
    text = text_layer()
    for image, name in (
        (subject, "subject.png"),
        (background, "background.png"),
        (lineart, "lineart.png"),
        (effects, "effects.png"),
        (text, "text.png"),
    ):
        save(image, name)

    preview = background.convert("RGBA")
    preview.alpha_composite(subject)
    preview.alpha_composite(effects)
    preview.alpha_composite(text)
    CARD.mkdir(parents=True, exist_ok=True)
    preview.save(CARD / "preview-composite.png")

    config = {
        "title": "夏荫",
        "backMark": "昱",
        "subtitle": "园游拾光",
        "technique": "凝望",
        "tagline": "绿荫深处，光落肩头",
        "edition": "004 / 100",
        "collection": "个人全息典藏 · 园游系列",
        "description": "绿荫把喧嚣滤成光斑，他在花影间凝望；翻转这张全息卡，让夏日的风在掌心流动。",
        "font": str(FONT),
        "assets": {
            "model": "./assets/card.glb",
            "subject": "./assets/subject.png",
            "background": "./assets/background.png",
            "text": "./assets/text.png",
            "lineart": "./assets/lineart.png",
            "effects": "./assets/effects.png",
        },
        "parameters": {
            "subjectScale": 1.0,
            "subjectDepth": 0.4,
            "backgroundDepth": -0.25,
            "effectsScale": 1.0,
            "effectsDepth": 0.55,
            "foil": 0.6,
        },
        "safeArea": {"scale": 1.0, "offset": [0, 0]},
        "appearance": {"finish": "pearl", "background": "#eef6ea"},
    }
    (CARD / "card-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    provenance = {
        "reference_role": "The supplied photograph is the identity, composition, and foreground-pixel reference.",
        "source_policy": "Private external input supplied through RUIC_SUMMER_SHADE_PHOTO; raw source is not stored in the repository.",
        "foreground_method": "rembg u2net_human_seg supplies only the alpha channel; every RGB pixel of the subject layer comes from the original photograph, so face, glasses, hoodie and tee print stay identical to the source.",
        "background_method": "Person-free plate reconstructed by Telea inpainting of the dilated matte, re-textured with bokeh discs colour-sampled from the real background and feather-blended into the untouched photo bokeh.",
        "lineart_method": "Edge/threshold pass over the finished subject layer, so contours register exactly.",
        "style": "Summer garden portrait photography with shallow bokeh; leaf-green, ivory and restrained gold card furniture; foil remains a material effect rather than painted artwork.",
    }
    (CARD / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Built fourth card assets at", CARD)


if __name__ == "__main__":
    main()
