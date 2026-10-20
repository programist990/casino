import json
import os
import time

from kivy.animation import Animation
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label

from city_data import new_city, sanitize_city

START_BALANCE = 1000000
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


SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")


class Sfx:
    """Tiny sound player shared across all casino games."""

    enabled = True
    cache = {}

    @classmethod
    def play(cls, name, volume=1.0):
        if not cls.enabled:
            return
        try:
            if name not in cls.cache:
                path = os.path.join(SOUND_DIR, name + ".wav")
                if os.path.exists(path):
                    cls.cache[name] = SoundLoader.load(path)
                else:
                    cls.cache[name] = None
            sound = cls.cache[name]
            if sound is not None:
                sound.volume = volume
                sound.stop()
                sound.play()
        except Exception:
            cls.cache[name] = None


# ----- wallet & stats -----


class Wallet:
    """Chips balance, stats, and daily bonus shared between all games."""

    DAILY_COOLDOWN = 60 * 60 * 12  # 12 hours bonus cooldown
    DAILY_BONUS_AMOUNT = 500

    def __init__(self, path):
        self.path = path
        self.balance = START_BALANCE
        self.last_daily = 0
        self.stats = {
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "biggest_win": 0,
            "total_won": 0,
            "total_lost": 0,
        }
        self.city = new_city()
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self.balance = START_BALANCE
            return
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                data = json.load(file)
            self.balance = int(data.get("balance", START_BALANCE))
            self.last_daily = float(data.get("last_daily", 0))
            loaded_stats = data.get("stats", {})
            for key in self.stats:
                if key in loaded_stats:
                    self.stats[key] = int(loaded_stats[key])
            self.city = sanitize_city(data.get("city"))
        except (ValueError, KeyError, OSError):
            self.balance = START_BALANCE

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "balance": self.balance,
                        "last_daily": self.last_daily,
                        "stats": self.stats,
                        "city": self.city,
                    },
                    file,
                    indent=2,
                )
        except OSError:
            pass

    def can_pay(self, amount):
        return self.balance >= amount

    def take(self, amount):
        self.balance = max(0, self.balance - amount)
        self.save()

    def add(self, amount):
        self.balance = self.balance + amount
        self.save()

    def record_game(self, net_win, bet):
        self.stats["games_played"] += 1
        if net_win > 0:
            self.stats["wins"] += 1
            if net_win > self.stats["biggest_win"]:
                self.stats["biggest_win"] = net_win
            self.stats["total_won"] += net_win
        elif net_win < 0:
            self.stats["losses"] += 1
            self.stats["total_lost"] += abs(net_win)
        self.save()

    def reset_stats(self):
        self.stats = {
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "biggest_win": 0,
            "total_won": 0,
            "total_lost": 0,
        }
        self.save()

    def can_claim_daily(self):
        return (time.time() - self.last_daily) >= self.DAILY_COOLDOWN

    def seconds_until_daily(self):
        left = self.DAILY_COOLDOWN - (time.time() - self.last_daily)
        return max(0, int(left))

    def claim_daily(self):
        if not self.can_claim_daily():
            return False
        self.last_daily = time.time()
        self.add(self.DAILY_BONUS_AMOUNT)
        return True

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
        kwargs.setdefault("font_size", dp(22))
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
        self.font_size = dp(24)
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

        # the text never sticks out of the button: the font shrinks if needed
        self._base_font = self.font_size
        self._fitting = False
        self.bind(
            font_size=self._remember_font, text=self._fit_text, width=self._fit_text
        )

    def _remember_font(self, *args):
        if not self._fitting:
            self._base_font = self.font_size
            self._fit_text()

    def _fit_text(self, *args):
        if self._fitting or self.width < dp(20) or not self.text:
            return
        self._fitting = True
        try:
            self.font_size = self._base_font
            self.texture_update()
            available = self.width - dp(14)
            text_width = self.texture_size[0]
            if text_width > available > 0:
                self.font_size = max(dp(9), self._base_font * available / text_width)
        finally:
            self._fitting = False

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
        super().__init__(size_hint_y=None, height=dp(64), spacing=dp(10), **kwargs)
        self.first_time = True

        back_button = RoundButton(text="Меню", btn_color=GRAY, size_hint_x=0.3)
        back_button.font_size = dp(22)
        back_button.bind(on_release=on_back)
        self.add_widget(back_button)

        self.balance_label = GLabel(
            font_size=dp(30), color=GOLD, halign="right", valign="middle"
        )
        self.balance_label.bind(size=self.update_text_size)
        self.add_widget(self.balance_label)

        chip = Image(source=CHIP_IMAGE, size_hint_x=None, width=dp(50))
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
    size = dp(size)
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

    anim = Animation(y=label.y + dp(150), opacity=0, duration=1.4, t="out_quad")
    anim.bind(on_complete=remove_label)
    anim.start(label)
