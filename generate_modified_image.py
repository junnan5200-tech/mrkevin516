from __future__ import annotations

import math
import random
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFilter


WIDTH = 503
HEIGHT = 1191
TARGET_BLUE = "#bbe1f5"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def blend(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def polygon_bounds(points: Iterable[tuple[float, float]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def gradient_fill(
    image: Image.Image,
    polygon: list[tuple[float, float]],
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
) -> None:
    left, top, right, bottom = polygon_bounds(polygon)
    width = max(1, right - left + 1)
    height = max(1, bottom - top + 1)

    grad = Image.new("RGBA", (width, height))
    grad_px = grad.load()
    for y in range(height):
        t = y / max(1, height - 1)
        color = blend(top_color, bottom_color, t)
        for x in range(width):
            grad_px[x, y] = (*color, 255)

    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    local_polygon = [(x - left, y - top) for x, y in polygon]
    mask_draw.polygon(local_polygon, fill=255)
    image.paste(grad, (left, top), mask)


def add_noise(
    image: Image.Image,
    polygon: list[tuple[float, float]],
    color: tuple[int, int, int],
    count: int,
    radius: int,
    opacity: int,
    seed: int,
) -> None:
    rng = random.Random(seed)
    left, top, right, bottom = polygon_bounds(polygon)
    mask = Image.new("L", (right - left + 1, bottom - top + 1), 0)
    mask_draw = ImageDraw.Draw(mask)
    local_polygon = [(x - left, y - top) for x, y in polygon]
    mask_draw.polygon(local_polygon, fill=255)

    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(count):
        x = rng.randint(left, right)
        y = rng.randint(top, bottom)
        r = rng.randint(max(1, radius // 2), radius)
        bbox = (x - r, y - r, x + r, y + r)
        draw.ellipse(bbox, fill=(*color, opacity))

    clipped = Image.new("RGBA", image.size, (0, 0, 0, 0))
    global_mask = Image.new("L", image.size, 0)
    global_mask.paste(mask, (left, top))
    clipped.paste(layer, (0, 0), global_mask)
    image.alpha_composite(clipped)


def add_shadow(
    image: Image.Image,
    polygon: list[tuple[float, float]],
    offset: tuple[int, int] = (10, 16),
    blur: int = 18,
    opacity: int = 65,
) -> None:
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    shifted = [(x + offset[0], y + offset[1]) for x, y in polygon]
    draw.polygon(shifted, fill=(0, 0, 0, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    image.alpha_composite(shadow)


def draw_prism(
    image: Image.Image,
    front: list[tuple[float, float]],
    top_offset: tuple[int, int],
    front_top: tuple[int, int, int],
    front_bottom: tuple[int, int, int],
    top_top: tuple[int, int, int],
    top_bottom: tuple[int, int, int],
    side_top: tuple[int, int, int],
    side_bottom: tuple[int, int, int],
    outline: tuple[int, int, int] = (120, 120, 120),
    shadow: bool = True,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]]]:
    top = [(x + top_offset[0], y + top_offset[1]) for x, y in front]
    top_face = [top[0], top[1], front[1], front[0]]
    right_face = [top[1], top[2], front[2], front[1]]

    if shadow:
        add_shadow(image, front + top[:2][::-1] + [top[3], top[0]], opacity=55)

    gradient_fill(image, top_face, top_top, top_bottom)
    gradient_fill(image, right_face, side_top, side_bottom)
    gradient_fill(image, front, front_top, front_bottom)

    draw = ImageDraw.Draw(image)
    draw.line(top + [top[0]], fill=outline, width=2)
    draw.line(front + [front[0]], fill=outline, width=2)
    for p1, p2 in zip(top, front):
        draw.line([p1, p2], fill=outline, width=2)

    return top, top_face, right_face


def draw_honeycomb_front(image: Image.Image, polygon: list[tuple[float, float]]) -> None:
    left, top, right, bottom = polygon_bounds(polygon)
    width = right - left
    height = bottom - top

    mask = Image.new("L", (width + 1, height + 1), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.polygon([(x - left, y - top) for x, y in polygon], fill=255)

    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    step = 54
    rows = math.ceil(height / 50) + 2
    cols = math.ceil(width / step) + 3

    for row in range(rows):
        cy = top + 18 + row * 48
        offset = 0 if row % 2 == 0 else step // 2
        for col in range(cols):
            cx = left - 20 + offset + col * step
            pts = [
                (cx - 18, cy),
                (cx - 9, cy - 16),
                (cx + 9, cy - 16),
                (cx + 18, cy),
                (cx + 9, cy + 16),
                (cx - 9, cy + 16),
                (cx - 18, cy),
            ]
            draw.line(pts, fill=(55, 55, 55, 220), width=3)

    clipped = Image.new("RGBA", image.size, (0, 0, 0, 0))
    global_mask = Image.new("L", image.size, 0)
    global_mask.paste(mask, (left, top))
    clipped.paste(layer, (0, 0), global_mask)
    image.alpha_composite(clipped)


def main() -> None:
    base = Image.new("RGBA", (WIDTH, HEIGHT), (251, 251, 251, 255))
    draw = ImageDraw.Draw(base)

    # Top green cover panel.
    top_panel = [(18, 125), (430, 96), (487, 108), (77, 137)]
    add_shadow(base, top_panel, offset=(8, 10), blur=12, opacity=40)
    gradient_fill(base, top_panel, (20, 120, 118), (14, 95, 96))
    draw.line(top_panel + [top_panel[0]], fill=(36, 92, 96), width=2)
    for ratio in (0.2, 0.48, 0.75):
        x1 = lerp(top_panel[0][0], top_panel[1][0], ratio)
        y1 = lerp(top_panel[0][1], top_panel[1][1], ratio)
        x2 = lerp(top_panel[3][0], top_panel[2][0], ratio)
        y2 = lerp(top_panel[3][1], top_panel[2][1], ratio)
        draw.line([(x1, y1), (x2, y2)], fill=(45, 95, 97), width=3)
    for i in range(16):
        t = i / 15
        y1 = lerp(top_panel[0][1], top_panel[3][1], t)
        y2 = lerp(top_panel[1][1], top_panel[2][1], t)
        x1 = lerp(top_panel[0][0], top_panel[3][0], t)
        x2 = lerp(top_panel[1][0], top_panel[2][0], t)
        draw.line([(x1, y1), (x2, y2)], fill=(120, 198, 194), width=1)

    # Metallic sheet.
    sheet_front = [(27, 363), (456, 363), (456, 422), (27, 422)]
    top, _, _ = draw_prism(
        base,
        sheet_front,
        (6, -7),
        front_top=(235, 238, 240),
        front_bottom=(206, 211, 215),
        top_top=(247, 247, 248),
        top_bottom=(224, 227, 229),
        side_top=(205, 210, 214),
        side_bottom=(183, 188, 192),
        outline=(182, 188, 194),
        shadow=False,
    )
    add_noise(base, sheet_front, (255, 255, 255), count=40, radius=18, opacity=18, seed=1)

    blue = hex_to_rgb(TARGET_BLUE)
    blue_top = blue
    blue_bottom = blue
    blue_side_top = blend(blue, (180, 206, 225), 0.15)
    blue_side_bottom = blend(blue, (150, 185, 210), 0.25)

    # Upper changed block (倒数第四块).
    upper_block_front = [(30, 503), (458, 503), (458, 581), (30, 581)]
    draw_prism(
        base,
        upper_block_front,
        (18, -19),
        front_top=blue_top,
        front_bottom=blue_bottom,
        top_top=blend(blue, (255, 255, 255), 0.15),
        top_bottom=blend(blue, (230, 240, 246), 0.05),
        side_top=blue_side_top,
        side_bottom=blue_side_bottom,
        outline=(144, 176, 199),
    )
    add_noise(base, upper_block_front, (255, 255, 255), count=120, radius=8, opacity=26, seed=2)
    add_noise(base, upper_block_front, (159, 196, 219), count=90, radius=6, opacity=18, seed=3)

    # Honeycomb core.
    honey_front = [(27, 665), (440, 665), (440, 757), (27, 757)]
    draw_prism(
        base,
        honey_front,
        (15, -17),
        front_top=(247, 247, 247),
        front_bottom=(224, 224, 224),
        top_top=(90, 90, 90),
        top_bottom=(58, 58, 58),
        side_top=(212, 212, 212),
        side_bottom=(177, 177, 177),
        outline=(110, 110, 110),
    )
    draw_honeycomb_front(base, honey_front)

    # Lower changed block (倒数第二块).
    lower_block_front = [(43, 833), (436, 833), (436, 925), (43, 925)]
    draw_prism(
        base,
        lower_block_front,
        (23, -22),
        front_top=blue_top,
        front_bottom=blue_bottom,
        top_top=blend(blue, (255, 255, 255), 0.15),
        top_bottom=blend(blue, (230, 240, 246), 0.05),
        side_top=blue_side_top,
        side_bottom=blue_side_bottom,
        outline=(144, 176, 199),
    )
    add_noise(base, lower_block_front, (255, 255, 255), count=140, radius=8, opacity=24, seed=4)
    add_noise(base, lower_block_front, (159, 196, 219), count=110, radius=6, opacity=16, seed=5)

    # Bottom metallic base.
    bottom_front = [(49, 1007), (437, 1007), (437, 1112), (49, 1112)]
    draw_prism(
        base,
        bottom_front,
        (22, -24),
        front_top=(204, 206, 209),
        front_bottom=(165, 168, 171),
        top_top=(238, 239, 240),
        top_bottom=(192, 194, 197),
        side_top=(177, 180, 183),
        side_bottom=(138, 140, 143),
        outline=(138, 140, 144),
    )
    add_noise(base, bottom_front, (255, 255, 255), count=75, radius=14, opacity=16, seed=6)

    # Small separators and light ambient shadowing between layers.
    for y in (455, 620, 792, 967):
        draw.line([(55, y), (440, y)], fill=(235, 235, 235), width=2)

    base = base.filter(ImageFilter.GaussianBlur(0.2))
    out = base.convert("RGB")
    out.save("edited_image.png", quality=96)


if __name__ == "__main__":
    main()
