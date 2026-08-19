"""Generate a real favicon.ico for the Raphael static UI (brand diamond mark)."""
import math
from PIL import Image, ImageDraw

# Brand palette (matches frontend halo/theme)
BG_INNER = (18, 22, 36)      # near-black navy
BG_OUTER = (10, 12, 22)
DIAMOND = (90, 220, 255)     # cyan
DIAMOND_CORE = (180, 130, 255)  # purple-ish highlight


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded-ish background circle
    pad = max(1, size // 16)
    d.ellipse([pad, pad, size - pad, size - pad], fill=BG_OUTER)
    inner = max(2, size // 8)
    d.ellipse([inner, inner, size - inner, size - inner], fill=BG_INNER)

    # diamond (◆) centered
    cx, cy = size / 2, size / 2
    r = size * 0.26
    # outer glow diamond
    points = [
        (cx, cy - r),
        (cx + r, cy),
        (cx, cy + r),
        (cx - r, cy),
    ]
    d.polygon(points, fill=DIAMOND)
    # inner core diamond (smaller, lighter)
    r2 = r * 0.5
    core = [
        (cx, cy - r2),
        (cx + r2, cy),
        (cx, cy + r2),
        (cx - r2, cy),
    ]
    d.polygon(core, fill=DIAMOND_CORE)
    return img


def main():
    sizes = [16, 32, 48]
    images = [draw_icon(s) for s in sizes]
    out = "frontend/favicon.ico"
    # PIL saves multi-size ICO when given a list of images
    images[0].save(out, sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"wrote {out} ({sizes})")


if __name__ == "__main__":
    main()
