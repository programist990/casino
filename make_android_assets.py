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


def make_presplash():
    size = 800
    image = background(size).convert("RGBA")
    draw = ImageDraw.Draw(image)
    chip = Image.open(CHIP).convert("RGBA").resize((260, 260), Image.LANCZOS)
    image.alpha_composite(chip, (270, 170))
    title = ImageFont.truetype(FONT_TITLE, 78)
    draw.text((400, 520), "LUCKY CASINO", font=title, fill=(60, 30, 0, 255), anchor="mm", stroke_width=6, stroke_fill=(60, 30, 0, 255))
    draw.text((400, 520), "LUCKY CASINO", font=title, fill=GOLD, anchor="mm")
    suits = ImageFont.truetype(FONT_SUITS, 54)
    draw.text((400, 620), "♠  ♥  ♦  ♣", font=suits, fill=(255, 255, 255, 140), anchor="mm")
    image.convert("RGB").save(os.path.join(OUT, "presplash.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_icon()
    make_presplash()
    print("done:", OUT)
