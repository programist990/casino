import random
from functools import partial

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen

from common import (
    BETS,
    GOLD,
    GRAY,
    GREEN,
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
    symbol_path,
)

# weight - how often the symbol appears, pay - multiplier for three in a row
SYMBOLS = [
    {"name": "7", "image": symbol_path("seven"), "weight": 1, "pay": 150},
    {"name": "BAR", "image": symbol_path("bar"), "weight": 2, "pay": 60},
    {"name": "BELL", "image": symbol_path("bell"), "weight": 3, "pay": 30},
    {"name": "PLUM", "image": symbol_path("plum"), "weight": 4, "pay": 18},
    {"name": "LEMON", "image": symbol_path("lemon"), "weight": 5, "pay": 12},
    {"name": "CHERRY", "image": symbol_path("cherry"), "weight": 6, "pay": 9},
]
PAIR_PAY = 2  # two matching symbols on the first two reels
STOP_DELAYS = [1.0, 1.6, 2.2]
IMAGE_SIZE = 0.8


def build_pool():
    pool = []
    for symbol in SYMBOLS:
        for i in range(symbol["weight"]):
            pool.append(symbol)
    return pool


def winning_reels(result):
    """Indexes of the reels that take part in a win."""
    first = result[0]["name"]
    second = result[1]["name"]
    third = result[2]["name"]
    if first == second and second == third:
        return [0, 1, 2]
    if first == second:
        return [0, 1]
    return []


def calc_win(result, bet):
    reels = winning_reels(result)
    if len(reels) == 3:
        return bet * result[0]["pay"]
    if len(reels) == 2:
        return bet * PAIR_PAY
    return 0


class Reel(FloatLayout):
    glow = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.05, 0.06, 0.09, 1)
            self.bg = RoundedRectangle(radius=[18])
            Color(1, 1, 1, 0.035)
            self.shine = RoundedRectangle(radius=[18, 18, 0, 0])
        with self.canvas.after:
            self.glow_color = Color(1, 0.82, 0.25, 0)
            self.ring = Line(rounded_rectangle=(0, 0, 10, 10, 18), width=4)

        self.image = Image(
            size_hint=(IMAGE_SIZE, IMAGE_SIZE),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.add_widget(self.image)
        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        x, y = self.pos
        width, height = self.size
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.shine.pos = (x, y + height * 0.5)
        self.shine.size = (width, height * 0.5)
        self.ring.rounded_rectangle = (x + 2, y + 2, width - 4, height - 4, 18)

    def on_glow(self, instance, value):
        self.glow_color.rgba = (1, 0.82, 0.25, value)

    def set_symbol(self, symbol):
        self.image.source = symbol["image"]

    def start_spin(self):
        Animation.cancel_all(self, "glow")
        self.glow = 0
        self.image.opacity = 0.6

    def jitter(self):
        """Small random shake while the reel is spinning."""
        offset = random.uniform(-0.07, 0.07)
        self.image.pos_hint = {"center_x": 0.5, "center_y": 0.5 + offset}

    def stop_spin(self, symbol):
        self.set_symbol(symbol)
        self.image.opacity = 1
        self.image.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        Animation.cancel_all(self.image, "size_hint_x", "size_hint_y")
        anim = Animation(size_hint_x=1, size_hint_y=1, duration=0.07)
        anim += Animation(
            size_hint_x=IMAGE_SIZE,
            size_hint_y=IMAGE_SIZE,
            duration=0.3,
            t="out_bounce",
        )
        anim.start(self.image)


class SlotsScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.pool = build_pool()
        self.bet_index = 0
        self.spinning = False
        self.stopped = [True, True, True]
        self.result = []
        self.tick_event = None

        root = Page(padding=16, spacing=10)

        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        title = GLabel(
            text="SLOTS", font_size=34, color=GOLD, size_hint_y=0.09
        )
        root.add_widget(title)

        reels_row = BoxLayout(spacing=10, size_hint_y=0.3)
        self.reels = []
        for i in range(3):
            reel = Reel()
            self.reels.append(reel)
            reels_row.add_widget(reel)
        root.add_widget(reels_row)

        self.message_label = MessageLabel(size_hint_y=0.1)
        root.add_widget(self.message_label)

        root.add_widget(self.build_paytable())

        self.bet_button = RoundButton(btn_color=GRAY, size_hint_y=0.1)
        self.bet_button.bind(on_release=self.change_bet)
        root.add_widget(self.bet_button)

        self.spin_button = RoundButton(
            text="КРУТИТЬ", btn_color=GREEN, size_hint_y=0.15
        )
        self.spin_button.font_size = 30
        self.spin_button.bind(on_release=self.spin)
        root.add_widget(self.spin_button)

        self.add_widget(root)

    def build_paytable(self):
        grid = GridLayout(cols=3, spacing=6, size_hint_y=0.12)
        for symbol in SYMBOLS:
            cell = BoxLayout(spacing=2)
            cell.add_widget(Image(source=symbol["image"], size_hint_x=0.45))
            cell.add_widget(
                GLabel(text="x" + str(symbol["pay"]), font_size=16, color=GOLD)
            )
            grid.add_widget(cell)
        return grid

    def on_pre_enter(self, *args):
        self.message_label.color = WHITE
        self.message_label.text = "Две одинаковые слева = x2"
        for i in range(3):
            self.reels[i].set_symbol(SYMBOLS[i])
        self.update_labels()

    def go_menu(self, *args):
        if self.spinning:
            return
        go_to(self.manager, "menu", "right")

    def current_bet(self):
        return BETS[self.bet_index]

    def update_labels(self):
        self.top_bar.set_balance(self.wallet.balance)
        self.bet_button.text = "Ставка: " + str(self.current_bet())

    def change_bet(self, *args):
        if self.spinning:
            return
        self.bet_index = self.bet_index + 1
        if self.bet_index >= len(BETS):
            self.bet_index = 0
        self.update_labels()

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
        self.stopped = [False, False, False]
        self.result = []
        for i in range(3):
            self.result.append(random.choice(self.pool))
            self.reels[i].start_spin()

        self.message_label.color = WHITE
        self.message_label.text = "Крутим..."
        self.update_labels()

        self.tick_event = Clock.schedule_interval(self.tick, 0.07)
        for i in range(3):
            Clock.schedule_once(partial(self.stop_reel, i), STOP_DELAYS[i])

    def tick(self, dt):
        for i in range(3):
            if not self.stopped[i]:
                self.reels[i].set_symbol(random.choice(self.pool))
                self.reels[i].jitter()

    def stop_reel(self, index, dt):
        self.stopped[index] = True
        self.reels[index].stop_spin(self.result[index])
        if index == 2:
            self.finish_spin()

    def finish_spin(self):
        if self.tick_event is not None:
            self.tick_event.cancel()
            self.tick_event = None

        win = calc_win(self.result, self.current_bet())
        if win > 0:
            self.wallet.add(win)
            self.message_label.color = GOLD
            self.message_label.text = "Выигрыш: " + str(win) + "!"
            pulse(self.message_label)
            float_text(self, "+" + str(win), GOLD, 0.45)
            for index in winning_reels(self.result):
                flash_glow(self.reels[index], 0.9)
        else:
            self.message_label.text = "Не повезло, попробуй ещё"

        if self.wallet.refill_if_broke():
            self.message_label.color = WHITE
            self.message_label.text = "Фишки кончились, держи новые"

        self.spinning = False
        self.spin_button.disabled = False
        self.update_labels()
