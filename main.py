import os
from functools import partial

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.widget import Widget
from kivy.utils import platform

from blackjack import BlackjackScreen
from common import (
    BLUE,
    CHIP_IMAGE,
    FONT_SUITS,
    GOLD,
    GRAY,
    GREEN,
    RED,
    WHITE,
    GLabel,
    Page,
    RoundButton,
    Wallet,
    go_to,
)
from roulette import RouletteScreen
from slots import SlotsScreen

TITLE_LIGHT = (1, 0.95, 0.65, 1)


class MenuScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet

        root = Page(padding=30, spacing=14)
        root.add_widget(Widget(size_hint_y=0.05))

        suits = GLabel(
            text="♠  ♥  ♦  ♣",
            font_name=FONT_SUITS,
            font_size=30,
            color=(1, 1, 1, 0.55),
            size_hint_y=0.08,
        )
        root.add_widget(suits)

        self.title = GLabel(
            text="LUCKY\nCASINO",
            font_size=56,
            color=GOLD,
            halign="center",
            size_hint_y=0.27,
            outline_width=3,
            outline_color=(0.25, 0.12, 0, 1),
        )
        root.add_widget(self.title)

        balance_row = BoxLayout(spacing=8, size_hint_y=0.09)
        balance_row.add_widget(Widget())
        balance_row.add_widget(Image(source=CHIP_IMAGE, size_hint_x=None, width=40))
        self.balance_label = GLabel(font_size=26, size_hint_x=None, width=110)
        balance_row.add_widget(self.balance_label)
        balance_row.add_widget(Widget())
        root.add_widget(balance_row)

        self.menu_buttons = []
        self.add_menu_button(root, "Слоты", GREEN, self.open_slots)
        self.add_menu_button(root, "Блэкджек", BLUE, self.open_blackjack)
        self.add_menu_button(root, "Рулетка", RED, self.open_roulette)
        self.add_menu_button(root, "Выход", GRAY, self.exit_app)

        note = GLabel(
            text="Игра на виртуальные фишки, без реальных денег",
            font_size=14,
            color=(1, 1, 1, 0.55),
            size_hint_y=0.06,
        )
        root.add_widget(note)

        self.add_widget(root)

    def add_menu_button(self, root, text, color, handler):
        button = RoundButton(text=text, btn_color=color, size_hint_y=0.11)
        button.bind(on_release=handler)
        root.add_widget(button)
        self.menu_buttons.append(button)

    def on_pre_enter(self, *args):
        self.balance_label.text = str(self.wallet.balance)
        delay = 0.0
        for button in self.menu_buttons:
            Animation.cancel_all(button, "opacity")
            button.opacity = 0
            Clock.schedule_once(partial(self.fade_in, button), delay)
            delay = delay + 0.08

    def fade_in(self, button, dt):
        Animation(opacity=1, duration=0.3, t="out_quad").start(button)

    def on_enter(self, *args):
        self.start_title_shimmer()

    def on_leave(self, *args):
        Animation.cancel_all(self.title, "color")
        self.title.color = GOLD

    def start_title_shimmer(self):
        Animation.cancel_all(self.title, "color")
        anim = Animation(color=TITLE_LIGHT, duration=1.4, t="in_out_sine")
        anim += Animation(color=GOLD, duration=1.4, t="in_out_sine")
        anim.repeat = True
        anim.start(self.title)

    def open_slots(self, *args):
        go_to(self.manager, "slots", "left")

    def open_blackjack(self, *args):
        go_to(self.manager, "blackjack", "left")

    def open_roulette(self, *args):
        go_to(self.manager, "roulette", "left")

    def exit_app(self, *args):
        App.get_running_app().stop()


class CasinoApp(App):
    def build(self):
        self.title = "Lucky Casino"
        Window.clearcolor = (0.01, 0.09, 0.07, 1)
        if platform in ("win", "linux", "macosx"):
            Window.size = (400, 700)

        os.makedirs(self.user_data_dir, exist_ok=True)
        wallet = Wallet(os.path.join(self.user_data_dir, "save.json"))

        manager = ScreenManager(transition=SlideTransition(duration=0.25))
        manager.add_widget(MenuScreen(wallet, name="menu"))
        manager.add_widget(SlotsScreen(wallet, name="slots"))
        manager.add_widget(BlackjackScreen(wallet, name="blackjack"))
        manager.add_widget(RouletteScreen(wallet, name="roulette"))
        return manager


if __name__ == "__main__":
    CasinoApp().run()
