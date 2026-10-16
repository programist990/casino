import json
import os

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label

START_BALANCE = 1000
BETS = [10, 50, 100, 500]

# ----- theme -----

GOLD = (1, 0.82, 0.25, 1)
GREEN = (0.13, 0.62, 0.3, 1)
RED = (0.82, 0.2, 0.25, 1)
BLUE = (0.22, 0.45, 0.85, 1)
GRAY = (0.28, 0.32, 0.38, 1)
DARK = (0.06, 0.07, 0.1, 1)
WHITE = (1, 1, 1, 1)
SOFT_RED = (1, 0.6, 0.6, 1)

BG_TOP = (0.06, 0.32, 0.22)
BG_BOTTOM = (0.01, 0.09, 0.07)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(BASE_DIR, "assets", "fonts", "RussoOne-Regular.ttf")
FONT_SUITS = os.path.join(BASE_DIR, "assets", "fonts", "DejaVuSans-Bold.ttf")
CHIP_IMAGE = os.path.join(BASE_DIR, "assets", "symbols", "chip.png")


def symbol_path(name):
    return os.path.join(BASE_DIR, "assets", "symbols", name + ".png")


# ----- wallet -----


class Wallet:
    """Chips balance shared between all games."""

    def __init__(self, path):
        self.path = path
        self.balance = self.load()

    def load(self):
        if not os.path.exists(self.path):
            return START_BALANCE
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return int(data["balance"])
        except (ValueError, KeyError, OSError):
            return START_BALANCE

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump({"balance": self.balance}, file)
        except OSError:
            pass

    def can_pay(self, amount):
        return self.balance >= amount

    def take(self, amount):
        self.balance = self.balance - amount
        self.save()

    def add(self, amount):
        self.balance = self.balance + amount
        self.save()

    def refill_if_broke(self):
        """Gives new chips when the player can't afford the smallest bet."""
        if self.balance < BETS[0]:
            self.balance = START_BALANCE
            self.save()
            return True
        return False


# ----- background -----

_gradient_texture = None


def get_gradient():
    """Vertical gradient from BG_BOTTOM (row 0) to BG_TOP, created once."""
    global _gradient_texture
    if _gradient_texture is not None:
        return _gradient_texture

    steps = 64
    data = []
    for i in range(steps):
        t = i / (steps - 1)
        for channel in range(3):
            value = BG_BOTTOM[channel] + (BG_TOP[channel] - BG_BOTTOM[channel]) * t
            data.append(int(value * 255))
        data.append(255)

    texture = Texture.create(size=(1, steps), colorfmt="rgba")
    texture.blit_buffer(bytes(data), colorfmt="rgba", bufferfmt="ubyte")
    texture.mag_filter = "linear"
    _gradient_texture = texture
    return texture


class Page(BoxLayout):
    """Vertical layout with the casino gradient as background."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = Rectangle(texture=get_gradient(), pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


# ----- widgets -----


class GLabel(Label):
    """Label that uses the title font by default."""

    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", FONT_TITLE)
        super().__init__(**kwargs)


class MessageLabel(GLabel):
    """Status line on a soft dark plate, wraps long text."""

    def __init__(self, **kwargs):
        kwargs.setdefault("font_size", 20)
        super().__init__(**kwargs)
        self.halign = "center"
        self.valign = "middle"
        with self.canvas.before:
            Color(0, 0, 0, 0.3)
            self.plate = RoundedRectangle(pos=self.pos, size=self.size, radius=[14])
        self.bind(pos=self.update_plate, size=self.update_plate)

    def update_plate(self, *args):
        self.plate.pos = self.pos
        self.plate.size = self.size
        self.text_size = (self.width - 16, self.height)


class RoundButton(Button):
    """Glossy rounded button with a shadow and a pressed state."""

    def __init__(self, btn_color=BLUE, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.font_name = FONT_TITLE
        self.font_size = 22
        self.btn_color = btn_color
        with self.canvas.before:
            Color(0, 0, 0, 0.35)
            self.shadow = RoundedRectangle(radius=[16])
            self.color_instr = Color(*btn_color)
            self.bg = RoundedRectangle(radius=[16])
            Color(1, 1, 1, 0.14)
            self.gloss = RoundedRectangle(radius=[16, 16, 0, 0])
        self.bind(
            pos=self.update_bg,
            size=self.update_bg,
            state=self.update_bg,
            disabled=self.update_bg,
        )
        self.update_bg()

    def update_bg(self, *args):
        x, y = self.pos
        width, height = self.size
        body_y = y + 4
        body_height = height - 4
        if self.state == "down":
            body_y = y + 1
            body_height = height - 2

        self.shadow.pos = (x, y)
        self.shadow.size = (width, body_height)
        self.bg.pos = (x, body_y)
        self.bg.size = (width, body_height)
        self.gloss.pos = (x, body_y + body_height * 0.5)
        self.gloss.size = (width, body_height * 0.5)

        red, green, blue, alpha = self.btn_color
        if self.disabled:
            self.color_instr.rgba = (red * 0.4, green * 0.4, blue * 0.4, alpha)
        elif self.state == "down":
            self.color_instr.rgba = (red * 0.75, green * 0.75, blue * 0.75, alpha)
        else:
            self.color_instr.rgba = (red, green, blue, alpha)


class TopBar(BoxLayout):
    """Back button + balance with a chip icon. The balance counts up/down."""

    shown = NumericProperty(0)

    def __init__(self, on_back, **kwargs):
        super().__init__(size_hint_y=None, height=56, spacing=10, **kwargs)
        self.first_time = True

        back_button = RoundButton(text="Меню", btn_color=GRAY, size_hint_x=0.3)
        back_button.font_size = 18
        back_button.bind(on_release=on_back)
        self.add_widget(back_button)

        self.balance_label = GLabel(font_size=26, color=GOLD, halign="right", valign="middle")
        self.balance_label.bind(size=self.update_text_size)
        self.add_widget(self.balance_label)

        chip = Image(source=CHIP_IMAGE, size_hint_x=None, width=44)
        self.add_widget(chip)

    def update_text_size(self, *args):
        self.balance_label.text_size = self.balance_label.size

    def set_balance(self, value):
        if self.first_time:
            self.first_time = False
            self.shown = value
            return
        Animation.cancel_all(self, "shown")
        Animation(shown=value, duration=0.6, t="out_quad").start(self)

    def on_shown(self, instance, value):
        self.balance_label.text = str(int(round(value)))


# ----- animation helpers -----


def go_to(manager, name, direction):
    manager.transition.direction = direction
    manager.current = name


def pulse(widget):
    """Quick double blink, used to draw attention to a message."""
    Animation.cancel_all(widget, "opacity")
    widget.opacity = 1
    anim = Animation(opacity=0.3, duration=0.12)
    anim += Animation(opacity=1, duration=0.12)
    anim += Animation(opacity=0.3, duration=0.12)
    anim += Animation(opacity=1, duration=0.12)
    anim.start(widget)


def flash_glow(widget, end_alpha):
    """Blinks widget.glow (a NumericProperty) and leaves it at end_alpha."""
    Animation.cancel_all(widget, "glow")
    anim = Animation(glow=1, duration=0.2)
    anim += Animation(glow=0.25, duration=0.2)
    anim += Animation(glow=1, duration=0.2)
    anim += Animation(glow=0.25, duration=0.2)
    anim += Animation(glow=end_alpha, duration=0.2)
    anim.start(widget)


def float_text(parent, text, color=GOLD, y_ratio=0.5, size=46):
    """Text that floats up and fades out, e.g. '+250' after a win."""
    label = GLabel(
        text=text,
        font_size=size,
        color=color,
        size_hint=(None, None),
        outline_width=3,
        outline_color=(0, 0, 0, 1),
    )
    label.texture_update()
    label.size = label.texture_size
    label.center_x = parent.width / 2
    label.y = parent.height * y_ratio
    parent.add_widget(label)

    def remove_label(animation, widget):
        if widget.parent is not None:
            widget.parent.remove_widget(widget)

    anim = Animation(y=label.y + 150, opacity=0, duration=1.4, t="out_quad")
    anim.bind(on_complete=remove_label)
    anim.start(label)
