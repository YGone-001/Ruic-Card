# -*- coding: utf-8 -*-
"""Post-process generated layers into skill-ready assets.

1. subject: the generator painted a *soft-gradient* light checkerboard (board
   tones 223-253 overlap the jacket highlights), so the skill's 2-tone
   converter can't lock on (coverage 0.76 < 0.80, tone_split 28 < TOL 32).
   Key it out instead: neutral-bright board test + border-connected component
   flood + interior hole fill. Deterministic, no AI matting.
2. background: clone-patch the generator watermark in the bottom-right corner.
3. lineart: edge/threshold pass over the FINISHED positioned subject (registration!).
4. effects: sparse procedural dust motes on transparent canvas.
"""
import os, random
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageOps
from scipy import ndimage

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = os.path.join(REPO_ROOT, "cards", "brick-gap")
GEN = os.environ.get("RUIC_BRICK_GAP_SOURCE_DIR")
if not GEN:
    raise RuntimeError(
        "Set RUIC_BRICK_GAP_SOURCE_DIR to the private directory containing "
        "the generated subject and background inputs."
    )
GEN = os.path.abspath(os.path.expanduser(GEN))
AST = os.path.join(CARD, "assets")
W, H = 1024, 1536

SUBJ_SRC = os.path.join(GEN, "Create_a_clean_cutout_of_the_y_2026-09-23T16-11-48.png")
BG_SRC = os.path.join(GEN, "Edit_this_photo__completely_re_2026-09-23T16-11-27.png")

# ---------------------------------------------------------------- subject ----
rgb = np.asarray(Image.open(SUBJ_SRC).convert("RGB")).astype(np.int16)
mn = rgb.min(axis=2)
mx = rgb.max(axis=2)
spread = mx - mn
# Board: bright AND neutral. Jacket is dimmer/warmer, hair/skin far darker.
board_like = (mn >= 219) & (spread <= 12)
lab, n = ndimage.label(board_like)
border_labels = np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))
border_labels = border_labels[(border_labels > 0)]
board = np.isin(lab, border_labels)
print("board fraction: %.4f (board_like %.4f)" % (board.mean(), board_like.mean()))

fig = ~board
fig = ndimage.binary_fill_holes(fig)                 # re-fill any flooded pinholes
comp, nc = ndimage.label(fig)
sizes = np.bincount(comp.ravel())
sizes[0] = 0
keep = [i for i in range(1, nc + 1) if sizes[i] >= max(4000, sizes.max() * 0.02)]
print("figure components kept:", [(i, int(sizes[i])) for i in keep], "of", nc)
fig = np.isin(comp, keep)

alpha_f = (fig * 255).astype(np.uint8)
a_img = Image.fromarray(alpha_f, "L").filter(ImageFilter.GaussianBlur(1.1))
solid = ndimage.binary_erosion(fig, iterations=2)
a_final = np.minimum(np.asarray(a_img), (solid * 255).astype(np.uint8))
rgba = np.dstack([rgb.astype(np.uint8), a_final])
subj = Image.fromarray(rgba, "RGBA")
bbox = subj.getchannel("A").getbbox()
print("subject bbox:", bbox)

# Mirror so the gaze matches the reference photo (frame-left), then compose.
subj = subj.transpose(Image.FLIP_LEFT_RIGHT)
a = subj.getchannel("A")
bbox = a.getbbox()
fig_img = subj.crop(bbox)
fw, fh = fig_img.size
# Drop the bottom of the source figure: the generator left a blocky hand
# artifact there (starts ~src y1432). Crop at 1042 keeps head->forearm clean.
keep_h = min(fh, 1042)
fig_img = fig_img.crop((0, 0, fw, keep_h))
# Scale so the cropped figure runs just past the card bottom edge: the cut
# line hides off-canvas (head-top y=320 -> bottom ~y1544).
target_h = 1224
scale = target_h / keep_h
new = fig_img.resize((max(1, round(fw * scale)), target_h), Image.LANCZOS)
canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
px, py = 430 - new.width // 2, 320
canvas.alpha_composite(new, (px, py))
canvas.save(os.path.join(AST, "subject.png"))
print("subject.png saved, fig size", new.size, "pos", (px, py))

# ------------------------------------------------------------ background ----
bg = Image.open(BG_SRC).convert("RGB")
patch_src = bg.crop((560, 1440, 790, 1536))          # clean texture left of the watermark
patch = patch_src.resize((240, 96), Image.LANCZOS)
mask = Image.new("L", patch.size, 0)
md = ImageDraw.Draw(mask)
md.rounded_rectangle((6, 6, patch.width - 6, patch.height - 6), radius=18, fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(6))
bg.paste(patch, (784, 1440), mask)
bg.save(os.path.join(AST, "background.png"))
print("background.png saved")

# --------------------------------------------------------------- lineart ----
# Dark contours on white, derived from the FINISHED positioned subject so the
# glow registers. Silhouette stroke from the alpha edge (clean, closed) plus
# interior detail edges from luminance (folds, jawline, hair mass).
alpha_np = np.asarray(canvas.getchannel("A")).astype(np.int16)
sil = Image.fromarray(((alpha_np > 40) * 255).astype(np.uint8), "L")
edge_a = sil.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.6))
flat = Image.new("RGBA", (W, H), (255, 255, 255, 255))
flat.alpha_composite(canvas)
lum = flat.convert("L")
edge_g = lum.filter(ImageFilter.GaussianBlur(1.4)).filter(ImageFilter.FIND_EDGES)
ea = np.asarray(edge_a).astype(np.int16)
eg = np.asarray(edge_g).astype(np.int16)
combined = np.maximum(ea, eg // 2)                    # silhouette wins, detail supports
strokes_np = np.where(combined > 34, 0, 255).astype(np.uint8)
strokes_np[:4, :] = 255; strokes_np[-4:, :] = 255     # kill the canvas-border artifact
strokes_np[:, :4] = 255; strokes_np[:, -4:] = 255
strokes = Image.fromarray(strokes_np, "L")
strokes = strokes.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.MinFilter(3))
lineart = Image.merge("RGB", (strokes, strokes, strokes))
lineart.save(os.path.join(AST, "lineart.png"))
print("lineart.png saved, extrema:", strokes.getextrema(),
      "dark px: %.4f" % ((strokes_np < 128).mean()))

# --------------------------------------------------------------- effects ----
random.seed(1239)
fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
fd = ImageDraw.Draw(fx)
warm = [(255, 236, 200), (255, 214, 170), (255, 245, 225), (250, 200, 160)]
for _ in range(110):
    x, y = random.randint(60, W - 60), random.randint(120, 1240)
    r = random.choice([2, 3, 3, 4, 4, 5, 6, 8, 10])
    col = random.choice(warm)
    fd.ellipse((x - r, y - r, x + r, y + r), fill=col + (random.randint(90, 175),))
for _ in range(6):
    x, y = random.randint(90, W - 90), random.randint(180, 1150)
    r = random.randint(26, 60)
    glow = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((4, 4, r * 2 - 4, r * 2 - 4), fill=(255, 232, 198, 46))
    glow = glow.filter(ImageFilter.GaussianBlur(9))
    fx.alpha_composite(glow, (x - r, y - r))
fx = fx.filter(ImageFilter.GaussianBlur(0.6))
fx.save(os.path.join(AST, "effects.png"))
print("effects.png saved")
print("ALL DONE")
