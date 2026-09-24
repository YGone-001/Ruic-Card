"""Quiet the particle layer in the card's typography and portrait focal zones."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    value = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return value * value * (3.0 - 2.0 * value)


def attenuation(x: float, y: float) -> float:
    """Keep the corners lively while protecting type and the subject's face."""
    top = 0.18 + 0.82 * smoothstep(0.025, 0.19, y)
    bottom = 0.24 + 0.76 * (1.0 - smoothstep(0.78, 0.965, y))

    # Soft elliptical mask around the face in the source's shared 2:3 frame.
    portrait = ((x - 0.45) / 0.22) ** 2 + ((y - 0.35) / 0.21) ** 2
    face = 0.16 + 0.84 * smoothstep(0.68, 1.14, portrait)
    return top * bottom * face


def soften(project: Path) -> Path:
    path = project / "assets" / "effects.png"
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    pixels = image.load()

    for row in range(height):
        y = row / max(1, height - 1)
        for column in range(width):
            red, green, blue, alpha = pixels[column, row]
            if alpha:
                x = column / max(1, width - 1)
                pixels[column, row] = (
                    red,
                    green,
                    blue,
                    round(alpha * attenuation(x, y)),
                )

    image.save(path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(soften(args.project))
