"""
Generates the Mimo system tray icon programmatically using Pillow.
No external image files needed — the icon is drawn from code.

States:
  active  — flame orange/red   (monitoring running)
  paused  — grey               (monitoring paused)
  alert   — bright red pulse   (roast firing)
"""

import os

from PIL import Image, ImageDraw

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)


def generate_tray_icon(size: int = 64, state: str = "active") -> Image.Image:
    """
    Draw a circular icon with a flame symbol inside.

    state: "active" | "paused" | "alert"
    Returns a PIL RGBA image.
    """
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle colour by state
    bg_colours = {
        "active": (30, 30, 45, 255),       # dark navy
        "paused": (50, 50, 55, 200),        # grey
        "alert":  (180, 30, 30, 255),       # red
    }
    bg = bg_colours.get(state, bg_colours["active"])
    draw.ellipse([1, 1, size - 1, size - 1], fill=bg)

    # Flame colours by state
    flame_outer = {
        "active": (240, 100, 30, 255),
        "paused": (110, 110, 120, 255),
        "alert":  (255, 80,  30, 255),
    }.get(state, (240, 100, 30, 255))

    flame_inner = {
        "active": (255, 210, 60, 255),
        "paused": (150, 150, 160, 255),
        "alert":  (255, 220, 60, 255),
    }.get(state, (255, 210, 60, 255))

    pad = size * 0.15
    cx  = size / 2

    # Outer flame (wider, taller)
    _draw_flame(draw, cx, pad, size - pad, flame_outer, scale=1.0)

    # Inner flame (narrower, shorter) — gives depth
    _draw_flame(draw, cx, pad * 2.5, size - pad * 1.5, flame_inner, scale=0.5)

    return img


def _draw_flame(draw, cx, y_top, y_bot, colour, scale=1.0):
    """Draw a simplified flame polygon."""
    h    = y_bot - y_top
    w    = h * 0.55 * scale
    mid  = y_top + h * 0.45

    points = [
        (cx,          y_top),          # tip
        (cx + w,      mid),            # right bulge
        (cx + w * 0.6, y_bot),         # right base
        (cx - w * 0.6, y_bot),         # left base
        (cx - w,      mid),            # left bulge
    ]
    draw.polygon(points, fill=colour)


def save_icon(state: str = "active", size: int = 64) -> str:
    """Save icon to assets/ and return the file path."""
    path = os.path.join(ASSETS_DIR, f"mimo_{state}_{size}.png")
    if not os.path.exists(path):
        img = generate_tray_icon(size=size, state=state)
        img.save(path)
    return path


def get_all_icons() -> dict:
    """Generate and return all icon states as PIL Images."""
    return {
        state: generate_tray_icon(size=64, state=state)
        for state in ("active", "paused", "alert")
    }


if __name__ == "__main__":
    # Run directly to preview icons
    for state in ("active", "paused", "alert"):
        path = save_icon(state)
        print(f"Saved: {path}")
