import os

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics import (
    BorderImage,
    Color,
    InstructionGroup,
    Line,
    PopMatrix,
    PushMatrix,
    Rectangle,
    RoundedRectangle,
    Rotate,
    Scale,
    Translate,
)
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget

import city_data as rules
from common import (
    BASE_DIR,
    CHIP_IMAGE,
    FONT_SUITS,
    GOLD,
    GRAY,
    GREEN,
    SOFT_RED,
    WHITE,
    GLabel,
    RoundButton,
    Sfx,
    float_text,
    go_to,
    pulse,
)

TEXT = (0.85, 0.88, 0.92, 0.95)
GOLD_BUTTON = (0.96, 0.72, 0.12, 1)
DARK_TEXT = (0.25, 0.14, 0.02, 1)
TAP_SLOP = dp(10)  # a finger moving less than this is a tap, not a drag

# the top and bottom panels float over the map
TOP_PANEL = 112
BOTTOM_PANEL = 190


# ----- pictures (made by make_city_assets.py) -----


def art(name):
    return os.path.join(BASE_DIR, "assets", "city", name)


def building_art(type_id):
    return art(f"{type_id}.png")


def landmark_art(landmark_id):
    return art(f"lm_{landmark_id}.png")


def fmt(amount):
    return f"{int(amount):,}".replace(",", " ")


def fmt_rate(value):
    """Chips per second: whole numbers stay whole, otherwise one digit after the comma."""
    if abs(value - round(value)) < 0.05:
        return fmt(round(value))
    whole, tenth = divmod(round(value * 10), 10)
    return f"{fmt(whole)},{tenth}"


def fmt_time(seconds):
    """How long something takes, in the biggest unit that reads well."""
    if seconds < 90:
        return f"{max(1, round(seconds))} с"
    if seconds < 5400:
        return f"{round(seconds / 60)} мин"
    return f"{seconds / 3600:.1f} ч".replace(".", ",")


MAX_ZOOM = 2.2  # the map can be enlarged this many times
ZOOM_STEP = 1.35  # one press of the + / - buttons
CAR_SIZE = (26, 14)  # dp, length x width
CAR_SPEED = 46  # dp per second
DECOR_FILES = {
    "round": "tree_round", "pine": "tree_pine", "pink": "tree_pink", "bush": "bush",
}


def fit_label(label):
    """Makes a label wrap/shorten inside its own box."""
    label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    return label


def nine_border(width, height, border=34):
    """Corner size for a stretchable picture, never bigger than the widget allows."""
    b = max(1, min(border, height * 0.45, width * 0.45))
    return (b, b, b, b)


def add_plate(widget, source, tint=(1, 1, 1, 1), inset=(0, 0, 0, 0), border=34):
    """Draws a stretchable picture (panel, card...) behind a widget and keeps it in place."""
    with widget.canvas.before:
        Color(*tint)
        plate = BorderImage(source=source, border=(border,) * 4)

    def update(*args):
        left, bottom, right, top = inset
        plate.pos = (widget.x + left, widget.y + bottom)
        plate.size = (max(1, widget.width - left - right), max(1, widget.height - bottom - top))
        plate.border = nine_border(plate.size[0], plate.size[1], border)

    widget.bind(pos=update, size=update)
    update()
    return plate


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


# ----- buttons -----


class CityButton(RoundButton):
    """Soft glossy button made from a picture. btn_color tints it; it sinks when pressed."""

    def __init__(self, btn_color=GREEN, **kwargs):
        self._ready = False
        self._btn_color = btn_color
        super().__init__(btn_color=btn_color, **kwargs)
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.4)
            self.shadow = BorderImage(source=art("btn.png"), border=(34,) * 4)
            self.tint = Color(*btn_color)
            self.body = BorderImage(source=art("btn.png"), border=(34,) * 4)
        self._ready = True
        self.update_bg()

    @property
    def btn_color(self):
        return self._btn_color

    @btn_color.setter
    def btn_color(self, value):
        self._btn_color = value
        self.update_bg()

    def update_bg(self, *args):
        if not getattr(self, "_ready", False):
            return
        x, y = self.pos
        w, h = self.size
        lift = dp(3)
        down = self.state == "down"
        top_gap = dp(1) if down else lift
        border = nine_border(w, h - lift)
        self.shadow.pos = (x, y)
        self.shadow.size = (w, max(1, h - lift))
        self.shadow.border = border
        self.body.pos = (x, y + (dp(1) if down else lift))
        self.body.size = (w, max(1, h - top_gap))
        self.body.border = border

        red, green, blue, alpha = self.btn_color
        if self.disabled:
            factor = 0.45
        elif down:
            factor = 0.78
        else:
            factor = 1.0
        self.tint.rgba = (red * factor, green * factor, blue * factor, alpha)


class PriceButton(CityButton):
    """A button with a chip picture and a price on it."""

    def __init__(self, price, chip=True, **kwargs):
        super().__init__(**kwargs)
        self.text = ""
        self.row = BoxLayout(spacing=dp(4), padding=(dp(8), dp(4), dp(8), dp(8)))
        if chip:
            self.row.add_widget(Image(source=CHIP_IMAGE, size_hint_x=None, width=dp(22)))
        self.price_label = GLabel(
            text=price,
            font_size=dp(17) if len(price) <= 8 else dp(14),
            color=self.color,
            halign="center",
            valign="middle",
        )
        self.row.add_widget(self.price_label)
        self.add_widget(self.row)
        self.bind(pos=self.place_row, size=self.place_row)
        self.place_row()

    def place_row(self, *args):
        self.row.pos = self.pos
        self.row.size = self.size


# ----- things standing on the map -----


class Plate(GLabel):
    """A small label on a dark rounded plate (building name, level stars)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.62)
            self.plate = RoundedRectangle(radius=[dp(8)])
        self.bind(pos=self.update_plate, size=self.update_plate)
        self.update_plate()

    def update_plate(self, *args):
        self.plate.pos = self.pos
        self.plate.size = self.size
        self.text_size = self.size


class MapPlot(FloatLayout):
    """One plot of land: a golden "+" when empty, or a building picture on a paved lot.

    Taps are not handled here: MapView decides if a touch was a tap or a drag.
    """

    def __init__(self, index, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(rules.PLOT_SIZE), dp(rules.PLOT_SIZE)))
        super().__init__(**kwargs)
        self.index = index
        self.plot = None

        self.sprite = Image(
            source=art("plot_empty.png"),
            fit_mode="fill",
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.add_widget(self.sprite)

        self.name_label = Plate(
            font_size=dp(12),
            halign="center",
            valign="middle",
            shorten=True,
            size_hint=(0.86, 0.17),
            pos_hint={"center_x": 0.5, "y": 0.05},
        )
        self.add_widget(self.name_label)

        self.stars_label = Plate(
            font_name=FONT_SUITS,
            font_size=dp(11),
            color=GOLD,
            halign="center",
            valign="middle",
            size_hint=(0.52, 0.15),
            pos_hint={"center_x": 0.5, "top": 0.97},
        )
        self.add_widget(self.stars_label)

        # "+2" that floats up above the building every second it earns
        self.coin_label = GLabel(
            font_size=dp(14),
            color=GOLD,
            size_hint=(None, None),
            size=(dp(60), dp(20)),
            halign="center",
            valign="middle",
            outline_width=2,
            outline_color=(0, 0, 0, 1),
            opacity=0,
        )
        self.coin_label.text_size = self.coin_label.size
        self.add_widget(self.coin_label)

        # golden frame for a building at the maximum level
        self.frame = InstructionGroup()
        self.canvas.after.add(self.frame)
        self.bind(pos=self.redraw_frame, size=self.redraw_frame)
        self.set_plot(None)

    def set_plot(self, plot):
        self.plot = plot
        if plot is None:
            self.sprite.source = art("plot_empty.png")
            self.name_label.opacity = 0
            self.stars_label.opacity = 0
        else:
            self.sprite.source = building_art(plot["type"])
            self.name_label.text = rules.BUILDINGS[plot["type"]]["name"]
            self.name_label.color = WHITE
            self.name_label.opacity = 1
            self.stars_label.text = "★" * plot["level"]
            self.stars_label.opacity = 1
        self.redraw_frame()

    def redraw_frame(self, *args):
        self.frame.clear()
        if self.plot is not None and self.plot["level"] >= rules.MAX_LEVEL:
            self.frame.add(Color(*GOLD[:3], 0.95))
            self.frame.add(
                Line(
                    rounded_rectangle=(
                        self.x + 2, self.y + 2, self.width - 4, self.height - 4, dp(20)
                    ),
                    width=dp(1.6),
                )
            )

    def income_pop(self, text):
        """A small number floats up from the building: this is the income of one second."""
        label = self.coin_label
        Animation.cancel_all(label)
        label.text = text
        label.opacity = 1
        label.center_x = self.center_x
        label.y = self.y + self.height * 0.62
        Animation(y=label.y + dp(30), opacity=0, duration=0.95, t="out_quad").start(label)

    def pop(self, big=True):
        """The picture bounces when something was built or upgraded here."""
        Animation.cancel_all(self.sprite, "size_hint")
        start = 0.45 if big else 0.86
        self.sprite.size_hint = (start, start)
        Animation(size_hint=(1, 1), duration=0.5 if big else 0.35, t="out_back").start(self.sprite)


class CasinoBuilding(FloatLayout):
    """The casino in the middle of the map. A tap opens the casino menu."""

    glow = NumericProperty(0.25)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(rules.CASINO_W), dp(rules.CASINO_H)))
        super().__init__(**kwargs)

        # a golden outline around the plaza that slowly pulses
        self.glow_group = InstructionGroup()
        self.glow_color = Color(1, 0.82, 0.25, self.glow)
        self.glow_line = Line(rounded_rectangle=(0, 0, 10, 10, 20), width=dp(2.6))
        self.glow_group.add(self.glow_color)
        self.glow_group.add(self.glow_line)
        self.canvas.before.add(self.glow_group)

        self.sprite = Image(
            source=art("casino.png"),
            fit_mode="fill",
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.add_widget(self.sprite)
        self.bind(pos=self.update_glow, size=self.update_glow)
        self.update_glow()

    def update_glow(self, *args):
        grow = dp(4)
        self.glow_line.rounded_rectangle = (
            self.x - grow, self.y - grow, self.width + 2 * grow, self.height + 2 * grow, dp(30)
        )

    def start_glow(self):
        self.stop_glow()
        anim = Animation(glow=0.9, duration=0.9, t="in_out_sine") + Animation(
            glow=0.2, duration=0.9, t="in_out_sine"
        )
        anim.repeat = True
        anim.start(self)

    def stop_glow(self):
        Animation.cancel_all(self, "glow")

    def on_glow(self, instance, value):
        self.glow_color.a = value


# ----- the map -----


class MapWorld(Widget):
    """The whole map. Everything on it is placed in map coordinates and the whole thing
    is shifted by one Translate and enlarged by one Scale, so panning and zooming cost
    a single number change."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(rules.MAP_W), dp(rules.MAP_H)))
        super().__init__(**kwargs)
        self.life_event = None
        self.cars = []
        self.clouds = []
        with self.canvas.before:
            PushMatrix()
            self.shift = Translate(0, 0)
            self.zoom = Scale(1, 1, 1)
            self.draw_ground()
        with self.canvas:
            self.draw_life()
        with self.canvas.after:
            PopMatrix()

    @staticmethod
    def to_map(x, y):
        """(0, 0) is the centre of the map; returns the point in map pixels."""
        return dp(rules.MAP_W) / 2 + dp(x), dp(rules.MAP_H) / 2 + dp(y)

    def draw_ground(self):
        width = dp(rules.MAP_W)
        height = dp(rules.MAP_H)

        # the ground: grass, desert, lake, roads, plaza... all painted into one picture
        Color(1, 1, 1, 1)
        Rectangle(texture=CoreImage(art("ground.png")).texture, pos=(0, 0), size=(width, height))

        # things standing on it (the lower ones are drawn last, so they overlap the ones behind)
        textures = {}
        for kind in rules.DECOR_SIZE:
            textures[kind] = CoreImage(art(DECOR_FILES.get(kind, kind) + ".png")).texture
        for kind, x, y in rules.decor_spots():
            w, h = rules.DECOR_SIZE[kind]
            if kind in ("round", "pine", "pink", "bush", "palm", "cactus", "barrel", "rock", "dry"):
                grow = 0.85 + 0.3 * (int(abs(x * 7 + y * 13)) % 10) / 10  # not all the same size
                w, h = w * grow, h * grow
            px, py = self.to_map(x, y)
            Rectangle(
                texture=textures[kind],
                pos=(px - dp(w) / 2, py - dp(h) * 0.15),
                size=(dp(w), dp(h)),
            )

        # edge of the map
        Color(0, 0, 0, 0.4)
        Line(rectangle=(0, 0, width, height), width=dp(3))

    def draw_life(self):
        """Cloud shadows and cars. They are moved by update_life()."""
        cloud = CoreImage(art("cloud.png")).texture
        Color(1, 1, 1, 1)
        for x, y, scale, speed in ((-200, 250, 1.3, 7), (380, -150, 1.8, 5), (800, 520, 1.1, 9)):
            rect = Rectangle(
                texture=cloud, pos=(0, 0), size=(dp(300 * scale), dp(150 * scale))
            )
            self.clouds.append({"rect": rect, "x": x, "y": y, "speed": speed})

        names = ["red", "blue", "yellow", "white", "green"]
        textures = {name: CoreImage(art(f"car_{name}.png")).texture for name in names}
        routes = {1: rules.Route(rules.car_route(1)), -1: rules.Route(rules.car_route(-1))}
        plan = [(1, 0.02, "red"), (1, 0.45, "blue"), (1, 0.75, "white"), (-1, 0.2, "yellow"), (-1, 0.62, "green")]
        for direction, start, name in plan:
            route = routes[direction]
            Color(1, 1, 1, 1)
            PushMatrix()
            rotation = Rotate(angle=0, origin=(0, 0))
            rect = Rectangle(
                texture=textures[name], pos=(0, 0), size=(dp(CAR_SIZE[0]), dp(CAR_SIZE[1]))
            )
            PopMatrix()
            self.cars.append(
                {
                    "route": route,
                    "dist": start * route.total,
                    "speed": CAR_SPEED * (1 + 0.12 * direction),
                    "rotation": rotation,
                    "rect": rect,
                }
            )
        self.update_life(0)

    def start_life(self):
        if self.life_event is None:
            self.life_event = Clock.schedule_interval(self.update_life, 1 / 30)

    def stop_life(self):
        if self.life_event is not None:
            self.life_event.cancel()
            self.life_event = None

    def update_life(self, dt):
        dt = min(dt, 0.1)  # after a pause the cars do not jump
        for car in self.cars:
            car["dist"] += car["speed"] * dt
            x, y, heading = car["route"].at(car["dist"])
            cx, cy = self.to_map(x, y)
            rect = car["rect"]
            rect.pos = (cx - rect.size[0] / 2, cy - rect.size[1] / 2)
            car["rotation"].origin = (cx, cy)
            car["rotation"].angle = heading
        for cloud in self.clouds:
            cloud["x"] += cloud["speed"] * dt
            if cloud["x"] > rules.MAP_W + 250:
                cloud["x"] = -450
            cloud["rect"].pos = (dp(cloud["x"]), self.to_map(0, cloud["y"])[1])


class MapView(StencilView):
    """A window onto the map.

    One finger drags the map, two fingers pinch to zoom (the mouse wheel zooms on a computer),
    a short touch is a tap on a building.
    """

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

        self.scale = 1.0  # how much the map is enlarged
        self.offset = None  # where the map's lower-left corner is, set when the size is known
        self.touches = {}  # the fingers that are on the map, by touch id
        self.pinch = None  # start values of a two-finger zoom
        self.last_pos = (0, 0)
        self.start_pos = (0, 0)
        self.dragging = False
        self.bind(pos=self.apply_offset, size=self.apply_offset)

    def set_center(self, widget, x, y):
        widget.center = self.world.to_map(x, y)

    def min_scale(self):
        """The smallest zoom: the map still covers the whole window."""
        if self.width < 2 or self.height < 2:
            return 0.1
        return max(self.width / self.world.width, self.height / self.world.height)

    def clamp_scale(self, value):
        return max(self.min_scale(), min(MAX_ZOOM, value))

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
        self.scale = self.clamp_scale(self.scale)
        world_w = self.world.width * self.scale
        world_h = self.world.height * self.scale
        if self.offset is None:
            self.offset = [
                rules.centered_offset(self.width, world_w),
                rules.centered_offset(self.height, world_h),
            ]
        self.offset[0] = rules.clamp_offset(self.offset[0], self.width, world_w)
        self.offset[1] = rules.clamp_offset(self.offset[1], self.height, world_h)
        self.world.shift.xy = (self.x + self.offset[0], self.y + self.offset[1])
        self.world.zoom.xyz = (self.scale, self.scale, self.scale)

    # --- zoom ---

    def map_point(self, x, y):
        """Window point -> map pixels (the lower-left corner of the map is 0, 0)."""
        return (
            (x - (self.x + self.offset[0])) / self.scale,
            (y - (self.y + self.offset[1])) / self.scale,
        )

    def zoom_at(self, new_scale, x, y):
        """Changes the zoom and keeps the map point under the window point (x, y) where it is."""
        if self.offset is None:
            return
        mx, my = self.map_point(x, y)
        self.scale = self.clamp_scale(new_scale)
        self.offset[0] = x - self.x - mx * self.scale
        self.offset[1] = y - self.y - my * self.scale
        self.apply_offset()

    def zoom_by(self, factor):
        self.zoom_at(self.scale * factor, self.center_x, self.center_y)

    def begin_pinch(self):
        first, second = list(self.touches.values())[:2]
        mid = ((first.x + second.x) / 2, (first.y + second.y) / 2)
        dist = max(dp(10), ((first.x - second.x) ** 2 + (first.y - second.y) ** 2) ** 0.5)
        self.pinch = {"dist": dist, "scale": self.scale, "anchor": self.map_point(*mid)}

    def update_pinch(self):
        first, second = list(self.touches.values())[:2]
        mid = ((first.x + second.x) / 2, (first.y + second.y) / 2)
        dist = max(dp(10), ((first.x - second.x) ** 2 + (first.y - second.y) ** 2) ** 0.5)
        self.scale = self.clamp_scale(self.pinch["scale"] * dist / self.pinch["dist"])
        # the point between the fingers stays under them, so zooming and moving work together
        self.offset[0] = mid[0] - self.x - self.pinch["anchor"][0] * self.scale
        self.offset[1] = mid[1] - self.y - self.pinch["anchor"][1] * self.scale
        self.apply_offset()

    # --- touches: one finger drags the map, a short touch is a tap ---

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or self.offset is None:
            return False
        if getattr(touch, "is_mouse_scrolling", False):  # mouse wheel
            factor = 1.2 if touch.button == "scrollup" else 1 / 1.2
            self.zoom_at(self.scale * factor, *touch.pos)
            return True
        if len(self.touches) >= 2:
            return False
        self.touches[touch.uid] = touch
        touch.grab(self)
        if len(self.touches) == 1:
            self.dragging = False
            self.start_pos = tuple(touch.pos)
            self.last_pos = tuple(touch.pos)
        else:
            self.dragging = True  # a second finger: this is a zoom, never a tap
            self.begin_pinch()
        return True

    def on_touch_move(self, touch):
        if touch.uid not in self.touches or touch.grab_current is not self:
            return False
        if len(self.touches) >= 2:
            if self.pinch is not None:
                self.update_pinch()
            return True
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
        if touch.uid not in self.touches or touch.grab_current is not self:
            return False
        touch.ungrab(self)
        del self.touches[touch.uid]
        self.pinch = None
        if self.touches:  # one finger is still down: it goes on dragging from where it is
            rest = next(iter(self.touches.values()))
            self.last_pos = tuple(rest.pos)
            self.dragging = True
            return True
        if not self.dragging and self.offset is not None:
            self.tap(*self.map_point(touch.x, touch.y))
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


# ----- top and bottom panels -----


class CityTopBar(BoxLayout):
    """Menu button and the chip balance on a dark pill. The balance counts up and down."""

    shown = NumericProperty(0)

    def __init__(self, on_back, **kwargs):
        super().__init__(size_hint_y=None, height=dp(52), spacing=dp(10), **kwargs)
        self.first_time = True

        back = CityButton(text="МЕНЮ", btn_color=GRAY, size_hint_x=None, width=dp(104))
        back.font_size = dp(19)
        back.bind(on_release=on_back)
        self.add_widget(back)

        pill = BoxLayout(padding=(dp(14), dp(5), dp(10), dp(5)), spacing=dp(8))
        add_plate(pill, art("card.png"))
        self.balance_label = fit_label(
            GLabel(font_size=dp(27), color=GOLD, halign="right", valign="middle")
        )
        pill.add_widget(self.balance_label)
        pill.add_widget(Image(source=CHIP_IMAGE, size_hint_x=None, width=dp(34)))
        self.add_widget(pill)

    def set_balance(self, value):
        if self.first_time:
            self.first_time = False
            self.shown = value
            return
        Animation.cancel_all(self, "shown")
        Animation(shown=value, duration=0.6, t="out_quad").start(self)

    def on_shown(self, instance, value):
        self.balance_label.text = fmt(round(value))


class LandmarkStrip(Tappable, BoxLayout):
    """Row of landmark pictures: bright when built, faded when not. Tap opens the list."""

    def __init__(self, **kwargs):
        kwargs.setdefault("spacing", dp(6))
        kwargs.setdefault("padding", (dp(10), dp(3)))
        super().__init__(**kwargs)
        add_plate(self, art("card.png"), border=30)

        self.icons = []
        for item in rules.LANDMARKS:
            icon = Image(source=landmark_art(item["id"]), fit_mode="contain")
            self.icons.append(icon)
            self.add_widget(icon)

    def refresh(self, city):
        for item, icon in zip(rules.LANDMARKS, self.icons):
            built = item["id"] in city["landmarks"]
            icon.color = (1, 1, 1, 1) if built else (0.5, 0.55, 0.65, 0.5)


# ----- dialogs -----


class Dialog(ModalView):
    """Dark glass card with a title, a scrollable list of rows and a close button."""

    def __init__(self, title, height, **kwargs):
        kwargs.setdefault("size_hint", (0.92, None))
        super().__init__(**kwargs)
        self.height = min(height, Window.height * 0.9)
        self.auto_dismiss = True
        self.background_color = (0, 0, 0, 0.72)

        container = BoxLayout(orientation="vertical", padding=(dp(16), dp(14)), spacing=dp(8))
        add_plate(container, art("panel.png"), border=32)

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

        self.rows = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        scroll.add_widget(self.rows)
        container.add_widget(scroll)

        close = CityButton(text="ЗАКРЫТЬ", btn_color=GRAY, size_hint_y=None, height=dp(50))
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

    def add_picture(self, path, height):
        self.rows.add_widget(
            Image(source=path, fit_mode="contain", size_hint_y=None, height=height)
        )

    def add_row(
        self,
        title,
        subtitle,
        button_text,
        button_color,
        on_press,
        disabled=False,
        title_color=WHITE,
        image=None,
        dim_image=False,
        chip=True,
    ):
        row = BoxLayout(
            size_hint_y=None, height=dp(72), spacing=dp(8), padding=(dp(8), dp(6), dp(8), dp(6))
        )
        add_plate(row, art("card.png"), border=28)
        if image:
            row.add_widget(
                Image(
                    source=image,
                    fit_mode="contain",
                    size_hint_x=None,
                    width=dp(56),
                    color=(0.5, 0.55, 0.65, 0.55) if dim_image else (1, 1, 1, 1),
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
                    font_size=dp(11),
                    color=TEXT,
                    halign="left",
                    valign="middle",
                    shorten=True,
                )
            )
        )
        row.add_widget(texts)
        button = PriceButton(
            button_text,
            chip=chip,
            btn_color=button_color,
            size_hint_x=None,
            width=dp(122),
            disabled=disabled,
        )
        if button_color == GOLD_BUTTON:
            button.price_label.color = DARK_TEXT
        button.bind(on_release=on_press)
        row.add_widget(button)
        self.rows.add_widget(row)


# ----- the screen -----


class CityScreen(Screen):
    def __init__(self, wallet, **kwargs):
        super().__init__(**kwargs)
        self.wallet = wallet
        self.tick_event = None
        self.pop_event = None
        self.first_visit = True

        root = FloatLayout()

        self.map = MapView(self.on_plot, self.on_casino, size_hint=(1, 1))
        root.add_widget(self.map)

        # top panel: menu button, balance, city rank
        top = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(TOP_PANEL),
            pos_hint={"top": 1},
            padding=(dp(18), dp(16), dp(18), dp(10)),
            spacing=dp(4),
        )
        add_plate(top, art("panel.png"), tint=(1, 1, 1, 0.94), inset=(dp(6), dp(2), dp(6), dp(6)), border=32)
        self.top_bar = CityTopBar(self.go_menu)
        top.add_widget(self.top_bar)
        self.info_label = fit_label(
            GLabel(
                font_size=dp(16),
                color=TEXT,
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(24),
            )
        )
        top.add_widget(self.info_label)
        root.add_widget(top)

        # bottom panel: message, landmarks, collect button
        bottom = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(BOTTOM_PANEL),
            pos_hint={"y": 0},
            padding=(dp(18), dp(12), dp(18), dp(16)),
            spacing=dp(6),
        )
        add_plate(bottom, art("panel.png"), tint=(1, 1, 1, 0.94), inset=(dp(6), dp(6), dp(6), dp(2)), border=32)

        self.message_label = fit_label(
            GLabel(
                font_size=dp(15),
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(42),
            )
        )
        bottom.add_widget(self.message_label)

        self.strip = LandmarkStrip(size_hint_y=None, height=dp(48))
        self.strip.callback = self.open_landmarks
        bottom.add_widget(self.strip)

        self.collect_button = CityButton(
            text="СОБРАТЬ", btn_color=GREEN, size_hint_y=None, height=dp(60)
        )
        self.collect_button.font_size = dp(25)
        self.collect_button.bind(on_release=self.collect)
        bottom.add_widget(self.collect_button)
        root.add_widget(bottom)

        # zoom buttons on the right, above the bottom panel
        for text, factor, lift in (("+", ZOOM_STEP, 72), ("-", 1 / ZOOM_STEP, 16)):
            zoom = CityButton(
                text=text, btn_color=GOLD_BUTTON, size_hint=(None, None), size=(dp(48), dp(48))
            )
            zoom.color = DARK_TEXT
            zoom.font_size = dp(30)
            zoom.pos_hint = {"right": 0.97}
            zoom.y = dp(BOTTOM_PANEL) + dp(lift)
            zoom.bind(on_release=lambda *a, f=factor: self.zoom_map(f))
            root.add_widget(zoom)

        self.add_widget(root)

    def zoom_map(self, factor):
        Sfx.play("click")
        self.map.zoom_by(factor)

    # --- showing the state ---

    def on_pre_enter(self, *args):
        self.say("Двигай карту пальцем. «+» - строить, казино - играть", WHITE)
        if self.first_visit:
            self.first_visit = False
            # the bottom panel is taller than the top one, so the middle of the free map is higher
            self.map.center_on_casino(dp((BOTTOM_PANEL - TOP_PANEL) / 2))
        self.refresh()

    def on_enter(self, *args):
        self.map.casino.start_glow()
        self.map.world.start_life()
        if self.tick_event is None:
            self.tick_event = Clock.schedule_interval(self.tick, 0.25)
        if self.pop_event is None:
            self.pop_event = Clock.schedule_interval(self.income_second, 1.0)

    def on_leave(self, *args):
        self.map.casino.stop_glow()
        self.map.world.stop_life()
        if self.tick_event is not None:
            self.tick_event.cancel()
            self.tick_event = None
        if self.pop_event is not None:
            self.pop_event.cancel()
            self.pop_event = None

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

        text = f"{rules.rank_name(city)} · доход {fmt_rate(rules.income_per_second(city))}/сек"
        if city["landmarks"]:
            text += f" (+{int(len(city['landmarks']) * rules.LANDMARK_BONUS * 100)}%)"
        self.info_label.text = text
        self.tick()

    def income_second(self, *args):
        """Once a second every working building shows how much it just earned."""
        city = self.wallet.city
        if rules.income_per_second(city) <= 0 or rules.pending(city) >= rules.capacity(city):
            return  # nothing is earned while the storage is full
        mult = rules.income_multiplier(city)
        for tile, plot in zip(self.map.plots, city["plots"]):
            if plot is not None:
                tile.income_pop("+" + fmt_rate(rules.building_income(plot["type"], plot["level"]) * mult))

    def tick(self, *args):
        city = self.wallet.city
        rate = rules.income_per_second(city)
        waiting = int(rules.pending(city))
        button = self.collect_button
        if rate <= 0:
            button.text = "ПОСТРОЙ ПЕРВОЕ ЗДАНИЕ"
            button.btn_color = GRAY
            button.color = WHITE
            button.disabled = True
        elif waiting < 1:
            button.text = "Копится доход..."
            button.btn_color = GRAY
            button.color = WHITE
            button.disabled = True
        else:
            full = waiting >= int(rules.capacity(city))
            button.text = f"СОБРАТЬ +{fmt(waiting)}" + ("  (ПОЛНО)" if full else "")
            button.btn_color = GOLD_BUTTON
            button.color = DARK_TEXT
            button.disabled = False

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

    def finish(self, text, cost, sound="chip", index=None, big=True):
        Sfx.play(sound)
        float_text(self, f"-{fmt(cost)}", SOFT_RED, 0.5, 34)
        self.say(text, GOLD)
        self.refresh()
        if index is not None:
            self.map.plots[index].pop(big)

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
        dialog = Dialog("СТРОИТЕЛЬСТВО", dp(560))
        dialog.add_text("Выбери, что построить на этом участке", height=22, size=14)
        mult = rules.income_multiplier(self.wallet.city)
        for type_id in rules.BUILDING_ORDER:
            spec = rules.BUILDINGS[type_id]
            cost = rules.upgrade_cost(type_id, 0)
            income = spec["income"] * mult
            affordable = rules.can_afford(self.wallet.balance, cost)
            dialog.add_row(
                spec["name"],
                f"+{fmt_rate(income)} в сек · окупится за {fmt_time(cost / income)}",
                fmt(cost),
                GREEN if affordable else GRAY,
                lambda *a, i=index, t=type_id, d=dialog: self.do_build(d, i, t),
                title_color=spec["color"][:3] + (1,),
                image=building_art(type_id),
            )
        dialog.open()

    def do_build(self, dialog, index, type_id):
        dialog.dismiss()
        cost = rules.upgrade_cost(type_id, 0)
        result = rules.buy_building(self.wallet, index, type_id)
        if result == "ok":
            self.finish(f"Построено: {rules.BUILDINGS[type_id]['name']}!", cost, index=index)
        elif result == "reserve":
            self.not_enough(cost)

    def open_upgrade(self, index):
        plot = self.wallet.city["plots"][index]
        spec = rules.BUILDINGS[plot["type"]]
        level = plot["level"]
        mult = rules.income_multiplier(self.wallet.city)

        dialog = Dialog(spec["name"].upper(), dp(430))
        dialog.add_picture(building_art(plot["type"]), dp(120))
        dialog.add_text(f"Уровень {level} из {rules.MAX_LEVEL}", color=GOLD, height=26, size=17)
        dialog.add_text(
            f"Доход сейчас: {fmt_rate(rules.building_income(plot['type'], level) * mult)} в сек"
        )
        if level >= rules.MAX_LEVEL:
            dialog.add_text("Максимальный уровень!", GOLD, height=30, size=17)
        else:
            cost = rules.upgrade_cost(plot["type"], level)
            next_income = rules.building_income(plot["type"], level + 1) * mult
            dialog.add_text(f"После улучшения: {fmt_rate(next_income)} в сек")
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
            self.finish(f"{name}: уровень {level}!", cost, index=index, big=False)
        elif result == "reserve":
            self.not_enough(cost)

    def open_landmarks(self, *args):
        Sfx.play("click")
        city = self.wallet.city
        dialog = Dialog("ДОСТОПРИМЕЧАТЕЛЬНОСТИ", dp(500))
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
                GOLD_BUTTON if owned else (GREEN if affordable else GRAY),
                (lambda *a: None) if owned else (lambda *a, k=item["id"], d=dialog: self.do_landmark(d, k)),
                image=landmark_art(item["id"]),
                dim_image=not owned,
                chip=not owned,
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
