import math
import os
import random
from functools import partial

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    PopMatrix,
    PushMatrix,
    Rectangle,
    Rotate,
    RoundedRectangle,
)
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from common import (
    BASE_DIR,
    BETS,
    BLUE,
    CHIP_IMAGE,
    FONT_SUITS,
    FONT_TITLE,
    GOLD,
    GRAY,
    GREEN,
    RED,
    SOFT_RED,
    WHITE,
    GLabel,
    MessageLabel,
    RoundButton,
    TopBar,
    float_text,
    get_gradient,
    go_to,
    pulse,
)

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["S", "H", "D", "C"]  # spades, hearts, diamonds, clubs
SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
CARD_W = 58
CARD_H = 86
CARD_GAP = 6
FLIGHT = 0.3  # how long a card flies from the shoe to the table
CARD_DELAY = 0.4  # pause between dealt cards
RED_CARD = (0.85, 0.1, 0.1, 1)
BLACK_CARD = (0.1, 0.1, 0.12, 1)

# ----- assets (all optional: the table still works without them) -----


def asset(folder, name):
    path = os.path.join(BASE_DIR, "assets", folder, name)
    if os.path.exists(path):
        return path
    return None


def tex(path):
    """Keyword arguments for a graphics instruction with an optional image."""
    if path:
        return {"source": path}
    return {}


FELT = asset("blackjack", "felt.png")
SPOT = asset("blackjack", "spot.png")
CARD_BACK = asset("blackjack", "card_back.png")
CHIP_LIST = [
    asset("blackjack", "chip_10.png") or CHIP_IMAGE,
    asset("blackjack", "chip_50.png") or CHIP_IMAGE,
    asset("blackjack", "chip_100.png") or CHIP_IMAGE,
    asset("blackjack", "chip_500.png") or CHIP_IMAGE,
]
SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")


class Sfx:
    """Tiny sound player. Silent if a file or the audio backend is missing."""

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


# ----- game rules -----


def new_deck():
    deck = []
    for suit in SUITS:
        for rank in RANKS:
            deck.append((rank, suit))
    random.shuffle(deck)
    return deck


def hand_value(hand):
    total = 0
    aces = 0
    for card in hand:
        rank = card[0]
        if rank == "A":
            aces = aces + 1
            total = total + 11
        elif rank == "J" or rank == "Q" or rank == "K":
            total = total + 10
        else:
            total = total + int(rank)
    while total > 21 and aces > 0:
        total = total - 10
        aces = aces - 1
    return total


def landed_count(views):
    count = 0
    for view in views:
        if view.landed:
            count = count + 1
    return count


def total_color(value):
    if value > 21:
        return SOFT_RED
    if value == 21:
        return GOLD
    return WHITE


def arc_points(cx, cy, rx, ry, lower, steps=36):
    """Flat [x, y, ...] list of a half ellipse (lower half = smile)."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        if lower:
            theta = math.pi + math.pi * t
        else:
            theta = math.pi * t
        points.append(cx + rx * math.cos(theta))
        points.append(cy + ry * math.sin(theta))
    return points


def remove_item(animation, widget):
    if widget.parent is not None:
        widget.parent.remove_widget(widget)


# ----- cards -----


class CardView(BoxLayout):
    """A playing card. Starts face down or face up, can flip over."""

    angle = NumericProperty(0)

    def __init__(self, card, hidden, **kwargs):
        super().__init__(orientation="vertical", padding=(0, 6), **kwargs)
        self.card = card
        self.hidden = hidden
        self.landed = False
        self.frame_target = 0
        self.full_width = CARD_W
        self.size_hint = (None, None)
        self.size = (self.full_width, CARD_H)
        self.pos_hint = {"center_y": 0.5}

        with self.canvas.before:
            PushMatrix()
            self.rotation = Rotate(angle=0, origin=(0, 0))
            Color(0, 0, 0, 0.3)
            self.shadow = RoundedRectangle(radius=[10])
            self.face_color = Color(1, 1, 1, 1)
            self.bg = RoundedRectangle(radius=[10])
            self.back_color = Color(1, 1, 1, 0)
            self.back = RoundedRectangle(radius=[10], **tex(CARD_BACK))
            self.edge_color = Color(0, 0, 0, 0.28)
            self.edge = Line(rounded_rectangle=(0, 0, 20, 20, 10), width=1)
            self.frame_color = Color(1, 0.82, 0.25, 0)
            self.frame = Line(rounded_rectangle=(0, 0, 20, 20, 7), width=1.3)
        with self.canvas.after:
            PopMatrix()

        self.rank_label = Label(font_name=FONT_TITLE, font_size=24)
        self.suit_label = Label(font_name=FONT_SUITS, font_size=32)
        self.add_widget(self.rank_label)
        self.add_widget(self.suit_label)

        self.bind(pos=self.update_bg, size=self.update_bg, angle=self.update_bg)
        self.show_side()

    def update_bg(self, *args):
        x, y = self.pos
        width, height = self.size
        self.rotation.angle = self.angle
        self.rotation.origin = self.center
        self.shadow.pos = (x + 2, y - 3)
        self.shadow.size = self.size
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.back.pos = self.pos
        self.back.size = self.size
        # thin outlines look broken while the card is squeezed during a flip
        if width >= 24:
            self.edge_color.a = 0.28
            self.frame_color.a = self.frame_target
            self.edge.rounded_rectangle = (x, y, width, height, 10)
            self.frame.rounded_rectangle = (x + 4, y + 4, width - 8, height - 8, 7)
        else:
            self.edge_color.a = 0
            self.frame_color.a = 0

    def show_side(self):
        if self.hidden:
            self.face_color.rgba = (0.15, 0.3, 0.7, 1)
            self.rank_label.text = ""
            self.frame_target = 0
            if CARD_BACK:
                self.back_color.a = 1
                self.suit_label.text = ""
            else:
                self.back_color.a = 0
                self.suit_label.text = "♦"
                self.suit_label.color = (0.55, 0.7, 1, 1)
        else:
            self.face_color.rgba = (1, 1, 1, 1)
            self.back_color.a = 0
            suit = self.card[1]
            rank = self.card[0]
            if suit == "H" or suit == "D":
                color = RED_CARD
            else:
                color = BLACK_CARD
            self.rank_label.text = rank
            self.rank_label.color = color
            self.suit_label.text = SUIT_SYMBOLS[suit]
            self.suit_label.color = color
            if rank == "A":
                self.suit_label.font_size = 42
            else:
                self.suit_label.font_size = 32
            if rank == "J" or rank == "Q" or rank == "K":
                self.frame_target = 0.9
            else:
                self.frame_target = 0
        self.update_bg()

    def flip_up(self):
        """Turns a face-down card face up: narrows, swaps the side, widens."""
        self.rank_label.opacity = 0
        self.suit_label.opacity = 0
        anim = Animation(width=2, duration=0.15)
        anim.bind(on_complete=self.finish_flip)
        anim.start(self)

    def finish_flip(self, *args):
        self.hidden = False
        self.show_side()
        self.rank_label.opacity = 1
        self.suit_label.opacity = 1
        Animation(width=self.full_width, duration=0.15).start(self)

    def land(self):
        """Little bounce when the card touches the table."""
        self.hop(10)

    def hop(self, lift):
        Animation.cancel_all(self, "height")
        anim = Animation(height=CARD_H + lift, duration=0.08, t="out_quad")
        anim += Animation(height=CARD_H, duration=0.3, t="out_bounce")
        anim.start(self)

    def dim(self):
        Animation(opacity=0.5, duration=0.4).start(self)


def make_row():
    row = BoxLayout(size_hint_y=0.2, spacing=CARD_GAP)
    row.left_spacer = Widget()
    row.right_spacer = Widget()
    row.add_widget(row.left_spacer)
    row.add_widget(row.right_spacer)
    return row


# ----- table decoration -----


class Shoe(Widget):
    """Stack of card backs in the corner, cards fly out of it."""

    nudge = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(size_hint=(None, None), size=(44, 62), **kwargs)
        self.bind(pos=self.redraw, size=self.redraw, nudge=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            for i in range(4):
                shift = (3 - i) * 2
                x = self.x + shift
                y = self.y - shift
                if i == 3:
                    x = x - self.nudge
                Color(0, 0, 0, 0.3)
                RoundedRectangle(pos=(x + 2, y - 2), size=self.size, radius=[7])
                Color(1, 1, 1, 1)
                RoundedRectangle(pos=(x, y), size=self.size, radius=[7], **tex(CARD_BACK))

    def kick(self):
        Animation.cancel_all(self, "nudge")
        anim = Animation(nudge=10, duration=0.05)
        anim += Animation(nudge=0, duration=0.2, t="out_quad")
        anim.start(self)


class TableBackground(FloatLayout):
    """Casino table: felt, warm lamp, gold lines, drifting suits and sparkles."""

    glow = NumericProperty(0.5)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.anchors = None

        with self.canvas:
            Color(1, 1, 1, 1)
            self.base = Rectangle(texture=get_gradient())
            if FELT:
                Color(1, 1, 1, 1)
                self.felt = Rectangle(source=FELT)
            else:
                self.felt = None
            self.spot_color = Color(1, 0.92, 0.6, 0)
            self.spot = Rectangle(**tex(SPOT))
            self.arcs = []
            for alpha, width in ((0.32, 1.8), (0.16, 1.2), (0.32, 1.8), (0.16, 1.2)):
                Color(1, 0.82, 0.25, alpha)
                self.arcs.append(Line(points=[0, 0, 1, 1], width=width))

        self.drifters = []
        for i in range(9):
            suit = random.choice(["♠", "♥", "♦", "♣"])
            alpha = random.uniform(0.05, 0.1)
            if suit == "♥" or suit == "♦":
                color = (1, 0.45, 0.45, alpha)
            else:
                color = (1, 1, 1, alpha)
            label = Label(
                text=suit,
                font_name=FONT_SUITS,
                font_size=random.randint(26, 62),
                color=color,
                size_hint=(None, None),
            )
            label.texture_update()
            label.size = label.texture_size
            label.speed = random.uniform(10, 26)
            self.drifters.append(label)
            self.add_widget(label)

        self.sparks = []
        for i in range(10):
            spark = Label(
                text="✦",
                font_name=FONT_SUITS,
                font_size=random.randint(12, 22),
                color=(1, 0.85, 0.4, 0.9),
                size_hint=(None, None),
                opacity=0,
            )
            spark.texture_update()
            spark.size = spark.texture_size
            self.sparks.append(spark)
            self.add_widget(spark)

        self.caption_top = self.make_caption("БЛЭКДЖЕК ПЛАТИТ 3 К 2")
        self.caption_bottom = self.make_caption("ДИЛЕР БЕРЁТ ДО 17")
        self.shoe = Shoe()
        self.add_widget(self.shoe)

        self.bind(pos=self.layout_decor, size=self.layout_decor)
        self.on_glow(self, self.glow)
        self.layout_decor()

    def make_caption(self, text):
        label = GLabel(
            text=text,
            font_size=13,
            color=(1, 0.82, 0.25, 0.34),
            size_hint=(None, None),
        )
        label.texture_update()
        label.size = label.texture_size
        self.add_widget(label)
        return label

    def track(self, title, dealer_row, player_row):
        """Remembers the widgets the decoration is drawn around."""
        self.anchors = (title, dealer_row, player_row)
        for widget in self.anchors:
            widget.bind(pos=self.layout_decor, size=self.layout_decor)
        self.layout_decor()

    def on_glow(self, instance, value):
        self.spot_color.a = value * 0.4

    def layout_decor(self, *args):
        self.base.pos = self.pos
        self.base.size = self.size
        if self.felt is not None:
            self.felt.pos = self.pos
            self.felt.size = self.size
        side = self.width * 1.6
        self.spot.size = (side, side)
        self.spot.pos = (self.center_x - side / 2, self.center_y - side / 2)

        if self.anchors is None:
            return
        title, dealer_row, player_row = self.anchors
        cx = self.center_x
        rx = self.width * 0.46
        ry = 56

        cy = dealer_row.y + 2 + ry
        self.arcs[0].points = arc_points(cx, cy, rx, ry, True)
        self.arcs[1].points = arc_points(cx, cy, rx - 12, ry - 8, True)
        cy = player_row.top - 2 - ry
        self.arcs[2].points = arc_points(cx, cy, rx, ry, False)
        self.arcs[3].points = arc_points(cx, cy, rx - 12, ry - 8, False)

        self.caption_top.center_x = cx
        self.caption_top.y = dealer_row.y + 8
        self.caption_bottom.center_x = cx
        self.caption_bottom.top = player_row.top - 8
        self.shoe.x = title.right - self.shoe.width - 14
        self.shoe.center_y = title.center_y

    def shoe_center(self):
        return (self.shoe.center_x, self.shoe.center_y)

    # ----- ambient animation, runs only while the screen is visible -----

    def start_ambient(self):
        self.stop_ambient()
        width = max(self.width, 1)
        height = max(self.height, 1)
        for label in self.drifters:
            label.x = random.uniform(0, max(1, width - label.width))
            label.y = random.uniform(-label.height, height)
            self.drift(label)
        for spark in self.sparks:
            spark.x = random.uniform(10, max(11, width - 30))
            spark.y = random.uniform(10, max(11, height - 30))
            spark.opacity = 0
            anim = Animation(opacity=0, duration=random.uniform(0, 2.5))
            anim += Animation(
                opacity=random.uniform(0.4, 0.9),
                duration=random.uniform(0.6, 1.2),
                t="in_out_sine",
            )
            anim += Animation(opacity=0, duration=random.uniform(0.6, 1.2), t="in_out_sine")
            anim.repeat = True
            anim.start(spark)
        glow = Animation(glow=0.95, duration=2.4, t="in_out_sine")
        glow += Animation(glow=0.5, duration=2.4, t="in_out_sine")
        glow.repeat = True
        glow.start(self)

    def drift(self, label):
        """Floats one big faint suit upwards, then sends it back to the bottom."""
        distance = self.height + 10 - label.y
        rise = Animation(y=self.height + 10, duration=max(1.0, distance / label.speed))
        rise.bind(on_complete=partial(self.schedule_recycle))
        rise.start(label)
        sway = random.uniform(14, 34)
        side = Animation(x=label.x + sway, duration=random.uniform(4, 7), t="in_out_sine")
        side += Animation(x=label.x, duration=random.uniform(4, 7), t="in_out_sine")
        side.repeat = True
        side.start(label)

    def schedule_recycle(self, animation, label):
        Clock.schedule_once(partial(self.recycle, label), 0)

    def recycle(self, label, dt):
        Animation.cancel_all(label)
        label.x = random.uniform(0, max(1, self.width - label.width))
        label.y = -label.height - 10
        self.drift(label)

    def stop_ambient(self):
        for label in self.drifters:
            Animation.cancel_all(label)
        for spark in self.sparks:
            Animation.cancel_all(spark)
            spark.opacity = 0
        Animation.cancel_all(self, "glow")


class BetStack(Widget):
    """The bet on the table: a stack of chips inside a gold ring."""

    lift = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(size_hint=(None, None), size=(48, 48), **kwargs)
        self.count = 0
        self.source = CHIP_IMAGE
        self.label = GLabel(
            text="",
            font_size=18,
            color=GOLD,
            size_hint=(None, None),
            size=(70, 26),
            halign="right",
            valign="middle",
        )
        self.label.text_size = self.label.size
        self.add_widget(self.label)
        self.bind(pos=self.redraw, size=self.redraw, lift=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.before.clear()
        cx = self.center_x
        with self.canvas.before:
            Color(1, 0.82, 0.25, 0.4)
            Line(circle=(cx, self.y + 22, 23), width=1.4)
            for i in range(self.count):
                y = self.y + 6 + i * 6 + self.lift * (i + 1) / self.count
                Color(0, 0, 0, 0.35)
                Ellipse(pos=(cx - 15, y - 2), size=(34, 34))
                Color(1, 1, 1, 1)
                Rectangle(source=self.source, pos=(cx - 17, y), size=(34, 34))
        self.label.right = self.x - 2
        self.label.center_y = self.y + 24

    def set_bet(self, amount, count, source, animate=True):
        self.count = count
        self.source = source
        self.label.text = str(amount)
        self.redraw()
        if animate:
            Animation.cancel_all(self, "lift")
            anim = Animation(lift=16, duration=0.08)
            anim += Animation(lift=0, duration=0.35, t="out_bounce")
            anim.start(self)

    def clear(self):
        self.count = 0
        self.label.text = ""
        self.redraw()

    def chip_center(self):
        return (self.center_x, self.y + 23)


class SoundToggle(Label):
    """Small note icon: tap to mute / unmute the table sounds."""

    def __init__(self, **kwargs):
        super().__init__(
            text="♪",
            font_name=FONT_SUITS,
            font_size=28,
            size_hint=(None, None),
            size=(44, 44),
            **kwargs
        )
        self.refresh()

    def refresh(self):
        if Sfx.enabled:
            self.color = (1, 0.82, 0.25, 0.85)
        else:
            self.color = (1, 1, 1, 0.25)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            Sfx.enabled = not Sfx.enabled
            self.refresh()
            Sfx.play("chip")
            return True
        return super().on_touch_down(touch)


class TableLayout(BoxLayout):
    """Vertical layout without its own background (the table draws it)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)


# ----- screen -----


class BlackjackScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.bet_index = 0
        self.bet = 0
        self.deck = []
        self.player = []
        self.dealer = []
        self.player_views = []
        self.dealer_views = []
        self.dealer_hidden = True
        self.in_round = False
        self.busy = False
        self.streak = 0
        self.dots_event = None
        self.dots_base = ""
        self.dots_step = 0

        self.table_bg = TableBackground()
        self.add_widget(self.table_bg)

        root = TableLayout(padding=16, spacing=8)
        self.root_layout = root

        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        self.title_label = GLabel(
            text="BLACKJACK", font_size=32, color=GOLD, size_hint_y=0.08
        )
        root.add_widget(self.title_label)

        self.dealer_label = GLabel(font_size=20, size_hint_y=0.06)
        root.add_widget(self.dealer_label)
        self.dealer_row = make_row()
        root.add_widget(self.dealer_row)

        self.message_label = MessageLabel(size_hint_y=0.1)
        root.add_widget(self.message_label)

        self.player_row = make_row()
        root.add_widget(self.player_row)
        self.player_label = GLabel(font_size=20, size_hint_y=0.06)
        root.add_widget(self.player_label)

        self.controls = BoxLayout(spacing=10, size_hint_y=0.13)
        root.add_widget(self.controls)

        self.bet_button = RoundButton(btn_color=GRAY)
        self.bet_button.bind(on_release=self.change_bet)
        self.deal_button = RoundButton(text="РАЗДАТЬ", btn_color=GREEN)
        self.deal_button.bind(on_release=self.deal)
        self.hit_button = RoundButton(text="ЕЩЁ", btn_color=BLUE)
        self.hit_button.bind(on_release=self.hit)
        self.stand_button = RoundButton(text="ХВАТИТ", btn_color=RED)
        self.stand_button.bind(on_release=self.stand)

        self.add_widget(root)

        self.bet_stack = BetStack()
        self.add_widget(self.bet_stack)
        self.sound_toggle = SoundToggle()
        self.add_widget(self.sound_toggle)

        self.table_bg.track(self.title_label, self.dealer_row, self.player_row)
        self.player_label.bind(pos=self.place_overlays, size=self.place_overlays)
        self.bind(size=self.place_overlays)
        Clock.schedule_once(self.place_overlays, 0)

    def place_overlays(self, *args):
        self.bet_stack.x = self.player_label.right - self.bet_stack.width - 6
        self.bet_stack.y = self.player_label.y - 6
        self.sound_toggle.x = self.title_label.x
        self.sound_toggle.center_y = self.title_label.center_y

    def on_pre_enter(self, *args):
        self.in_round = False
        self.set_busy(False)
        self.player = []
        self.dealer = []
        self.dealer_hidden = True
        self.clear_table()
        self.set_message("Сделай ставку")
        self.refresh_totals()
        self.show_idle_controls()
        self.show_bet_chips(False)
        self.play_intro()

    def on_enter(self, *args):
        self.table_bg.start_ambient()

    def on_leave(self, *args):
        self.table_bg.stop_ambient()
        self.stop_dots()

    def go_menu(self, *args):
        if self.in_round or self.busy:
            self.set_message("Сначала доиграй раунд", SOFT_RED)
            self.shake(6)
            return
        go_to(self.manager, "menu", "right")

    # ----- small animation helpers -----

    def fade_in(self, widget, dt):
        Animation(opacity=1, duration=0.3, t="out_quad").start(widget)

    def play_intro(self):
        """Parts of the table appear one after another."""
        delay = 0.0
        for widget in reversed(self.root_layout.children):
            Animation.cancel_all(widget, "opacity")
            widget.opacity = 0
            Clock.schedule_once(partial(self.fade_in, widget), delay)
            delay = delay + 0.06

    def fade_in_button(self, button, delay):
        Animation.cancel_all(button, "opacity")
        button.opacity = 0
        Clock.schedule_once(partial(self.fade_in, button), delay)

    def start_breathing(self):
        """The deal button gently pulses while the player is choosing a bet."""
        Animation.cancel_all(self.deal_button, "opacity")
        self.deal_button.opacity = 0
        first = Animation(opacity=1, duration=0.3)
        breath = Animation(opacity=0.78, duration=0.9, t="in_out_sine")
        breath += Animation(opacity=1, duration=0.9, t="in_out_sine")
        breath.repeat = True
        first.bind(on_complete=partial(self.begin_breath, breath))
        first.start(self.deal_button)

    def begin_breath(self, breath, animation, widget):
        breath.start(widget)

    def stop_breathing(self):
        Animation.cancel_all(self.deal_button, "opacity")
        self.deal_button.opacity = 1

    def pop_label(self, label, big, small):
        Animation.cancel_all(label, "font_size")
        label.font_size = small
        anim = Animation(font_size=big, duration=0.08)
        anim += Animation(font_size=small, duration=0.25, t="out_back")
        anim.start(label)

    def set_message(self, text, color=WHITE, dots=False):
        self.stop_dots()
        self.message_label.color = color
        self.message_label.text = text
        Animation.cancel_all(self.message_label, "opacity")
        self.message_label.opacity = 0.4
        Animation(opacity=1, duration=0.25).start(self.message_label)
        if dots:
            self.dots_base = text
            self.dots_step = 0
            self.dots_event = Clock.schedule_interval(self.tick_dots, 0.35)

    def tick_dots(self, dt):
        self.dots_step = self.dots_step + 1
        self.message_label.text = self.dots_base + "." * (self.dots_step % 4)

    def stop_dots(self):
        if self.dots_event is not None:
            self.dots_event.cancel()
            self.dots_event = None

    def set_total(self, label, text, color):
        changed = label.text != text
        label.text = text
        label.color = color
        if changed:
            self.pop_label(label, 27, 20)

    def shake(self, strength=10):
        Animation.cancel_all(self.root_layout, "x")
        anim = Animation(x=-strength, duration=0.04)
        anim += Animation(x=strength * 0.9, duration=0.05)
        anim += Animation(x=-strength * 0.7, duration=0.05)
        anim += Animation(x=strength * 0.45, duration=0.05)
        anim += Animation(x=0, duration=0.05)
        anim.start(self.root_layout)

    def flash(self, rgb, alpha):
        overlay = Widget()
        with overlay.canvas:
            Color(rgb[0], rgb[1], rgb[2], alpha)
            Rectangle(pos=(0, 0), size=self.size)
        overlay.opacity = 0
        self.add_widget(overlay)
        anim = Animation(opacity=1, duration=0.08)
        anim += Animation(opacity=0, duration=0.55)
        anim.bind(on_complete=remove_item)
        anim.start(overlay)

    def show_banner(self, text, color, size=58):
        banner = GLabel(
            text=text,
            font_size=10,
            color=color,
            size_hint=(1, None),
            height=140,
            outline_width=4,
            outline_color=(0, 0, 0, 1),
        )
        banner.x = 0
        banner.center_y = self.message_label.center_y
        banner.opacity = 0
        self.add_widget(banner)
        anim = Animation(font_size=size, opacity=1, duration=0.35, t="out_back")
        anim += Animation(duration=0.9)
        anim += Animation(opacity=0, y=banner.y + 40, duration=0.4)
        anim.bind(on_complete=remove_item)
        anim.start(banner)

    def burst(self, x, y, count, color=GOLD):
        """Sparkles flying out of a point."""
        for i in range(count):
            star = Label(
                text="✦",
                font_name=FONT_SUITS,
                font_size=random.randint(14, 28),
                color=color,
                size_hint=(None, None),
            )
            star.texture_update()
            star.size = star.texture_size
            star.x = x - star.width / 2
            star.y = y - star.height / 2
            self.add_widget(star)
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(50, 140)
            anim = Animation(
                x=star.x + math.cos(angle) * distance,
                y=star.y + math.sin(angle) * distance,
                opacity=0,
                duration=random.uniform(0.6, 1.0),
                t="out_quad",
            )
            anim.bind(on_complete=remove_item)
            anim.start(star)

    def coin_rain(self, count):
        for i in range(count):
            Clock.schedule_once(self.drop_confetti, random.uniform(0, 0.9))

    def drop_confetti(self, dt):
        size = random.randint(18, 34)
        if random.random() < 0.55:
            item = Image(
                source=random.choice(CHIP_LIST),
                size_hint=(None, None),
                size=(size, size),
            )
        else:
            suit = random.choice(["♠", "♥", "♦", "♣"])
            if suit == "♥" or suit == "♦":
                color = (1, 0.4, 0.4, 1)
            else:
                color = (1, 1, 1, 1)
            item = Label(
                text=suit,
                font_name=FONT_SUITS,
                font_size=size,
                color=color,
                size_hint=(None, None),
            )
            item.texture_update()
            item.size = item.texture_size
        item.x = random.uniform(0, max(1, self.width - size))
        item.y = self.height + 10
        self.add_widget(item)
        fall = random.uniform(1.3, 2.3)
        sway = random.uniform(-40, 40)
        start_x = item.x
        side = Animation(x=start_x + sway, duration=fall / 2, t="in_out_sine")
        side += Animation(x=start_x, duration=fall / 2, t="in_out_sine")
        side.start(item)
        drop = Animation(y=-60, duration=fall, t="in_quad")
        drop.bind(on_complete=remove_item)
        drop.start(item)

    def fly_chip(self, source, start, end, delay=0.0, size=30):
        Clock.schedule_once(partial(self.launch_chip, source, start, end, size), delay)

    def launch_chip(self, source, start, end, size, dt):
        chip = Image(source=source, size_hint=(None, None), size=(size, size))
        chip.x = start[0] - size / 2
        chip.y = start[1] - size / 2
        self.add_widget(chip)
        anim = Animation(
            x=end[0] - size / 2,
            y=end[1] - size / 2,
            duration=0.5,
            t="in_out_quad",
        )
        anim += Animation(opacity=0, duration=0.08)
        anim.bind(on_complete=remove_item)
        anim.start(chip)

    def balance_target(self):
        return (self.top_bar.right - 22, self.top_bar.center_y)

    # ----- ui -----

    def current_bet(self):
        return BETS[self.bet_index]

    def set_busy(self, flag):
        self.busy = flag
        self.deal_button.disabled = flag
        self.hit_button.disabled = flag
        self.stand_button.disabled = flag

    def show_bet_chips(self, animate=True):
        count = min(self.bet_index + 1, 5)
        source = CHIP_LIST[min(self.bet_index, len(CHIP_LIST) - 1)]
        self.bet_stack.set_bet(self.current_bet(), count, source, animate)

    def show_idle_controls(self, update_balance=True):
        self.controls.clear_widgets()
        self.controls.add_widget(self.bet_button)
        self.controls.add_widget(self.deal_button)
        self.bet_button.text = "Ставка: " + str(self.current_bet())
        if update_balance:
            self.top_bar.set_balance(self.wallet.balance)
        self.fade_in_button(self.bet_button, 0.0)
        self.start_breathing()

    def show_play_controls(self):
        self.stop_breathing()
        self.controls.clear_widgets()
        self.controls.add_widget(self.hit_button)
        self.controls.add_widget(self.stand_button)
        self.top_bar.set_balance(self.wallet.balance)
        self.fade_in_button(self.hit_button, 0.0)
        self.fade_in_button(self.stand_button, 0.08)

    def change_bet(self, *args):
        if self.busy or self.in_round:
            return
        self.bet_index = self.bet_index + 1
        if self.bet_index >= len(BETS):
            self.bet_index = 0
        self.bet_button.text = "Ставка: " + str(self.current_bet())
        self.pop_label(self.bet_button, 27, 22)
        self.show_bet_chips()
        Sfx.play("chip")

    def clear_row(self, row):
        row.clear_widgets()
        row.add_widget(row.left_spacer)
        row.add_widget(row.right_spacer)
        Animation.cancel_all(row, "spacing")
        row.spacing = CARD_GAP

    def clear_table(self):
        self.clear_row(self.dealer_row)
        self.clear_row(self.player_row)
        self.player_views = []
        self.dealer_views = []

    def fit_gap(self, row, count):
        """Gap between cards; goes negative (cards overlap) when the row is full."""
        available = row.width - 8
        needed = count * CARD_W + (count - 1) * CARD_GAP
        if count <= 1 or needed <= available:
            return CARD_GAP
        return (available - count * CARD_W) / (count - 1)

    def card_target(self, row, count, gap):
        """Where the newest card ends up once the row has finished laying out."""
        leftover = row.width - count * CARD_W - (count + 1) * gap
        left = row.x + leftover / 2 + gap + (count - 1) * (CARD_W + gap)
        return (left + CARD_W / 2, row.center_y)

    def add_card_view(self, row, views, card, hidden):
        view = CardView(card, hidden)
        view.width = 8
        view.opacity = 0
        views.append(view)
        count = len(views)
        gap = self.fit_gap(row, count)

        row.remove_widget(row.right_spacer)
        row.add_widget(view)
        row.add_widget(row.right_spacer)
        Animation(spacing=gap, duration=FLIGHT, t="out_quad").start(row)
        Animation(width=view.full_width, duration=FLIGHT, t="out_quad").start(view)

        self.fly_card(card, hidden, self.card_target(row, count, gap), view)

    def fly_card(self, card, hidden, target, view):
        """A copy of the card flies from the shoe, then the real card appears."""
        ghost = CardView(card, hidden)
        ghost.pos_hint = {}
        sx, sy = self.table_bg.shoe_center()
        ghost.x = sx - CARD_W / 2
        ghost.y = sy - CARD_H / 2
        ghost.angle = random.uniform(-40, -15)
        self.add_widget(ghost)
        self.table_bg.shoe.kick()
        Sfx.play("deal")
        anim = Animation(
            x=target[0] - CARD_W / 2,
            y=target[1] - CARD_H / 2,
            angle=0,
            duration=FLIGHT,
            t="out_quad",
        )
        anim.bind(on_complete=partial(self.finish_flight, view))
        anim.start(ghost)

    def finish_flight(self, view, animation, ghost):
        if ghost.parent is not None:
            ghost.parent.remove_widget(ghost)
        view.landed = True
        view.opacity = 1
        view.land()
        self.refresh_totals()

    def refresh_totals(self):
        """Totals count only the cards that already landed on the table."""
        shown_player = self.player[: landed_count(self.player_views)]
        shown_dealer = self.dealer[: landed_count(self.dealer_views)]

        if len(shown_player) == 0:
            self.set_total(self.player_label, "Игрок", WHITE)
        else:
            value = hand_value(shown_player)
            self.set_total(self.player_label, "Игрок: " + str(value), total_color(value))

        if len(shown_dealer) == 0 or self.dealer_hidden:
            self.set_total(self.dealer_label, "Дилер", WHITE)
        else:
            value = hand_value(shown_dealer)
            self.set_total(self.dealer_label, "Дилер: " + str(value), total_color(value))

    # ----- dealing animation -----

    def sync_cards(self, done):
        """Puts missing cards on the table one by one, then calls done()."""
        player_count = len(self.player_views)
        dealer_count = len(self.dealer_views)

        if player_count < len(self.player) and player_count <= dealer_count:
            card = self.player[player_count]
            self.add_card_view(self.player_row, self.player_views, card, False)
        elif dealer_count < len(self.dealer):
            card = self.dealer[dealer_count]
            hidden = self.dealer_hidden and dealer_count == 1
            self.add_card_view(self.dealer_row, self.dealer_views, card, hidden)
        elif player_count < len(self.player):
            card = self.player[player_count]
            self.add_card_view(self.player_row, self.player_views, card, False)
        else:
            self.refresh_totals()
            done()
            return

        Clock.schedule_once(partial(self.sync_next, done), CARD_DELAY)

    def sync_next(self, done, dt):
        self.sync_cards(done)

    def call_done(self, done, dt):
        done()

    def reveal_dealer(self, done):
        """Flips the dealer's hidden card, then calls done()."""
        self.dealer_hidden = False
        if len(self.dealer_views) > 1 and self.dealer_views[1].hidden:
            self.dealer_views[1].flip_up()
            Sfx.play("flip")
        Clock.schedule_once(self.refresh_totals_later, 0.35)
        Clock.schedule_once(partial(self.call_done, done), 0.6)

    def refresh_totals_later(self, dt):
        self.refresh_totals()

    # ----- game logic -----

    def deal(self, *args):
        if self.busy or self.in_round:
            return
        bet = self.current_bet()
        if not self.wallet.can_pay(bet):
            self.set_message("Не хватает фишек, уменьши ставку", SOFT_RED)
            self.shake(6)
            return

        self.bet = bet
        self.wallet.take(bet)
        self.top_bar.set_balance(self.wallet.balance)
        self.stop_breathing()
        self.show_bet_chips()
        Sfx.play("chip")
        for i in range(min(3, self.bet_stack.count)):
            self.fly_chip(
                self.bet_stack.source,
                self.balance_target(),
                self.bet_stack.chip_center(),
                i * 0.08,
                24,
            )
        self.deck = new_deck()
        self.player = []
        self.dealer = []
        self.player.append(self.deck.pop())
        self.dealer.append(self.deck.pop())
        self.player.append(self.deck.pop())
        self.dealer.append(self.deck.pop())
        self.dealer_hidden = True
        self.in_round = True
        self.set_busy(True)
        self.clear_table()
        self.set_message("Раздаём", WHITE, True)
        self.sync_cards(self.after_deal)

    def after_deal(self):
        if hand_value(self.player) == 21:
            self.reveal_dealer(self.natural_result)
            return
        self.set_message("Твой ход")
        self.show_play_controls()
        self.set_busy(False)

    def natural_result(self):
        if hand_value(self.dealer) == 21:
            self.finish_round("push", "Оба блэкджек, ничья")
        else:
            self.finish_round("blackjack", "Блэкджек!")

    def hit(self, *args):
        if self.busy or not self.in_round:
            return
        self.set_busy(True)
        self.player.append(self.deck.pop())
        self.sync_cards(self.after_hit)

    def after_hit(self):
        value = hand_value(self.player)
        if value > 21:
            self.reveal_dealer(self.bust_result)
        elif value == 21:
            self.start_dealer()
        else:
            self.set_busy(False)

    def bust_result(self):
        self.finish_round("bust", "Перебор")

    def stand(self, *args):
        if self.busy or not self.in_round:
            return
        self.set_busy(True)
        self.start_dealer()

    def start_dealer(self):
        self.set_message("Ходит дилер", WHITE, True)
        self.reveal_dealer(self.dealer_turn)

    def dealer_turn(self):
        """Dealer takes cards one at a time until 17 or more."""
        if hand_value(self.dealer) < 17:
            self.dealer.append(self.deck.pop())
            self.sync_cards(self.dealer_turn)
            return
        self.evaluate()

    def evaluate(self):
        player_value = hand_value(self.player)
        dealer_value = hand_value(self.dealer)
        if dealer_value > 21:
            self.finish_round("win", "У дилера перебор")
        elif player_value > dealer_value:
            self.finish_round("win", "Ты победил")
        elif player_value == dealer_value:
            self.finish_round("push", "Ничья")
        else:
            self.finish_round("lose", "Дилер выиграл")

    def finish_round(self, outcome, text):
        bet = self.bet
        payout = 0
        if outcome == "blackjack":
            payout = bet * 2 + bet // 2
        elif outcome == "win":
            payout = bet * 2
        elif outcome == "push":
            payout = bet

        if payout > 0:
            self.wallet.add(payout)

        net = payout - bet
        color = WHITE
        if net > 0:
            text = text + ": +" + str(net)
            color = GOLD
        elif net < 0:
            text = text + ": -" + str(bet)
            color = SOFT_RED

        if outcome == "win" or outcome == "blackjack":
            self.streak = self.streak + 1
        elif outcome == "lose" or outcome == "bust":
            self.streak = 0
        if net > 0 and self.streak >= 2:
            text = text + "\nСерия побед: " + str(self.streak)

        if self.wallet.refill_if_broke():
            color = WHITE
            text = "Фишки кончились, держи новые"
            self.streak = 0

        self.in_round = False
        self.set_message(text, color)
        if net > 0:
            pulse(self.message_label)
            float_text(self, "+" + str(net), GOLD, 0.45)
        self.play_outcome_fx(outcome, bet)

        self.refresh_totals()
        # when chips fly to the balance, the counter starts when they arrive
        self.show_idle_controls(payout == 0)
        if payout > 0:
            Clock.schedule_once(self.update_balance_later, 1.0)
        self.set_busy(False)

    def update_balance_later(self, dt):
        self.top_bar.set_balance(self.wallet.balance)

    # ----- round result effects -----

    def play_outcome_fx(self, outcome, bet):
        stack = self.bet_stack
        count = stack.count
        source = stack.source
        stack_pos = stack.chip_center()
        balance_pos = self.balance_target()
        shoe_pos = self.table_bg.shoe_center()

        if outcome == "win" or outcome == "blackjack":
            hold = 1.9
            big = outcome == "blackjack"
            if big:
                Sfx.play("blackjack")
            else:
                Sfx.play("win")
            for i in range(count):
                self.fly_chip(source, shoe_pos, stack_pos, 0.1 + i * 0.08)
            for i in range(count * 2):
                self.fly_chip(source, stack_pos, balance_pos, 0.8 + i * 0.07)
            Clock.schedule_once(self.clear_stack, 0.78)
            self.celebrate(self.player_views)
            for view in self.dealer_views:
                view.dim()
            center = self.player_row.center
            if big:
                self.burst(center[0], center[1], 24)
                self.coin_rain(36)
                self.show_banner("BLACKJACK!", GOLD, 62)
            else:
                self.burst(center[0], center[1], 12)
                self.coin_rain(16)
            self.flash((1, 0.85, 0.3), 0.16)
        elif outcome == "push":
            hold = 1.0
            Sfx.play("push")
            for i in range(count):
                self.fly_chip(source, stack_pos, balance_pos, 0.15 + i * 0.08)
            self.clear_stack()
            float_text(self, "Ничья", WHITE, 0.45, 36)
        else:
            hold = 0.9
            Sfx.play("lose")
            for i in range(count):
                self.fly_chip(source, stack_pos, shoe_pos, 0.1 + i * 0.08)
            self.clear_stack()
            for view in self.player_views:
                view.dim()
            float_text(self, "-" + str(bet), SOFT_RED, 0.45)
            if outcome == "bust":
                self.flash((0.9, 0.05, 0.05), 0.34)
                self.shake(12)
                self.show_banner("ПЕРЕБОР!", SOFT_RED, 54)
            else:
                self.flash((0.9, 0.1, 0.1), 0.16)
        Clock.schedule_once(self.restore_stack, hold)

    def celebrate(self, views):
        """The winning cards hop one after another."""
        for i, view in enumerate(views):
            Clock.schedule_once(partial(self.hop_card, view), i * 0.09)

    def hop_card(self, view, dt):
        view.hop(18)

    def clear_stack(self, *args):
        self.bet_stack.clear()

    def restore_stack(self, *args):
        if not self.in_round:
            self.show_bet_chips()
