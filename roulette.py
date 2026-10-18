import random

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from common import (
    BETS,
    FONT_TITLE,
    GOLD,
    GRAY,
    GREEN,
    RED,
    SOFT_RED,
    WHITE,
    GLabel,
    MessageLabel,
    Page,
    RoundButton,
    Sfx,
    TopBar,
    flash_glow,
    float_text,
    go_to,
    pulse,
)
from wheel import BLACK_COLOR, WheelCap, color_rgba, number_color

HISTORY_SIZE = 8

# kind -> (button text, multiplier label, base color)
SIMPLE_BETS = [
    ("red", "КРАСНОЕ", "x2", RED),
    ("black", "ЧЁРНОЕ", "x2", (0.12, 0.14, 0.18, 1)),
    ("even", "ЧЁТНОЕ", "x2", (0.18, 0.36, 0.72, 1)),
    ("odd", "НЕЧЁТ", "x2", (0.18, 0.36, 0.72, 1)),
    ("low", "1 — 18", "x2", (0.38, 0.22, 0.62, 1)),
    ("high", "19 — 36", "x2", (0.38, 0.22, 0.62, 1)),
]

DOZEN_BETS = [
    ("dozen1", "1 — 12", "x3"),
    ("dozen2", "13 — 24", "x3"),
    ("dozen3", "25 — 36", "x3"),
]


def color_name(number):
    color = number_color(number)
    if color == "green":
        return "зеро"
    if color == "red":
        return "красное"
    return "чёрное"


def is_winning(kind, pick, result):
    """Checks one bet against the result. Zero loses every simple bet."""
    if kind == "number":
        return result == pick
    if result == 0:
        return False
    if kind == "red":
        return number_color(result) == "red"
    if kind == "black":
        return number_color(result) == "black"
    if kind == "even":
        return result % 2 == 0
    if kind == "odd":
        return result % 2 == 1
    if kind == "low":
        return result <= 18
    if kind == "high":
        return result >= 19
    if kind == "dozen1":
        return 1 <= result <= 12
    if kind == "dozen2":
        return 13 <= result <= 24
    if kind == "dozen3":
        return 25 <= result <= 36
    return False


def payout_multiplier(kind):
    """Total return per 1 chip bet (stake included)."""
    if kind == "number":
        return 36
    if kind in ("dozen1", "dozen2", "dozen3"):
        return 3
    return 2


def bet_display_name(kind, pick):
    if kind == "number":
        return f"Число {pick}"
    for k, text, mult, _ in SIMPLE_BETS:
        if k == kind:
            return f"{text} ({mult})"
    for k, text, mult in DOZEN_BETS:
        if k == kind:
            return f"Дюжина {text} ({mult})"
    return kind


class RouletteBetButton(Button):
    """Glossy betting button with distinct colors, payout badge,

    and active glowing golden selection frame.
    """

    def __init__(self, kind, text, mult="x2", base_color=GRAY, **kwargs):
        super().__init__(**kwargs)
        self.kind = kind
        self.label_text = text
        self.mult_text = mult
        self.base_color = base_color
        self.is_active = False

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.font_name = FONT_TITLE
        self.font_size = 19

        with self.canvas.before:
            Color(0, 0, 0, 0.35)
            self.shadow = RoundedRectangle(radius=[12])
            self.color_instr = Color(*base_color)
            self.bg = RoundedRectangle(radius=[12])
            Color(1, 1, 1, 0.12)
            self.gloss = RoundedRectangle(radius=[12, 12, 0, 0])
            self.glow_color = Color(1, 0.85, 0.25, 0)
            self.glow_border = Line(rounded_rectangle=(0, 0, 10, 10, 12), width=2.6)

        self.bind(
            pos=self.update_graphics,
            size=self.update_graphics,
            state=self.update_graphics,
        )
        self.refresh_display()

    def set_active(self, active):
        self.is_active = active
        self.refresh_display()
        self.update_graphics()

    def refresh_display(self):
        if self.is_active:
            self.text = f"★ {self.label_text} [{self.mult_text}]"
            self.color = GOLD
        else:
            self.text = f"{self.label_text} ({self.mult_text})"
            self.color = WHITE

    def update_graphics(self, *args):
        x, y = self.pos
        w, h = self.size
        body_y = y + 3 if self.state != "down" else y + 1
        body_h = h - 3 if self.state != "down" else h - 1

        self.shadow.pos = (x, y)
        self.shadow.size = (w, body_h)
        self.bg.pos = (x, body_y)
        self.bg.size = (w, body_h)
        self.gloss.pos = (x, body_y + body_h * 0.5)
        self.gloss.size = (w, body_h * 0.5)

        r, g, b, a = self.base_color
        if self.disabled:
            self.color_instr.rgba = (r * 0.4, g * 0.4, b * 0.4, a)
        elif self.state == "down":
            self.color_instr.rgba = (r * 0.75, g * 0.75, b * 0.75, a)
        elif self.is_active:
            self.color_instr.rgba = (
                min(1.0, r * 1.25),
                min(1.0, g * 1.25),
                min(1.0, b * 1.25),
                a,
            )
        else:
            self.color_instr.rgba = (r, g, b, a)

        if self.is_active:
            self.glow_color.rgba = (1, 0.85, 0.25, 1)
            self.glow_border.rounded_rectangle = (x, body_y, w, body_h, 12)
        else:
            self.glow_color.rgba = (1, 1, 1, 0.12)
            self.glow_border.rounded_rectangle = (x, body_y, w, body_h, 12)


class NumberBetButton(Button):
    """Button for betting on a specific number, styled like a roulette pocket."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pick = 17
        self.is_active = False
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.font_name = FONT_TITLE
        self.font_size = 21

        with self.canvas.before:
            Color(0, 0, 0, 0.35)
            self.shadow = RoundedRectangle(radius=[12])
            self.pocket_color = Color(*color_rgba(self.pick))
            self.bg = RoundedRectangle(radius=[12])
            Color(1, 1, 1, 0.14)
            self.gloss = RoundedRectangle(radius=[12, 12, 0, 0])
            self.glow_color = Color(1, 0.85, 0.25, 0)
            self.glow_border = Line(rounded_rectangle=(0, 0, 10, 10, 12), width=2.6)

        self.bind(
            pos=self.update_graphics,
            size=self.update_graphics,
            state=self.update_graphics,
        )

    def set_pick(self, number, is_active):
        self.pick = number
        self.is_active = is_active
        if is_active:
            self.text = f"★ ЧИСЛО: {number} (x36)"
            self.color = GOLD
        else:
            self.text = f"Число: {number} (x36)"
            self.color = WHITE
        self.pocket_color.rgba = color_rgba(number)
        self.update_graphics()

    def update_graphics(self, *args):
        x, y = self.pos
        w, h = self.size
        body_y = y + 3 if self.state != "down" else y + 1
        body_h = h - 3 if self.state != "down" else h - 1

        self.shadow.pos = (x, y)
        self.shadow.size = (w, body_h)
        self.bg.pos = (x, body_y)
        self.bg.size = (w, body_h)
        self.gloss.pos = (x, body_y + body_h * 0.5)
        self.gloss.size = (w, body_h * 0.5)

        if self.is_active:
            self.glow_color.rgba = (1, 0.85, 0.25, 1)
            self.glow_border.rounded_rectangle = (x, body_y, w, body_h, 12)
        else:
            self.glow_color.rgba = (1, 1, 1, 0.15)
            self.glow_border.rounded_rectangle = (x, body_y, w, body_h, 12)


class ChipLabel(GLabel):
    """Small round marker with the number, coloured like the pocket."""

    def __init__(self, number, **kwargs):
        super().__init__(text=str(number), **kwargs)
        self.font_size = 18
        self.size_hint = (None, None)
        self.size = (40, 40)
        self.pos_hint = {"center_y": 0.5}
        with self.canvas.before:
            Color(*color_rgba(number))
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])
            Color(1, 1, 1, 0.15)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 20), width=1)
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, 20)


class RouletteScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.bet_index = 0
        self.kind = "red"
        self.pick = 17
        self.result = 0
        self.spinning = False
        self.history = []

        self.tick_sound_event = None

        root = Page(padding=16, spacing=7)

        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        title = GLabel(text="РУЛЕТКА", font_size=36, color=GOLD, size_hint_y=0.065)
        root.add_widget(title)

        self.wheel = WheelCap(size_hint_y=0.23)
        root.add_widget(self.wheel)

        self.message_label = MessageLabel(size_hint_y=0.075)
        root.add_widget(self.message_label)

        # Recent pockets history row
        self.history_row = BoxLayout(spacing=5, size_hint_y=0.06)
        root.add_widget(self.history_row)

        # 1. Simple Bets Grid (2 cols x 3 rows)
        grid = GridLayout(cols=2, spacing=6, size_hint_y=0.21)
        self.kind_buttons = {}
        for kind, text, mult, color in SIMPLE_BETS:
            btn = RouletteBetButton(
                kind=kind, text=text, mult=mult, base_color=color
            )
            btn.bind(on_release=self.make_kind_handler(kind))
            self.kind_buttons[kind] = btn
            grid.add_widget(btn)
        root.add_widget(grid)

        # 2. Dozens Row (3 bets)
        dozen_row = BoxLayout(spacing=6, size_hint_y=0.065)
        dozen_color = (0.13, 0.44, 0.28, 1)
        for kind, text, mult in DOZEN_BETS:
            btn = RouletteBetButton(
                kind=kind, text=text, mult=mult, base_color=dozen_color
            )
            btn.bind(on_release=self.make_kind_handler(kind))
            self.kind_buttons[kind] = btn
            dozen_row.add_widget(btn)
        root.add_widget(dozen_row)

        # 3. Interactive Number Bet Row
        number_row = BoxLayout(spacing=6, size_hint_y=0.07)
        minus_button = RoundButton(text="-", btn_color=GRAY, size_hint_x=0.22)
        minus_button.font_size = 24
        minus_button.bind(on_release=self.pick_minus)

        self.number_button = NumberBetButton(size_hint_x=0.56)
        self.number_button.bind(on_release=self.select_number_bet)

        plus_button = RoundButton(text="+", btn_color=GRAY, size_hint_x=0.22)
        plus_button.font_size = 24
        plus_button.bind(on_release=self.pick_plus)

        number_row.add_widget(minus_button)
        number_row.add_widget(self.number_button)
        number_row.add_widget(plus_button)
        root.add_widget(number_row)

        # 4. Bottom Controls: Bet amount and Spin button
        controls = BoxLayout(spacing=8, size_hint_y=0.10)
        self.bet_button = RoundButton(btn_color=GRAY)
        self.bet_button.font_size = 24
        self.bet_button.bind(on_release=self.change_bet)

        self.spin_button = RoundButton(text="КРУТИТЬ", btn_color=GREEN)
        self.spin_button.font_size = 28
        self.spin_button.bind(on_release=self.spin)

        controls.add_widget(self.bet_button)
        controls.add_widget(self.spin_button)
        root.add_widget(controls)

        self.add_widget(root)

    def make_kind_handler(self, kind):
        def handler(*args):
            self.select_kind(kind)

        return handler

    def on_pre_enter(self, *args):
        self.message_label.color = WHITE
        self.message_label.text = "Выбери ставку и крути"
        self.wheel.set_unknown()
        self.update_labels()

    def go_menu(self, *args):
        if self.spinning:
            return
        go_to(self.manager, "menu", "right")

    def current_bet(self):
        return BETS[self.bet_index]

    def select_kind(self, kind):
        if self.spinning:
            return
        self.kind = kind
        self.update_labels()
        Sfx.play("chip")

    def select_number_bet(self, *args):
        self.select_kind("number")

    def pick_minus(self, *args):
        if self.spinning:
            return
        self.pick = self.pick - 1
        if self.pick < 0:
            self.pick = 36
        self.kind = "number"
        self.update_labels()
        Sfx.play("click")

    def pick_plus(self, *args):
        if self.spinning:
            return
        self.pick = self.pick + 1
        if self.pick > 36:
            self.pick = 0
        self.kind = "number"
        self.update_labels()
        Sfx.play("click")

    def change_bet(self, *args):
        if self.spinning:
            return
        self.bet_index = self.bet_index + 1
        if self.bet_index >= len(BETS):
            self.bet_index = 0
        self.update_labels()
        Sfx.play("chip")

    def update_labels(self):
        self.top_bar.set_balance(self.wallet.balance)
        self.bet_button.text = f"Ставка: {self.current_bet()}"

        # Update active states on bet buttons
        for kind, button in self.kind_buttons.items():
            button.set_active(kind == self.kind)

        # Update number bet button
        self.number_button.set_pick(self.pick, is_active=(self.kind == "number"))

        self.refresh_history()

    def refresh_history(self):
        self.history_row.clear_widgets()
        self.history_row.add_widget(Widget())
        for number in self.history:
            self.history_row.add_widget(ChipLabel(number))
        self.history_row.add_widget(Widget())

    def play_wheel_tick(self, dt):
        Sfx.play("click", volume=0.5)

    def spin(self, *args):
        if self.spinning:
            return
        bet = self.current_bet()
        if not self.wallet.can_pay(bet):
            self.message_label.color = SOFT_RED
            self.message_label.text = "Не хватает фишек, уменьши ставку"
            Sfx.play("lose")
            return

        self.wallet.take(bet)
        self.spinning = True
        self.spin_button.disabled = True
        self.result = random.randint(0, 36)
        Animation.cancel_all(self.wheel, "glow")
        self.wheel.glow = 0.35
        self.message_label.color = WHITE
        self.message_label.text = "Крутим..."
        self.update_labels()

        Sfx.play("spin")
        self.tick_sound_event = Clock.schedule_interval(self.play_wheel_tick, 0.4)
        self.wheel.spin_to(self.result, self.finish_spin)

    def finish_spin(self):
        if self.tick_sound_event is not None:
            self.tick_sound_event.cancel()
            self.tick_sound_event = None

        bet = self.current_bet()
        description = str(self.result) + ", " + color_name(self.result)
        self.wheel.pop()
        Sfx.play("stop")

        if is_winning(self.kind, self.pick, self.result):
            payout = bet * payout_multiplier(self.kind)
            self.wallet.add(payout)
            self.wallet.record_game(payout - bet, bet)
            self.message_label.color = GOLD
            self.message_label.text = description + ". Выигрыш: " + str(payout) + "!"
            pulse(self.message_label)
            float_text(self, "+" + str(payout), GOLD, 0.55)
            flash_glow(self.wheel, 0.9)
            Sfx.play("win")
        else:
            self.wallet.record_game(-bet, bet)
            self.message_label.text = description + ". Не повезло"
            Sfx.play("lose")

        self.history.insert(0, self.result)
        if len(self.history) > HISTORY_SIZE:
            self.history.pop()

        if self.wallet.refill_if_broke():
            self.message_label.color = WHITE
            self.message_label.text = "Фишки кончились, держи новые"

        self.spinning = False
        self.spin_button.disabled = False
        self.update_labels()
