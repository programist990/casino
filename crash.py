import math
import random

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from common import (
    BETS,
    BLUE,
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
    float_text,
    go_to,
    pulse,
)

HISTORY_LIMIT = 6


class CrashGraph(Widget):
    """Canvas widget showing a dark radar grid and a rising glowing curve with a rocket marker."""

    curve_progress = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points = []
        self.crashed = False
        self.cashed_out = False
        with self.canvas.before:
            Color(0.04, 0.05, 0.08, 0.9)
            self.bg = RoundedRectangle(radius=[16])
            # Grid lines
            self.grid_color = Color(1, 1, 1, 0.06)
            self.grid_lines = [Line(points=[0, 0, 1, 1], width=1) for _ in range(5)]
            # Rising trail
            self.trail_glow = Color(1, 0.82, 0.25, 0.2)
            self.line_glow = Line(points=[], width=6)
            self.trail_color = Color(1, 0.82, 0.25, 1)
            self.line_curve = Line(points=[], width=2.5)
            # Rocket head
            self.rocket_color = Color(1, 0.85, 0.3, 1)
            self.rocket = RoundedRectangle(radius=[6])

        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        w, h = self.width, self.height
        x0, y0 = self.x, self.y

        # update grid
        for i in range(5):
            gy = y0 + (h / 5) * (i + 1)
            self.grid_lines[i].points = [x0 + 10, gy, x0 + w - 10, gy]

        self.update_curve(self.curve_progress)

    def update_curve(self, progress):
        self.curve_progress = progress
        if not self.points:
            x0 = self.x + 20
            y0 = self.y + 20
            self.line_curve.points = [x0, y0]
            self.line_glow.points = [x0, y0]
            self.rocket.pos = (x0 - 6, y0 - 6)
            self.rocket.size = (12, 12)
            return

        x0 = self.x + 20
        y0 = self.y + 20
        max_w = self.width - 40
        max_h = self.height - 40

        pts = []
        steps = len(self.points)
        for i, val in enumerate(self.points):
            px = x0 + (i / max(steps, 1)) * max_w
            # exponential curve upward
            py = y0 + min(1.0, (val - 1.0) / 4.0) * max_h
            pts.extend([px, py])

        self.line_curve.points = pts
        self.line_glow.points = pts
        if pts:
            tip_x, tip_y = pts[-2], pts[-1]
            self.rocket.pos = (tip_x - 7, tip_y - 7)
            self.rocket.size = (14, 14)

    def set_crashed(self):
        self.crashed = True
        self.trail_color.rgba = (0.9, 0.2, 0.2, 1)
        self.trail_glow.rgba = (0.9, 0.1, 0.1, 0.3)
        self.rocket_color.rgba = (1, 0.3, 0.3, 1)

    def set_cashed_out(self):
        self.cashed_out = True
        self.trail_color.rgba = (0.2, 0.9, 0.4, 1)
        self.trail_glow.rgba = (0.1, 0.9, 0.3, 0.3)
        self.rocket_color.rgba = (0.3, 1, 0.5, 1)

    def reset(self):
        self.points = [1.0]
        self.crashed = False
        self.cashed_out = False
        self.trail_color.rgba = GOLD
        self.trail_glow.rgba = (1, 0.82, 0.25, 0.25)
        self.rocket_color.rgba = (1, 0.9, 0.4, 1)
        self.redraw()


class CrashHistoryBadge(GLabel):
    def __init__(self, mult, **kwargs):
        super().__init__(text=f"{mult:.2f}x", **kwargs)
        self.font_size = 14
        self.size_hint = (None, None)
        self.size = (62, 28)
        color = GOLD if mult >= 2.0 else (SOFT_RED if mult < 1.5 else WHITE)
        self.color = color
        with self.canvas.before:
            Color(0.12, 0.14, 0.2, 0.9)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class CrashScreen(Screen):
    """Crash game: multiplier ticks up in real time, player must cash out before crash!"""

    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.bet_index = 0
        self.flying = False
        self.cashed_out = False
        self.multiplier = 1.00
        self.crash_point = 1.00
        self.history = [1.42, 3.10, 1.15, 2.05, 5.80]
        self.tick_event = None
        self.start_time = 0

        root = Page(padding=16, spacing=10)

        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        title = GLabel(text="CRASH РАКЕТА", font_size=32, color=GOLD, size_hint_y=0.08)
        root.add_widget(title)

        # History row
        self.history_row = BoxLayout(spacing=6, size_hint_y=0.05)
        root.add_widget(self.history_row)

        # Main graph display
        self.graph = CrashGraph(size_hint_y=0.38)
        graph_box = FloatLayout(size_hint_y=0.38)
        graph_box.add_widget(self.graph)

        self.mult_label = GLabel(
            text="1.00x",
            font_size=48,
            color=GOLD,
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            size_hint=(None, None),
            outline_width=3,
            outline_color=(0, 0, 0, 1),
        )
        graph_box.add_widget(self.mult_label)
        root.add_widget(graph_box)

        self.message_label = MessageLabel(size_hint_y=0.09)
        root.add_widget(self.message_label)

        # Controls
        self.bet_button = RoundButton(btn_color=GRAY, size_hint_y=0.09)
        self.bet_button.bind(on_release=self.change_bet)
        root.add_widget(self.bet_button)

        self.action_button = RoundButton(
            text="СТАРТ", btn_color=GREEN, size_hint_y=0.15
        )
        self.action_button.font_size = 28
        self.action_button.bind(on_release=self.on_action)
        root.add_widget(self.action_button)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.update_labels()
        self.refresh_history()
        self.message_label.color = WHITE
        self.message_label.text = "Сделай ставку и жми СТАРТ"
        self.graph.reset()
        self.mult_label.text = "1.00x"
        self.mult_label.color = GOLD

    def go_menu(self, *args):
        if self.flying:
            return
        go_to(self.manager, "menu", "right")

    def current_bet(self):
        return BETS[self.bet_index]

    def update_labels(self):
        self.top_bar.set_balance(self.wallet.balance)
        self.bet_button.text = "Ставка: " + str(self.current_bet())

    def refresh_history(self):
        self.history_row.clear_widgets()
        self.history_row.add_widget(Widget())
        for m in reversed(self.history[-HISTORY_LIMIT:]):
            self.history_row.add_widget(CrashHistoryBadge(m))
        self.history_row.add_widget(Widget())

    def change_bet(self, *args):
        if self.flying:
            return
        self.bet_index = self.bet_index + 1
        if self.bet_index >= len(BETS):
            self.bet_index = 0
        self.update_labels()
        Sfx.play("chip")

    def generate_crash_point(self):
        # 96% RTP house edge formula
        r = random.random()
        if r < 0.04:
            return 1.00
        mult = 0.96 / (1.0 - r)
        return max(1.01, round(mult, 2))

    def on_action(self, *args):
        if not self.flying:
            self.start_flight()
        else:
            self.cash_out()

    def start_flight(self):
        bet = self.current_bet()
        if not self.wallet.can_pay(bet):
            self.message_label.color = SOFT_RED
            self.message_label.text = "Не хватает фишек, уменьши ставку"
            Sfx.play("lose")
            return

        self.wallet.take(bet)
        self.update_labels()
        self.flying = True
        self.cashed_out = False
        self.multiplier = 1.00
        self.crash_point = self.generate_crash_point()
        self.graph.reset()

        self.bet_button.disabled = True
        self.action_button.text = f"ЗАБРАТЬ ({bet})"
        self.action_button.btn_color = GOLD
        self.message_label.color = WHITE
        self.message_label.text = "Ракета летит! Успей забрать"

        Sfx.play("spin")
        self.tick_event = Clock.schedule_interval(self.tick, 0.05)

    def tick(self, dt):
        if not self.flying:
            return

        # Growth formula accelerates over time
        growth_rate = 0.015 + (self.multiplier - 1.0) * 0.05
        self.multiplier = round(self.multiplier + growth_rate, 2)

        self.mult_label.text = f"{self.multiplier:.2f}x"
        self.graph.points.append(self.multiplier)
        self.graph.redraw()

        if not self.cashed_out:
            potential = int(self.current_bet() * self.multiplier)
            self.action_button.text = f"ЗАБРАТЬ (+{potential})"

        if self.multiplier >= self.crash_point:
            self.crash()

    def cash_out(self):
        if not self.flying or self.cashed_out:
            return

        self.cashed_out = True
        win = int(self.current_bet() * self.multiplier)
        net = win - self.current_bet()
        self.wallet.add(win)
        self.wallet.record_game(net, self.current_bet())
        self.top_bar.set_balance(self.wallet.balance)

        self.graph.set_cashed_out()
        self.action_button.disabled = True
        self.action_button.text = f"ЗАБРАЛ: +{win}"
        self.action_button.btn_color = GRAY
        self.message_label.color = GOLD
        self.message_label.text = f"Успел забрать на x{self.multiplier:.2f}! (+{win})"
        pulse(self.message_label)
        float_text(self, f"+{win}", GOLD, 0.45)
        Sfx.play("win")

    def crash(self):
        if self.tick_event is not None:
            self.tick_event.cancel()
            self.tick_event = None

        self.flying = False
        self.graph.set_crashed()
        self.mult_label.text = f"КРАШ! {self.crash_point:.2f}x"
        self.mult_label.color = SOFT_RED
        pulse(self.mult_label)
        Sfx.play("crash")

        self.history.append(self.crash_point)
        self.refresh_history()

        if not self.cashed_out:
            bet = self.current_bet()
            self.wallet.record_game(-bet, bet)
            self.message_label.color = SOFT_RED
            self.message_label.text = f"Ракета взорвалась на x{self.crash_point:.2f}!"
            float_text(self, f"-{bet}", SOFT_RED, 0.45)

        if self.wallet.refill_if_broke():
            self.message_label.color = WHITE
            self.message_label.text = "Фишки кончились, держи новые"

        self.action_button.text = "СТАРТ"
        self.action_button.btn_color = GREEN
        self.action_button.disabled = False
        self.bet_button.disabled = False
        self.update_labels()
