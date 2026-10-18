import os
from functools import partial

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
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
    SOFT_RED,
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

VIP_TIERS = [
    # (min_games, max_games, title, level_label, stars_count)
    (0, 10, "Новичок", "УРОВЕНЬ 1", 1),
    (10, 50, "Бронзовый игрок", "УРОВЕНЬ 2", 2),
    (50, 100, "Серебряный игрок", "УРОВЕНЬ 3", 3),
    (100, 250, "Золотой VIP", "УРОВЕНЬ 4", 4),
    (250, float("inf"), "Хайроллер ЛЕГЕНДА", "MAX УРОВЕНЬ", 5),
]


def format_chips(amount):
    """Format integer with thousands separator."""
    return f"{amount:,}".replace(",", " ")


def get_plural_rounds(n):
    """Correct Russian grammar for rounds."""
    n_abs = abs(n) % 100
    n10 = n_abs % 10
    if 11 <= n_abs <= 19:
        return f"{n} раундов"
    if n10 == 1:
        return f"{n} раунд"
    if 2 <= n10 <= 4:
        return f"{n} раунда"
    return f"{n} раундов"


class StatCard(BoxLayout):
    """Card container with subtle translucent plate and sleek border."""

    def __init__(
        self,
        bg_color=(0.04, 0.08, 0.12, 0.90),
        border_color=(1, 1, 1, 0.09),
        radius=14,
        **kwargs,
    ):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.radius = radius

        with self.canvas.before:
            self.c_bg = Color(*self.bg_color)
            self.rect_bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.radius]
            )
            self.c_border = Color(*self.border_color)
            self.rect_border = Line(
                rounded_rectangle=(
                    self.x + 0.5,
                    self.y + 0.5,
                    max(1, self.width - 1),
                    max(1, self.height - 1),
                    self.radius,
                ),
                width=1.1,
            )
        self.bind(pos=self._update_card, size=self._update_card)

    def _update_card(self, *args):
        self.rect_bg.pos = self.pos
        self.rect_bg.size = self.size
        self.rect_border.rounded_rectangle = (
            self.x + 0.5,
            self.y + 0.5,
            max(1, self.width - 1),
            max(1, self.height - 1),
            self.radius,
        )


class ProgressBarWidget(Widget):
    """Sleek horizontal progress bar with rounded corners."""

    progress = NumericProperty(0.0)

    def __init__(self, bar_color=GOLD, track_color=(0.02, 0.05, 0.08, 0.95), **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", 10)
        super().__init__(**kwargs)
        self.bar_color = bar_color
        self.track_color = track_color

        with self.canvas.before:
            Color(*self.track_color)
            self.track = RoundedRectangle(radius=[5])
            Color(*self.bar_color)
            self.fill = RoundedRectangle(radius=[5])

        self.bind(pos=self._update_bar, size=self._update_bar, progress=self._update_bar)

    def _update_bar(self, *args):
        self.track.pos = self.pos
        self.track.size = self.size
        fill_w = max(0.0, min(float(self.width), float(self.width) * float(self.progress)))
        if fill_w < 1:
            self.fill.size = (0, 0)
        else:
            self.fill.pos = self.pos
            self.fill.size = (fill_w, self.height)
            self.fill.radius = [min(5, fill_w / 2)]


class ResultRatioBar(Widget):
    """Tri-segmented horizontal bar showing wins (green), pushes (blue), and losses (red)."""

    win_ratio = NumericProperty(0.0)
    push_ratio = NumericProperty(0.0)
    loss_ratio = NumericProperty(0.0)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", 14)
        super().__init__(**kwargs)

        with self.canvas.before:
            # Base track (empty/neutral when 0 games)
            Color(0.10, 0.14, 0.18, 0.95)
            self.track = RoundedRectangle(radius=[7])
            # Loss rect (Red)
            Color(0.85, 0.22, 0.28, 1)
            self.loss_rect = RoundedRectangle(radius=[7])
            # Push rect (Blue)
            Color(0.22, 0.52, 0.92, 1)
            self.push_rect = RoundedRectangle(radius=[0])
            # Win rect (Green)
            Color(0.14, 0.75, 0.35, 1)
            self.win_rect = RoundedRectangle(radius=[7, 0, 0, 7])

        self.bind(
            pos=self._update_bar,
            size=self._update_bar,
            win_ratio=self._update_bar,
            push_ratio=self._update_bar,
            loss_ratio=self._update_bar,
        )

    def _update_bar(self, *args):
        w, h = self.width, self.height
        x, y = self.x, self.y
        self.track.pos = (x, y)
        self.track.size = (w, h)

        total = float(self.win_ratio + self.push_ratio + self.loss_ratio)
        if total <= 0.001 or w < 2:
            self.win_rect.size = (0, 0)
            self.push_rect.size = (0, 0)
            self.loss_rect.size = (0, 0)
            return

        w_win = max(0.0, min(float(w), float(w) * self.win_ratio))
        w_push = max(0.0, min(float(w - w_win), float(w) * self.push_ratio))
        w_loss = max(0.0, float(w - w_win - w_push)) if self.loss_ratio > 0 else 0.0

        # Win segment
        if w_win > 0:
            rad = [7] if (w_push <= 0 and w_loss <= 0) else [7, 0, 0, 7]
            self.win_rect.radius = rad
            self.win_rect.pos = (x, y)
            self.win_rect.size = (w_win, h)
        else:
            self.win_rect.size = (0, 0)

        # Push segment
        if w_push > 0:
            rad = (
                [7]
                if (w_win <= 0 and w_loss <= 0)
                else (
                    [7, 0, 0, 7]
                    if w_win <= 0
                    else ([0, 7, 7, 0] if w_loss <= 0 else [0])
                )
            )
            self.push_rect.radius = rad
            self.push_rect.pos = (x + w_win, y)
            self.push_rect.size = (w_push, h)
        else:
            self.push_rect.size = (0, 0)

        # Loss segment
        if w_loss > 0:
            rad = [7] if (w_win <= 0 and w_push <= 0) else [0, 7, 7, 0]
            self.loss_rect.radius = rad
            self.loss_rect.pos = (x + w_win + w_push, y)
            self.loss_rect.size = (w_loss, h)
        else:
            self.loss_rect.size = (0, 0)


class StatTile(BoxLayout):
    """Compact metric card for 2x2 dashboard."""

    def __init__(
        self,
        title,
        value="0",
        subtext="",
        value_color=GOLD,
        bg_color=(0.04, 0.08, 0.12, 0.92),
        border_color=(1, 1, 1, 0.08),
        icon_path=None,
        **kwargs,
    ):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", (10, 8))
        kwargs.setdefault("spacing", 2)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", 80)
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color

        with self.canvas.before:
            self.c_bg = Color(*self.bg_color)
            self.rect_bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
            self.c_border = Color(*self.border_color)
            self.rect_border = Line(
                rounded_rectangle=(
                    self.x + 0.5,
                    self.y + 0.5,
                    max(1, self.width - 1),
                    max(1, self.height - 1),
                    12,
                ),
                width=1.1,
            )
        self.bind(pos=self._update_tile, size=self._update_tile)

        # Title
        self.lbl_title = GLabel(
            text=title,
            font_size=dp(12),
            color=(0.72, 0.82, 0.92, 0.8),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(16),
        )
        self.lbl_title.bind(size=self._sync_text)
        self.add_widget(self.lbl_title)

        # Value row
        val_row = BoxLayout(
            orientation="horizontal", spacing=dp(5), size_hint_y=None, height=dp(30)
        )
        if icon_path:
            val_row.add_widget(Image(source=icon_path, size_hint_x=None, width=dp(22)))
        self.lbl_val = GLabel(
            text=value,
            font_size=dp(20),
            color=value_color,
            halign="left",
            valign="middle",
        )
        self.lbl_val.bind(size=self._sync_text)
        val_row.add_widget(self.lbl_val)
        self.add_widget(val_row)

        # Subtext
        self.lbl_sub = GLabel(
            text=subtext,
            font_size=dp(11),
            color=(1, 1, 1, 0.45),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(14),
        )
        self.lbl_sub.bind(size=self._sync_text)
        self.add_widget(self.lbl_sub)

    def _sync_text(self, instance, *args):
        instance.text_size = instance.size

    def _update_tile(self, *args):
        self.rect_bg.pos = self.pos
        self.rect_bg.size = self.size
        self.rect_border.rounded_rectangle = (
            self.x + 0.5,
            self.y + 0.5,
            max(1, self.width - 1),
            max(1, self.height - 1),
            12,
        )

    def set_value(self, text, color=None):
        self.lbl_val.text = text
        if color:
            self.lbl_val.color = color

    def set_subtext(self, text):
        self.lbl_sub.text = text


class StatRow(BoxLayout):
    """Single stat item row with alternating subtle stripe and formatted value."""

    def __init__(
        self,
        label_text,
        value_text,
        value_color=GOLD,
        is_alternate=False,
        **kwargs,
    ):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", 34)
        kwargs.setdefault("padding", (10, 0))
        super().__init__(**kwargs)

        if is_alternate:
            with self.canvas.before:
                Color(1, 1, 1, 0.03)
                self.bg = RoundedRectangle(radius=[6])
            self.bind(pos=self._update_bg, size=self._update_bg)

        self.lbl_name = GLabel(
            text=label_text,
            font_size=dp(14),
            color=(0.85, 0.88, 0.92, 0.88),
            halign="left",
            valign="middle",
            size_hint_x=0.55,
        )
        self.lbl_name.bind(size=self._sync_size)

        self.lbl_val = GLabel(
            text=value_text,
            font_size=dp(16),
            color=value_color,
            halign="right",
            valign="middle",
            size_hint_x=0.45,
        )
        self.lbl_val.bind(size=self._sync_size)

        self.add_widget(self.lbl_name)
        self.add_widget(self.lbl_val)

    def _sync_size(self, instance, *args):
        instance.text_size = instance.size

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def set_value(self, val_text, color=None):
        self.lbl_val.text = val_text
        if color:
            self.lbl_val.color = color


class ResetConfirmModal(ModalView):
    """Sleek modal dialog to confirm resetting stats."""

    def __init__(self, on_confirm, **kwargs):
        kwargs.setdefault("size_hint", (0.86, None))
        kwargs.setdefault("height", 210)
        kwargs.setdefault("auto_dismiss", True)
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0.72)
        self.on_confirm = on_confirm

        container = BoxLayout(
            orientation="vertical",
            padding=(dp(18), dp(16)),
            spacing=dp(10),
        )
        with container.canvas.before:
            Color(0.06, 0.10, 0.14, 0.98)
            self.rect_bg = RoundedRectangle(radius=[16])
            Color(0.85, 0.25, 0.3, 0.5)
            self.rect_border = Line(rounded_rectangle=(0, 0, 0, 0, 16), width=1.2)

        def update_plate(*args):
            self.rect_bg.pos = container.pos
            self.rect_bg.size = container.size
            self.rect_border.rounded_rectangle = (
                container.x + 0.5,
                container.y + 0.5,
                max(1, container.width - 1),
                max(1, container.height - 1),
                16,
            )

        container.bind(pos=update_plate, size=update_plate)

        # Title
        lbl_title = GLabel(
            text="СБРОС СТАТИСТИКИ",
            font_size=dp(20),
            color=SOFT_RED,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(26),
        )
        lbl_title.bind(size=lambda inst, *a: setattr(inst, "text_size", inst.size))
        container.add_widget(lbl_title)

        # Message
        lbl_msg = GLabel(
            text="Обнулить всю историю раундов и рекорды?\nБаланс ваших фишек не изменится.",
            font_size=dp(13),
            color=(0.85, 0.88, 0.92, 0.9),
            halign="center",
            valign="middle",
            size_hint_y=1,
        )
        lbl_msg.bind(size=lambda inst, *a: setattr(inst, "text_size", inst.size))
        container.add_widget(lbl_msg)

        # Buttons
        btn_box = BoxLayout(
            orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(44)
        )
        btn_cancel = RoundButton(text="ОТМЕНА", btn_color=GRAY, size_hint_x=0.5)
        btn_cancel.font_size = dp(17)
        btn_cancel.bind(on_release=self.dismiss)

        btn_yes = RoundButton(text="СБРОСИТЬ", btn_color=RED, size_hint_x=0.5)
        btn_yes.font_size = dp(17)

        def _do_reset(*args):
            self.dismiss()
            if self.on_confirm:
                self.on_confirm()

        btn_yes.bind(on_release=_do_reset)

        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_yes)
        container.add_widget(btn_box)

        self.add_widget(container)


class StatsScreen(Screen):
    """Enhanced player stats screen with VIP progression, metric tiles, and ratio visualizer."""

    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self._target_vip_progress = 0.0
        self._target_win_ratio = 0.0
        self._target_push_ratio = 0.0
        self._target_loss_ratio = 0.0

        root = Page(padding=(dp(14), dp(10), dp(14), dp(12)), spacing=dp(8))

        # 1. Top bar with back button & live balance counter
        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        # 2. Screen Header
        title = GLabel(
            text="СТАТИСТИКА ИГРОКА",
            font_size=dp(30),
            color=GOLD,
            size_hint_y=None,
            height=dp(36),
            halign="center",
            valign="middle",
        )
        title.bind(size=self._sync_text_size)
        root.add_widget(title)

        # 3. Scrollable content container
        scroll = ScrollView(
            do_scroll_x=False,
            bar_width=4,
            bar_color=(GOLD[0], GOLD[1], GOLD[2], 0.6),
            size_hint_y=1,
        )
        self.content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            padding=(0, 2, 0, 8),
        )
        self.content.bind(minimum_height=self.content.setter("height"))

        # --- A. VIP Status & Loyalty Card ---
        self.vip_card = StatCard(
            bg_color=(0.05, 0.13, 0.10, 0.95),
            border_color=(1, 0.82, 0.25, 0.45),
            height=dp(106),
            padding=(dp(14), dp(10)),
            spacing=dp(6),
        )
        vip_header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(26))
        self.vip_title = GLabel(
            text="Новичок",
            font_size=dp(18),
            color=GOLD,
            halign="left",
            valign="middle",
            size_hint_x=0.55,
        )
        self.vip_title.bind(size=self._sync_text_size)

        vip_badge_box = BoxLayout(
            orientation="horizontal",
            spacing=dp(4),
            size_hint_x=0.45,
        )
        self.vip_stars = GLabel(
            text="★",
            font_name=FONT_SUITS,
            font_size=dp(14),
            color=GOLD,
            halign="right",
            valign="middle",
            size_hint_x=0.55,
        )
        self.vip_stars.bind(size=self._sync_text_size)
        self.vip_lvl_badge = GLabel(
            text="УР. 1",
            font_size=dp(12),
            color=(0.85, 0.92, 0.88, 0.85),
            halign="right",
            valign="middle",
            size_hint_x=0.45,
        )
        self.vip_lvl_badge.bind(size=self._sync_text_size)
        vip_badge_box.add_widget(self.vip_stars)
        vip_badge_box.add_widget(self.vip_lvl_badge)

        vip_header.add_widget(self.vip_title)
        vip_header.add_widget(vip_badge_box)

        self.vip_progress_bar = ProgressBarWidget(bar_color=GOLD, height=dp(9))

        vip_sub_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(18))
        self.vip_percent = GLabel(
            text="0%",
            font_size=dp(12),
            color=(0.7, 0.85, 0.78, 0.85),
            halign="left",
            valign="middle",
            size_hint_x=0.3,
        )
        self.vip_percent.bind(size=self._sync_text_size)
        self.vip_subtext = GLabel(
            text="",
            font_size=dp(12),
            color=(1, 1, 1, 0.75),
            halign="right",
            valign="middle",
            size_hint_x=0.7,
        )
        self.vip_subtext.bind(size=self._sync_text_size)
        vip_sub_row.add_widget(self.vip_percent)
        vip_sub_row.add_widget(self.vip_subtext)

        self.vip_card.add_widget(vip_header)
        self.vip_card.add_widget(self.vip_progress_bar)
        self.vip_card.add_widget(vip_sub_row)
        self.content.add_widget(self.vip_card)

        # --- B. 2x2 Financial & Performance Grid ---
        self.kpi_grid = GridLayout(
            cols=2,
            spacing=dp(8),
            size_hint_y=None,
            height=dp(168),
        )

        self.tile_bank = StatTile(
            title="ТЕКУЩИЙ БАНК",
            value="0",
            subtext="Баланс кошелька",
            value_color=GOLD,
            icon_path=CHIP_IMAGE,
            bg_color=(0.04, 0.08, 0.14, 0.92),
            border_color=(0.2, 0.45, 0.85, 0.35),
        )
        self.tile_profit = StatTile(
            title="ЧИСТЫЙ ПРОФИТ",
            value="0",
            subtext="Прибыль за все игры",
            value_color=WHITE,
            bg_color=(0.04, 0.10, 0.08, 0.92),
            border_color=(0.14, 0.65, 0.35, 0.35),
        )
        self.tile_biggest = StatTile(
            title="РЕКОРДНЫЙ КУШ",
            value="+0",
            subtext="Макс. занос за раунд",
            value_color=GOLD,
            bg_color=(0.08, 0.07, 0.04, 0.92),
            border_color=(1, 0.82, 0.25, 0.35),
        )
        self.tile_winrate = StatTile(
            title="ПРОЦЕНТ ПОБЕД",
            value="0.0%",
            subtext="Доля выигрышей",
            value_color=GOLD,
            bg_color=(0.07, 0.05, 0.11, 0.92),
            border_color=(0.6, 0.35, 0.9, 0.35),
        )

        self.kpi_grid.add_widget(self.tile_bank)
        self.kpi_grid.add_widget(self.tile_profit)
        self.kpi_grid.add_widget(self.tile_biggest)
        self.kpi_grid.add_widget(self.tile_winrate)
        self.content.add_widget(self.kpi_grid)

        # --- C. Distribution / Ratio Visualizer Card ---
        self.ratio_card = StatCard(
            bg_color=(0.04, 0.07, 0.11, 0.92),
            border_color=(1, 1, 1, 0.08),
            height=dp(96),
            padding=(dp(12), dp(8)),
            spacing=dp(6),
        )
        lbl_ratio_title = GLabel(
            text="СООТНОШЕНИЕ РЕЗУЛЬТАТОВ",
            font_size=dp(13),
            color=(0.75, 0.85, 0.95, 0.8),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(18),
        )
        lbl_ratio_title.bind(size=self._sync_text_size)
        self.ratio_card.add_widget(lbl_ratio_title)

        self.ratio_bar = ResultRatioBar(height=dp(12))
        self.ratio_card.add_widget(self.ratio_bar)

        badges_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(20))
        self.badge_wins = GLabel(
            text="Побед: 0",
            font_size=dp(13),
            color=(0.25, 0.88, 0.45, 1),
            halign="left",
            valign="middle",
            size_hint_x=0.35,
        )
        self.badge_wins.bind(size=self._sync_text_size)
        self.badge_pushes = GLabel(
            text="",
            font_size=dp(13),
            color=(0.4, 0.7, 1, 1),
            halign="center",
            valign="middle",
            size_hint_x=0.3,
        )
        self.badge_pushes.bind(size=self._sync_text_size)
        self.badge_losses = GLabel(
            text="Поражений: 0",
            font_size=dp(13),
            color=SOFT_RED,
            halign="right",
            valign="middle",
            size_hint_x=0.35,
        )
        self.badge_losses.bind(size=self._sync_text_size)

        badges_row.add_widget(self.badge_wins)
        badges_row.add_widget(self.badge_pushes)
        badges_row.add_widget(self.badge_losses)
        self.ratio_card.add_widget(badges_row)
        self.content.add_widget(self.ratio_card)

        # --- D. Detailed Records Card ---
        self.records_card = StatCard(
            bg_color=(0.04, 0.07, 0.11, 0.92),
            border_color=(1, 1, 1, 0.08),
            height=dp(204),
            padding=(dp(10), dp(8)),
            spacing=dp(2),
        )
        lbl_rec_title = GLabel(
            text="ДЕТАЛЬНАЯ СТАТИСТИКА",
            font_size=dp(13),
            color=(1, 0.82, 0.25, 0.85),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(22),
            padding=(dp(4), dp(0)),
        )
        lbl_rec_title.bind(size=self._sync_text_size)
        self.records_card.add_widget(lbl_rec_title)

        self.row_games = StatRow("Всего раундов", "0", WHITE, is_alternate=True)
        self.row_wins = StatRow("Победных раундов", "0", GREEN, is_alternate=False)
        self.row_losses = StatRow("Поражений", "0", SOFT_RED, is_alternate=True)
        self.row_won = StatRow("Суммарный выигрыш", "+0", GREEN, is_alternate=False)
        self.row_lost = StatRow("Суммарный проигрыш", "-0", SOFT_RED, is_alternate=True)

        self.records_card.add_widget(self.row_games)
        self.records_card.add_widget(self.row_wins)
        self.records_card.add_widget(self.row_losses)
        self.records_card.add_widget(self.row_won)
        self.records_card.add_widget(self.row_lost)
        self.content.add_widget(self.records_card)

        # --- E. Actions Row (Reset Stats + Back) ---
        actions_row = BoxLayout(
            orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(48)
        )
        self.btn_reset = RoundButton(
            text="СБРОС СТАТИСТИКИ",
            btn_color=(0.35, 0.12, 0.15, 1),
            size_hint_x=0.52,
        )
        self.btn_reset.font_size = dp(15)
        self.btn_reset.bind(on_release=self.confirm_reset)

        back_btn = RoundButton(
            text="В МЕНЮ", btn_color=GRAY, size_hint_x=0.48
        )
        back_btn.font_size = dp(18)
        back_btn.bind(on_release=self.go_menu)

        actions_row.add_widget(self.btn_reset)
        actions_row.add_widget(back_btn)
        self.content.add_widget(actions_row)

        scroll.add_widget(self.content)
        root.add_widget(scroll)

        self.add_widget(root)

    def _sync_text_size(self, instance, *args):
        instance.text_size = instance.size

    def on_pre_enter(self, *args):
        self.refresh()

    def on_enter(self, *args):
        # Smoothly animate the progress bars on screen display
        self.vip_progress_bar.progress = 0.0
        Animation.cancel_all(self.vip_progress_bar, "progress")
        Animation(
            progress=self._target_vip_progress, duration=0.45, t="out_quad"
        ).start(self.vip_progress_bar)

        self.ratio_bar.win_ratio = 0.0
        self.ratio_bar.push_ratio = 0.0
        self.ratio_bar.loss_ratio = 0.0
        Animation.cancel_all(
            self.ratio_bar, "win_ratio", "push_ratio", "loss_ratio"
        )
        Animation(
            win_ratio=self._target_win_ratio,
            push_ratio=self._target_push_ratio,
            loss_ratio=self._target_loss_ratio,
            duration=0.45,
            t="out_quad",
        ).start(self.ratio_bar)

    def go_menu(self, *args):
        Sfx.play("click")
        go_to(self.manager, "menu", "right")

    def confirm_reset(self, *args):
        Sfx.play("click")
        ResetConfirmModal(on_confirm=self.do_reset).open()

    def do_reset(self):
        self.wallet.reset_stats()
        Sfx.play("bonus")
        self.refresh()
        self.on_enter()

    def get_vip_info(self, games):
        for idx, (min_g, max_g, title, lvl, stars) in enumerate(VIP_TIERS):
            if games < max_g:
                progress = (
                    (games - min_g) / (max_g - min_g) if max_g != float("inf") else 1.0
                )
                remaining = max_g - games
                next_title = VIP_TIERS[idx + 1][2] if idx + 1 < len(VIP_TIERS) else None
                return {
                    "title": title,
                    "level": lvl,
                    "stars": "★" * stars,
                    "progress": max(0.0, min(1.0, progress)),
                    "remaining": remaining,
                    "next_title": next_title,
                    "is_max": False,
                }
        return {
            "title": VIP_TIERS[-1][2],
            "level": VIP_TIERS[-1][3],
            "stars": "★" * VIP_TIERS[-1][4],
            "progress": 1.0,
            "remaining": 0,
            "next_title": None,
            "is_max": True,
        }

    def refresh(self):
        stats = self.wallet.stats
        games = stats.get("games_played", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        pushes = max(0, games - wins - losses)
        biggest = stats.get("biggest_win", 0)
        won = stats.get("total_won", 0)
        lost = stats.get("total_lost", 0)
        win_rate = (wins / games * 100) if games > 0 else 0.0
        profit = won - lost

        # 1. Update TopBar
        self.top_bar.set_balance(self.wallet.balance)

        # 2. Update VIP Card
        vip = self.get_vip_info(games)
        self.vip_title.text = vip["title"]
        self.vip_lvl_badge.text = vip["level"]
        self.vip_stars.text = vip["stars"]
        self._target_vip_progress = vip["progress"]
        self.vip_progress_bar.progress = vip["progress"]
        self.vip_percent.text = f"{int(vip['progress'] * 100)}%"

        if vip["is_max"]:
            self.vip_subtext.text = "Максимальный VIP ранг достигнут!"
        else:
            self.vip_subtext.text = (
                f"Ещё {get_plural_rounds(vip['remaining'])} до «{vip['next_title']}»"
            )

        # 3. Update 2x2 KPI Tiles
        self.tile_bank.set_value(format_chips(self.wallet.balance), GOLD)

        if profit > 0:
            self.tile_profit.set_value(f"+{format_chips(profit)}", GREEN)
            self.tile_profit.set_subtext("Общий профит: в плюсе")
        elif profit < 0:
            self.tile_profit.set_value(f"-{format_chips(abs(profit))}", SOFT_RED)
            self.tile_profit.set_subtext("Общий профит: в минусе")
        else:
            self.tile_profit.set_value("0", WHITE)
            self.tile_profit.set_subtext("Общий профит: в нуле")

        self.tile_biggest.set_value(f"+{format_chips(biggest)}", GOLD)

        if win_rate >= 50.0:
            self.tile_winrate.set_value(f"{win_rate:.1f}%", GREEN)
        elif win_rate >= 35.0:
            self.tile_winrate.set_value(f"{win_rate:.1f}%", GOLD)
        else:
            self.tile_winrate.set_value(
                f"{win_rate:.1f}%", SOFT_RED if games > 0 else WHITE
            )
        self.tile_winrate.set_subtext(f"{wins} побед из {games}")

        # 4. Update Ratio Visualizer Bar
        if games > 0:
            w_ratio = wins / games
            p_ratio = pushes / games
            l_ratio = losses / games
            self._target_win_ratio = w_ratio
            self._target_push_ratio = p_ratio
            self._target_loss_ratio = l_ratio
            self.ratio_bar.win_ratio = w_ratio
            self.ratio_bar.push_ratio = p_ratio
            self.ratio_bar.loss_ratio = l_ratio

            self.badge_wins.text = f"Побед: {wins} ({w_ratio*100:.0f}%)"
            if pushes > 0:
                self.badge_pushes.text = f"Ничьих: {pushes} ({p_ratio*100:.0f}%)"
            else:
                self.badge_pushes.text = ""
            self.badge_losses.text = f"Поражений: {losses} ({l_ratio*100:.0f}%)"
        else:
            self._target_win_ratio = 0.0
            self._target_push_ratio = 0.0
            self._target_loss_ratio = 0.0
            self.ratio_bar.win_ratio = 0.0
            self.ratio_bar.push_ratio = 0.0
            self.ratio_bar.loss_ratio = 0.0
            self.badge_wins.text = "Побед: 0"
            self.badge_pushes.text = ""
            self.badge_losses.text = "Поражений: 0"

        # 5. Update Detailed Records
        self.row_games.set_value(str(games), WHITE)
        self.row_wins.set_value(str(wins), GREEN)
        self.row_losses.set_value(str(losses), SOFT_RED)
        self.row_won.set_value(f"+{format_chips(won)}", GREEN)
        self.row_lost.set_value(f"-{format_chips(lost)}", SOFT_RED)


class MenuScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.timer_event = None

        root = Page(padding=dp(20), spacing=dp(9))
        root.add_widget(Widget(size_hint_y=0.005))

        suits = GLabel(
            text="♠  ♥  ♦  ♣",
            font_name=FONT_SUITS,
            font_size=dp(34),
            color=(1, 1, 1, 0.55),
            size_hint_y=0.045,
        )
        root.add_widget(suits)

        self.title = GLabel(
            text="LUCKY\nCASINO",
            font_size=dp(64),
            color=GOLD,
            halign="center",
            size_hint_y=0.16,
            outline_width=3,
            outline_color=(0.25, 0.12, 0, 1),
        )
        root.add_widget(self.title)

        balance_row = BoxLayout(spacing=dp(8), size_hint_y=0.065)
        balance_row.add_widget(Widget())
        balance_row.add_widget(Image(source=CHIP_IMAGE, size_hint_x=None, width=dp(52)))
        self.balance_label = GLabel(font_size=dp(36), size_hint_x=None, width=dp(160))
        balance_row.add_widget(self.balance_label)
        balance_row.add_widget(Widget())
        root.add_widget(balance_row)

        self.daily_button = RoundButton(
            text="ЕЖЕДНЕВНЫЙ БОНУС", btn_color=GOLD, size_hint_y=0.08
        )
        self.daily_button.font_size = dp(24)
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
            font_size=dp(17),
            color=(1, 1, 1, 0.45),
            size_hint_y=0.04,
        )
        root.add_widget(note)

        self.add_widget(root)

    def add_menu_button(self, root, text, color, handler):
        button = RoundButton(text=text, btn_color=color, size_hint_y=0.076)
        button.font_size = dp(28)
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
