"""Makes the pictures for the city screen: buildings, trees, grass, buttons, panels, icons.

Run once:  python make_city_assets.py   (needs Pillow and numpy)
Creates everything in assets/city/. The game only loads the PNG files, so this script
is needed only when you want to change how something looks.

Every picture is painted 3 times bigger and then shrunk, so the edges are smooth.
Coordinates in the drawing functions are "design units": a tile is 256 x 256 units.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "assets", "city")
FONT_TITLE = os.path.join(BASE, "assets", "fonts", "RussoOne-Regular.ttf")
FONT_SUITS = os.path.join(BASE, "assets", "fonts", "DejaVuSans-Bold.ttf")

SS = 3  # painted this many times bigger, then shrunk


def vgrad(width, height, top, bottom):
    width, height = max(1, int(width)), max(1, int(height))
    top = np.array(list(top) + [255] * (4 - len(top)), dtype=float)
    bottom = np.array(list(bottom) + [255] * (4 - len(bottom)), dtype=float)
    t = np.linspace(0, 1, height)[:, None, None]
    column = top * (1 - t) + bottom * t
    return Image.fromarray(np.broadcast_to(column, (height, width, 4)).astype("uint8"), "RGBA")


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


class Paint:
    """A canvas measured in design units; `final_w` is the width of the saved picture in pixels."""

    def __init__(self, width, height, final_w):
        self.k = final_w * SS / width
        self.final = (final_w, int(round(height * final_w / width)))
        self.size = (int(round(width * self.k)), int(round(height * self.k)))
        self.img = Image.new("RGBA", self.size, (0, 0, 0, 0))

    # --- helpers ---
    def u(self, value):
        return value * self.k

    def px(self, points):
        return [self.u(v) for v in points]

    def blank(self):
        return Image.new("RGBA", self.size, (0, 0, 0, 0))

    def add(self, layer):
        self.img.alpha_composite(layer)

    def draw_on_layer(self, fn):
        layer = self.blank()
        fn(ImageDraw.Draw(layer))
        return layer

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        out = self.img.resize(self.final, Image.LANCZOS)
        out.save(os.path.join(OUT, name), optimize=True)
        return out

    # --- masks and gradients ---
    def mask_rrect(self, x0, y0, x1, y1, r=0):
        mask = Image.new("L", self.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(self.px([x0, y0, x1, y1]), radius=self.u(r), fill=255)
        return mask

    def mask_poly(self, points):
        mask = Image.new("L", self.size, 0)
        flat = self.px([c for p in points for c in p])
        ImageDraw.Draw(mask).polygon(flat, fill=255)
        return mask

    def fill_gradient(self, mask, bbox, top, bottom):
        x0, y0, x1, y1 = [int(self.u(v)) for v in bbox]
        layer = self.blank()
        layer.paste(vgrad(x1 - x0, y1 - y0, top, bottom), (x0, y0))
        alpha = ImageChops.multiply(layer.getchannel("A"), mask)
        layer.putalpha(alpha)
        self.add(layer)

    def rrect_g(self, x0, y0, x1, y1, top, bottom, r=0):
        self.fill_gradient(self.mask_rrect(x0, y0, x1, y1, r), (x0, y0, x1, y1), top, bottom)

    def poly_g(self, points, top, bottom):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        self.fill_gradient(self.mask_poly(points), (min(xs), min(ys), max(xs), max(ys)), top, bottom)

    # --- plain shapes ---
    def rect(self, x0, y0, x1, y1, fill=None, r=0, outline=None, width=1):
        def fn(d):
            d.rounded_rectangle(
                self.px([x0, y0, x1, y1]), radius=self.u(r), fill=fill, outline=outline,
                width=max(1, int(self.u(width))),
            )
        self.add(self.draw_on_layer(fn))

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        def fn(d):
            d.ellipse(self.px([x0, y0, x1, y1]), fill=fill, outline=outline, width=max(1, int(self.u(width))))
        self.add(self.draw_on_layer(fn))

    def poly(self, points, fill=None, outline=None, width=1):
        flat = self.px([c for p in points for c in p])

        def fn(d):
            if fill is not None:
                d.polygon(flat, fill=fill)
            if outline is not None:
                d.line(flat + flat[:2], fill=outline, width=max(1, int(self.u(width))), joint="curve")
        self.add(self.draw_on_layer(fn))

    def line(self, points, fill, width=1):
        flat = self.px([c for p in points for c in p])
        self.add(self.draw_on_layer(
            lambda d: d.line(flat, fill=fill, width=max(1, int(self.u(width))), joint="curve")))

    def text(self, x, y, string, size, fill, font=FONT_TITLE, anchor="mm", stroke=0, stroke_fill=None):
        face = ImageFont.truetype(font, int(self.u(size)))

        def fn(d):
            d.text((self.u(x), self.u(y)), string, font=face, fill=fill, anchor=anchor,
                   stroke_width=int(self.u(stroke)), stroke_fill=stroke_fill)
        self.add(self.draw_on_layer(fn))

    # --- effects ---
    def shadow(self, fn, blur=6, alpha=0.45, dx=0, dy=0):
        """fn(draw, k) paints the shape in any colour; it becomes a soft black shadow."""
        layer = self.blank()
        fn(ImageDraw.Draw(layer))
        black = Image.new("RGBA", self.size, (0, 0, 0, 255))
        black.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        black = black.filter(ImageFilter.GaussianBlur(self.u(blur)))
        shifted = ImageChops.offset(black, int(self.u(dx)), int(self.u(dy)))
        self.add(shifted)

    def glow(self, fn, color, blur=5, strength=2):
        layer = self.blank()
        fn(ImageDraw.Draw(layer), color)
        halo = layer.filter(ImageFilter.GaussianBlur(self.u(blur)))
        for _ in range(strength):
            self.add(halo)
        self.add(layer)

    def bulbs(self, points, color=(255, 236, 160), size=2.2):
        """Row of glowing light bulbs."""
        def fn(d, c):
            for x, y in points:
                r = self.u(size)
                d.ellipse([self.u(x) - r, self.u(y) - r, self.u(x) + r, self.u(y) + r], fill=c + (255,))
        self.glow(fn, color, blur=2.4, strength=2)
        for x, y in points:
            r = self.u(size * 0.45)
            ImageDraw.Draw(self.img).ellipse(
                [self.u(x) - r, self.u(y) - r, self.u(x) + r, self.u(y) + r], fill=(255, 255, 255, 255))

    def neon_text(self, x, y, string, size, color, font=FONT_TITLE):
        face = ImageFont.truetype(font, int(self.u(size)))

        def fn(d, c):
            d.text((self.u(x), self.u(y)), string, font=face, fill=c + (255,), anchor="mm")
        self.glow(fn, color, blur=3.2, strength=2)
        core = mix(color, (255, 255, 255), 0.55)
        self.text(x, y, string, size, core + (255,), font)

    def window(self, x0, y0, x1, y1, lit=True, frame=(250, 246, 238), cross=True):
        self.rect(x0 - 1.6, y0 - 1.6, x1 + 1.6, y1 + 1.6, fill=frame + (255,), r=1.5)
        if lit:
            self.rrect_g(x0, y0, x1, y1, (255, 236, 150), (255, 178, 80), r=1)
        else:
            self.rrect_g(x0, y0, x1, y1, (96, 128, 170), (46, 66, 108), r=1)
        if cross:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            self.line([(mx, y0), (mx, y1)], frame + (255,), 1.1)
            self.line([(x0, my), (x1, my)], frame + (255,), 1.1)
        # a glint of light across the glass
        self.poly([(x0, y1), (x0 + (x1 - x0) * 0.35, y0), (x0 + (x1 - x0) * 0.55, y0), (x0 + (x1 - x0) * 0.2, y1)],
                  fill=(255, 255, 255, 46))

    def door(self, x0, y0, x1, y1, color=(110, 70, 40), glass=False):
        self.rect(x0 - 1.5, y0 - 1.5, x1 + 1.5, y1, fill=shade(color, 0.55) + (255,), r=2)
        self.rrect_g(x0, y0, x1, y1, shade(color, 1.25), shade(color, 0.8), r=1.5)
        if glass:
            self.rrect_g(x0 + 3, y0 + 3, x1 - 3, y1 - 12, (200, 235, 255), (110, 160, 210), r=1)
        self.ellipse(x1 - 6, (y0 + y1) / 2 - 1.5, x1 - 3, (y0 + y1) / 2 + 1.5, fill=(255, 215, 90, 255))

    def awning(self, x0, y0, x1, y1, c1, c2, stripe=11):
        """Striped awning with a scalloped edge."""
        n = max(1, int((x1 - x0) // stripe))
        w = (x1 - x0) / n
        mask = Image.new("L", self.size, 0)
        md = ImageDraw.Draw(mask)
        for i in range(n):
            xa, xb = x0 + i * w, x0 + (i + 1) * w
            md.polygon(self.px([xa, y0 - 2, xb, y0 - 2, xb, y1 - (xb - xa) / 2, xa, y1 - (xb - xa) / 2]), fill=255)
            md.pieslice(self.px([xa, y1 - w, xb, y1]), 0, 180, fill=255)
        layer = self.blank()
        ld = ImageDraw.Draw(layer)
        for i in range(n):
            xa, xb = x0 + i * w, x0 + (i + 1) * w
            color = c1 if i % 2 == 0 else c2
            ld.rectangle(self.px([xa, y0 - 2, xb, y1]), fill=color + (255,))
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        self.shadow(lambda d: d.rectangle(self.px([x0 + 2, y0, x1 + 2, y1]), fill=(0, 0, 0, 255)), blur=3, alpha=0.4, dy=4)
        self.add(layer)
        # shading on the awning
        top = self.blank()
        top.paste(vgrad(layer.width, int(self.u(y1 - y0)), (255, 255, 255, 70), (0, 0, 0, 40)), (0, int(self.u(y0))))
        top.putalpha(ImageChops.multiply(top.getchannel("A"), mask))
        self.add(top)

    def shingles(self, points, base, row=6.0, seed=1):
        """Fills a roof polygon with rows of shingles."""
        rng = random.Random(seed)
        mask = self.mask_poly(points)
        ys = [p[1] for p in points]
        xs = [p[0] for p in points]
        layer = self.blank()
        ld = ImageDraw.Draw(layer)
        y = min(ys)
        r = 0
        while y < max(ys):
            tone = 1.12 - 0.3 * ((y - min(ys)) / max(1, max(ys) - min(ys)))
            shift = (r % 2) * 5
            x = min(xs) - 10 + shift
            while x < max(xs) + 10:
                c = shade(base, tone * rng.uniform(0.92, 1.08))
                ld.rectangle(self.px([x, y, x + 10, y + row]), fill=c + (255,))
                ld.line(self.px([x + 10, y, x + 10, y + row]), fill=shade(base, 0.55) + (160,), width=max(1, int(self.u(0.6))))
                x += 10
            ld.line(self.px([min(xs) - 10, y + row, max(xs) + 10, y + row]), fill=shade(base, 0.5) + (170,),
                    width=max(1, int(self.u(0.8))))
            y += row
            r += 1
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        self.add(layer)


# ----- ground for a building: the paved lot -----


def lot(p, w=256, h=256, border=(196, 168, 90)):
    p.shadow(lambda d: d.rounded_rectangle(p.px([10, 14, w - 4, h - 2]), radius=p.u(26), fill=(0, 0, 0, 255)),
             blur=5, alpha=0.5)
    p.rrect_g(5, 5, w - 5, h - 5, (205, 200, 188), (150, 146, 138), r=26)
    # paving stones
    layer = p.blank()
    d = ImageDraw.Draw(layer)
    step = 32
    for x in range(5 + step, w - 5, step):
        d.line(p.px([x, 8, x, h - 8]), fill=(90, 86, 80, 60), width=max(1, int(p.u(0.8))))
    for y in range(5 + step, h - 5, step):
        d.line(p.px([8, y, w - 8, y]), fill=(90, 86, 80, 60), width=max(1, int(p.u(0.8))))
    mask = p.mask_rrect(5, 5, w - 5, h - 5, 26)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    p.add(layer)
    p.rect(5, 5, w - 5, h - 5, outline=(92, 88, 82, 255), r=26, width=2.4)
    p.rect(9, 9, w - 9, h - 9, outline=border + (150,), r=22, width=1.2)


def building_shadow(p, x0, y0, x1, y1, dx=9, dy=6):
    p.shadow(lambda d: d.rectangle(p.px([x0 + dx, y0 + dy + 8, x1 + dx, y1 + dy]), fill=(0, 0, 0, 255)),
             blur=5, alpha=0.32)


def dome(p, cx, base_y, rx, ry, top, bottom, ribs=5):
    """A half-ball dome sitting on a flat base line."""
    box = (cx - rx, base_y - ry, cx + rx, base_y + ry)
    mask = Image.new("L", p.size, 0)
    ImageDraw.Draw(mask).pieslice(p.px(list(box)), 180, 360, fill=255)
    p.fill_gradient(mask, (cx - rx, base_y - ry, cx + rx, base_y), top, bottom)
    layer = p.blank()
    d = ImageDraw.Draw(layer)
    for i in range(1, ribs):
        t = -1 + 2 * i / ribs
        d.line(p.px([cx + t * rx * 0.15, base_y - ry, cx + t * rx, base_y]), fill=shade(bottom, 0.7) + (130,),
               width=max(1, int(p.u(1.1))))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    p.add(layer)
    p.ellipse(cx - rx * 0.62, base_y - ry * 0.86, cx - rx * 0.12, base_y - ry * 0.4, fill=(255, 255, 255, 80))


def wall(p, x0, y0, x1, y1, top, bottom, outline=None):
    p.rrect_g(x0, y0, x1, y1, top, bottom, r=1.5)
    # light on the left edge, dark on the right
    p.rect(x0, y0, x0 + 2.4, y1, fill=(255, 255, 255, 60))
    p.rect(x1 - 3.2, y0, x1, y1, fill=(0, 0, 0, 55))
    p.rect(x0, y1 - 3, x1, y1, fill=(0, 0, 0, 70))
    if outline:
        p.rect(x0, y0, x1, y1, outline=outline + (255,), r=1.5, width=1.2)


def roof_top(p, back, front, top_color, bottom_color):
    """Roof seen from above: a trapezoid, narrower at the back."""
    (bx0, by), (bx1, _) = back
    (fx0, fy), (fx1, _) = front
    p.poly_g([(bx0, by), (bx1, by), (fx1, fy), (fx0, fy)], top_color, bottom_color)
    p.line([(bx0, by), (fx0, fy)], (255, 255, 255, 80), 1.2)
    p.line([(bx0, by), (bx1, by)], (255, 255, 255, 90), 1.2)


# ----- the buildings -----


def make_diner():
    p = Paint(256, 256, 320)
    lot(p)
    building_shadow(p, 42, 112, 214, 200)
    # back roof edge, then the roof from above
    roof_top(p, ((56, 104), (200, 104)), ((42, 126), (214, 126)), (236, 124, 76), (206, 88, 52))
    for x in (74, 164):
        p.rect(x, 108, x + 18, 120, fill=(150, 150, 156, 255), r=2)
        p.rect(x + 2, 109, x + 16, 112, fill=(200, 200, 206, 255), r=1)
    p.rrect_g(42, 126, 214, 138, (188, 66, 40), (146, 44, 28), r=1)
    wall(p, 46, 138, 210, 200, (255, 240, 205), (232, 204, 156))
    # tile band
    for i in range(0, 164, 8):
        p.rect(46 + i, 188, 46 + i + 4, 196, fill=(214, 90, 60, 255))
        p.rect(46 + i + 4, 188, 46 + i + 8, 196, fill=(255, 245, 225, 255))
    p.awning(46, 138, 210, 160, (214, 56, 52), (255, 246, 232))
    p.window(58, 164, 100, 190)
    p.window(156, 164, 198, 190)
    p.door(112, 162, 144, 200, color=(40, 120, 130), glass=True)
    # sign on the roof
    p.rect(98, 56, 102, 108, fill=(110, 90, 70, 255))
    p.rect(154, 56, 158, 108, fill=(110, 90, 70, 255))
    p.rrect_g(84, 50, 172, 92, (150, 30, 36), (96, 16, 26), r=7)
    p.rect(84, 50, 172, 92, outline=(255, 205, 80, 255), r=7, width=2)
    p.neon_text(128, 72, "ЕДА", 27, (255, 214, 90))
    p.bulbs([(90 + i * 10.5, 54) for i in range(8)], size=1.7)
    p.save("diner.png")


def make_motel():
    p = Paint(256, 256, 320)
    lot(p)
    building_shadow(p, 30, 110, 226, 200)
    roof_top(p, ((48, 96), (208, 96)), ((32, 118), (224, 118)), (92, 190, 200), (46, 140, 160))
    p.rrect_g(32, 118, 224, 128, (34, 110, 130), (24, 84, 104), r=1)
    wall(p, 36, 128, 220, 200, (236, 246, 252), (196, 222, 236))
    p.rect(36, 160, 220, 166, fill=(40, 100, 130, 255))  # balcony floor line
    bay = (220 - 36) / 5
    for i in range(5):
        x = 36 + i * bay
        # upper floor: window + door
        p.window(x + 6, 134, x + 18, 154, frame=(255, 255, 255))
        p.door(x + 22, 134, x + 33, 160, color=(40, 110, 140))
        p.text(x + 27.5, 130.5, str(201 + i), 5.5, (30, 70, 100, 255), font=FONT_SUITS)
        # lower floor
        p.window(x + 6, 172, x + 18, 192, frame=(255, 255, 255))
        p.door(x + 22, 170, x + 33, 200, color=(190, 90, 60))
        p.text(x + 27.5, 167.5, str(101 + i), 5.5, (30, 70, 100, 255), font=FONT_SUITS)
    # balcony railing
    p.line([(36, 150), (220, 150)], (255, 255, 255, 230), 1.4)
    for i in range(0, 185, 7):
        p.line([(36 + i, 150), (36 + i, 160)], (255, 255, 255, 200), 0.9)
    # roof sign
    p.rect(60, 62, 64, 100, fill=(90, 100, 110, 255))
    p.rect(192, 62, 196, 100, fill=(90, 100, 110, 255))
    p.rrect_g(48, 48, 208, 80, (20, 40, 66), (10, 22, 42), r=7)
    p.rect(48, 48, 208, 80, outline=(120, 230, 255, 255), r=7, width=2)
    p.neon_text(124, 64, "МОТЕЛЬ", 22, (110, 225, 255))
    p.poly([(180, 56), (196, 64), (180, 72)], fill=(255, 120, 190, 255))
    p.save("motel.png")


def make_bar():
    p = Paint(256, 256, 320)
    lot(p)
    building_shadow(p, 40, 100, 216, 200)
    roof_top(p, ((62, 90), (194, 90)), ((44, 120), (212, 120)), (110, 70, 150), (70, 38, 106))
    p.shingles([(62, 90), (194, 90), (212, 120), (44, 120)], (96, 58, 136), row=6, seed=3)
    p.rrect_g(44, 120, 212, 130, (60, 30, 90), (40, 18, 66), r=1)
    wall(p, 48, 130, 208, 200, (178, 74, 128), (120, 40, 92))
    # bricks
    layer = p.blank()
    d = ImageDraw.Draw(layer)
    for r_i, y in enumerate(range(131, 200, 7)):
        d.line(p.px([48, y, 208, y]), fill=(70, 20, 50, 120), width=max(1, int(p.u(0.7))))
        for x in range(48 + (r_i % 2) * 8, 208, 16):
            d.line(p.px([x, y, x, y + 7]), fill=(70, 20, 50, 100), width=max(1, int(p.u(0.7))))
    p.add(layer)
    # big window with neon
    p.rect(58, 144, 112, 194, fill=(40, 20, 50, 255), r=4)
    p.rrect_g(61, 147, 109, 191, (255, 170, 96), (200, 90, 90), r=3)
    p.rect(61, 147, 109, 191, outline=(255, 210, 140, 255), r=3, width=1)
    for x in (72, 90):
        p.ellipse(x, 160, x + 14, 190, fill=(60, 20, 50, 200))  # silhouettes of bottles
    p.neon_text(85, 156, "BAR", 17, (255, 90, 170), font=FONT_TITLE)
    # door
    p.door(138, 146, 176, 200, color=(86, 48, 40), glass=False)
    p.ellipse(150, 156, 164, 170, fill=(255, 200, 110, 255))
    p.awning(130, 132, 184, 148, (120, 40, 140), (230, 190, 245), stripe=9)
    # hanging sign and barrels
    p.rrect_g(184, 150, 206, 176, (40, 20, 50), (24, 10, 34), r=3)
    p.rect(184, 150, 206, 176, outline=(255, 90, 170, 255), r=3, width=1.4)
    p.text(195, 163, "♪", 18, (255, 160, 215, 255), font=FONT_SUITS)
    for x in (212, 226):
        p.shadow(lambda d, x=x: d.ellipse(p.px([x - 8, 188, x + 8, 206]), fill=(0, 0, 0, 255)), blur=2, alpha=0.5, dx=2, dy=2)
        p.rrect_g(x - 8, 178, x + 8, 202, (190, 128, 70), (120, 76, 40), r=6)
        p.line([(x - 8, 185), (x + 8, 185)], (60, 40, 30, 255), 1.4)
        p.line([(x - 8, 195), (x + 8, 195)], (60, 40, 30, 255), 1.4)
    p.save("bar.png")


def make_hotel():
    p = Paint(256, 256, 320)
    lot(p)
    building_shadow(p, 44, 60, 212, 200, dx=18, dy=10)
    # side wings
    for x0, x1 in ((40, 84), (172, 216)):
        p.poly_g([(x0 + 4, 150), (x1 - 4, 150), (x1, 160), (x0, 160)], (240, 232, 214), (200, 190, 170))
        wall(p, x0, 160, x1, 200, (96, 140, 220), (58, 96, 170))
        p.window(x0 + 6, 170, x0 + 16, 188, frame=(220, 230, 245))
        p.window(x1 - 16, 170, x1 - 6, 188, frame=(220, 230, 245))
    # tower
    p.poly_g([(92, 46), (164, 46), (176, 62), (80, 62)], (232, 240, 250), (176, 192, 222))
    p.line([(92, 46), (80, 62)], (255, 255, 255, 120), 1.2)
    p.rect(110, 34, 146, 48, fill=(150, 160, 190, 255), r=2)
    p.rrect_g(120, 24, 136, 38, (120, 130, 160), (80, 90, 120), r=2)
    p.line([(128, 24), (128, 6)], (190, 196, 210, 255), 2)
    p.bulbs([(128, 6)], color=(255, 90, 80), size=3)
    wall(p, 80, 62, 176, 200, (92, 138, 224), (44, 78, 158))
    rng = random.Random(5)
    for row in range(7):
        for col in range(4):
            x = 87 + col * 22
            y = 94 + row * 15
            p.window(x, y, x + 14, y + 9, lit=rng.random() > 0.35, frame=(200, 214, 240), cross=False)
    # name plate and entrance
    p.rrect_g(88, 68, 168, 86, (30, 54, 110), (18, 34, 76), r=4)
    p.rect(88, 68, 168, 86, outline=(255, 205, 80, 255), r=4, width=1.6)
    p.neon_text(128, 77.5, "ОТЕЛЬ", 14, (255, 214, 90))
    p.poly_g([(94, 170), (162, 170), (170, 182), (86, 182)], (255, 214, 96), (214, 150, 40))
    p.rect(96, 182, 160, 200, fill=(30, 40, 70, 255))
    p.rrect_g(100, 184, 156, 200, (200, 235, 255), (110, 160, 210), r=2)
    p.line([(128, 184), (128, 200)], (60, 80, 120, 255), 1.4)
    p.rect(120, 200, 136, 218, fill=(200, 40, 56, 255))
    p.bulbs([(98 + i * 8, 171.5) for i in range(9)], size=1.5)
    p.save("hotel.png")


def make_theater():
    p = Paint(256, 256, 320)
    lot(p)
    building_shadow(p, 38, 76, 218, 200)
    # dome behind
    dome(p, 128, 92, 36, 52, (255, 236, 150), (204, 140, 40), ribs=5)
    p.line([(128, 42), (128, 24)], (255, 215, 90, 255), 2)
    p.ellipse(123, 17, 133, 27, fill=(255, 215, 90, 255))
    # pediment
    p.poly_g([(34, 124), (128, 66), (222, 124)], (206, 60, 70), (150, 30, 44))
    p.poly_g([(52, 120), (128, 76), (204, 120)], (238, 96, 100), (184, 52, 62))
    p.line([(34, 124), (128, 66), (222, 124)], (255, 215, 120, 255), 2)
    p.ellipse(113, 88, 143, 118, fill=(255, 214, 96, 255), outline=(150, 100, 20, 255), width=1.6)
    p.text(128, 103, "♪", 24, (150, 30, 44, 255), font=FONT_SUITS)
    # building and columns
    wall(p, 42, 124, 214, 200, (252, 240, 214), (226, 206, 170))
    p.rrect_g(38, 122, 218, 134, (255, 214, 96), (214, 156, 44), r=1)
    p.door(110, 154, 146, 200, color=(150, 30, 44), glass=False)
    p.rrect_g(112, 156, 144, 170, (255, 226, 130), (230, 170, 60), r=2)
    for x in (50, 76, 168, 194):
        p.shadow(lambda d, x=x: d.rectangle(p.px([x + 3, 134, x + 17, 200]), fill=(0, 0, 0, 255)), blur=2, alpha=0.4, dx=3)
        p.rrect_g(x, 134, x + 14, 200, (255, 252, 244), (212, 200, 176), r=2)
        p.rect(x - 2, 134, x + 16, 140, fill=(236, 220, 186, 255), r=1.5)
        p.rect(x - 2, 194, x + 16, 200, fill=(236, 220, 186, 255), r=1.5)
        p.line([(x + 4, 140), (x + 4, 194)], (190, 176, 150, 150), 0.9)
        p.line([(x + 9, 140), (x + 9, 194)], (190, 176, 150, 150), 0.9)
    # marquee over the door
    p.rrect_g(94, 138, 162, 154, (40, 14, 26), (26, 8, 16), r=3)
    p.rect(94, 138, 162, 154, outline=(255, 205, 80, 255), r=3, width=1.4)
    p.neon_text(128, 146.5, "ШОУ", 11, (255, 214, 90))
    # steps
    for i, (x0, x1) in enumerate(((52, 204), (58, 198), (64, 192))):
        y = 200 + i * 5
        p.rrect_g(x0, y, x1, y + 5, (236, 232, 224), (190, 184, 172), r=1)
    p.save("theater.png")


def make_casino():
    p = Paint(300, 250, 600)
    # the plaza
    p.shadow(lambda d: d.rounded_rectangle(p.px([8, 12, 298, 248]), radius=p.u(34), fill=(0, 0, 0, 255)), blur=6, alpha=0.5)
    p.rrect_g(3, 3, 297, 245, (190, 184, 176), (130, 126, 120), r=34)
    p.rect(3, 3, 297, 245, outline=(80, 76, 70, 255), r=34, width=2.6)
    p.rect(8, 8, 292, 240, outline=(214, 170, 70, 200), r=29, width=1.4)
    layer = p.blank()
    d = ImageDraw.Draw(layer)
    for x in range(35, 297, 32):
        d.line(p.px([x, 8, x, 240]), fill=(80, 76, 70, 55), width=max(1, int(p.u(0.8))))
    for y in range(35, 245, 32):
        d.line(p.px([8, y, 292, y]), fill=(80, 76, 70, 55), width=max(1, int(p.u(0.8))))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), p.mask_rrect(3, 3, 297, 245, 34)))
    p.add(layer)
    # red carpet
    p.rect(132, 190, 168, 246, fill=(168, 20, 44, 255))
    p.rect(132, 190, 135, 246, fill=(255, 205, 80, 255))
    p.rect(165, 190, 168, 246, fill=(255, 205, 80, 255))
    for y in (214, 234):
        p.rect(124, y, 130, y + 6, fill=(255, 205, 80, 255), r=3)
        p.rect(170, y, 176, y + 6, fill=(255, 205, 80, 255), r=3)

    building_shadow(p, 22, 70, 278, 196, dx=18, dy=10)

    # side wings
    for x0, x1 in ((22, 78), (222, 278)):
        p.poly_g([(x0 + 5, 122), (x1 - 5, 122), (x1, 138), (x0, 138)], (255, 222, 120), (214, 158, 50))
        wall(p, x0, 138, x1, 196, (160, 34, 58), (104, 16, 38))
        p.rect(x0, 138, x1, 143, fill=(255, 205, 80, 255))
        p.rect(x0, 190, x1, 196, fill=(255, 205, 80, 255))
        p.window(x0 + 8, 152, x0 + 22, 178, frame=(255, 214, 96))
        p.window(x1 - 22, 152, x1 - 8, 178, frame=(255, 214, 96))
        p.bulbs([(x0 + 6 + i * 9, 140.5) for i in range(int((x1 - x0 - 6) // 9))], size=1.4)
    # towers at the corners of the wings
    for cx in (22, 278):
        p.rrect_g(cx - 9, 100, cx + 9, 196, (255, 226, 130), (190, 130, 40), r=3)
        p.poly_g([(cx - 12, 102), (cx + 12, 102), (cx, 78)], (255, 236, 150), (214, 150, 44))
        p.bulbs([(cx, 76)], color=(255, 120, 120), size=2.6)

    # main block: roof from above, dome, wall
    p.poly_g([(92, 82), (208, 82), (232, 108), (68, 108)], (255, 226, 130), (214, 160, 52))
    p.line([(92, 82), (68, 108)], (255, 255, 255, 120), 1.6)
    p.line([(92, 82), (208, 82)], (255, 255, 255, 120), 1.6)
    # drum and dome
    p.rrect_g(112, 70, 188, 100, (232, 184, 72), (176, 116, 36), r=3)
    for x in range(120, 188, 12):
        p.rrect_g(x, 76, x + 6, 96, (255, 236, 160), (222, 160, 60), r=3)
    p.rect(108, 66, 192, 74, fill=(255, 214, 96, 255), r=3)
    dome(p, 150, 68, 46, 40, (255, 240, 160), (206, 140, 40), ribs=6)
    p.line([(150, 30), (150, 12)], (255, 215, 90, 255), 2.4)
    p.glow(lambda d, c: d.ellipse(p.px([142, 2, 158, 18]), fill=c + (255,)), (255, 70, 90), blur=4, strength=2)
    p.ellipse(144, 4, 156, 16, fill=(255, 60, 80, 255), outline=(255, 215, 90, 255), width=1.4)
    # wall
    wall(p, 68, 108, 232, 196, (176, 38, 64), (112, 16, 40))
    p.rect(68, 108, 232, 114, fill=(255, 205, 80, 255))
    p.rect(68, 190, 232, 196, fill=(255, 205, 80, 255))
    p.bulbs([(72 + i * 8, 111) for i in range(20)], size=1.5)
    # windows on both sides of the entrance
    for x in (80, 100):
        p.window(x, 150, x + 14, 176, frame=(255, 214, 96))
    for x in (186, 206):
        p.window(x, 150, x + 14, 176, frame=(255, 214, 96))
    # sign
    p.shadow(lambda d: d.rounded_rectangle(p.px([88, 122, 212, 148]), radius=p.u(6), fill=(0, 0, 0, 255)), blur=3, alpha=0.5, dx=2, dy=3)
    p.rrect_g(86, 118, 214, 146, (30, 10, 22), (14, 4, 12), r=6)
    p.rect(86, 118, 214, 146, outline=(255, 205, 80, 255), r=6, width=2)
    p.neon_text(150, 132.5, "КАЗИНО", 21, (255, 214, 90))
    # entrance: arch with golden light
    p.glow(lambda d, c: d.rounded_rectangle(p.px([126, 154, 174, 196]), radius=p.u(20), fill=c + (255,)), (255, 200, 90), blur=5, strength=1)
    p.rrect_g(124, 152, 176, 196, (255, 205, 80), (214, 140, 40), r=22)
    p.rrect_g(130, 158, 170, 196, (255, 244, 196), (255, 196, 96), r=18)
    p.line([(150, 160), (150, 196)], (170, 100, 30, 255), 1.6)
    p.text(138, 176, "♠", 11, (150, 20, 40, 255), font=FONT_SUITS)
    p.text(162, 176, "♦", 11, (190, 20, 40, 255), font=FONT_SUITS)
    # suits on the wings
    p.save("casino.png")


# ----- the empty plot -----


def make_plot_empty():
    p = Paint(256, 256, 320)
    p.shadow(lambda d: d.rounded_rectangle(p.px([10, 14, 252, 254]), radius=p.u(26), fill=(0, 0, 0, 255)), blur=5, alpha=0.4)
    p.rrect_g(5, 5, 251, 251, (92, 122, 96), (62, 92, 70), r=26)  # a grassy patch, a bit lighter than the ground
    p.rect(5, 5, 251, 251, outline=(30, 56, 40, 255), r=26, width=2.4)
    # dashed golden outline
    layer = p.blank()
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1, r = 14, 14, 242, 242, 20
    segments = 38
    d.rounded_rectangle(p.px([x0, y0, x1, y1]), radius=p.u(r), outline=(255, 214, 96, 220), width=int(p.u(2.2)))
    mask = Image.new("L", p.size, 255)
    md = ImageDraw.Draw(mask)
    perimeter = 4 * (x1 - x0 - 2 * r) + 2 * math.pi * r
    # cut small gaps along the outline to make it look dashed
    cx, cy = 128, 128
    for i in range(segments):
        a = 2 * math.pi * (i + 0.5) / segments
        px_ = cx + math.cos(a) * 140
        py_ = cy + math.sin(a) * 140
        md.ellipse(p.px([px_ - 5, py_ - 5, px_ + 5, py_ + 5]), fill=0)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    p.add(layer)
    # the plus button
    p.shadow(lambda d: d.ellipse(p.px([84, 88, 172, 176]), fill=(0, 0, 0, 255)), blur=4, alpha=0.5, dy=3)
    p.glow(lambda d, c: d.ellipse(p.px([82, 82, 174, 174]), fill=c + (255,)), (255, 200, 70), blur=7, strength=1)
    p.rrect_g(82, 82, 174, 174, (255, 226, 120), (232, 160, 40), r=46)
    p.rect(82, 82, 174, 174, outline=(150, 90, 20, 255), r=46, width=2)
    p.ellipse(94, 88, 150, 120, fill=(255, 255, 255, 70))
    p.rect(124, 102, 132, 154, fill=(255, 255, 255, 255), r=4)
    p.rect(102, 124, 154, 132, fill=(255, 255, 255, 255), r=4)
    p.save("plot_empty.png")


# ----- trees and grass -----


def make_tree(name, kind, seed):
    rng = random.Random(seed)
    p = Paint(100, 100, 100)
    p.shadow(lambda d: d.ellipse(p.px([20, 52, 90, 96]), fill=(0, 0, 0, 255)), blur=4, alpha=0.4)
    if kind == "pine":
        p.rect(46, 66, 54, 84, fill=(96, 62, 36, 255), r=2)
        for i, (w, y) in enumerate(((40, 58), (32, 40), (24, 24))):
            p.poly_g([(50 - w / 2 - 4, y + 22), (50 + w / 2 + 4, y + 22), (50, y - 4)],
                     (60, 150, 90), (22, 88, 56))
            p.poly([(50, y - 4), (50 - w / 2 - 4, y + 22), (50 - w / 4, y + 22)], fill=(255, 255, 255, 40))
    else:
        p.rect(45, 62, 55, 86, fill=(104, 68, 38, 255), r=3)
        body = (70, 168, 86) if kind == "round" else (180, 90, 100)
        spots = [(50, 40, 30), (30, 52, 22), (70, 52, 22), (50, 62, 22), (38, 36, 18), (62, 36, 18)]
        for (x, y, r) in spots:
            p.ellipse(x - r, y - r, x + r, y + r, fill=shade(body, 0.7) + (255,))
        for (x, y, r) in spots:
            p.rrect_g(x - r + 2, y - r, x + r - 2, y + r - 3, shade(body, 1.18), shade(body, 0.86), r=r)
        for _ in range(9):
            x, y = rng.uniform(26, 74), rng.uniform(22, 62)
            p.ellipse(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill=shade(body, 1.4) + (170,))
        if kind == "pink":
            for _ in range(14):
                x, y = rng.uniform(24, 76), rng.uniform(20, 66)
                p.ellipse(x - 2, y - 2, x + 2, y + 2, fill=(255, 226, 236, 230))
    p.save(name)


def make_bush():
    p = Paint(60, 60, 60)
    p.shadow(lambda d: d.ellipse(p.px([8, 30, 56, 54]), fill=(0, 0, 0, 255)), blur=3, alpha=0.4)
    for x, y, r in ((22, 36, 14), (38, 36, 14), (30, 28, 14)):
        p.ellipse(x - r, y - r, x + r, y + r, fill=(30, 100, 60, 255))
    for x, y, r in ((22, 34, 12), (38, 34, 12), (30, 26, 12)):
        p.rrect_g(x - r, y - r, x + r, y + r, (96, 180, 98), (50, 132, 70), r=r)
    p.save("bush.png")


def make_grass():
    size = 256
    rng = np.random.default_rng(11)
    base = np.array([34, 116, 70], dtype=float)
    noise = rng.random((16, 16))
    big = np.kron(noise, np.ones((16, 16)))
    for _ in range(3):  # blur that wraps around the edges, so the tile joins itself
        big = (big + np.roll(big, 5, 0) + np.roll(big, -5, 0) + np.roll(big, 5, 1) + np.roll(big, -5, 1)) / 5
    big = (big - big.min()) / (big.max() - big.min())
    img = np.zeros((size, size, 3))
    for c in range(3):
        img[:, :, c] = base[c] * (0.86 + 0.26 * big)
    image = Image.fromarray(img.clip(0, 255).astype("uint8"), "RGB").convert("RGBA")
    draw = ImageDraw.Draw(image)
    py = random.Random(4)
    for _ in range(700):  # little grass blades; each is drawn again shifted so it wraps around
        x, y = py.uniform(0, size), py.uniform(0, size)
        tone = py.choice([(24, 92, 56), (52, 146, 84), (64, 160, 92), (20, 80, 50)])
        h = py.uniform(3, 7)
        for ox in (-size, 0, size):
            for oy in (-size, 0, size):
                draw.line([x + ox, y + oy, x + ox + py.uniform(-1.5, 1.5), y + oy - h], fill=tone + (200,), width=1)
    for _ in range(26):  # tiny flowers
        x, y = py.uniform(0, size), py.uniform(0, size)
        c = py.choice([(255, 236, 140), (255, 255, 255), (255, 170, 190)])
        draw.ellipse([x - 1.2, y - 1.2, x + 1.2, y + 1.2], fill=c + (230,))
    image.convert("RGB").save(os.path.join(OUT, "grass.png"), optimize=True)


# ----- buttons and panels (stretchable: the corners stay round) -----


def make_button():
    size = 96
    p = Paint(size, size, size)
    # white-ish body: the game tints it with the button colour
    p.rrect_g(2, 3, size - 2, size - 2, (255, 255, 255), (178, 178, 178), r=34)
    p.rect(2, 3, size - 2, size - 2, outline=(0, 0, 0, 90), r=34, width=1.6)
    layer = p.blank()
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(p.px([6, 6, size - 6, size * 0.52]), radius=p.u(28), fill=(255, 255, 255, 70))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), p.mask_rrect(2, 3, size - 2, size - 2, 34)))
    p.add(layer)
    p.rect(5, size - 14, size - 5, size - 5, fill=(0, 0, 0, 38), r=14)
    p.save("btn.png")


def make_panel():
    size = 96
    p = Paint(size, size, size)
    p.rrect_g(2, 2, size - 2, size - 2, (22, 34, 46, 245), (8, 16, 24, 250), r=30)
    p.rect(2, 2, size - 2, size - 2, outline=(255, 205, 80, 150), r=30, width=2)
    p.rect(6, 6, size - 6, size - 6, outline=(255, 255, 255, 22), r=26, width=1)
    p.save("panel.png")


def make_card():
    size = 96
    p = Paint(size, size, size)
    p.rrect_g(2, 2, size - 2, size - 2, (38, 54, 70, 255), (24, 36, 50, 255), r=26)
    p.rect(2, 2, size - 2, size - 2, outline=(255, 255, 255, 36), r=26, width=1.4)
    p.save("card.png")


# ----- landmark icons -----


def make_landmarks():
    gold = (255, 214, 96)

    def base(name):
        p = Paint(96, 96, 96)
        p.ellipse(10, 76, 86, 92, fill=(0, 0, 0, 80))
        return p

    # fountain
    p = base("fountain")
    p.rrect_g(14, 62, 82, 82, (230, 226, 216), (160, 154, 142), r=9)
    p.rrect_g(18, 58, 78, 70, (110, 200, 240), (60, 140, 200), r=6)
    p.rrect_g(42, 36, 54, 64, (230, 226, 216), (170, 164, 150), r=3)
    p.rrect_g(30, 38, 66, 46, (230, 226, 216), (170, 164, 150), r=4)
    for x, y in ((48, 14), (36, 22), (60, 22), (28, 34), (68, 34)):
        p.ellipse(x - 3, y - 3, x + 3, y + 3, fill=(170, 225, 255, 230))
    p.line([(48, 36), (48, 16)], (170, 225, 255, 220), 3)
    p.save("lm_fountain.png")

    # ferris wheel
    p = base("wheel")
    p.line([(48, 86), (30, 40)], (200, 200, 210, 255), 4)
    p.line([(48, 86), (66, 40)], (200, 200, 210, 255), 4)
    p.ellipse(16, 8, 80, 72, outline=gold + (255,), width=4)
    p.ellipse(28, 20, 68, 60, outline=gold + (160,), width=2)
    for i in range(8):
        a = i * math.pi / 4
        p.line([(48, 40), (48 + 32 * math.cos(a), 40 + 32 * math.sin(a))], gold + (210,), 1.6)
        cx, cy = 48 + 32 * math.cos(a), 40 + 32 * math.sin(a)
        p.ellipse(cx - 5, cy - 5, cx + 5, cy + 5, fill=[(255, 90, 100), (90, 190, 255), (120, 230, 140), (255, 160, 60)][i % 4] + (255,))
    p.ellipse(42, 34, 54, 46, fill=gold + (255,))
    p.save("lm_wheel.png")

    # neon sign (star)
    p = base("sign")
    p.rect(44, 52, 52, 86, fill=(130, 130, 140, 255), r=2)
    p.glow(lambda d, c: d.polygon(p.px([v for pt in _star(48, 34, 30, 13) for v in pt]), fill=c + (255,)), (255, 90, 170), blur=5, strength=2)
    p.poly(_star(48, 34, 28, 12), fill=(255, 120, 190, 255), outline=(255, 235, 250, 255), width=2)
    p.save("lm_sign.png")

    # tower
    p = base("tower")
    p.poly_g([(36, 86), (60, 86), (54, 34), (42, 34)], (214, 218, 232), (120, 130, 160))
    p.rrect_g(26, 20, 70, 36, (255, 226, 130), (214, 150, 40), r=7)
    p.poly_g([(36, 20), (60, 20), (48, 4)], (255, 226, 130), (214, 150, 40))
    p.line([(48, 4), (48, 0)], (255, 215, 90, 255), 2)
    for y in (46, 58, 70):
        p.rect(44, y, 52, y + 5, fill=(255, 226, 130, 255), r=1.5)
    p.save("lm_tower.png")

    # mega resort (crown)
    p = base("resort")
    p.poly_g([(14, 74), (82, 74), (86, 28), (64, 48), (48, 16), (32, 48), (10, 28)], (255, 232, 140), (214, 150, 40))
    p.poly([(14, 74), (82, 74), (86, 28), (64, 48), (48, 16), (32, 48), (10, 28)], outline=(150, 90, 20, 255), width=2)
    p.rect(14, 74, 82, 84, fill=(214, 150, 40, 255), r=3)
    for x, c in ((26, (255, 90, 100)), (48, (90, 190, 255)), (70, (120, 230, 140))):
        p.ellipse(x - 5, 60 - 5, x + 5, 60 + 5, fill=c + (255,), outline=(255, 255, 255, 200), width=1.2)
    for x, y in ((10, 28), (48, 16), (86, 28)):
        p.ellipse(x - 5, y - 5, x + 5, y + 5, fill=(255, 245, 200, 255))
    p.save("lm_resort.png")


def _star(cx, cy, outer, inner, points=5):
    out = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = -math.pi / 2 + i * math.pi / points
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    make_grass()
    make_plot_empty()
    make_diner()
    make_motel()
    make_bar()
    make_hotel()
    make_theater()
    make_casino()
    make_tree("tree_round.png", "round", 1)
    make_tree("tree_pine.png", "pine", 2)
    make_tree("tree_pink.png", "pink", 3)
    make_bush()
    make_button()
    make_panel()
    make_card()
    make_landmarks()
    print("done:", ", ".join(sorted(os.listdir(OUT))))


if __name__ == "__main__":
    main()
