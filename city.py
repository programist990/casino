from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import (
    Color,
    Ellipse,
    InstructionGroup,
    Line,
    PopMatrix,
    PushMatrix,
    Rectangle,
    RoundedRectangle,
    Translate,
    Triangle,
)
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget

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
    RoundButton,
    Sfx,
    TopBar,
    float_text,
    go_to,
    pulse,
)

DIM = (1, 1, 1, 0.3)
TEXT = (0.85, 0.88, 0.92, 0.95)
TAP_SLOP = dp(10)  # a finger moving less than this is a tap, not a drag


def fmt(amount):
    return f"{int(amount):,}".replace(",", " ")


def shade(color, factor):
    return (min(1, color[0] * factor), min(1, color[1] * factor), min(1, color[2] * factor), 1)


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


# ----- things standing on the map (seen from above) -----


class MapPlot(FloatLayout):
    """One plot of land: a "+" when empty, or a building drawn from above.

    Taps are not handled here: MapView decides if a touch was a tap or a drag.
    """

    def __init__(self, index, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(rules.PLOT_SIZE), dp(rules.PLOT_SIZE)))
        super().__init__(**kwargs)
        self.index = index
        self.plot = None
        self.art = InstructionGroup()
        self.canvas.add(self.art)

        self.plus = GLabel(
            text="+",
            font_size=dp(46),
            color=(1, 0.9, 0.5, 0.9),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            size_hint=(1, 0.5),
        )
        self.add_widget(self.plus)

        self.name_label = fit_label(
            GLabel(
                font_size=dp(13),
                halign="center",
                valign="middle",
                shorten=True,
                pos_hint={"x": 0, "y": 0.02},
                size_hint=(1, 0.22),
            )
        )
        self.add_widget(self.name_label)

        self.level_label = fit_label(
            GLabel(
                font_size=dp(13),
                color=GOLD,
                halign="right",
                valign="middle",
                pos_hint={"right": 0.95, "top": 0.99},
                size_hint=(0.6, 0.2),
            )
        )
        self.add_widget(self.level_label)

        self.bind(pos=self.redraw, size=self.redraw)

    def set_plot(self, plot):
        self.plot = plot
        if plot is None:
            self.plus.opacity = 1
            self.name_label.text = ""
            self.level_label.text = ""
        else:
            self.plus.opacity = 0
            self.name_label.text = rules.BUILDINGS[plot["type"]]["name"]
            self.name_label.color = WHITE
            self.level_label.text = f"Ур. {plot['level']}"
        self.redraw()

    def redraw(self, *args):
        self.art.clear()
        x, y = self.pos
        w, h = self.size
        if w < 10 or h < 10:
            return

        if self.plot is None:
            # a free plot: soft patch, dashed gold outline and a "+" button
            self.art.add(Color(0.02, 0.07, 0.06, 0.45))
            self.art.add(RoundedRectangle(pos=self.pos, size=self.size, radius=[14]))
            self.art.add(Color(1, 0.82, 0.25, 0.6))
            self.art.add(
                Line(
                    rounded_rectangle=(x + 2, y + 2, w - 4, h - 4, 14),
                    width=1.3,
                    dash_length=7,
                    dash_offset=5,
                )
            )
            r = w * 0.24
            self.art.add(Color(1, 0.82, 0.25, 0.2))
            self.art.add(Ellipse(pos=(x + w / 2 - r, y + h / 2 - r), size=(2 * r, 2 * r)))
            self.art.add(Color(1, 0.82, 0.25, 0.7))
            self.art.add(Line(circle=(x + w / 2, y + h / 2, r), width=1.4))
            return

        spec = rules.BUILDINGS[self.plot["type"]]
        level = self.plot["level"]
        color = spec["color"]
        dark = shade(color, 0.55)

        # concrete pad the building stands on
        self.art.add(Color(0.13, 0.15, 0.17, 1))
        self.art.add(RoundedRectangle(pos=self.pos, size=self.size, radius=[14]))
        self.art.add(Color(1, 1, 1, 0.12))
        self.art.add(Line(rounded_rectangle=(x + 1, y + 1, w - 2, h - 2, 14), width=1))

        side = w * 0.78 * spec["width"]
        cx = x + w / 2
        cy = y + h * 0.6
        bx = cx - side / 2
        by = cy - side / 2
        shape = spec["shape"]
        offset = dp(5)

        # shadow: the roof "stands" above the ground
        self.art.add(Color(0, 0, 0, 0.4))
        if shape == "dome":
            self.art.add(Ellipse(pos=(bx + offset, by - offset), size=(side, side)))
        else:
            self.art.add(Rectangle(pos=(bx + offset, by - offset), size=(side, side)))

        if shape == "peak":
            # gable roof: two slopes, one lit and one in shade, ridge between them
            half = side / 2
            self.art.add(Color(*color))
            self.art.add(Rectangle(pos=(bx, by), size=(half, side)))
            self.art.add(Color(*shade(color, 0.7)))
            self.art.add(Rectangle(pos=(bx + half, by), size=(half, side)))
            self.art.add(Color(1, 1, 1, 0.45))
            self.art.add(Line(points=[cx, by + dp(2), cx, by + side - dp(2)], width=1.3))
        elif shape == "flat":
            # flat roof with air conditioners and a small pool
            self.art.add(Color(*shade(color, 0.75)))
            self.art.add(Rectangle(pos=(bx, by), size=(side, side)))
            self.art.add(Color(*color))
            self.art.add(
                Rectangle(pos=(bx + dp(4), by + dp(4)), size=(side - dp(8), side - dp(8)))
            )
            unit = side * 0.16
            self.art.add(Color(*dark))
            self.art.add(Rectangle(pos=(bx + side * 0.12, by + side * 0.66), size=(unit, unit)))
            self.art.add(Rectangle(pos=(bx + side * 0.36, by + side * 0.66), size=(unit, unit)))
            self.art.add(Color(0.55, 0.85, 1, 0.95))
            self.art.add(
                RoundedRectangle(
                    pos=(bx + side * 0.12, by + side * 0.14),
                    size=(side * 0.46, side * 0.28),
                    radius=[4],
                )
            )
        elif shape == "spire":
            # tower: stepped square roof with a cross in the middle
            self.art.add(Color(*dark))
            self.art.add(Rectangle(pos=(bx, by), size=(side, side)))
            inner = side * 0.74
            self.art.add(Color(*color))
            self.art.add(Rectangle(pos=(cx - inner / 2, cy - inner / 2), size=(inner, inner)))
            core = side * 0.36
            self.art.add(Color(*shade(color, 1.3)))
            self.art.add(Rectangle(pos=(cx - core / 2, cy - core / 2), size=(core, core)))
            self.art.add(Color(1, 1, 1, 0.5))
            self.art.add(Line(points=[cx - core / 2, cy, cx + core / 2, cy], width=1.2))
            self.art.add(Line(points=[cx, cy - core / 2, cx, cy + core / 2], width=1.2))
        else:
            # dome: concentric circles
            self.art.add(Color(*dark))
            self.art.add(Ellipse(pos=(bx, by), size=(side, side)))
            inner = side * 0.78
            self.art.add(Color(*color))
            self.art.add(Ellipse(pos=(cx - inner / 2, cy - inner / 2), size=(inner, inner)))
            core = side * 0.34
            self.art.add(Color(*shade(color, 1.3)))
            self.art.add(Ellipse(pos=(cx - core / 2, cy - core / 2), size=(core, core)))
            self.art.add(Color(1, 1, 1, 0.4))
            self.art.add(Line(circle=(cx, cy, inner / 2), width=1.1))

        # the maximum level gets a golden frame
        if level >= rules.MAX_LEVEL:
            self.art.add(Color(*GOLD[:3], 0.9))
            self.art.add(Line(rounded_rectangle=(x + 1, y + 1, w - 2, h - 2, 14), width=1.6))


class CasinoBuilding(FloatLayout):
    """The casino in the middle of the map, seen from above. A tap opens the casino menu."""

    glow = NumericProperty(0.25)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(rules.CASINO_W), dp(rules.CASINO_H)))
        super().__init__(**kwargs)
        self.art = InstructionGroup()
        self.canvas.add(self.art)
        self.glow_color = None

        self.spade = GLabel(
            text="♠",
            font_name=FONT_SUITS,
            font_size=dp(46),
            color=(0.35, 0.05, 0.1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.58},
            size_hint=(1, 0.4),
        )
        self.add_widget(self.spade)

        self.sign = GLabel(
            text="КАЗИНО",
            font_size=dp(27),
            color=GOLD,
            outline_width=2,
            outline_color=(0.25, 0.02, 0.05, 1),
            pos_hint={"center_x": 0.5, "y": 0.06},
            size_hint=(1, 0.22),
        )
        self.add_widget(self.sign)

        self.bind(pos=self.redraw, size=self.redraw)

    def start_glow(self):
        self.stop_glow()
        anim = Animation(glow=0.85, duration=0.9, t="in_out_sine") + Animation(
            glow=0.25, duration=0.9, t="in_out_sine"
        )
        anim.repeat = True
        anim.start(self)

    def stop_glow(self):
        Animation.cancel_all(self, "glow")

    def on_glow(self, instance, value):
        if self.glow_color is not None:
            self.glow_color.a = value

    def redraw(self, *args):
        self.art.clear()
        x, y = self.pos
        w, h = self.size
        if w < 10 or h < 10:
            return
        cx = x + w / 2
        cy = y + h * 0.58

        # stone square around the building
        pad = dp(26)
        self.art.add(Color(0.2, 0.22, 0.26, 1))
        self.art.add(
            RoundedRectangle(pos=(x - pad, y - pad), size=(w + 2 * pad, h + 2 * pad), radius=[28])
        )
        self.art.add(Color(1, 1, 1, 0.1))
        self.art.add(
            Line(rounded_rectangle=(x - pad, y - pad, w + 2 * pad, h + 2 * pad, 28), width=1.2)
        )

        # red carpet from the entrance
        self.art.add(Color(0.8, 0.1, 0.18, 1))
        self.art.add(Rectangle(pos=(cx - dp(20), y - pad), size=(dp(40), pad + dp(6))))
        self.art.add(Color(1, 0.82, 0.25, 0.8))
        self.art.add(Line(points=[cx - dp(20), y - pad, cx - dp(20), y + dp(6)], width=1))
        self.art.add(Line(points=[cx + dp(20), y - pad, cx + dp(20), y + dp(6)], width=1))

        # shadow and the building itself
        self.art.add(Color(0, 0, 0, 0.4))
        self.art.add(RoundedRectangle(pos=(x + dp(7), y - dp(7)), size=self.size, radius=[18]))
        self.art.add(Color(0.45, 0.06, 0.12, 1))
        self.art.add(RoundedRectangle(pos=self.pos, size=self.size, radius=[18]))

        # gold roof edge and a darker roof inside it
        self.art.add(Color(*GOLD))
        self.art.add(RoundedRectangle(pos=(x + dp(6), y + dp(6)), size=(w - dp(12), h - dp(12)), radius=[14]))
        self.art.add(Color(0.6, 0.08, 0.16, 1))
        self.art.add(RoundedRectangle(pos=(x + dp(10), y + dp(10)), size=(w - dp(20), h - dp(20)), radius=[12]))

        # four towers in the corners
        tower = dp(26)
        self.art.add(Color(*GOLD))
        for tx in (x + dp(10), x + w - dp(10) - tower):
            for ty in (y + dp(10), y + h - dp(10) - tower):
                self.art.add(Rectangle(pos=(tx, ty), size=(tower, tower)))
                self.art.add(Color(0.45, 0.06, 0.12, 1))
                self.art.add(Rectangle(pos=(tx + dp(5), ty + dp(5)), size=(tower - dp(10), tower - dp(10))))
                self.art.add(Color(*GOLD))

        # dome in the middle
        r = dp(44)
        self.art.add(Color(0.3, 0.03, 0.08, 1))
        self.art.add(Ellipse(pos=(cx - r - dp(3), cy - r - dp(3)), size=(2 * r + dp(6), 2 * r + dp(6))))
        self.art.add(Color(*GOLD))
        self.art.add(Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r)))
        self.art.add(Color(1, 0.93, 0.6, 1))
        self.art.add(Ellipse(pos=(cx - r * 0.78, cy - r * 0.78), size=(r * 1.56, r * 1.56)))

        # neon outline that slowly pulses
        self.glow_color = Color(1, 0.82, 0.25, self.glow)
        self.art.add(self.glow_color)
        self.art.add(Line(rounded_rectangle=(x - dp(3), y - dp(3), w + dp(6), h + dp(6), 20), width=2.4))


# ----- the map -----


class MapWorld(Widget):
    """The whole map. Everything on it is placed in map coordinates and the whole thing
    is shifted by one Translate, so panning costs a single number change."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(rules.MAP_W), dp(rules.MAP_H)))
        super().__init__(**kwargs)
        with self.canvas.before:
            PushMatrix()
            self.shift = Translate(0, 0)
            self.draw_ground()
        with self.canvas.after:
            PopMatrix()

    @staticmethod
    def to_map(x, y):
        """(0, 0) is the centre of the map; returns the point in map pixels."""
        return dp(rules.MAP_W) / 2 + dp(x), dp(rules.MAP_H) / 2 + dp(y)

    def draw_ground(self):
        width = dp(rules.MAP_W)
        height = dp(rules.MAP_H)

        Color(0.06, 0.27, 0.19, 1)
        Rectangle(pos=(0, 0), size=(width, height))
        # mowing stripes
        Color(1, 1, 1, 0.035)
        stripe = dp(100)
        for i in range(0, int(width // stripe) + 1, 2):
            Rectangle(pos=(i * stripe, 0), size=(stripe, height))

        # stone square under the casino
        cx, cy = self.to_map(0, 0)
        half_w = dp(rules.CASINO_W / 2 + 26)
        half_h = dp(rules.CASINO_H / 2 + 26)

        # roads
        road = dp(rules.ROAD_WIDTH)
        Color(0.11, 0.12, 0.14, 1)
        for rx in rules.ROAD_X:
            Rectangle(pos=(self.to_map(rx, 0)[0] - road / 2, 0), size=(road, height))
        for ry in rules.ROAD_Y:
            Rectangle(pos=(0, self.to_map(0, ry)[1] - road / 2), size=(width, road))
        Color(1, 1, 1, 0.3)
        for rx in rules.ROAD_X:
            x = self.to_map(rx, 0)[0]
            Line(points=[x, 0, x, height], width=1, dash_length=dp(10), dash_offset=dp(8))
        for ry in rules.ROAD_Y:
            y = self.to_map(0, ry)[1]
            Line(points=[0, y, width, y], width=1, dash_length=dp(10), dash_offset=dp(8))

        # trees
        for tx, ty, radius in rules.tree_spots():
            px, py = self.to_map(tx, ty)
            r = dp(radius)
            Color(0, 0, 0, 0.25)
            Ellipse(pos=(px - r + dp(3), py - r - dp(3)), size=(2 * r, 2 * r))
            Color(0.04, 0.2, 0.12, 1)
            Ellipse(pos=(px - r, py - r), size=(2 * r, 2 * r))
            Color(0.1, 0.38, 0.2, 1)
            Ellipse(pos=(px - r * 0.65, py - r * 0.5), size=(r * 1.3, r * 1.3))

        # edge of the map
        Color(0, 0, 0, 0.4)
        Line(rectangle=(0, 0, width, height), width=dp(3))


class MapView(StencilView):
    """A window onto the map. Drag to move the map, tap a building to use it."""

    def __init__(self, on_plot, on_casino, **kwargs):
        super().__init__(**kwargs)
        self.on_plot = on_plot
        self.on_casino = on_casino

        self.world = MapWorld()
        self.add_widget(self.world)

        self.casino = CasinoBuilding()
        self.set_center(self.casino, 0, 0)
        self.world.add_widget(self.casino)

        self.plots = []
        for index, (dx, dy) in enumerate(rules.PLOT_OFFSETS):
            plot = MapPlot(index)
            self.set_center(plot, dx, dy)
            self.world.add_widget(plot)
            self.plots.append(plot)

        self.offset = None  # where the map's lower-left corner is, set when the size is known
        self.touch = None
        self.last_pos = (0, 0)
        self.start_pos = (0, 0)
        self.dragging = False
        self.bind(pos=self.apply_offset, size=self.apply_offset)

    def set_center(self, widget, x, y):
        widget.center = self.world.to_map(x, y)

    def center_on_casino(self, shift_y=0):
        """Puts the casino in the middle of the window (shift_y moves it up, e.g. away from a panel)."""
        self.offset = None
        self.apply_offset()
        if self.offset is not None:
            self.offset[1] += shift_y
            self.apply_offset()

    def apply_offset(self, *args):
        if self.width < 2 or self.height < 2:
            return
        if self.offset is None:
            self.offset = [
                rules.centered_offset(self.width, self.world.width),
                rules.centered_offset(self.height, self.world.height),
            ]
        self.offset[0] = rules.clamp_offset(self.offset[0], self.width, self.world.width)
        self.offset[1] = rules.clamp_offset(self.offset[1], self.height, self.world.height)
        self.world.shift.xy = (self.x + self.offset[0], self.y + self.offset[1])

    # --- touches: one finger drags the map, a short touch is a tap ---

    def on_touch_down(self, touch):
        if self.touch is not None or not self.collide_point(*touch.pos):
            return False
        self.touch = touch
        self.dragging = False
        self.start_pos = tuple(touch.pos)
        self.last_pos = tuple(touch.pos)
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch is not self.touch or touch.grab_current is not self:
            return False
        if not self.dragging:
            moved = ((touch.x - self.start_pos[0]) ** 2 + (touch.y - self.start_pos[1]) ** 2) ** 0.5
            if moved > TAP_SLOP:
                self.dragging = True
        if self.dragging and self.offset is not None:
            self.offset[0] += touch.x - self.last_pos[0]
            self.offset[1] += touch.y - self.last_pos[1]
            self.apply_offset()
        self.last_pos = tuple(touch.pos)
        return True

    def on_touch_up(self, touch):
        if touch is not self.touch or touch.grab_current is not self:
            return False
        touch.ungrab(self)
        self.touch = None
        if not self.dragging and self.offset is not None:
            self.tap(touch.x - (self.x + self.offset[0]), touch.y - (self.y + self.offset[1]))
        self.dragging = False
        return True

    def tap(self, map_x, map_y):
        """map_x/map_y are in map pixels (the lower-left corner of the map is 0, 0)."""
        for plot in self.plots:
            if plot.collide_point(map_x, map_y):
                self.on_plot(plot)
                return
        if self.casino.collide_point(map_x, map_y):
            self.on_casino()


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


def hud_plate(widget, alpha=0.55):
    """Dark see-through plate behind a block of buttons, so it reads on top of the map."""
    with widget.canvas.before:
        Color(0, 0, 0, alpha)
        plate = RoundedRectangle(radius=[0, 0, 18, 18])

    def update(*args):
        plate.pos = widget.pos
        plate.size = widget.size

    widget.bind(pos=update, size=update)
    return plate


class CityScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.tick_event = None
        self.first_visit = True

        root = FloatLayout()

        self.map = MapView(self.on_plot, self.on_casino, size_hint=(1, 1))
        root.add_widget(self.map)

        # top: back button, balance, city rank
        top = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(106),
            pos_hint={"top": 1},
            padding=(dp(12), dp(8), dp(12), dp(4)),
            spacing=dp(4),
        )
        hud_plate(top)
        self.top_bar = TopBar(self.go_menu)
        top.add_widget(self.top_bar)
        self.info_label = fit_label(
            GLabel(
                font_size=dp(16),
                color=TEXT,
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(26),
            )
        )
        top.add_widget(self.info_label)
        root.add_widget(top)

        # bottom: message, landmarks, collect button
        bottom = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(176),
            pos_hint={"y": 0},
            padding=(dp(12), dp(8), dp(12), dp(10)),
            spacing=dp(6),
        )
        with bottom.canvas.before:
            Color(0, 0, 0, 0.55)
            bottom_plate = RoundedRectangle(radius=[18, 18, 0, 0])

        def update_bottom(*args):
            bottom_plate.pos = bottom.pos
            bottom_plate.size = bottom.size

        bottom.bind(pos=update_bottom, size=update_bottom)

        self.message_label = MessageLabel(size_hint_y=None, height=dp(44))
        self.message_label.font_size = dp(17)
        bottom.add_widget(self.message_label)

        self.strip = LandmarkStrip(size_hint_y=None, height=dp(44))
        self.strip.callback = self.open_landmarks
        bottom.add_widget(self.strip)

        self.collect_button = RoundButton(
            text="СОБРАТЬ", btn_color=GREEN, size_hint_y=None, height=dp(58)
        )
        self.collect_button.font_size = dp(26)
        self.collect_button.bind(on_release=self.collect)
        bottom.add_widget(self.collect_button)
        root.add_widget(bottom)

        self.add_widget(root)

    # --- showing the state ---

    def on_pre_enter(self, *args):
        self.say("Двигай карту пальцем. «+» - строить, казино - играть", WHITE)
        if self.first_visit:
            self.first_visit = False
            self.map.center_on_casino(dp(35))  # the bottom panel is taller than the top one
        self.refresh()

    def on_enter(self, *args):
        self.map.casino.start_glow()
        if self.tick_event is None:
            self.tick_event = Clock.schedule_interval(self.tick, 1.0)

    def on_leave(self, *args):
        self.map.casino.stop_glow()
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
        for tile, plot in zip(self.map.plots, city["plots"]):
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

    def on_plot(self, tile):
        Sfx.play("click")
        if tile.plot is None:
            self.open_build(tile.index)
        else:
            self.open_upgrade(tile.index)

    def on_casino(self, *args):
        Sfx.play("click")
        go_to(self.manager, "menu", "right")

    def open_build(self, index):
        dialog = Dialog("СТРОИТЕЛЬСТВО", dp(470))
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
