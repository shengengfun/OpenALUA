"""Generate OpenALUA application icons (self-made, no vendor assets)."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

OUT = r"d:\Project\OpenALUA\src-tauri\icons"

ACCENT = (0, 200, 255)
ACCENT2 = (31, 111, 235)


def rounded_gradient(size: int, radius_ratio: float = 0.22) -> Image.Image:
    """Rounded square with a diagonal gradient."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size - 2)
            px[x, y] = (
                int(ACCENT[0] * (1 - t) + ACCENT2[0] * t),
                int(ACCENT[1] * (1 - t) + ACCENT2[1] * t),
                int(ACCENT[2] * (1 - t) + ACCENT2[2] * t),
                255,
            )
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255
    )
    img.paste(grad, (0, 0), mask)
    return img


def draw_mark(img: Image.Image) -> Image.Image:
    """Draw a stylised 'A' (AULA / OpenALUA) in dark ink."""
    size = img.width
    d = ImageDraw.Draw(img)
    ink = (6, 20, 28, 255)

    # triangle (the 'A' bowl)
    w = size * 0.46
    h = size * 0.42
    cx, cy = size / 2, size * 0.56
    apex = (cx, cy - h)
    left = (cx - w / 2, cy + h * 0.55)
    right = (cx + w / 2, cy + h * 0.55)
    d.polygon([apex, left, right], fill=ink)

    # inner cut-out
    w2, h2 = w * 0.46, h * 0.46
    cy2 = cy + h * 0.06
    d.polygon(
        [
            (cx, cy2 - h2),
            (cx - w2 / 2, cy2 + h2 * 0.55),
            (cx + w2 / 2, cy2 + h2 * 0.55),
        ],
        fill=(0, 0, 0, 0),
    )

    # crossbar
    bar_h = max(2, int(size * 0.045))
    d.rectangle(
        [cx - w * 0.20, cy + h * 0.02, cx + w * 0.20, cy + h * 0.02 + bar_h],
        fill=ink,
    )

    # light "keycaps" dots on top
    r = max(1.5, size * 0.028)
    for i, x in enumerate((0.30, 0.5, 0.70)):
        d.ellipse(
            [size * x - r, size * 0.20 - r, size * x + r, size * 0.20 + r],
            fill=(255, 255, 255, 210),
        )
    return img


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(OUT, exist_ok=True)

    base = draw_mark(rounded_gradient(1024))

    # flatten for formats without alpha
    def flat(size):
        return base.resize((size, size), Image.LANCZOS)

    sizes = {
        "32x32.png": 32,
        "128x128.png": 128,
        "128x128@2x.png": 256,
        "icon.png": 512,
        "Square30x30Logo.png": 30,
        "Square44x44Logo.png": 44,
        "Square71x71Logo.png": 71,
        "Square89x89Logo.png": 89,
        "Square107x107Logo.png": 107,
        "Square142x142Logo.png": 142,
        "Square150x150Logo.png": 150,
        "Square284x284Logo.png": 284,
        "Square310x310Logo.png": 310,
        "StoreLogo.png": 50,
    }
    for name, s in sizes.items():
        flat(s).save(os.path.join(OUT, name))
        print("wrote", name)

    base.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT, "icon.ico"),
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("wrote icon.ico")


if __name__ == "__main__":
    main()
