"""Generates extra assets for the blackjack table.

Run once:  python make_blackjack_assets.py   (needs Pillow: pip install pillow)
The game itself does not need Pillow, only the finished PNG / WAV files.

Creates:
  assets/blackjack/felt.png        table cloth with soft light and a suit pattern
  assets/blackjack/spot.png        warm lamp glow that slowly pulses
  assets/blackjack/card_back.png   card back (shoe, flying cards, hidden card)
  assets/blackjack/chip_*.png      coloured bet chips (10 / 50 / 100 / 500)
  assets/sounds/*.wav              deal, flip, chip, win, blackjack, lose, push
"""
import math
import os
import random
import struct
import wave

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(BASE, "assets", "fonts", "RussoOne-Regular.ttf")
FONT_SUITS = os.path.join(BASE, "assets", "fonts", "DejaVuSans-Bold.ttf")
OUT_DIR = os.path.join(BASE, "assets", "blackjack")
SOUND_DIR = os.path.join(BASE, "assets", "sounds")

GOLD = (255, 205, 50, 255)
GOLD_DARK = (170, 110, 0, 255)


def lerp(a, b, t):
    return a + (b - a) * t


# ----- table cloth -----


def make_felt():
    width, height = 512, 896
    random.seed(7)
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    center_x = width / 2
    center_y = height * 0.46
    bottom = (3, 23, 18)
    top = (11, 62, 43)
    middle = (22, 112, 78)
    for y in range(height):
        row_t = 1 - y / height  # 1 on the top edge
        edge = [lerp(bottom[c], top[c], row_t) for c in range(3)]
        for x in range(width):
            dx = (x - center_x) / (width * 0.72)
            dy = (y - center_y) / (height * 0.58)
            distance = math.sqrt(dx * dx + dy * dy)
            light = max(0.0, 1.0 - distance) ** 1.5
            grain = random.randint(-4, 4)
            pixels[x, y] = tuple(
                max(0, min(255, int(lerp(edge[c], middle[c], light) + grain)))
                for c in range(3)
            )

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype(FONT_SUITS, 30)
    suits = ["♠", "♥", "♦", "♣"]
    step = 92
    row = 0
    for y in range(20, height, step):
        shift = 0 if row % 2 == 0 else step // 2
        for column, x in enumerate(range(10 + shift, width, step)):
            suit = suits[(row + column) % 4]
            draw.text((x, y), suit, font=font, fill=(255, 255, 255, 13), anchor="mm")
        row += 1
    for offset in range(-height, width, 64):
        draw.line((offset, 0, offset + height, height), fill=(255, 255, 255, 5), width=1)
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    image.save(os.path.join(OUT_DIR, "felt.png"))


def make_spot():
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = image.load()
    center = size / 2
    for y in range(size):
        for x in range(size):
            distance = math.hypot(x - center, y - center) / center
            alpha = max(0.0, 1.0 - distance) ** 2
            pixels[x, y] = (255, 236, 160, int(alpha * 255))
    image.save(os.path.join(OUT_DIR, "spot.png"))


# ----- card back -----


def make_card_back():
    width, height = 464, 688  # drawn 4x, saved 2x
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=64, fill=(250, 250, 252, 255))

    inner_box = (22, 22, width - 23, height - 23)
    draw.rounded_rectangle(inner_box, radius=44, fill=(38, 77, 179, 255))

    pattern = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pattern_draw = ImageDraw.Draw(pattern)
    for offset in range(-height, width, 56):
        pattern_draw.line((offset, 0, offset + height, height), fill=(95, 140, 235, 255), width=5)
        pattern_draw.line((offset + height, 0, offset, height), fill=(95, 140, 235, 255), width=5)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle(inner_box, radius=44, fill=255)
    image.paste(pattern, (0, 0), Image.composite(pattern.split()[3], Image.new("L", (width, height), 0), mask))

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((44, 44, width - 45, height - 45), radius=30, outline=GOLD, width=6)
    cx, cy = width / 2, height / 2
    draw.ellipse((cx - 118, cy - 118, cx + 118, cy + 118), fill=(20, 45, 120, 255), outline=GOLD, width=8)
    font = ImageFont.truetype(FONT_SUITS, 200)
    draw.text((cx, cy + 6), "♦", font=font, fill=GOLD, anchor="mm")
    small = ImageFont.truetype(FONT_SUITS, 60)
    for px, py in ((92, 100), (width - 92, 100), (92, height - 100), (width - 92, height - 100)):
        draw.text((px, py), "♦", font=small, fill=GOLD, anchor="mm")

    image.resize((116, 172), Image.LANCZOS).save(os.path.join(OUT_DIR, "card_back.png"))


# ----- chips -----


def make_chip(name, base, stripe, inner, rim, symbol):
    big = 1024
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    center = big / 2
    radius = 470
    draw.ellipse((center - radius, center - radius, center + radius, center + radius), fill=base)
    for i in range(8):
        angle = math.radians(i * 45)
        points = []
        for dr, da in ((radius, -9), (radius, 9), (radius - 120, 9), (radius - 120, -9)):
            a = angle + math.radians(da)
            points.append((center + dr * math.cos(a), center + dr * math.sin(a)))
        draw.polygon(points, fill=stripe)
    inner_radius = radius - 150
    draw.ellipse(
        (center - inner_radius, center - inner_radius, center + inner_radius, center + inner_radius),
        fill=inner,
        outline=rim,
        width=26,
    )
    font = ImageFont.truetype(FONT_TITLE, 300)
    draw.text((center, center + 6), "$", font=font, fill=symbol, anchor="mm")
    image.resize((128, 128), Image.LANCZOS).save(os.path.join(OUT_DIR, name + ".png"))


def make_chips():
    make_chip("chip_10", (225, 228, 235, 255), (70, 80, 100, 255), (170, 176, 190, 255), GOLD, (60, 70, 90, 255))
    make_chip("chip_50", (40, 90, 200, 255), (255, 255, 255, 255), (25, 60, 150, 255), GOLD, GOLD)
    make_chip("chip_100", (200, 30, 45, 255), (255, 255, 255, 255), (160, 15, 30, 255), GOLD, GOLD)
    make_chip("chip_500", (28, 28, 36, 255), GOLD, (12, 12, 18, 255), GOLD, GOLD)


# ----- sounds -----

RATE = 22050


def write_wav(name, samples):
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = 0.85 / peak if peak > 0.85 else 1.0
    path = os.path.join(SOUND_DIR, name + ".wav")
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        frames = b"".join(struct.pack("<h", int(max(-1, min(1, s * scale)) * 32000)) for s in samples)
        wav.writeframes(frames)


def blank(seconds):
    return [0.0] * int(RATE * seconds)


def add(target, start, tone):
    begin = int(start * RATE)
    for i, value in enumerate(tone):
        if begin + i < len(target):
            target[begin + i] += value


def noise_hit(length, decay, volume, highpass=True):
    out = []
    previous = 0.0
    for i in range(int(RATE * length)):
        t = i / RATE
        value = random.uniform(-1, 1)
        shaped = value - previous if highpass else value
        previous = value
        envelope = min(1.0, t * 500) * math.exp(-t * decay)
        out.append(shaped * envelope * volume)
    return out


def bell(freq, length, volume, decay=9.0):
    out = []
    for i in range(int(RATE * length)):
        t = i / RATE
        envelope = min(1.0, t * 300) * math.exp(-t * decay)
        value = math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(2 * math.pi * freq * 2 * t)
        out.append(value * envelope * volume)
    return out


def clink(volume):
    out = []
    for i in range(int(RATE * 0.18)):
        t = i / RATE
        envelope = min(1.0, t * 800) * math.exp(-t * 30)
        value = 0.0
        for freq, amp in ((2200, 1.0), (3300, 0.6), (4700, 0.35)):
            value += amp * math.sin(2 * math.pi * freq * t)
        out.append(value * envelope * volume * 0.4)
    return out


def make_sounds():
    random.seed(3)

    write_wav("deal", noise_hit(0.14, 38, 0.55))

    flip = noise_hit(0.08, 70, 0.4)
    click = [math.sin(2 * math.pi * 1700 * i / RATE) * math.exp(-i / RATE * 90) * 0.5 for i in range(len(flip))]
    write_wav("flip", [a + b for a, b in zip(flip, click)])

    chip = blank(0.28)
    add(chip, 0.0, clink(1.0))
    add(chip, 0.06, clink(0.7))
    write_wav("chip", chip)

    win = blank(0.9)
    for index, freq in enumerate((523, 659, 784, 1047)):
        add(win, index * 0.11, bell(freq, 0.5, 0.5))
    write_wav("win", win)

    fanfare = blank(1.6)
    for index, freq in enumerate((523, 659, 784, 1047, 1319, 1568)):
        add(fanfare, index * 0.09, bell(freq, 0.6, 0.45))
    for freq in (523, 659, 784, 1047):
        add(fanfare, 0.7, bell(freq, 0.9, 0.3, decay=4.0))
    write_wav("blackjack", fanfare)

    lose = blank(0.8)
    for index, freq in enumerate((330, 277, 220)):
        add(lose, index * 0.17, bell(freq, 0.45, 0.6, decay=7.0))
    write_wav("lose", lose)

    push = blank(0.5)
    add(push, 0.0, bell(440, 0.3, 0.45, decay=10.0))
    add(push, 0.15, bell(440, 0.3, 0.35, decay=10.0))
    write_wav("push", push)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SOUND_DIR, exist_ok=True)
    make_felt()
    make_spot()
    make_card_back()
    make_chips()
    make_sounds()
    print("done:", OUT_DIR, SOUND_DIR)


if __name__ == "__main__":
    main()
