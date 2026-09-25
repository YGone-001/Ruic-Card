"""Build the layered source art for the second "暮途" holographic card.

The supplied photograph remains the source of the foreground pixels.  The
generated silhouette is used only as an alpha guide, so the subject is not
silently re-illustrated or substituted.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "cards" / "sunset-drive"
ASSETS = CARD / "assets"
WEB_ASSETS = ROOT / "web" / "assets" / "cards" / "sunset-drive"
CANVAS = (1024, 1536)
PHOTO_VALUE = os.environ.get("RUIC_SUNSET_DRIVE_PHOTO")
BACKGROUND_VALUE = os.environ.get("RUIC_SUNSET_DRIVE_BACKGROUND")
PHOTO = Path(PHOTO_VALUE).expanduser() if PHOTO_VALUE else None
BACKGROUND = Path(BACKGROUND_VALUE).expanduser() if BACKGROUND_VALUE else None
FONT = Path(r"C:\Windows\Fonts\simkai.ttf")


def fit(image: Image.Image, mode: str) -> Image.Image:
    """Resize a same-ratio portrait to the shared card canvas."""
    return image.convert(mode).resize(CANVAS, Image.Resampling.LANCZOS)


def subject_layer() -> Image.Image:
    original = fit(Image.open(PHOTO), "RGB")

    # The generated silhouette guide was useful to check the intended extent,
    # but its face was not registered pixel-for-pixel to the reference.  A
    # seeded GrabCut pass works from the actual reference RGB pixels instead:
    # hard background/foreground seeds are deliberately conservative and the
    # resulting edge is softened only after segmentation.
    pixels = cv2.cvtColor(np.asarray(original), cv2.COLOR_RGB2BGR)
    mask = np.full((CANVAS[1], CANVAS[0]), cv2.GC_PR_BGD, dtype=np.uint8)
    mask[:80, :] = cv2.GC_BGD
    mask[:1280, :56] = cv2.GC_BGD
    mask[:760, 984:] = cv2.GC_BGD
    subject_outline = np.array(
        [
            (320, 280), (365, 165), (485, 92), (640, 86), (770, 120),
            (858, 205), (888, 330), (872, 460), (825, 595), (820, 700),
            (915, 770), (1023, 825), (1023, 1535), (0, 1535), (0, 1430),
            (70, 1345), (135, 1230), (195, 1110), (244, 990), (275, 875),
            (294, 790), (300, 723), (286, 674), (270, 628), (272, 577),
            (254, 545), (273, 508), (280, 460), (300, 396),
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(mask, [subject_outline], cv2.GC_PR_FGD)
    confirmed_head = np.array(
        [
            (365, 225), (455, 140), (645, 122), (790, 180), (846, 300),
            (830, 445), (765, 585), (630, 720), (470, 750), (350, 655),
            (306, 520), (320, 350),
        ],
        dtype=np.int32,
    )
    confirmed_body = np.array(
        [
            (420, 790), (650, 720), (850, 760), (1000, 850), (1023, 1535),
            (0, 1535), (54, 1410), (135, 1260), (220, 1115), (300, 940),
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(mask, [confirmed_head, confirmed_body], cv2.GC_FGD)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(pixels, mask, None, bg_model, fg_model, 7, cv2.GC_INIT_WITH_MASK)
    cutout = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)
    alpha = Image.fromarray(cutout, "L").filter(ImageFilter.GaussianBlur(0.8))
    subject = original.copy()
    subject.putalpha(alpha)
    return subject


def lineart_layer(subject: Image.Image) -> Image.Image:
    """Dark contour strokes on white, derived from the finished subject layer."""
    alpha = subject.getchannel("A")
    silhouette = alpha.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    detail_source = Image.new("RGB", CANVAS, "white")
    detail_source.paste(subject.convert("RGB"), mask=alpha)
    details = detail_source.convert("L").filter(ImageFilter.GaussianBlur(1.0)).filter(
        ImageFilter.FIND_EDGES
    )
    outline = silhouette.point(lambda value: 0 if value > 18 else 255, "L")
    internal = details.point(lambda value: 0 if value > 64 else 255, "L")
    alpha_limit = alpha.point(lambda value: 255 if value > 80 else 0, "L")
    internal = Image.composite(internal, Image.new("L", CANVAS, 255), alpha_limit)
    strokes = ImageChops.darker(outline, internal).filter(ImageFilter.MedianFilter(3))
    return Image.merge("RGB", (strokes, strokes, strokes))


def effects_layer() -> Image.Image:
    random.seed(20260924)
    effects = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(effects)
    colors = [(255, 225, 168), (255, 190, 112), (255, 242, 211), (246, 136, 74)]
    # Keep the top and bottom typography zones quiet while the particles read
    # as a separate, sparse pane around the figure.
    for _ in range(104):
        x = random.randint(55, CANVAS[0] - 55)
        y = random.randint(325, 1215)
        radius = random.choice((1, 2, 2, 3, 3, 4, 5, 7))
        color = random.choice(colors)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=color + (random.randint(66, 164),),
        )
    for _ in range(5):
        x = random.randint(110, CANVAS[0] - 110)
        y = random.randint(390, 1090)
        radius = random.randint(20, 44)
        glow = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse(
            (4, 4, radius * 2 - 4, radius * 2 - 4),
            fill=random.choice(colors) + (36,),
        )
        effects.alpha_composite(glow.filter(ImageFilter.GaussianBlur(7)), (x - radius, y - radius))
    return effects.filter(ImageFilter.GaussianBlur(0.35))


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size=size)


def centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, font_: ImageFont.FreeTypeFont, fill: tuple[int, ...]) -> None:
    draw.text(xy, value, font=font_, fill=fill, anchor="ma")


def text_layer() -> Image.Image:
    text = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text)
    gold = (255, 226, 159, 242)
    faint_gold = (255, 226, 159, 185)
    ivory = (255, 245, 226, 246)

    draw.rounded_rectangle((26, 26, 998, 1510), radius=27, outline=(255, 224, 151, 224), width=3)
    draw.rounded_rectangle((39, 39, 985, 1497), radius=20, outline=(255, 243, 215, 142), width=1)
    draw.text((76, 92), "行车系列  ·  SUNSET DRIVE", font=font(22), fill=gold)
    draw.text((76, 145), "暮途", font=font(74), fill=ivory)
    draw.text((79, 238), "落  日  慕  思", font=font(25), fill=faint_gold)
    draw.line((76, 294, 948, 294), fill=(255, 222, 149, 206), width=2)
    draw.line((76, 1235, 948, 1235), fill=(255, 222, 149, 192), width=2)
    centered(draw, (512, 1285), "天色渐暗，路还在向前", font(25), gold)
    centered(draw, (512, 1352), "向光而行", font(49), ivory)
    draw.text((76, 1442), "002  /  100", font=font(22), fill=gold)
    draw.text((753, 1442), "HOLOGRAPHIC", font=font(19), fill=gold)
    return text


def save(image: Image.Image, name: str) -> None:
    for directory in (ASSETS, WEB_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)
        image.save(directory / name)


def main() -> None:
    if PHOTO is None or BACKGROUND is None:
        raise RuntimeError(
            "Set RUIC_SUNSET_DRIVE_PHOTO and RUIC_SUNSET_DRIVE_BACKGROUND "
            "to private source image paths."
        )
    if not all(path.exists() for path in (PHOTO, BACKGROUND, FONT)):
        missing = [str(path) for path in (PHOTO, BACKGROUND, FONT) if not path.exists()]
        raise FileNotFoundError("Missing card source(s): " + ", ".join(missing))
    subject = subject_layer()
    background = fit(Image.open(BACKGROUND), "RGB")
    lineart = lineart_layer(subject)
    effects = effects_layer()
    text = text_layer()
    save(subject, "subject.png")
    save(background, "background.png")
    save(lineart, "lineart.png")
    save(effects, "effects.png")
    save(text, "text.png")

    # A flat inspection render is intentionally only a QA artifact: the live
    # card supplies foil and depth in its material/shader instead of baking
    # either effect into these layers.
    preview = background.convert("RGBA")
    preview.alpha_composite(subject)
    preview.alpha_composite(effects)
    preview.alpha_composite(text)
    preview.save(CARD / "preview-composite.png")

    config = {
        "title": "暮途",
        "backMark": "博",
        "subtitle": "落日慕思",
        "technique": "向光而行",
        "tagline": "天色渐暗，路还在向前",
        "edition": "002 / 100",
        "collection": "个人全息典藏 · 行车系列",
        "description": "夕阳停在镜片与车窗之间；翻转这张全息卡，让行驶中的光从掌心掠过。",
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
            "subjectScale": 1.05,
            "subjectDepth": 0.38,
            "backgroundDepth": -0.22,
            "effectsScale": 1.0,
            "effectsDepth": 0.58,
            "foil": 0.64,
        },
        "safeArea": {"scale": 1.0, "offset": [0, 0]},
    }
    CARD.mkdir(parents=True, exist_ok=True)
    (CARD / "card-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    provenance = {
        "reference_role": "The supplied photograph is the identity, composition, and foreground-pixel reference.",
        "background_prompt": "Remove the seated man and reconstruct only the same car interior, window, sunset sky, sun, distant landscape, dashboard, and seat; no people or text.",
        "mask_prompt": "Create a high-contrast person silhouette guide at the original framing for an extraction QA reference.",
        "foreground_method": "Original-photo RGB pixels and a seeded segmentation pass; no regenerated face or clothing is used in the final subject layer.",
    }
    (CARD / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Built second card assets at", CARD)


if __name__ == "__main__":
    # Imported here to keep the top-level dependency list obvious in the rest
    # of the script and avoid an accidental image operation without Pillow.
    from PIL import ImageChops

    main()
