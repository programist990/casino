"""Makes the app icon and the splash screen for the Android build.

Run once:  python make_android_assets.py   (needs Pillow)
Creates assets/android/icon.png and assets/android/presplash.png
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "assets", "android")
CHIP = os.path.join(BASE, "assets", "symbols", "chip.png")
FONT_TITLE = os.path.join(BASE, "assets", "fonts", "RussoOne-Regular.ttf")
FONT_SUITS = os.path.join(BASE, "assets", "fonts", "DejaVuSans-Bold.ttf")

BG_TOP = (15, 82, 56)
BG_BOTTOM = (3, 23, 18)
GOLD = (255, 205, 50, 255)


def background(size):
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    center = size / 2
    for y in range(size):
        t = 1 - y / size
        for x in range(size):
            d = math.hypot(x - center, y - center * 0.9) / (size * 0.7)
            light = max(0.0, 1.0 - d) ** 1.4
            base = [BG_BOTTOM[c] + (BG_TOP[c] - BG_BOTTOM[c]) * t for c in range(3)]
            pixels[x, y] = tuple(int(min(255, base[c] + light * 38)) for c in range(3))
    return image


def make_icon():
    size = 512
    image = background(size).convert("RGBA")
    draw = ImageDraw.Draw(image)
    suits = ImageFont.truetype(FONT_SUITS, 70)
    for text, x, y in (("♠", 70, 70), ("♥", 442, 70), ("♦", 70, 442), ("♣", 442, 442)):
        color = (255, 120, 120, 150) if text in "♥♦" else (255, 255, 255, 130)
        draw.text((x, y), text, font=suits, fill=color, anchor="mm")
    chip = Image.open(CHIP).convert("RGBA").resize((330, 330), Image.LANCZOS)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((95, 108, 427, 440), fill=(0, 0, 0, 100))
    image = Image.alpha_composite(image, shadow)
    image.alpha_composite(chip, (91, 91))
    image.convert("RGB").save(os.path.join(OUT, "icon.png"))


def splash_background(width, height):
    """Dark base colour with a soft glow in the middle.

    The edges are exactly BASE_COLOR (the same as android.presplash_color in
    buildozer.spec), so the picture blends into the screen on any phone shape.
    """
    base = (2, 23, 15)
    small_w, small_h = width // 4, height // 4
    image = Image.new("RGB", (small_w, small_h))
    pixels = image.load()
    cx, cy = small_w / 2, small_h * 0.42
    radius = small_h * 0.42
    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot((x - cx) * 1.35, y - cy) / radius
            light = max(0.0, 1.0 - d) ** 1.6
            pixels[x, y] = tuple(
                int(min(255, base[c] + light * (BG_TOP[c] - base[c] + 14))) for c in range(3)
            )
    return image.resize((width, height), Image.LANCZOS)


def make_presplash():
    # tall rectangle, like a phone screen (9:20). The edges have the same colour
    # as android.presplash_color, so the picture fills the whole screen.
    width, height = 1080, 2400
    image = splash_background(width, height).convert("RGBA")
    draw = ImageDraw.Draw(image)
    cx = width // 2

    chip_size = 560
    chip = Image.open(CHIP).convert("RGBA").resize((chip_size, chip_size), Image.LANCZOS)
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        (cx - chip_size // 2 + 20, 700 + 40, cx + chip_size // 2 + 20, 700 + chip_size + 40),
        fill=(0, 0, 0, 110),
    )
    image = Image.alpha_composite(image, shadow)
    image.alpha_composite(chip, (cx - chip_size // 2, 700))
    draw = ImageDraw.Draw(image)

    title = ImageFont.truetype(FONT_TITLE, 190)
    for text, y in (("LUCKY", 1480), ("CASINO", 1690)):
        draw.text((cx, y), text, font=title, fill=(60, 30, 0, 255), anchor="mm", stroke_width=12, stroke_fill=(60, 30, 0, 255))
        draw.text((cx, y), text, font=title, fill=GOLD, anchor="mm")

    suits = ImageFont.truetype(FONT_SUITS, 110)
    draw.text((cx, 1950), "\u2660  \u2665  \u2666  \u2663", font=suits, fill=(255, 255, 255, 150), anchor="mm")
    image.convert("RGB").save(os.path.join(OUT, "presplash.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_icon()
    make_presplash()
    print("done:", OUT)
