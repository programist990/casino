import math
from functools import partial

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import (
    Color,
    Ellipse,
    InstructionGroup,
    Line,
    PopMatrix,
    PushMatrix,
    Rectangle,
    Rotate,
    RoundedRectangle,
    Triangle,
)
from kivy.properties import NumericProperty
from kivy.uix.stencilview import StencilView

from common import FONT_TITLE, GREEN, RED, GLabel

# real european wheel, clockwise from zero
WHEEL_ORDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26,
]
POCKETS = len(WHEEL_ORDER)
STEP = 360 / POCKETS

RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK_COLOR = (0.14, 0.14, 0.18, 1)
GOLD_LINE = (0.9, 0.7, 0.2, 1)
SPIN_TIME = 5.2


def number_color(number):
    if number == 0:
        return "green"
    if number in RED_NUMBERS:
        return "red"
    return "black"


def color_rgba(number):
    color = number_color(number)
    if color == "green":
        return GREEN
    if color == "red":
        return RED
    return BLACK_COLOR


class WheelBadge(GLabel):
    """Plate in the hub showing the number under the pointer."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (96, 44)
        self.font_size = 30
        with self.canvas.before:
            Color(1, 0.82, 0.25, 0.9)
            self.outline = RoundedRectangle(radius=[14])
            self.plate_color = Color(0.1, 0.1, 0.15, 1)
            self.plate = RoundedRectangle(radius=[12])
        self.bind(pos=self.update_plate, size=self.update_plate)

    def update_plate(self, *args):
        self.outline.pos = self.pos
        self.outline.size = self.size
        self.plate.pos = (self.x + 2, self.y + 2)
        self.plate.size = (self.width - 4, self.height - 4)

    def show_number(self, number):
        self.text = str(number)
        self.plate_color.rgba = color_rgba(number)

    def show_unknown(self):
        self.text = "?"
        self.plate_color.rgba = (0.1, 0.1, 0.15, 1)

    def pop(self):
        Animation.cancel_all(self, "font_size")
        anim = Animation(font_size=42, duration=0.12)
        anim += Animation(font_size=30, duration=0.3, t="out_bounce")
        anim.start(self)


class WheelCap(StencilView):
    """Top part of a big roulette wheel. The lower part is cut off."""

    wheel_angle = NumericProperty(0)
    ball_angle = NumericProperty(0)
    glow = NumericProperty(0.35)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.textures = {}
        self.disc_rotate = None
        self.ball_rotate = None
        self.live = False
        self.shown_index = -1

        self.group = InstructionGroup()
        self.canvas.add(self.group)

        with self.canvas.after:
            self.glow_color = Color(1, 0.82, 0.25, 0.35)
            self.frame = Line(rectangle=(0, 0, 10, 10), width=3)
            Color(1, 0.82, 0.25, 1)
            self.pointer = Triangle(points=(0, 0, 0, 0, 0, 0))

        self.badge = WheelBadge()
        self.badge.show_unknown()
        self.add_widget(self.badge)

        self.rebuild_trigger = Clock.create_trigger(self.rebuild)
        self.bind(pos=self.rebuild_trigger, size=self.rebuild_trigger)
        self.rebuild_trigger()

    # ----- drawing -----

    def number_texture(self, number):
        if number not in self.textures:
            label = CoreLabel(text=str(number), font_size=15, font_name=FONT_TITLE)
            label.refresh()
            self.textures[number] = label.texture
        return self.textures[number]

    def add_circle(self, cx, cy, radius, color):
        self.group.add(Color(*color))
        self.group.add(
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))
        )

    def rebuild(self, dt=None):
        x, y = self.pos
        width, height = self.size
        if width < 20 or height < 20:
            return

        cx = x + width / 2
        radius = width * 0.56
        cy = y + height - 20 - radius

        r_gold = radius - 6
        r_out = radius - 9
        r_in = r_out - 34
        r_hub = r_in - 26
        r_text = (r_out + r_in) / 2

        group = self.group
        group.clear()

        group.add(Color(0.03, 0.05, 0.07, 1))
        group.add(Rectangle(pos=self.pos, size=self.size))

        # spinning disc
        group.add(PushMatrix())
        self.disc_rotate = Rotate(angle=self.wheel_angle, origin=(cx, cy))
        group.add(self.disc_rotate)

        self.add_circle(cx, cy, radius, (0.42, 0.26, 0.1, 1))
        self.add_circle(cx, cy, r_gold, GOLD_LINE)
        self.add_circle(cx, cy, r_out, (0.08, 0.08, 0.1, 1))

        for i in range(POCKETS):
            group.add(Color(*color_rgba(WHEEL_ORDER[i])))
            group.add(
                Ellipse(
                    pos=(cx - r_out, cy - r_out),
                    size=(r_out * 2, r_out * 2),
                    angle_start=i * STEP,
                    angle_end=(i + 1) * STEP,
                )
            )

        group.add(Color(*GOLD_LINE[:3], 0.7))
        for i in range(POCKETS):
            angle = math.radians(i * STEP)
            sine = math.sin(angle)
            cosine = math.cos(angle)
            group.add(
                Line(
                    points=[
                        cx + r_in * sine,
                        cy + r_in * cosine,
                        cx + r_out * sine,
                        cy + r_out * cosine,
                    ],
                    width=1,
                )
            )

        self.add_circle(cx, cy, r_in, (0.17, 0.1, 0.05, 1))
        group.add(Color(*GOLD_LINE))
        group.add(Line(circle=(cx, cy, r_in), width=2))
        self.add_circle(cx, cy, r_hub, (0.06, 0.07, 0.1, 1))
        group.add(Color(*GOLD_LINE))
        group.add(Line(circle=(cx, cy, r_hub), width=2))
        group.add(Line(circle=(cx, cy, r_hub * 0.55), width=1.5))

        for i in range(POCKETS):
            texture = self.number_texture(WHEEL_ORDER[i])
            group.add(PushMatrix())
            group.add(Rotate(angle=-(i + 0.5) * STEP, origin=(cx, cy)))
            group.add(Color(1, 1, 1, 1))
            group.add(
                Rectangle(
                    texture=texture,
                    size=texture.size,
                    pos=(
                        cx - texture.width / 2,
                        cy + r_text - texture.height / 2,
                    ),
                )
            )
            group.add(PopMatrix())

        group.add(PopMatrix())

        # ball rides on the dark track, opposite to the wheel
        group.add(PushMatrix())
        self.ball_rotate = Rotate(angle=self.ball_angle, origin=(cx, cy))
        group.add(self.ball_rotate)
        r_track = (r_in + r_hub) / 2
        ball = 8
        group.add(Color(0, 0, 0, 0.45))
        group.add(
            Ellipse(
                pos=(cx - ball + 2, cy + r_track - ball - 2),
                size=(ball * 2, ball * 2),
            )
        )
        group.add(Color(0.96, 0.96, 0.96, 1))
        group.add(
            Ellipse(
                pos=(cx - ball, cy + r_track - ball), size=(ball * 2, ball * 2)
            )
        )
        group.add(Color(1, 1, 1, 1))
        group.add(
            Ellipse(pos=(cx - 4, cy + r_track + 1), size=(5, 5))
        )
        group.add(PopMatrix())

        # fixed parts
        top = y + height
        self.pointer.points = (cx - 11, top - 2, cx + 11, top - 2, cx, top - 19)
        self.frame.rectangle = (x + 1, y + 1, width - 2, height - 2)
        self.badge.center_x = cx
        self.badge.y = y + 8

    # ----- properties -----

    def on_wheel_angle(self, instance, value):
        if self.disc_rotate is not None:
            self.disc_rotate.angle = value
        if self.live:
            index = int((value % 360) / STEP) % POCKETS
            if index != self.shown_index:
                self.shown_index = index
                self.badge.show_number(WHEEL_ORDER[index])

    def on_ball_angle(self, instance, value):
        if self.ball_rotate is not None:
            self.ball_rotate.angle = value

    def on_glow(self, instance, value):
        self.glow_color.rgba = (1, 0.82, 0.25, value)

    # ----- actions -----

    def set_unknown(self):
        self.live = False
        self.badge.show_unknown()

    def spin_to(self, number, on_done):
        """Spins the wheel so that `number` stops under the pointer."""
        index = WHEEL_ORDER.index(number)
        target = (index + 0.5) * STEP
        need = (target - self.wheel_angle % 360) % 360
        final = self.wheel_angle + 360 * 5 + need

        self.live = True
        self.shown_index = -1
        Animation.cancel_all(self, "wheel_angle", "ball_angle")
        self.ball_angle = 0
        Animation(wheel_angle=final, duration=SPIN_TIME, t="out_cubic").start(self)
        Animation(ball_angle=-360 * 5, duration=SPIN_TIME, t="out_quad").start(self)
        Clock.schedule_once(partial(self.call_done, on_done), SPIN_TIME + 0.05)

    def call_done(self, on_done, dt):
        on_done()

    def pop(self):
        self.badge.pop()
