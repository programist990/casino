from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import (
    Color,
    Ellipse,
    InstructionGroup,
    Line,
    Rectangle,
    RoundedRectangle,
    Triangle,
)
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

import city_data as rules
from common import (
    FONT_SUITS,
    GOLD,
    GRAY,
    GREEN,
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

DIM = (1, 1, 1, 0.3)
TEXT = (0.85, 0.88, 0.92, 0.95)


def fmt(amount):
    return f"{int(amount):,}".replace(",", " ")


def shade(color, factor):
    return (color[0] * factor, color[1] * factor, color[2] * factor, 1)


def fit_label(label):
    """Makes a label wrap/shorten inside its own box."""
    label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    return label


class Tappable:
    """Mixin: a widget that reacts to a tap by calling self.callback(self)."""

    callback = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self.collide_point(*touch.pos) and self.callback:
                self.callback(self)
            return True
        return super().on_touch_up(touch)


# ----- one plot of land -----


class PlotTile(Tappable, FloatLayout):
    """A square of land: empty (dashed outline) or with a building drawn in code."""

    def __init__(self, index, **kwargs):
        super().__init__(**kwargs)
        self.index = index
        self.plot = None

        with self.canvas.before:
            Color(0.02, 0.07, 0.06, 0.75)
            self.bg = RoundedRectangle(radius=[12])
        self.art = InstructionGroup()
        self.canvas.add(self.art)

        self.plus = GLabel(
            text="+",
            font_size=dp(34),
            color=DIM,
            pos_hint={"center_x": 0.5, "center_y": 0.58},
            size_hint=(1, 0.4),
        )
        self.add_widget(self.plus)

        self.name_label = fit_label(
            GLabel(
                font_size=dp(13),
                halign="center",
                valign="middle",
                shorten=True,
                pos_hint={"x": 0, "y": 0.02},
                size_hint=(1, 0.24),
            )
        )
        self.add_widget(self.name_label)

        self.level_label = fit_label(
            GLabel(
                font_size=dp(13),
                color=GOLD,
                halign="right",
                valign="middle",
                pos_hint={"right": 0.96, "top": 0.99},
                size_hint=(0.6, 0.2),
            )
        )
        self.add_widget(self.level_label)

        self.bind(pos=self.redraw, size=self.redraw)

    def set_plot(self, plot):
        self.plot = plot
        if plot is None:
            self.plus.opacity = 1
            self.name_label.text = "Свободно"
            self.name_label.color = DIM
            self.level_label.text = ""
        else:
            self.plus.opacity = 0
            self.name_label.text = rules.BUILDINGS[plot["type"]]["name"]
            self.name_label.color = WHITE
            self.level_label.text = f"Ур. {plot['level']}"
        self.redraw()

    def redraw(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.art.clear()
        x, y = self.pos
        w, h = self.size
        if w < 10 or h < 10:
            return

        if self.plot is None:
            self.art.add(Color(1, 1, 1, 0.22))
            self.art.add(
                Line(
                    rounded_rectangle=(x + 2, y + 2, w - 4, h - 4, 12),
                    width=1.2,
                    dash_length=6,
                    dash_offset=5,
                )
            )
            return

        spec = rules.BUILDINGS[self.plot["type"]]
        level = self.plot["level"]
        color = spec["color"]
        dark = shade(color, 0.5)

        art_h = h * 0.7
        ground = y + h * 0.27
        body_w = w * spec["width"] * 0.8
        body_h = min(art_h * 0.72, art_h * (spec["height"] + 0.09 * (level - 1)))
        body_x = x + (w - body_w) / 2
        roof_h = art_h * 0.2
        top = ground + body_h

        # ground shadow
        self.art.add(Color(0, 0, 0, 0.35))
        self.art.add(Rectangle(pos=(x + w * 0.08, ground - dp(3)), size=(w * 0.84, dp(3))))

        # a dome sits behind the body, so it is drawn first
        if spec["shape"] == "dome":
            self.art.add(Color(*color))
            self.art.add(
                Ellipse(
                    pos=(body_x + body_w * 0.12, top - roof_h * 0.8),
                    size=(body_w * 0.76, roof_h * 2.0),
                )
            )

        # body with a neon strip on top
        self.art.add(Color(*dark))
        self.art.add(Rectangle(pos=(body_x, ground), size=(body_w, body_h)))
        self.art.add(Color(*color))
        self.art.add(Rectangle(pos=(body_x, top - dp(4)), size=(body_w, dp(4))))

        # windows: some are lit, some are dark
        cols = max(2, int(body_w // dp(16)))
        rows = max(1, int((body_h - dp(8)) // dp(14)))
        cell_w = body_w / cols
        cell_h = (body_h - dp(8)) / rows
        win_w = cell_w * 0.5
        win_h = cell_h * 0.5
        for row in range(rows):
            for col in range(cols):
                lit = (row * 3 + col * 2 + level) % 3 != 0
                self.art.add(Color(1, 0.9, 0.5, 0.9) if lit else Color(0, 0, 0, 0.35))
                self.art.add(
                    Rectangle(
                        pos=(
                            body_x + col * cell_w + (cell_w - win_w) / 2,
                            ground + dp(2) + row * cell_h + (cell_h - win_h) / 2,
                        ),
                        size=(win_w, win_h),
                    )
                )

        # roof
        self.art.add(Color(*color))
        if spec["shape"] == "peak":
            self.art.add(
                Triangle(
                    points=[
                        body_x - dp(2), top,
                        body_x + body_w + dp(2), top,
                        body_x + body_w / 2, top + roof_h,
                    ]
                )
            )
        elif spec["shape"] == "spire":
            tower_x = body_x + body_w * 0.25
            tower_w = body_w * 0.5
            self.art.add(Color(*dark))
            self.art.add(Rectangle(pos=(tower_x, top), size=(tower_w, roof_h * 0.5)))
            self.art.add(Color(*color))
            self.art.add(
                Triangle(
                    points=[
                        tower_x, top + roof_h * 0.5,
                        tower_x + tower_w, top + roof_h * 0.5,
                        tower_x + tower_w / 2, top + roof_h * 1.2,
                    ]
                )
            )
        elif spec["shape"] == "flat":
            self.art.add(
                Rectangle(pos=(body_x + body_w * 0.3, top), size=(body_w * 0.4, dp(5)))
            )

        # the maximum level gets a golden frame
        if level >= rules.MAX_LEVEL:
            self.art.add(Color(*GOLD[:3], 0.85))
            self.art.add(Line(rounded_rectangle=(x + 1, y + 1, w - 2, h - 2, 12), width=1.5))


# ----- landmark strip -----


class LandmarkStrip(Tappable, BoxLayout):
    """Row of landmark icons: golden when built, dim when not. Tap opens the list."""

    def __init__(self, **kwargs):
        kwargs.setdefault("spacing", dp(6))
        kwargs.setdefault("padding", (dp(8), dp(4)))
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.3)
            self.plate = RoundedRectangle(radius=[14])
        self.bind(pos=self.update_plate, size=self.update_plate)

        self.icons = []
        for item in rules.LANDMARKS:
            icon = GLabel(text=item["symbol"], font_name=FONT_SUITS, font_size=dp(28))
            self.icons.append(icon)
            self.add_widget(icon)

    def update_plate(self, *args):
        self.plate.pos = self.pos
        self.plate.size = self.size

    def refresh(self, city):
        for item, icon in zip(rules.LANDMARKS, self.icons):
            icon.color = GOLD if item["id"] in city["landmarks"] else DIM


# ----- dialogs -----


class Dialog(ModalView):
    """Dark card with a title, a scrollable list of rows and a close button."""

    def __init__(self, title, height, **kwargs):
        kwargs.setdefault("size_hint", (0.92, None))
        super().__init__(**kwargs)
        self.height = min(height, Window.height * 0.9)
        self.auto_dismiss = True
        self.background_color = (0, 0, 0, 0.72)

        container = BoxLayout(
            orientation="vertical", padding=(dp(14), dp(12)), spacing=dp(8)
        )
        with container.canvas.before:
            Color(0.06, 0.10, 0.14, 0.98)
            plate = RoundedRectangle(radius=[16])
            Color(1, 0.82, 0.25, 0.5)
            border = Line(rounded_rectangle=(0, 0, 0, 0, 16), width=1.2)

        def update_plate(*args):
            plate.pos = container.pos
            plate.size = container.size
            border.rounded_rectangle = (
                container.x + 0.5,
                container.y + 0.5,
                max(1, container.width - 1),
                max(1, container.height - 1),
                16,
            )

        container.bind(pos=update_plate, size=update_plate)

        container.add_widget(
            fit_label(
                GLabel(
                    text=title,
                    font_size=dp(21),
                    color=GOLD,
                    halign="center",
                    valign="middle",
                    size_hint_y=None,
                    height=dp(30),
                )
            )
        )

        self.rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        scroll.add_widget(self.rows)
        container.add_widget(scroll)

        close = RoundButton(
            text="ЗАКРЫТЬ", btn_color=GRAY, size_hint_y=None, height=dp(46)
        )
        close.font_size = dp(18)
        close.bind(on_release=self.dismiss)
        container.add_widget(close)

        self.add_widget(container)

    def add_text(self, text, color=TEXT, height=26, size=15):
        label = fit_label(
            GLabel(
                text=text,
                font_size=dp(size),
                color=color,
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(height),
            )
        )
        self.rows.add_widget(label)

    def add_row(
        self,
        title,
        subtitle,
        button_text,
        button_color,
        on_press,
        disabled=False,
        title_color=WHITE,
        symbol=None,
        symbol_color=GOLD,
    ):
        row = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
        if symbol:
            row.add_widget(
                GLabel(
                    text=symbol,
                    font_name=FONT_SUITS,
                    font_size=dp(28),
                    color=symbol_color,
                    size_hint_x=None,
                    width=dp(36),
                )
            )
        texts = BoxLayout(orientation="vertical")
        texts.add_widget(
            fit_label(
                GLabel(
                    text=title,
                    font_size=dp(17),
                    color=title_color,
                    halign="left",
                    valign="middle",
                    shorten=True,
                )
            )
        )
        texts.add_widget(
            fit_label(
                GLabel(
                    text=subtitle,
                    font_size=dp(12),
                    color=TEXT,
                    halign="left",
                    valign="middle",
                    shorten=True,
                )
            )
        )
        row.add_widget(texts)
        button = RoundButton(
            text=button_text,
            btn_color=button_color,
            size_hint_x=None,
            width=dp(118),
            disabled=disabled,
        )
        button.font_size = dp(17)
        button.bind(on_release=on_press)
        row.add_widget(button)
        self.rows.add_widget(row)


# ----- the screen -----


class CityScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.tick_event = None

        root = Page(padding=dp(16), spacing=dp(8))

        self.top_bar = TopBar(self.go_menu)
        root.add_widget(self.top_bar)

        root.add_widget(GLabel(text="ГОРОД", font_size=dp(36), color=GOLD, size_hint_y=0.07))

        self.info_label = fit_label(
            GLabel(
                font_size=dp(16),
                color=TEXT,
                halign="center",
                valign="middle",
                size_hint_y=0.05,
            )
        )
        root.add_widget(self.info_label)

        grid = GridLayout(cols=3, rows=4, spacing=dp(8), size_hint_y=0.48)
        self.tiles = []
        for index in range(rules.PLOT_COUNT):
            tile = PlotTile(index)
            tile.callback = self.on_tile
            self.tiles.append(tile)
            grid.add_widget(tile)
        root.add_widget(grid)

        self.strip = LandmarkStrip(size_hint_y=0.075)
        self.strip.callback = self.open_landmarks
        root.add_widget(self.strip)

        self.message_label = MessageLabel(size_hint_y=0.1)
        root.add_widget(self.message_label)

        self.collect_button = RoundButton(
            text="СОБРАТЬ", btn_color=GREEN, size_hint_y=0.11
        )
        self.collect_button.font_size = dp(26)
        self.collect_button.bind(on_release=self.collect)
        root.add_widget(self.collect_button)

        self.add_widget(root)

    # --- showing the state ---

    def on_pre_enter(self, *args):
        self.say("Нажми на участок, чтобы строить. Значки внизу: достопримечательности", WHITE)
        self.refresh()

    def on_enter(self, *args):
        if self.tick_event is None:
            self.tick_event = Clock.schedule_interval(self.tick, 1.0)

    def on_leave(self, *args):
        if self.tick_event is not None:
            self.tick_event.cancel()
            self.tick_event = None

    def go_menu(self, *args):
        Sfx.play("click")
        go_to(self.manager, "menu", "right")

    def say(self, text, color=WHITE):
        self.message_label.color = color
        self.message_label.text = text

    def refresh(self):
        city = self.wallet.city
        self.top_bar.set_balance(self.wallet.balance)
        for tile, plot in zip(self.tiles, city["plots"]):
            tile.set_plot(plot)
        self.strip.refresh(city)

        text = f"{rules.rank_name(city)} · доход {fmt(rules.income_per_hour(city))}/ч"
        if city["landmarks"]:
            text += f" (+{int(len(city['landmarks']) * rules.LANDMARK_BONUS * 100)}%)"
        self.info_label.text = text
        self.tick()

    def tick(self, *args):
        city = self.wallet.city
        rate = rules.income_per_hour(city)
        waiting = int(rules.pending(city))
        if rate <= 0:
            self.collect_button.text = "ПОСТРОЙ ПЕРВОЕ ЗДАНИЕ"
            self.collect_button.btn_color = GRAY
            self.collect_button.disabled = True
        elif waiting < 1:
            self.collect_button.text = "Копится доход..."
            self.collect_button.btn_color = GRAY
            self.collect_button.disabled = True
        else:
            full = waiting >= int(rules.capacity(city))
            self.collect_button.text = f"СОБРАТЬ +{fmt(waiting)}" + ("  (ПОЛНО)" if full else "")
            self.collect_button.btn_color = GREEN
            self.collect_button.disabled = False

    # --- actions ---

    def collect(self, *args):
        amount = rules.collect(self.wallet)
        if amount > 0:
            Sfx.play("bonus")
            float_text(self, f"+{fmt(amount)}", GOLD, 0.5)
            self.say(f"Собрано {fmt(amount)} фишек", GOLD)
        else:
            self.say("Пока нечего собирать", WHITE)
        self.refresh()

    def not_enough(self, cost):
        Sfx.play("click")
        missing = cost + rules.CITY_RESERVE - self.wallet.balance
        self.say(
            f"Не хватает {fmt(missing)} фишек. {fmt(rules.CITY_RESERVE)} всегда остаётся для игры",
            SOFT_RED,
        )
        pulse(self.message_label)

    def finish(self, text, cost, sound="chip"):
        Sfx.play(sound)
        float_text(self, f"-{fmt(cost)}", SOFT_RED, 0.5, 34)
        self.say(text, GOLD)
        self.refresh()

    def on_tile(self, tile):
        Sfx.play("click")
        if tile.plot is None:
            self.open_build(tile.index)
        else:
            self.open_upgrade(tile.index)

    def open_build(self, index):
        dialog = Dialog(f"УЧАСТОК {index + 1}", dp(470))
        dialog.add_text("Выбери, что построить", height=22, size=14)
        mult = rules.income_multiplier(self.wallet.city)
        for type_id in rules.BUILDING_ORDER:
            spec = rules.BUILDINGS[type_id]
            cost = rules.upgrade_cost(type_id, 0)
            affordable = rules.can_afford(self.wallet.balance, cost)
            dialog.add_row(
                spec["name"],
                f"+{fmt(spec['income'] * mult)} фишек в час",
                fmt(cost),
                GREEN if affordable else GRAY,
                lambda *a, i=index, t=type_id, d=dialog: self.do_build(d, i, t),
                title_color=spec["color"][:3] + (1,),
            )
        dialog.open()

    def do_build(self, dialog, index, type_id):
        dialog.dismiss()
        cost = rules.upgrade_cost(type_id, 0)
        result = rules.buy_building(self.wallet, index, type_id)
        if result == "ok":
            self.finish(f"Построено: {rules.BUILDINGS[type_id]['name']}!", cost)
        elif result == "reserve":
            self.not_enough(cost)

    def open_upgrade(self, index):
        plot = self.wallet.city["plots"][index]
        spec = rules.BUILDINGS[plot["type"]]
        level = plot["level"]
        mult = rules.income_multiplier(self.wallet.city)

        dialog = Dialog(spec["name"].upper(), dp(300))
        dialog.add_text(f"Уровень {level} из {rules.MAX_LEVEL}", height=26, size=17)
        dialog.add_text(
            f"Доход сейчас: {fmt(rules.building_income(plot['type'], level) * mult)} в час"
        )
        if level >= rules.MAX_LEVEL:
            dialog.add_text("Максимальный уровень!", GOLD, height=30, size=17)
        else:
            cost = rules.upgrade_cost(plot["type"], level)
            next_income = rules.building_income(plot["type"], level + 1) * mult
            dialog.add_text(f"После улучшения: {fmt(next_income)} в час")
            affordable = rules.can_afford(self.wallet.balance, cost)
            dialog.add_row(
                f"Уровень {level + 1}",
                "улучшить здание",
                fmt(cost),
                GREEN if affordable else GRAY,
                lambda *a, i=index, d=dialog: self.do_upgrade(d, i),
            )
        dialog.open()

    def do_upgrade(self, dialog, index):
        dialog.dismiss()
        plot = self.wallet.city["plots"][index]
        cost = rules.upgrade_cost(plot["type"], plot["level"])
        name = rules.BUILDINGS[plot["type"]]["name"]
        result = rules.upgrade_building(self.wallet, index)
        if result == "ok":
            level = self.wallet.city["plots"][index]["level"]
            self.finish(f"{name}: уровень {level}!", cost)
        elif result == "reserve":
            self.not_enough(cost)

    def open_landmarks(self, *args):
        Sfx.play("click")
        city = self.wallet.city
        dialog = Dialog("ДОСТОПРИМЕЧАТЕЛЬНОСТИ", dp(450))
        dialog.add_text(
            f"Каждая даёт +{int(rules.LANDMARK_BONUS * 100)}% ко всему доходу города",
            height=24,
            size=13,
        )
        for item in rules.LANDMARKS:
            owned = item["id"] in city["landmarks"]
            affordable = rules.can_afford(self.wallet.balance, item["cost"])
            dialog.add_row(
                item["name"],
                "построено" if owned else f"+{int(rules.LANDMARK_BONUS * 100)}% к доходу",
                "ЕСТЬ" if owned else fmt(item["cost"]),
                GOLD if owned else (GREEN if affordable else GRAY),
                lambda *a, k=item["id"], d=dialog: self.do_landmark(d, k),
                disabled=owned,
                symbol=item["symbol"],
                symbol_color=GOLD if owned else DIM,
            )
        dialog.open()

    def do_landmark(self, dialog, landmark_id):
        dialog.dismiss()
        item = next(x for x in rules.LANDMARKS if x["id"] == landmark_id)
        result = rules.buy_landmark(self.wallet, landmark_id)
        if result == "ok":
            self.finish(f"{item['name']} построен! Доход города вырос", item["cost"], "win")
        elif result == "reserve":
            self.not_enough(item["cost"])
