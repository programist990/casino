import random

from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from common import (
    BETS,
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
    TopBar,
    flash_glow,
    float_text,
    go_to,
    pulse,
)
from wheel import BLACK_COLOR, WheelCap, color_rgba, number_color

HISTORY_SIZE = 8

# kind -> button text
SIMPLE_BETS = [
    ("red", "Красное"),
    ("black", "Чёрное"),
    ("even", "Чётное"),
    ("odd", "Нечётное"),
    ("low", "1-18"),
    ("high", "19-36"),
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
    return False


def payout_multiplier(kind):
    """Total return per 1 chip bet (stake included)."""
    if kind == "number":
        return 36
    return 2


class ChipLabel(GLabel):
    """Small round marker with the number, coloured like the pocket."""

    def __init__(self, number, **kwargs):
        super().__init__(text=str(number), **kwargs)
        self.font_size = 15
        self.size_hint = (None, None)
        self.size = (34, 34)
        self.pos_hint = {"center_y": 0.5}
        with self.canvas.before:
            Color(*color_rgba(number))
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[17])
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


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
        self.kind_texts = {}

        root = Page(padding=16, spacing=8)

        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        title = GLabel(
            text="РУЛЕТКА", font_size=30, color=GOLD, size_hint_y=0.06
        )
        root.add_widget(title)

        self.wheel = WheelCap(size_hint_y=0.24)
        root.add_widget(self.wheel)

        self.message_label = MessageLabel(size_hint_y=0.08)
        root.add_widget(self.message_label)

        self.history_row = BoxLayout(spacing=4, size_hint_y=0.06)
        root.add_widget(self.history_row)

        grid = GridLayout(cols=2, spacing=8, size_hint_y=0.3)
        self.kind_buttons = {}
        for kind, text in SIMPLE_BETS:
            button = RoundButton(text=text, btn_color=self.base_color(kind))
            button.font_size = 20
            button.bind(on_release=self.make_kind_handler(kind))
            self.kind_buttons[kind] = button
            self.kind_texts[kind] = text
            grid.add_widget(button)
        root.add_widget(grid)

        number_row = BoxLayout(spacing=8, size_hint_y=0.09)
        minus_button = RoundButton(text="-", btn_color=GRAY, size_hint_x=0.25)
        minus_button.bind(on_release=self.pick_minus)
        self.number_button = RoundButton(btn_color=GRAY, size_hint_x=0.5)
        self.number_button.font_size = 20
        self.number_button.bind(on_release=self.select_number_bet)
        plus_button = RoundButton(text="+", btn_color=GRAY, size_hint_x=0.25)
        plus_button.bind(on_release=self.pick_plus)
        number_row.add_widget(minus_button)
        number_row.add_widget(self.number_button)
        number_row.add_widget(plus_button)
        root.add_widget(number_row)

        controls = BoxLayout(spacing=8, size_hint_y=0.13)
        self.bet_button = RoundButton(btn_color=GRAY)
        self.bet_button.font_size = 20
        self.bet_button.bind(on_release=self.change_bet)
        self.spin_button = RoundButton(text="КРУТИТЬ", btn_color=GREEN)
        self.spin_button.bind(on_release=self.spin)
        controls.add_widget(self.bet_button)
        controls.add_widget(self.spin_button)
        root.add_widget(controls)

        self.add_widget(root)

    # ----- helpers for buttons -----

    def base_color(self, kind):
        if kind == "red":
            return RED
        if kind == "black":
            return BLACK_COLOR
        return GRAY

    def make_kind_handler(self, kind):
        def handler(*args):
            self.select_kind(kind)

        return handler

    # ----- ui -----

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

    def pick_plus(self, *args):
        if self.spinning:
            return
        self.pick = self.pick + 1
        if self.pick > 36:
            self.pick = 0
        self.kind = "number"
        self.update_labels()

    def change_bet(self, *args):
        if self.spinning:
            return
        self.bet_index = self.bet_index + 1
        if self.bet_index >= len(BETS):
            self.bet_index = 0
        self.update_labels()

    def update_labels(self):
        self.top_bar.set_balance(self.wallet.balance)
        self.bet_button.text = "Ставка: " + str(self.current_bet())

        for kind in self.kind_buttons:
            button = self.kind_buttons[kind]
            text = self.kind_texts[kind]
            if kind == self.kind:
                button.text = "[ " + text + " ]"
                button.color = GOLD
            else:
                button.text = text
                button.color = WHITE

        if self.kind == "number":
            self.number_button.text = "[ Число " + str(self.pick) + " ]"
            self.number_button.color = GOLD
        else:
            self.number_button.text = "Число " + str(self.pick)
            self.number_button.color = WHITE

        self.refresh_history()

    def refresh_history(self):
        self.history_row.clear_widgets()
        self.history_row.add_widget(Widget())
        for number in self.history:
            self.history_row.add_widget(ChipLabel(number))
        self.history_row.add_widget(Widget())

    # ----- game logic -----

    def spin(self, *args):
        if self.spinning:
            return
        bet = self.current_bet()
        if not self.wallet.can_pay(bet):
            self.message_label.color = SOFT_RED
            self.message_label.text = "Не хватает фишек, уменьши ставку"
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
        self.wheel.spin_to(self.result, self.finish_spin)

    def finish_spin(self):
        bet = self.current_bet()
        description = str(self.result) + ", " + color_name(self.result)
        self.wheel.pop()

        if is_winning(self.kind, self.pick, self.result):
            payout = bet * payout_multiplier(self.kind)
            self.wallet.add(payout)
            self.message_label.color = GOLD
            self.message_label.text = description + ". Выигрыш: " + str(payout) + "!"
            pulse(self.message_label)
            float_text(self, "+" + str(payout), GOLD, 0.55)
            flash_glow(self.wheel, 0.9)
        else:
            self.message_label.text = description + ". Не повезло"

        self.history.insert(0, self.result)
        if len(self.history) > HISTORY_SIZE:
            self.history.pop()

        if self.wallet.refill_if_broke():
            self.message_label.color = WHITE
            self.message_label.text = "Фишки кончились, держи новые"

        self.spinning = False
        self.spin_button.disabled = False
        self.update_labels()
