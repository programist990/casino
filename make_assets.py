"""Generates slot symbol images and the chip icon into assets/symbols.

Run once:  python make_assets.py   (needs Pillow: pip install pillow)
The game itself does not need Pillow, only the finished PNG files.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE, "assets", "fonts", "RussoOne-Regular.ttf")
OUT_DIR = os.path.join(BASE, "assets", "symbols")

BIG = 1024  # drawn big, then scaled down for smooth edges
SMALL = 256

GOLD = (255, 205, 50, 255)
GOLD_DARK = (170, 110, 0, 255)


def new_canvas():
    image = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def save(image, name, size=SMALL):
    small = image.resize((size, size), Image.LANCZOS)
    small.save(os.path.join(OUT_DIR, name + ".png"))


def bezier(p0, p1, p2, steps=24):
    points = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        points.append((x, y))
    return points


def ball(draw, center, radius, base, body, light):
    """A shaded sphere: dark base, lighter body, small highlight."""
    cx, cy = center
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base)
    inner = radius * 0.93
    draw.ellipse(
        (cx - inner, cy - inner - 6, cx + inner * 0.95, cy + inner * 0.9),
        fill=body,
    )
    hx = cx - radius * 0.38
    hy = cy - radius * 0.42
    draw.ellipse(
        (hx - radius * 0.2, hy - radius * 0.14, hx + radius * 0.2, hy + radius * 0.14),
        fill=light,
    )


def leaf(draw, points):
    draw.polygon(points, fill=(70, 150, 60, 255), outline=(40, 100, 35, 255), width=10)


def make_cherry():
    image, draw = new_canvas()
    apex = (590, 190)
    left_top = (330, 560)
    right_top = (690, 600)
    draw.line(bezier(left_top, (380, 280), apex), fill=(60, 120, 45, 255), width=30)
    draw.line(bezier(right_top, (700, 330), apex), fill=(60, 120, 45, 255), width=30)
    leaf(draw, [(590, 190), (800, 100), (900, 210), (720, 270)])
    ball(draw, (320, 720), 195, (140, 10, 30, 255), (215, 30, 55, 255), (255, 190, 200, 255))
    ball(draw, (700, 760), 195, (140, 10, 30, 255), (215, 30, 55, 255), (255, 190, 200, 255))
    save(image, "cherry")


def make_plum():
    image, draw = new_canvas()
    draw.line([(512, 300), (540, 170)], fill=(95, 65, 30, 255), width=34)
    leaf(draw, [(540, 190), (760, 120), (850, 230), (660, 280)])
    ball(draw, (512, 580), 340, (70, 25, 115, 255), (140, 75, 205, 255), (215, 175, 245, 255))
    draw.arc((470, 250, 560, 380), 70, 110, fill=(70, 25, 115, 255), width=14)
    save(image, "plum")


def make_lemon():
    image, draw = new_canvas()
    # draw straight, rotate afterwards
    draw.polygon([(190, 440), (70, 510), (200, 610)], fill=(235, 205, 20, 255))
    draw.polygon([(834, 440), (954, 510), (824, 610)], fill=(235, 205, 20, 255))
    draw.ellipse((150, 300, 874, 740), fill=(240, 210, 30, 255), outline=(190, 150, 0, 255), width=14)
    draw.ellipse((220, 340, 700, 560), fill=(252, 232, 80, 255))
    draw.ellipse((260, 360, 460, 440), fill=(255, 248, 170, 255))
    leaf(draw, [(700, 320), (820, 190), (930, 260), (800, 360)])
    image = image.rotate(18, resample=Image.BICUBIC)
    save(image, "lemon")


def make_bell():
    image, draw = new_canvas()
    outline = GOLD_DARK
    draw.polygon([(312, 420), (712, 420), (830, 770), (194, 770)], fill=GOLD, outline=outline, width=14)
    draw.ellipse((312, 200, 712, 640), fill=GOLD, outline=outline, width=14)
    draw.polygon([(318, 430), (706, 430), (822, 764), (202, 764)], fill=GOLD)
    draw.ellipse((330, 214, 694, 560), fill=GOLD)
    draw.rounded_rectangle((170, 750, 854, 836), radius=42, fill=(235, 170, 20, 255), outline=outline, width=14)
    draw.ellipse((452, 830, 572, 950), fill=(235, 170, 20, 255), outline=outline, width=14)
    draw.ellipse((472, 150, 552, 230), fill=(235, 170, 20, 255), outline=outline, width=14)
    draw.ellipse((360, 270, 440, 520), fill=(255, 238, 160, 255))
    save(image, "bell")


def make_bar():
    image, draw = new_canvas()
    draw.rounded_rectangle((70, 300, 954, 724), radius=80, fill=(25, 25, 32, 255), outline=GOLD, width=30)
    font = ImageFont.truetype(FONT_PATH, 330)
    draw.text((512, 520), "BAR", font=font, fill=GOLD, anchor="mm")
    save(image, "bar")


def make_seven():
    image, draw = new_canvas()
    font = ImageFont.truetype(FONT_PATH, 900)
    draw.text((530, 560), "7", font=font, fill=(0, 0, 0, 120), anchor="mm", stroke_width=34, stroke_fill=(0, 0, 0, 120))
    draw.text((512, 540), "7", font=font, fill=(225, 30, 35, 255), anchor="mm", stroke_width=34, stroke_fill=GOLD)
    save(image, "seven")


def make_chip():
    image, draw = new_canvas()
    center = BIG / 2
    radius = 470
    draw.ellipse((center - radius, center - radius, center + radius, center + radius), fill=(200, 30, 45, 255))
    for i in range(8):
        angle = math.radians(i * 45)
        points = []
        for dr, da in ((radius, -9), (radius, 9), (radius - 120, 9), (radius - 120, -9)):
            a = angle + math.radians(da)
            points.append((center + dr * math.cos(a), center + dr * math.sin(a)))
        draw.polygon(points, fill=(255, 255, 255, 255))
    inner = radius - 150
    draw.ellipse((center - inner, center - inner, center + inner, center + inner), fill=(160, 15, 30, 255), outline=GOLD, width=26)
    font = ImageFont.truetype(FONT_PATH, 300)
    draw.text((center, center + 6), "$", font=font, fill=GOLD, anchor="mm")
    save(image, "chip", 128)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    make_cherry()
    make_plum()
    make_lemon()
    make_bell()
    make_bar()
    make_seven()
    make_chip()
    print("done:", OUT_DIR)


if __name__ == "__main__":
    main()
