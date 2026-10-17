import os
from functools import partial

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.widget import Widget
from kivy.utils import platform

from blackjack import BlackjackScreen
from crash import CrashScreen
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
    Sfx,
    TopBar,
    Wallet,
    float_text,
    go_to,
    pulse,
)
from roulette import RouletteScreen
from slots import SlotsScreen

TITLE_LIGHT = (1, 0.95, 0.65, 1)


class StatsScreen(Screen):
    """Player stats screen showing games, winrate, records and VIP rank."""

    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet

        root = Page(padding=20, spacing=10)
        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        title = GLabel(text="СТАТИСТИКА", font_size=32, color=GOLD, size_hint_y=0.08)
        root.add_widget(title)

        self.rank_label = GLabel(text="", font_size=20, color=GOLD, size_hint_y=0.07)
        root.add_widget(self.rank_label)

        self.stats_grid = GridLayout(cols=2, spacing=8, size_hint_y=0.55)
        root.add_widget(self.stats_grid)

        root.add_widget(Widget(size_hint_y=0.04))
        back_btn = RoundButton(text="В МЕНЮ", btn_color=GRAY, size_hint_y=0.1)
        back_btn.bind(on_release=self.go_menu)
        root.add_widget(back_btn)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.refresh()

    def go_menu(self, *args):
        Sfx.play("click")
        go_to(self.manager, "menu", "right")

    def get_vip_rank(self, games):
        if games < 10:
            return "Новичок ★"
        if games < 50:
            return "Бронзовый игрок ★★"
        if games < 100:
            return "Серебряный игрок ★★★"
        if games < 250:
            return "Золотой VIP ★★★★"
        return "Хайроллер ЛЕГЕНДА ★★★★★"

    def refresh(self):
        stats = self.wallet.stats
        games = stats.get("games_played", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        biggest = stats.get("biggest_win", 0)
        won = stats.get("total_won", 0)
        lost = stats.get("total_lost", 0)
        win_rate = (wins / games * 100) if games > 0 else 0

        self.rank_label.text = f"Ранг: {self.get_vip_rank(games)}"

        self.stats_grid.clear_widgets()
        items = [
            ("Всего игр:", str(games)),
            ("Побед:", str(wins)),
            ("Поражений:", str(losses)),
            ("Винрейт:", f"{win_rate:.1f}%"),
            ("Рекордный занос:", f"+{biggest}"),
            ("Суммарный выигрыш:", f"+{won}"),
            ("Суммарный проигрыш:", f"-{lost}"),
            ("Текущий баланс:", str(self.wallet.balance)),
        ]
        for name, val in items:
            l1 = GLabel(text=name, font_size=16, color=WHITE, halign="left", valign="middle")
            l1.bind(size=self.update_text_size)
            l2 = GLabel(text=val, font_size=16, color=GOLD, halign="right", valign="middle")
            l2.bind(size=self.update_text_size)
            self.stats_grid.add_widget(l1)
            self.stats_grid.add_widget(l2)

    def update_text_size(self, widget, *args):
        widget.text_size = widget.size


class MenuScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.timer_event = None

        root = Page(padding=24, spacing=10)
        root.add_widget(Widget(size_hint_y=0.02))

        suits = GLabel(
            text="♠  ♥  ♦  ♣",
            font_name=FONT_SUITS,
            font_size=26,
            color=(1, 1, 1, 0.55),
            size_hint_y=0.05,
        )
        root.add_widget(suits)

        self.title = GLabel(
            text="LUCKY\nCASINO",
            font_size=50,
            color=GOLD,
            halign="center",
            size_hint_y=0.20,
            outline_width=3,
            outline_color=(0.25, 0.12, 0, 1),
        )
        root.add_widget(self.title)

        balance_row = BoxLayout(spacing=8, size_hint_y=0.08)
        balance_row.add_widget(Widget())
        balance_row.add_widget(Image(source=CHIP_IMAGE, size_hint_x=None, width=38))
        self.balance_label = GLabel(font_size=26, size_hint_x=None, width=120)
        balance_row.add_widget(self.balance_label)
        balance_row.add_widget(Widget())
        root.add_widget(balance_row)

        self.daily_button = RoundButton(
            text="ЕЖЕДНЕВНЫЙ БОНУС", btn_color=GOLD, size_hint_y=0.08
        )
        self.daily_button.font_size = 17
        self.daily_button.bind(on_release=self.claim_daily_bonus)
        root.add_widget(self.daily_button)

        self.menu_buttons = [self.daily_button]
        self.add_menu_button(root, "Слоты", GREEN, self.open_slots)
        self.add_menu_button(root, "Блэкджек", BLUE, self.open_blackjack)
        self.add_menu_button(root, "Рулетка", RED, self.open_roulette)
        self.add_menu_button(root, "Краш (Ракета)", GOLD, self.open_crash)
        self.add_menu_button(root, "Статистика", GRAY, self.open_stats)
        self.add_menu_button(root, "Выход", (0.2, 0.2, 0.25, 1), self.exit_app)

        note = GLabel(
            text="Игра на виртуальные фишки, без реальных денег",
            font_size=13,
            color=(1, 1, 1, 0.45),
            size_hint_y=0.04,
        )
        root.add_widget(note)

        self.add_widget(root)

    def add_menu_button(self, root, text, color, handler):
        button = RoundButton(text=text, btn_color=color, size_hint_y=0.08)
        button.font_size = 19
        button.bind(on_release=handler)
        root.add_widget(button)
        self.menu_buttons.append(button)

    def update_daily_button(self, *args):
        if self.wallet.can_claim_daily():
            self.daily_button.text = f"БОНУС: +{self.wallet.DAILY_BONUS_AMOUNT} ФИШЕК!"
            self.daily_button.btn_color = GOLD
            self.daily_button.disabled = False
        else:
            sec = self.wallet.seconds_until_daily()
            h = sec // 3600
            m = (sec % 3600) // 60
            s = sec % 60
            self.daily_button.text = f"Бонус через: {h:02d}:{m:02d}:{s:02d}"
            self.daily_button.btn_color = GRAY
            self.daily_button.disabled = True

    def claim_daily_bonus(self, *args):
        if self.wallet.claim_daily():
            Sfx.play("bonus")
            pulse(self.balance_label)
            float_text(self, f"+{self.wallet.DAILY_BONUS_AMOUNT}", GOLD, 0.5)
            self.balance_label.text = str(self.wallet.balance)
            self.update_daily_button()

    def on_pre_enter(self, *args):
        self.balance_label.text = str(self.wallet.balance)
        self.update_daily_button()
        if self.timer_event is None:
            self.timer_event = Clock.schedule_interval(self.update_daily_button, 1.0)
        delay = 0.0
        for button in self.menu_buttons:
            Animation.cancel_all(button, "opacity")
            button.opacity = 0
            Clock.schedule_once(partial(self.fade_in, button), delay)
            delay = delay + 0.05

    def fade_in(self, button, dt):
        Animation(opacity=1, duration=0.25, t="out_quad").start(button)

    def on_enter(self, *args):
        self.start_title_shimmer()

    def on_leave(self, *args):
        if self.timer_event is not None:
            self.timer_event.cancel()
            self.timer_event = None
        Animation.cancel_all(self.title, "color")
        self.title.color = GOLD

    def start_title_shimmer(self):
        Animation.cancel_all(self.title, "color")
        anim = Animation(color=TITLE_LIGHT, duration=1.4, t="in_out_sine")
        anim += Animation(color=GOLD, duration=1.4, t="in_out_sine")
        anim.repeat = True
        anim.start(self.title)

    def open_slots(self, *args):
        Sfx.play("click")
        go_to(self.manager, "slots", "left")

    def open_blackjack(self, *args):
        Sfx.play("click")
        go_to(self.manager, "blackjack", "left")

    def open_roulette(self, *args):
        Sfx.play("click")
        go_to(self.manager, "roulette", "left")

    def open_crash(self, *args):
        Sfx.play("click")
        go_to(self.manager, "crash", "left")

    def open_stats(self, *args):
        Sfx.play("click")
        go_to(self.manager, "stats", "left")

    def exit_app(self, *args):
        Sfx.play("click")
        App.get_running_app().stop()


class CasinoApp(App):
    def build(self):
        self.title = "Lucky Casino"
        Window.clearcolor = (0.01, 0.09, 0.07, 1)
        if platform in ("win", "linux", "macosx"):
            Window.size = (400, 700)

        os.makedirs(self.user_data_dir, exist_ok=True)
        wallet = Wallet(os.path.join(self.user_data_dir, "save.json"))

        self.wallet = wallet
        manager = ScreenManager(transition=SlideTransition(duration=0.25))
        manager.add_widget(MenuScreen(wallet, name="menu"))
        manager.add_widget(SlotsScreen(wallet, name="slots"))
        manager.add_widget(BlackjackScreen(wallet, name="blackjack"))
        manager.add_widget(RouletteScreen(wallet, name="roulette"))
        manager.add_widget(CrashScreen(wallet, name="crash"))
        manager.add_widget(StatsScreen(wallet, name="stats"))
        self.manager = manager
        Window.bind(on_keyboard=self.on_key)
        return manager

    def on_key(self, window, key, *args):
        """Android back button: go to the menu first, exit only from the menu."""
        if key == 27 and self.manager.current != "menu":
            go_to(self.manager, "menu", "right")
            return True
        return False

    def on_pause(self):
        # Android: without this the app is killed when the user switches away
        self.wallet.save()
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    CasinoApp().run()
