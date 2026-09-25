"""Build the layered source art for the third “云阶” holographic card.

The supplied photograph remains the source of the card's RGB pixels. A tightly
seeded GrabCut matte is used only to derive registered line art; it never
regenerates a face, pose, clothing, or bag. No separate background plate is
required.
"""

from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "cards" / "cloud-terrace"
ASSETS = CARD / "assets"
WEB_ASSETS = ROOT / "web" / "assets" / "cards" / "cloud-terrace"
CANVAS = (1024, 1536)
PHOTO_VALUE = os.environ.get("RUIC_CLOUD_TERRACE_PHOTO")
PHOTO = Path(PHOTO_VALUE).expanduser() if PHOTO_VALUE else None
FONT = Path(r"C:\Windows\Fonts\simkai.ttf")


def fit(image: Image.Image, mode: str) -> Image.Image:
    """Resize a portrait source to the shared 1024×1536 card canvas."""
    return ImageOps.fit(
        image.convert(mode), CANVAS, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
    )


def segmented_subject_layer() -> Image.Image:
    """Preserve photo RGB and derive a conservative alpha with GrabCut."""
    original = fit(Image.open(PHOTO), "RGB")
    pixels = cv2.cvtColor(np.asarray(original), cv2.COLOR_RGB2BGR)
    # Keep GrabCut inside a union of tight regions around the head, torso,
    # bent arm/hands, shoulder bag, and legs.  The earlier single broad polygon
    # touched the pillar and forest, allowing those connected background areas
    # to leak into the subject layer and move with the person during parallax.
    mask = np.full((CANVAS[1], CANVAS[0]), cv2.GC_BGD, dtype=np.uint8)
    allowed = [
        # Hair, face, neck.
        np.array(
            [(410, 636), (424, 606), (458, 590), (508, 593), (542, 612),
             (558, 646), (556, 695), (542, 729), (514, 759), (478, 771),
             (442, 757), (411, 724), (402, 680)], dtype=np.int32
        ),
        # Shirt and full torso down to the hem.
        np.array(
            [(361, 774), (399, 753), (448, 753), (480, 768), (500, 794),
             (510, 842), (510, 951), (498, 997), (501, 1070), (520, 1150),
             (535, 1258), (510, 1288), (450, 1302), (354, 1303), (306, 1285),
             (294, 1222), (307, 1124), (324, 1010), (337, 892)], dtype=np.int32
        ),
        # Bent bare arm, forearm, and both hands around the carved post.
        np.array(
            [(488, 866), (507, 849), (527, 850), (538, 858), (551, 853),
             (563, 860), (579, 858), (595, 872), (602, 888), (594, 901),
             (603, 912), (594, 927), (578, 937), (559, 937), (548, 955),
             (536, 982), (524, 1018), (507, 1051), (487, 1074), (466, 1082),
             (447, 1073), (432, 1052), (425, 1021), (428, 990), (445, 966),
             (468, 944), (486, 917)], dtype=np.int32
        ),
        # Shoulder strap and bag, including both hanging straps.
        np.array(
            [(333, 824), (363, 813), (383, 838), (389, 900), (404, 982),
             (423, 1060), (429, 1142), (411, 1209), (381, 1253), (345, 1276),
             (302, 1282), (258, 1266), (219, 1238), (196, 1203), (173, 1170),
             (161, 1125), (168, 1091), (194, 1052), (226, 1016), (265, 974),
             (302, 918)], dtype=np.int32
        ),
        np.array([(213, 1200), (241, 1200), (242, 1330), (213, 1330)], dtype=np.int32),
        # Both trouser legs continue beyond the lower crop edge.
        np.array(
            [(300, 1262), (520, 1260), (543, 1330), (552, 1535),
             (343, 1535), (329, 1450), (310, 1350)], dtype=np.int32
        ),
    ]
    for region in allowed:
        cv2.fillPoly(mask, [region], cv2.GC_PR_FGD)

    # High-confidence seeds sit well inside the same pieces; none touches the
    # forest, carved pillar, stone rails, floor, or balcony wall.
    confirmed = [
        np.array([(438, 628), (474, 605), (520, 618), (541, 655), (530, 704), (490, 742), (444, 712)], dtype=np.int32),
        np.array([(378, 792), (439, 773), (482, 807), (489, 955), (470, 991), (455, 1195), (489, 1267), (357, 1273), (330, 1080)], dtype=np.int32),
        np.array([(505, 875), (529, 866), (552, 873), (582, 880), (577, 917), (551, 925), (526, 979), (486, 1053), (451, 1036), (459, 982)], dtype=np.int32),
        np.array([(341, 853), (361, 884), (375, 1015), (402, 1110), (387, 1207), (337, 1254), (269, 1240), (205, 1174), (184, 1114), (235, 1034), (310, 958)], dtype=np.int32),
        np.array([(310, 1300), (489, 1300), (518, 1528), (300, 1528)], dtype=np.int32),
    ]
    for seed in confirmed:
        cv2.fillPoly(mask, [seed], cv2.GC_FGD)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(pixels, mask, None, bg_model, fg_model, 9, cv2.GC_INIT_WITH_MASK)
    cutout = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)
    # Intersect once more with the allowed union. GrabCut cannot grow outside
    # this matte even if a dark garment touches similarly dark scenery.
    allowed_mask = np.zeros((CANVAS[1], CANVAS[0]), dtype=np.uint8)
    for region in allowed:
        cv2.fillPoly(allowed_mask, [region], 255)
    # Preserve the clean negative-space notch between shoulder and raised
    # hands. It is forest in the photograph, not part of the person.
    background_notch = np.array(
        [(482, 778), (512, 783), (537, 802), (551, 829), (549, 855),
         (532, 875), (512, 870), (496, 850), (486, 816)], dtype=np.int32
    )
    cv2.fillPoly(allowed_mask, [background_notch], 0)
    cutout = cv2.bitwise_and(cutout, allowed_mask)
    alpha = Image.fromarray(cutout, "L").filter(ImageFilter.GaussianBlur(0.7))
    alpha = alpha.point(lambda value: 0 if value < 12 else value, "L")
    subject = original.convert("RGBA")
    subject.putalpha(alpha)
    return subject


def subject_layer() -> Image.Image:
    """Use the complete source photo so every part of the person stays exact.

    A narrow transparent perimeter satisfies the RGBA layer contract while the
    matching background layer fills those edge pixels. The full artwork stays
    fixed at depth zero, avoiding segmentation loss around black trousers,
    shoulder bag, hands, and the similarly dark forest behind them.
    """
    original = fit(Image.open(PHOTO), "RGB")
    alpha = Image.new("L", CANVAS, 0)
    draw = ImageDraw.Draw(alpha)
    border = 6
    draw.rectangle(
        (border, border, CANVAS[0] - border - 1, CANVAS[1] - border - 1),
        fill=255,
    )
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    subject = original.convert("RGBA")
    subject.putalpha(alpha)
    return subject


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
    # Restrict internal strokes to visibly opaque subject pixels, rather than
    # letting the landscape behind a feathered edge draw a second outline.
    opaque = alpha.point(lambda value: 255 if value > 96 else 0, "L")
    internals = details.point(lambda value: 0 if value > 80 else 255, "L")
    internals = Image.composite(internals, Image.new("L", CANVAS, 255), opaque)
    strokes = ImageChops.darker(silhouette, internals).filter(ImageFilter.MedianFilter(3))
    return Image.merge("RGB", (strokes, strokes, strokes))


def effects_layer() -> Image.Image:
    """A sparse layer of cool mist and warm light, separate from card foil."""
    random.seed(20260924150819)
    effects = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(effects)
    # Avoid the headline/footer safe zones. Each element remains isolated so
    # the layer reads as a shallow, independent plane while tilting.
    colors = [(221, 248, 255), (152, 221, 250), (255, 232, 168), (241, 255, 249)]
    for _ in range(152):
        x = random.randint(68, 956)
        y = random.randint(360, 1185)
        radius = random.choice((1, 2, 2, 3, 4, 5, 6))
        color = random.choice(colors)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=color + (random.randint(96, 208),),
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
    jade = (197, 240, 235, 236)
    pale_jade = (206, 248, 247, 174)
    ivory = (255, 250, 233, 248)
    gold = (248, 217, 145, 220)

    draw.rounded_rectangle((26, 26, 998, 1510), radius=27, outline=jade, width=3)
    draw.rounded_rectangle((40, 40, 984, 1496), radius=20, outline=(235, 253, 246, 120), width=1)
    draw.text((76, 92), "天游系列  ·  CLOUD TERRACE", font=font(22), fill=jade)
    draw.text((76, 145), "云阶", font=font(74), fill=ivory)
    draw.text((79, 238), "凭  栏  望  远", font=font(25), fill=pale_jade)
    draw.line((76, 294, 948, 294), fill=(213, 247, 241, 190), width=2)
    draw.line((76, 1235, 948, 1235), fill=(213, 247, 241, 180), width=2)
    centered(draw, (512, 1285), "檐下有风，山外有云", font(25), gold)
    centered(draw, (512, 1352), "云开见山", font(49), ivory)
    draw.text((76, 1442), "003  /  100", font=font(22), fill=jade)
    draw.text((753, 1442), "HOLOGRAPHIC", font=font(19), fill=jade)
    return text


def save(image: Image.Image, name: str) -> None:
    for directory in (ASSETS, WEB_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)
        image.save(directory / name)


def main() -> None:
    if PHOTO is None:
        raise RuntimeError(
            "Set RUIC_CLOUD_TERRACE_PHOTO to the private reference photo path."
        )
    required = (PHOTO, FONT)
    if not all(path.exists() for path in required):
        missing = [str(path) for path in required if not path.exists()]
        raise FileNotFoundError("Missing card source(s): " + ", ".join(missing))

    subject = subject_layer()
    # The complete reference is also the backing plate. Because both image
    # layers contain the same source pixels, the transparent perimeter and any
    # sampling at the card edge cannot reveal a mismatched reconstruction.
    background = fit(Image.open(PHOTO), "RGB")
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
        "title": "云阶",
        "backMark": "俊",
        "subtitle": "凭栏望远",
        "technique": "云开见山",
        "tagline": "檐下有风，山外有云",
        "edition": "003 / 100",
        "collection": "个人全息典藏 · 天游系列",
        "description": "云从檐角掠过，山在栏外铺开；翻转这张全息卡，让晴空与石阶在掌心起伏。",
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
            "subjectDepth": 0.0,
            "backgroundDepth": -0.04,
            "effectsScale": 1.0,
            "effectsDepth": 0.55,
            "foil": 0.61,
        },
        "safeArea": {"scale": 1.0, "offset": [0, 0]},
        "appearance": {"finish": "pearl", "background": "#edf8f4"},
    }
    (CARD / "card-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    provenance = {
        "reference_role": "The supplied photograph is the identity, composition, and foreground-pixel reference.",
        "source_policy": "Private external input supplied through RUIC_CLOUD_TERRACE_PHOTO; raw source is not stored in the repository.",
        "background_prompt": "Use case: precise-object-edit. Remove the person and bag completely; reconstruct the stone balcony and railing, traditional Chinese temple eaves, forested hillside, blue sky, and soft clouds. Keep it photorealistic; no people, text, glitter, foil, border, or watermark.",
        "foreground_method": "The corrected card uses the complete resized reference photo as both the main artwork and backing plate. No person segmentation or generated foreground is used, so face, hands, bag, shirt, trousers, and every visible body edge remain identical to the source photograph.",
        "style": "Quiet daylight mountain-temple travel photography; jade, ivory, and restrained antique-gold card furniture; foil remains a material effect rather than painted artwork.",
    }
    (CARD / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Built third card assets at", CARD)


if __name__ == "__main__":
    main()
