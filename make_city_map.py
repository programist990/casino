"""Paints the ground of the city map and the things that stand on it.

Run once:  python make_city_map.py   (needs Pillow and numpy; run make_city_assets.py first,
it makes the grass tile and the trees this script builds on)

Creates in assets/city/:
  ground.png                     the whole map: grass, desert, lake, stream, roads, plaza, park, parking
  palm / cactus / barrel / rock / dry / lamp / bench / umbrella / billboard .png   things on the ground
  car_*.png                      little cars that drive around the ring road
  cloud.png                      soft cloud shadow that drifts over the map

Where everything goes comes from city_data.py, the same file the game reads.
The game only loads the PNG files, so this script is needed only to change how it looks.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import city_data as cd
from make_city_assets import OUT, Paint, mix, shade

S = 2  # ground pixels per dp
HI = 2  # masks are painted this many times bigger, then shrunk (smooth edges)
SIZE = cd.MAP_W * S
K = S * HI
ASPHALT = (50, 52, 58)


# ======================= sprites =======================


def sprite(_name, design_w, design_h, kind):
    w, h = cd.DECOR_SIZE[kind]
    return Paint(design_w, design_h, w * 2)


def make_palm():
    p = sprite("palm", 100, 130, "palm")
    p.shadow(lambda d: d.ellipse(p.px([22, 112, 84, 128]), fill=(0, 0, 0, 255)), blur=4, alpha=0.4)
    p.poly_g([(44, 124), (56, 124), (60, 70), (54, 48), (46, 48), (50, 72)], (150, 108, 64), (104, 70, 40))
    for y in range(58, 122, 9):  # rings on the trunk
        p.line([(46, y), (57, y - 2)], (86, 56, 32, 200), width=1.6)
    cx, cy = 52, 48
    fronds = [(-170, 40), (-140, 46), (-108, 40), (-72, 40), (-40, 46), (-10, 40), (20, 30), (160, 30)]
    for angle, length in fronds:
        a = math.radians(angle)
        spine = []
        for i in range(0, 11):
            t = i / 10
            spine.append((cx + length * t * math.cos(a), cy + length * t * math.sin(a) + 20 * t * t))
        left, right = [], []
        for i, (x, y) in enumerate(spine):
            t = i / 10
            width = 7.5 * math.sin(math.pi * min(1, t * 1.05)) ** 0.7
            nx, ny = -math.sin(a), math.cos(a)
            left.append((x + nx * width, y + ny * width))
            right.append((x - nx * width, y - ny * width))
        poly = left + right[::-1]
        p.poly(poly, fill=(34, 112, 62, 255))
        p.poly([(x, y - 1) for x, y in left[1:-1]] + [(x, y) for x, y in spine[-2:0:-1]], fill=(84, 180, 90, 255))
        p.line(spine, (28, 90, 52, 255), width=1.2)
    for dx, dy in ((-4, 4), (4, 4), (0, 8)):
        p.ellipse(cx + dx - 4, cy + dy - 4, cx + dx + 4, cy + dy + 4, fill=(110, 70, 36, 255))
    p.save("palm.png")


def make_cactus():
    p = sprite("cactus", 60, 100, "cactus")
    p.shadow(lambda d: d.ellipse(p.px([8, 86, 54, 98]), fill=(0, 0, 0, 255)), blur=3, alpha=0.4)
    green_d, green_l = (36, 112, 70), (96, 176, 108)

    def limb(x0, y0, x1, y1):
        p.rrect_g(x0 - 1.5, y0, x1 + 1.5, y1, shade(green_d, 0.8), shade(green_d, 0.8), r=(x1 - x0) / 2 + 1.5)
        p.rrect_g(x0, y0, x1, y1, green_l, green_d, r=(x1 - x0) / 2)
    limb(25, 12, 37, 92)
    limb(8, 44, 18, 66)
    limb(8, 44, 25, 54)
    limb(43, 30, 53, 52)
    limb(31, 42, 53, 52)
    for x in (28, 31, 34):
        p.line([(x, 20), (x, 88)], (30, 96, 60, 150), width=0.9)
    for x, y in ((31, 12), (13, 44), (48, 30)):
        p.ellipse(x - 3, y - 3, x + 3, y + 3, fill=(255, 130, 170, 255))
    p.save("cactus.png")


def make_barrel():
    p = sprite("barrel", 52, 52, "barrel")
    p.shadow(lambda d: d.ellipse(p.px([6, 34, 48, 48]), fill=(0, 0, 0, 255)), blur=3, alpha=0.4)
    p.ellipse(8, 14, 44, 46, fill=(30, 100, 62, 255))
    p.rrect_g(10, 14, 42, 44, (108, 186, 112), (44, 128, 76), r=16)
    for x in (18, 26, 34):
        p.line([(26 + (x - 26) * 0.3, 15), (x, 30), (26 + (x - 26) * 0.6, 44)], (30, 96, 60, 170), width=1)
    p.ellipse(21, 13, 31, 21, fill=(255, 120, 160, 255))
    p.ellipse(24, 15, 28, 19, fill=(255, 220, 90, 255))
    p.save("barrel.png")


def make_rock():
    p = sprite("rock", 68, 52, "rock")
    p.shadow(lambda d: d.ellipse(p.px([4, 34, 64, 50]), fill=(0, 0, 0, 255)), blur=3, alpha=0.4)
    p.poly_g([(6, 42), (12, 22), (28, 12), (46, 16), (60, 30), (62, 42), (34, 46)], (186, 154, 120), (122, 94, 70))
    p.poly([(28, 12), (46, 16), (40, 28), (22, 26)], fill=(255, 235, 205, 70))
    p.poly([(6, 42), (12, 22), (22, 26), (20, 44)], fill=(0, 0, 0, 28))
    p.poly([(40, 28), (60, 30), (62, 42), (34, 46)], fill=(0, 0, 0, 36))
    p.save("rock.png")


def make_dry():
    p = sprite("dry", 60, 48, "dry")
    p.shadow(lambda d: d.ellipse(p.px([6, 30, 54, 46]), fill=(0, 0, 0, 255)), blur=3, alpha=0.35)
    rng = random.Random(3)
    for _ in range(46):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(8, 22)
        x, y = 30 + r * math.cos(a), 28 + r * 0.8 * math.sin(a)
        x2, y2 = 30 + (r * 0.3) * math.cos(a + 1), 28 + (r * 0.3) * math.sin(a + 1)
        p.line([(x2, y2), ((x + x2) / 2 + rng.uniform(-3, 3), (y + y2) / 2 + rng.uniform(-3, 3)), (x, y)],
               rng.choice([(150, 112, 62, 255), (120, 86, 46, 255), (176, 138, 80, 255)]), width=1.1)
    p.save("dry.png")


def make_lamp():
    p = sprite("lamp", 36, 92, "lamp")
    p.shadow(lambda d: d.ellipse(p.px([8, 82, 30, 91]), fill=(0, 0, 0, 255)), blur=2, alpha=0.4)
    p.rrect_g(14, 84, 22, 88, (70, 74, 84), (40, 42, 50), r=2)
    p.rrect_g(16, 22, 20, 86, (96, 100, 112), (50, 54, 64), r=2)
    p.glow(lambda d, c: d.ellipse(p.px([9, 6, 27, 24]), fill=c), (255, 224, 130, 120), blur=5, strength=1)
    p.rrect_g(9, 8, 27, 24, (255, 246, 200), (255, 214, 110), r=9)
    p.rrect_g(8, 4, 28, 10, (84, 88, 100), (46, 50, 60), r=3)
    p.save("lamp.png")


def make_bench():
    p = sprite("bench", 72, 44, "bench")
    p.shadow(lambda d: d.ellipse(p.px([4, 28, 70, 42]), fill=(0, 0, 0, 255)), blur=2, alpha=0.35)
    for x in (10, 58):
        p.rrect_g(x, 22, x + 4, 38, (70, 74, 84), (44, 46, 54), r=1)
    p.rrect_g(6, 4, 66, 10, (176, 122, 70), (130, 86, 48), r=2)
    p.rrect_g(6, 12, 66, 18, (176, 122, 70), (130, 86, 48), r=2)
    p.rrect_g(4, 22, 68, 29, (196, 140, 82), (146, 98, 56), r=2)
    p.save("bench.png")


def make_umbrella():
    p = sprite("umbrella", 80, 80, "umbrella")
    p.shadow(lambda d: d.ellipse(p.px([18, 58, 66, 76]), fill=(0, 0, 0, 255)), blur=4, alpha=0.35)
    p.rrect_g(38, 24, 42, 72, (240, 236, 226), (170, 164, 150), r=2)
    colours = [(226, 60, 66), (250, 250, 250)]
    cx, cy, rx, ry = 40, 30, 32, 22
    n = 6
    for i in range(n):
        a0 = math.pi + math.pi * i / n
        a1 = math.pi + math.pi * (i + 1) / n
        pts = [(cx, cy + 4), (cx + rx * math.cos(a0), cy + 4 + ry * math.sin(a0) * 1.0),
               (cx + rx * math.cos((a0 + a1) / 2), cy + 4 + ry * math.sin((a0 + a1) / 2) * 1.05),
               (cx + rx * math.cos(a1), cy + 4 + ry * math.sin(a1) * 1.0)]
        p.poly(pts, fill=colours[i % 2] + (255,))
    p.line([(cx - rx, cy + 4), (cx + rx, cy + 4)], (150, 40, 44, 255), width=1.6)
    p.ellipse(cx - 2, cy - 21, cx + 2, cy - 17, fill=(255, 220, 90, 255))
    p.save("umbrella.png")


def make_billboard():
    p = sprite("billboard", 168, 152, "billboard")
    p.shadow(lambda d: d.ellipse(p.px([20, 132, 150, 150]), fill=(0, 0, 0, 255)), blur=5, alpha=0.4)
    for x in (48, 114):
        p.rrect_g(x, 76, x + 7, 144, (110, 114, 126), (60, 64, 74), r=2)
    p.rrect_g(8, 8, 160, 86, (60, 64, 76), (34, 36, 46), r=8)
    p.rrect_g(14, 14, 154, 80, (40, 8, 58), (92, 14, 70), r=6)
    p.glow(lambda d, c: d.rounded_rectangle(p.px([14, 14, 154, 80]), radius=p.u(6), outline=c, width=max(1, int(p.u(1.6)))),
           (255, 220, 100, 255), blur=3, strength=1)
    p.neon_text(84, 38, "ДЖЕКПОТ", 20, (255, 226, 120))
    p.neon_text(84, 64, "7 7 7", 18, (255, 90, 120))
    p.bulbs([(14 + i * 14, 11) for i in range(11)], size=2)
    p.bulbs([(14 + i * 14, 83) for i in range(11)], size=2)
    p.save("billboard.png")


CAR_COLOURS = {
    "red": (214, 48, 56), "blue": (50, 108, 222), "yellow": (240, 188, 40),
    "white": (234, 236, 242), "green": (46, 158, 90),
}


def car_image(colour, final_w=96):
    """A car seen from above, driving to the right (+x)."""
    p = Paint(96, 52, final_w)
    p.shadow(lambda d: d.rounded_rectangle(p.px([6, 10, 94, 50]), radius=p.u(12), fill=(0, 0, 0, 255)),
             blur=2.5, alpha=0.45)
    for x in (22, 62):  # wheels
        p.rrect_g(x, 2, x + 18, 10, (40, 40, 46), (20, 20, 24), r=3)
        p.rrect_g(x, 42, x + 18, 50, (40, 40, 46), (20, 20, 24), r=3)
    p.rrect_g(4, 6, 92, 46, shade(colour, 1.2), shade(colour, 0.78), r=14)
    p.rect(8, 8, 88, 12, fill=(255, 255, 255, 60), r=3)
    p.poly_g([(58, 12), (74, 17), (74, 35), (58, 40)], (60, 80, 110), (24, 34, 52))  # windscreen
    p.poly_g([(22, 14), (14, 17), (14, 35), (22, 38)], (50, 66, 92), (24, 34, 52))  # back window
    p.rrect_g(22, 12, 58, 40, shade(colour, 1.1), shade(colour, 0.9), r=7)  # roof
    p.rect(86, 11, 92, 19, fill=(255, 244, 190, 255), r=2)
    p.rect(86, 33, 92, 41, fill=(255, 244, 190, 255), r=2)
    p.rect(4, 11, 8, 19, fill=(220, 40, 40, 255), r=1)
    p.rect(4, 33, 8, 41, fill=(220, 40, 40, 255), r=1)
    return p.img.resize(p.final, Image.LANCZOS)


def make_cars():
    for name, colour in CAR_COLOURS.items():
        car_image(colour).save(os.path.join(OUT, f"car_{name}.png"), optimize=True)


def make_cloud():
    img = Image.new("L", (256, 128), 0)
    d = ImageDraw.Draw(img)
    for x, y, rx, ry in ((70, 70, 52, 32), (118, 56, 62, 40), (170, 70, 56, 34), (128, 78, 90, 30)):
        d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=255)
    img = img.filter(ImageFilter.GaussianBlur(14))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.putalpha(img.point(lambda v: int(v * 0.5)))
    out.save(os.path.join(OUT, "cloud.png"), optimize=True)


# ======================= the ground =======================


def noise(scale_px, seed, size=SIZE):
    """Smooth random values 0..1 (blobs about `scale_px` big)."""
    rng = np.random.default_rng(seed)
    n = max(2, int(size / scale_px) + 2)
    small = Image.fromarray((rng.random((n, n)) * 255).astype("uint8"), "L")
    big = small.resize((n * int(scale_px), n * int(scale_px)), Image.BICUBIC).crop((0, 0, size, size))
    return np.asarray(big, dtype=np.float32) / 255.0


def to_px(x, y):
    return ((x + cd.MAP_W / 2) * K, (cd.MAP_H / 2 - y) * K)


def flat(points):
    out = []
    for x, y in points:
        out.extend(to_px(x, y))
    return out


class Mask:
    """A black and white picture of one shape, in dp coordinates. result() is smooth 0..1."""

    def __init__(self):
        self.img = Image.new("L", (SIZE * HI, SIZE * HI), 0)
        self.d = ImageDraw.Draw(self.img)

    def poly(self, points, value=255):
        self.d.polygon(flat(points), fill=value)
        return self

    def circle(self, cx, cy, r, value=255):
        x, y = to_px(cx, cy)
        self.d.ellipse([x - r * K, y - r * K, x + r * K, y + r * K], fill=value)
        return self

    def rect(self, cx, cy, w, h, radius=0, value=255):
        x0, y0 = to_px(cx - w / 2, cy + h / 2)
        x1, y1 = to_px(cx + w / 2, cy - h / 2)
        self.d.rounded_rectangle([x0, y0, x1, y1], radius=radius * K, fill=value)
        return self

    def line(self, points, width, closed=False, value=255):
        pts = list(points) + ([points[0]] if closed else [])
        self.d.line(flat(pts), fill=value, width=max(1, int(width * K)), joint="curve")
        if not closed:  # round ends
            for cx, cy in (pts[0], pts[-1]):
                self.circle(cx, cy, width / 2, value)
        return self

    def result(self, blur=0.0):
        small = self.img.resize((SIZE, SIZE), Image.BOX)
        if blur:
            small = small.filter(ImageFilter.GaussianBlur(blur))
        return (np.asarray(small, dtype=np.float32) / 255.0)[:, :, None]


def lay(base, mask, colour, strength=1.0):
    """Paints `colour` (a tuple or a picture) over `base` where the mask is white."""
    a = mask * strength
    col = np.array(colour, dtype=np.float32) if isinstance(colour, tuple) else colour
    base *= 1 - a
    base += a * col
    return base


def offset_path(points, distance):
    out = []
    n = len(points)
    for i in range(n):
        a = points[max(0, i - 1)]
        b = points[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1
        out.append((points[i][0] - dy / length * distance, points[i][1] + dx / length * distance))
    return out


def trim_path(points, start, end):
    """Cuts `start` dp off the beginning and `end` dp off the end of a path."""
    lengths = [0.0]
    for i in range(1, len(points)):
        lengths.append(lengths[-1] + math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]))
    total = lengths[-1]
    return [pt for pt, ln in zip(points, lengths) if start <= ln <= total - end]


def dashes(points, dash, gap, closed=False):
    pts = list(points) + ([points[0]] if closed else [])
    pieces, current, left, drawing = [], [pts[0]], dash, True
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        length = math.hypot(x1 - x0, y1 - y0)
        pos = 0.0
        while length - pos > left:
            pos += left
            t = pos / length
            point = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if drawing:
                current.append(point)
                pieces.append(current)
                current = []
            else:
                current = [point]
            drawing = not drawing
            left = dash if drawing else gap
        left -= length - pos
        if drawing:
            current.append((x1, y1))
    if drawing and len(current) > 1:
        pieces.append(current)
    return pieces


def desert_edge_path():
    """The wobbly line where the green land turns into desert."""
    base = cd.rounded_square(cd.DESERT_EDGE, 80, steps=24)
    dense = []
    for i in range(len(base)):
        ax, ay = base[i]
        bx, by = base[(i + 1) % len(base)]
        length = math.hypot(bx - ax, by - ay)
        count = max(1, int(length / 7))
        for k in range(count):
            dense.append((ax + (bx - ax) * k / count, ay + (by - ay) * k / count))
    c = cd.DESERT_EDGE - 80
    out = []
    for i, (x, y) in enumerate(dense):
        nx, ny = x - max(-c, min(c, x)), y - max(-c, min(c, y))
        length = math.hypot(nx, ny)
        if length < 1e-6:
            nx, ny, length = (1, 0, 1) if abs(x) > abs(y) else (0, 1, 1)
        wobble = 9 * math.sin(i * 0.23 + 1) + 6 * math.sin(i * 0.071 + 2) + 4 * math.sin(i * 0.5)
        out.append((x + nx / length * wobble, y + ny / length * wobble))
    return out


def make_ground():
    H = SIZE
    rng = random.Random(21)
    npr = np.random.default_rng(5)

    # ---- grass ----
    tile = np.asarray(Image.open(os.path.join(OUT, "grass.png")).convert("RGB"), dtype=np.float32)
    reps = H // tile.shape[0] + 1
    base = np.tile(tile, (reps, reps, 1))[:H, :H].copy()
    big, mid = noise(380, 1), noise(90, 2)
    base *= (0.86 + 0.26 * big + 0.07 * mid)[:, :, None]

    # ---- desert and beach ----
    m = Mask()
    m.rect(0, 0, cd.MAP_W + 40, cd.MAP_H + 40)
    m.poly(desert_edge_path(), 0)
    m.poly(cd.DESERT_PATCH)
    m.poly(cd.BEACH)
    soft = m.result(blur=14)
    ragged = soft[:, :, 0] + (noise(46, 13) - 0.5) * 0.5 + (noise(150, 14) - 0.5) * 0.35
    sand_mask = np.clip((ragged - 0.5) * 5.0 + 0.5, 0, 1)[:, :, None]
    sand_mask = np.asarray(Image.fromarray((sand_mask[:, :, 0] * 255).astype("uint8")).filter(
        ImageFilter.GaussianBlur(1.6)), dtype=np.float32)[:, :, None] / 255.0
    sand = np.zeros_like(base)
    sand[:] = (226, 200, 144)
    sand *= (0.93 + 0.12 * noise(200, 3) + 0.05 * noise(40, 4))[:, :, None]
    xs = np.arange(H, dtype=np.float32)[None, :]
    ys = np.arange(H, dtype=np.float32)[:, None]
    ripple = np.sin((xs * 0.55 + ys * 0.35) * 0.09 + noise(260, 6) * 14.0)  # wind ripples
    sand *= (1 + 0.022 * ripple)[:, :, None]
    sand += npr.normal(0, 3.5, sand.shape[:2])[:, :, None]
    lay(base, sand_mask, sand)

    # ---- park lawn ----
    cx, cy, w, h = cd.PARK
    m = Mask().rect(cx, cy, w, h, 14)
    lawn = m.result(blur=0.6)
    stripe = 1 + 0.05 * np.sin(xs * 0.35)
    lay(base, lawn, base * 1.14 * stripe[:, :, None] + np.array([4, 10, 0], dtype=np.float32))
    hedge = Mask().rect(cx, cy, w, h, 14).rect(cx, cy, w - 9, h - 9, 11, 0)
    lay(base, hedge.result(blur=0.4), (28, 98, 56))
    lay(base, Mask().rect(cx, cy + 1, w - 3, h - 4, 12).rect(cx, cy, w - 9, h - 9, 11, 0).result(blur=0.4), (66, 150, 84), 0.5)

    # ---- water: lake, stream (with a sandy bank) ----
    bank = Mask().line(cd.STREAM, cd.STREAM_WIDTH + 9).result(blur=2.5)
    lay(base, bank, (206, 186, 134))
    water_m = Mask().poly(cd.LAKE).line(cd.STREAM, cd.STREAM_WIDTH)
    water = water_m.result(blur=0.7)
    depth = np.clip(Mask().poly(cd.LAKE).result(blur=22) * 1.5, 0, 1)
    depth = np.maximum(depth, 0.55 * Mask().line(cd.STREAM, cd.STREAM_WIDTH).result(blur=0.7))
    shallow, deep = np.array([118, 206, 226], np.float32), np.array([34, 112, 184], np.float32)
    wcol = shallow + (deep - shallow) * depth
    wcol = wcol * (0.95 + 0.1 * noise(50, 8))[:, :, None]
    lay(base, water, wcol)
    foam = water * np.clip(1 - water_m.result(blur=6) * 1.2, 0, 1)
    lay(base, foam, (236, 248, 250), 0.75)
    wl = Image.new("RGBA", (H, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wl)
    lx = [p[0] for p in cd.LAKE]
    ly = [p[1] for p in cd.LAKE]
    for _ in range(120):  # sparkles and ripples
        x, y = rng.uniform(min(lx), max(lx)), rng.uniform(min(ly), max(ly))
        if cd.in_polygon(x, y, cd.LAKE) and cd.path_distance(x, y, cd.LAKE, True) > 8:
            px, py = (x + 600) * S, (600 - y) * S
            wd.arc([px - 7, py - 3, px + 7, py + 3], 200, 340, fill=(255, 255, 255, 120), width=2)
    for _ in range(7):  # lily pads
        x, y = rng.uniform(min(lx), max(lx)), rng.uniform(min(ly), max(ly))
        if cd.in_polygon(x, y, cd.LAKE) and cd.path_distance(x, y, cd.LAKE, True) > 14:
            px, py = (x + 600) * S, (600 - y) * S
            r = rng.uniform(5, 8) * S / 2
            wd.ellipse([px - r, py - r * 0.7, px + r, py + r * 0.7], fill=(60, 150, 80, 255))
            wd.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=(255, 170, 200, 255))

    # ---- dirt road ----
    edge = Mask().line(cd.DIRT_ROAD, cd.DIRT_WIDTH + 5).result(blur=1.8)
    lay(base, edge, (176, 142, 92), 0.75)
    dirt = Mask().line(cd.DIRT_ROAD, cd.DIRT_WIDTH).result(blur=0.8)
    dcol = np.zeros_like(base)
    dcol[:] = (204, 166, 112)
    dcol *= (0.92 + 0.14 * noise(30, 9))[:, :, None]
    lay(base, dirt, dcol)
    for side in (-3.4, 3.4):
        lay(base, Mask().line(offset_path(cd.DIRT_ROAD, side), 2.4).result(blur=0.8), (160, 124, 80), 0.7)

    # ---- paved roads ----
    paved = [r for r in cd.ROADS if r["kind"] != "dirt"]

    def road_union(extra):
        m = Mask()
        for r in paved:
            m.line(r["points"], r["width"] + extra, closed=r.get("closed", False))
        return m.result(blur=0.4)

    shade_m = road_union(cd.PAVE * 2 + 6)
    lay(base, shade_m, (0, 0, 0), 0.18)  # a soft shadow around the pavement
    side = np.zeros_like(base)
    side[:] = (178, 172, 160)
    side *= (0.95 + 0.08 * noise(24, 10))[:, :, None]
    lay(base, road_union(cd.PAVE * 2), side)
    lay(base, road_union(5), (214, 211, 203))
    asph = np.zeros_like(base)
    asph[:] = ASPHALT
    asph *= (0.94 + 0.1 * noise(18, 11))[:, :, None]
    asph += npr.normal(0, 2.5, asph.shape[:2])[:, :, None]
    lay(base, road_union(0), asph)

    # bridge where the stream crosses the ring road
    bx, by = cd.BRIDGE_AT
    lay(base, Mask().rect(bx, by, cd.RING_WIDTH + 2 * cd.PAVE + 4, cd.STREAM_WIDTH + 16, 2).result(blur=0.5), (196, 190, 178))
    lay(base, Mask().rect(bx, by, cd.RING_WIDTH, cd.STREAM_WIDTH + 16).result(blur=0.4), asph)
    for sx in (-1, 1):
        wall = Mask().rect(bx + sx * (cd.RING_WIDTH / 2 + 3.5), by, 5, cd.STREAM_WIDTH + 16, 1.5)
        lay(base, wall.result(blur=0.4), (150, 142, 128))
        lay(base, Mask().rect(bx + sx * (cd.RING_WIDTH / 2 + 3.5), by, 2, cd.STREAM_WIDTH + 14, 1).result(blur=0.4), (214, 208, 194))

    # road markings
    yellow, white = (244, 204, 64), (238, 238, 232)
    cuts_x = [-cd.RING_HALF] + cd.ROAD_X + [cd.RING_HALF]
    cuts_y = [-cd.RING_HALF] + cd.ROAD_Y + [cd.RING_HALF]
    yel = Mask()
    for x in cd.ROAD_X:  # double yellow line on the vertical avenues
        for a, b in zip(cuts_y[:-1], cuts_y[1:]):
            y0, y1 = a + 17, b - 17
            if y1 > y0:
                for o in (-1.5, 1.5):
                    yel.line([(x + o, y0), (x + o, y1)], 1.1)
    for y in cd.ROAD_Y:
        for a, b in zip(cuts_x[:-1], cuts_x[1:]):
            x0, x1 = a + 17, b - 17
            if x1 > x0:
                for o in (-1.5, 1.5):
                    yel.line([(x0, y + o), (x1, y + o)], 1.1)
    lay(base, yel.result(blur=0.3), yellow, 0.95)
    wm = Mask()
    for piece in dashes(cd.RING, 14, 12, closed=True):
        wm.line(piece, 1.5)
    for r in paved:
        if r["kind"] == "side":
            for piece in dashes(trim_path(r["points"], 22, 22), 10, 9):
                if len(piece) > 1:
                    wm.line(piece, 1.3)
    for r in paved:  # solid edge lines on the avenues
        if r["kind"] == "avenue":
            for o in (-cd.ROAD_WIDTH / 2 + 2.5, cd.ROAD_WIDTH / 2 - 2.5):
                (x0, y0), (x1, y1) = r["points"]
                if x0 == x1:
                    for a, b in zip(cuts_y[:-1], cuts_y[1:]):
                        wm.line([(x0 + o, a + 15), (x0 + o, b - 15)], 0.8)
                else:
                    for a, b in zip(cuts_x[:-1], cuts_x[1:]):
                        wm.line([(a + 15, y0 + o), (b - 15, y0 + o)], 0.8)
    lay(base, wm.result(blur=0.3), white, 0.8)
    zebra = Mask()
    for x in cd.ROAD_X:  # pedestrian crossings on the avenues
        for y in (-150, 150):
            for i in range(-4, 5):
                zebra.rect(x + i * 2.9, y, 1.7, 9)
    for y in cd.ROAD_Y:
        for x in (-157, 157):
            for i in range(-4, 5):
                zebra.rect(x, y + i * 2.9, 9, 1.7)
    lay(base, zebra.result(blur=0.3), white, 0.9)
    man = Mask()
    for x, y in ((112, 260), (-112, -260), (260, 105), (-260, -105), (-112, 380), (112, -380)):
        man.circle(x + 4, y, 3.4)
    lay(base, man.result(blur=0.4), (30, 31, 36), 0.9)

    # ---- plaza around the casino ----
    R = cd.PLAZA_R
    lay(base, Mask().circle(0, 0, R + 9).result(blur=7), (0, 0, 0), 0.3)
    xs_dp = (np.arange(H, dtype=np.float32)[None, :] / S) - cd.MAP_W / 2
    ys_dp = cd.MAP_H / 2 - (np.arange(H, dtype=np.float32)[:, None] / S)
    rr = np.sqrt(xs_dp ** 2 + ys_dp ** 2)
    checker = ((np.floor(xs_dp / 13) + np.floor(ys_dp / 13)) % 2)[:, :, None]
    plaza = np.where(checker > 0, np.array([224, 214, 194], np.float32), np.array([208, 197, 176], np.float32))
    plaza = plaza * (0.97 + 0.05 * noise(14, 12))[:, :, None]
    bands = [(148, 156, (196, 150, 56)), (140, 148, (122, 30, 46)), (136, 140, (232, 214, 150))]
    for lo, hi, colour in bands:
        sel = ((rr >= lo) & (rr < hi))[:, :, None]
        plaza = np.where(sel, np.array(colour, np.float32), plaza)
    def star_points(long_r, short_r, inner_r):
        pts = []
        for i in range(16):
            a = math.radians(i * 22.5)
            r = long_r if i % 4 == 0 else short_r if i % 2 == 0 else inner_r
            pts.append((r * math.cos(a), r * math.sin(a)))
        return pts
    lay(base, Mask().circle(0, 0, R).result(blur=0.6), plaza)
    lay(base, Mask().poly(star_points(134, 92, 34)).result(blur=0.5), (196, 150, 56))
    lay(base, Mask().poly(star_points(124, 84, 30)).result(blur=0.5), (142, 34, 50))
    lay(base, Mask().poly(star_points(70, 50, 24)).result(blur=0.5), (232, 214, 150))
    lay(base, Mask().circle(0, 0, 34).result(blur=0.5), (196, 150, 56))
    lay(base, Mask().circle(0, 0, 30).result(blur=0.5), (232, 214, 150))
    carpet = Mask().rect(0, -125, 26, 60)
    lay(base, carpet.result(blur=0.4), (200, 160, 60))
    lay(base, Mask().rect(0, -125, 22, 60).result(blur=0.4), (150, 24, 40))
    bulbs = Image.new("RGBA", (H, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bulbs)
    for i in range(36):
        a = math.radians(i * 10)
        px, py = (R - 4) * math.cos(a) * S + H / 2, H / 2 - (R - 4) * math.sin(a) * S
        bd.ellipse([px - 3.4, py - 3.4, px + 3.4, py + 3.4], fill=(255, 244, 176, 120))
        bd.ellipse([px - 1.6, py - 1.6, px + 1.6, py + 1.6], fill=(255, 252, 226, 255))

    # ---- park paths, fountain, flowers ----
    cx, cy, w, h = cd.PARK
    ring = [(cx + 70 * math.cos(t / 40 * 6.2832), cy + 38 * math.sin(t / 40 * 6.2832)) for t in range(40)]
    lay(base, Mask().line(ring, 11, closed=True).result(blur=0.5), (192, 172, 132))
    lay(base, Mask().line(ring, 8.5, closed=True).result(blur=0.5), (232, 216, 178))
    lay(base, Mask().line([(cx - 70, cy), (cx - w / 2 + 2, cy)], 8.5).result(blur=0.5), (232, 216, 178))
    lay(base, Mask().line([(cx + 70, cy), (cx + w / 2 - 2, cy)], 8.5).result(blur=0.5), (232, 216, 178))
    lay(base, Mask().circle(cx, cy, 25).result(blur=0.6), (160, 156, 148))
    lay(base, Mask().circle(cx, cy, 23).result(blur=0.6), (226, 222, 212))
    lay(base, Mask().circle(cx, cy, 17).result(blur=0.6), (92, 184, 226))
    lay(base, Mask().circle(cx, cy, 6).result(blur=0.6), (236, 248, 255))
    fl = ImageDraw.Draw(wl)
    for bx_, by_ in ((-38, 28), (38, 28), (-38, -28), (38, -28)):
        px, py = (cx + bx_ + 600) * S, (600 - (cy + by_)) * S
        fl.ellipse([px - 12 * S, py - 8.6 * S, px + 12 * S, py + 8.6 * S], fill=(26, 92, 52, 255))
        fl.ellipse([px - 10.6 * S, py - 7.4 * S, px + 10.6 * S, py + 7.4 * S], fill=(48, 128, 70, 255))
        palette = rng.sample([(255, 96, 128), (255, 214, 64), (200, 120, 240), (255, 255, 255), (255, 140, 60)], 3)
        for _ in range(70):
            a, rd = rng.uniform(0, 6.28), rng.uniform(0, 1) ** 0.5
            dx, dy = px + math.cos(a) * rd * 9.4 * S, py + math.sin(a) * rd * 6.4 * S
            fl.ellipse([dx - 2.6, dy - 2.6, dx + 2.6, dy + 2.6], fill=rng.choice(palette) + (255,))
            fl.ellipse([dx - 0.8, dy - 0.8, dx + 0.8, dy + 0.8], fill=(255, 240, 150, 255))

    # ---- parking lot ----
    px_, py_, pw, ph = cd.PARKING
    lay(base, Mask().rect(px_ - 5, py_ - ph / 2 - 8, 26, 18).result(blur=0.4), ASPHALT)
    lay(base, Mask().rect(px_, py_, pw + 6, ph + 6, 6).result(blur=0.5), (214, 211, 203))
    lay(base, Mask().rect(px_, py_, pw, ph, 4).result(blur=0.5), asph)
    pk = ImageDraw.Draw(wl)
    left, top = px_ - pw / 2, py_ + ph / 2
    bays = 8
    bay_w = (pw - 10) / bays
    cars = []
    for row, (y_top, y_bot) in enumerate(((top - 6, top - 6 - 32), (py_ - ph / 2 + 6 + 32, py_ - ph / 2 + 6))):
        for i in range(bays + 1):
            x = left + 5 + i * bay_w
            pk.line([((x + 600) * S, (600 - y_top) * S), ((x + 600) * S, (600 - y_bot) * S)], fill=(236, 236, 230, 230), width=2)
        for i in range(bays):
            if rng.random() < 0.65:
                cars.append((left + 5 + (i + 0.5) * bay_w, (y_top + y_bot) / 2, 90 if row == 0 else -90,
                             rng.choice(list(CAR_COLOURS.values()))))

    # ---- flower patches on the lawns ----
    for _ in range(130):
        x, y = rng.uniform(-590, 590), rng.uniform(-590, 590)
        if cd.in_desert(x, y) or cd.blocked(x, y, 5):
            continue
        colour = rng.choice([(255, 236, 140), (255, 255, 255), (255, 150, 180), (200, 150, 255)])
        for _ in range(7):
            dx, dy = (x + rng.uniform(-5, 5) + 600) * S, (600 - (y + rng.uniform(-4, 4))) * S
            fl.ellipse([dx - 1.7, dy - 1.7, dx + 1.7, dy + 1.7], fill=colour + (235,))

    # ---- done: stamp little things, save ----
    image = Image.fromarray(np.clip(base, 0, 255).astype("uint8"), "RGB").convert("RGBA")
    image.alpha_composite(wl)
    image.alpha_composite(bulbs)
    for x, y, angle, colour in cars:
        stamp = car_image(colour, final_w=int(24 * S)).rotate(angle, expand=True, resample=Image.BICUBIC)
        image.alpha_composite(stamp, (int((x + 600) * S - stamp.width / 2), int((600 - y) * S - stamp.height / 2)))
    image = image.convert("RGB")
    image.save(os.path.join(OUT, "ground.png"), optimize=True)
    return image


def main():
    os.makedirs(OUT, exist_ok=True)
    for fn in (make_palm, make_cactus, make_barrel, make_rock, make_dry, make_lamp,
               make_bench, make_umbrella, make_billboard, make_cars, make_cloud):
        fn()
    make_ground()
    print("done:", os.path.join(OUT, "ground.png"))


if __name__ == "__main__":
    main()
