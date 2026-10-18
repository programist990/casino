import math
import random

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    Mesh,
    PopMatrix,
    PushMatrix,
    Rotate,
    RoundedRectangle,
    Translate,
    Triangle,
)
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
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
    Sfx,
    TopBar,
    float_text,
    go_to,
    pulse,
)

HISTORY_LIMIT = 6


class CrashGraph(Widget):
    """Canvas widget showing a deep-space background with animated streaming stars,

    a rising glowing curve, and a detailed animated flying rocket with thruster flames.
    """

    curve_progress = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points = []
        self.crashed = False
        self.cashed_out = False
        self.is_flying = False
        self.anim_time = 0.0
        self.rocket_pos = (0, 0)
        self.rocket_angle = 30.0
        self.flame_boost = 1.0

        # Explosion parameters
        self.explosion_active = False
        self.explosion_r = 0.0
        self.explosion_alpha = 0.0

        # Initialize stars for cosmic background
        self.stars = []
        for _ in range(35):
            self.stars.append(
                {
                    "rx": random.random(),
                    "ry": random.random(),
                    "size": random.uniform(1.8, 3.6),
                    "speed": random.uniform(0.15, 0.45),
                    "twinkle_speed": random.uniform(2.0, 5.0),
                    "phase": random.uniform(0, math.pi * 2),
                }
            )

        # Thruster particle sparks
        self.sparks = []

        with self.canvas.before:
            # Cosmic deep space background
            Color(0.02, 0.03, 0.07, 0.96)
            self.bg = RoundedRectangle(radius=[16])

            # Space grid
            self.grid_color = Color(0.2, 0.4, 0.6, 0.08)
            self.grid_lines = [Line(points=[0, 0, 1, 1], width=1) for _ in range(5)]

            # Background stars
            self.star_colors = [Color(1, 1, 1, 0.7) for _ in range(35)]
            self.star_shapes = [
                Ellipse(size=(s["size"], s["size"])) for s in self.stars
            ]
            self.star_streaks = [Line(points=[0, 0, 0, 0], width=1.2) for _ in range(35)]

            # Rising trail glow & curve
            self.trail_glow = Color(1, 0.82, 0.25, 0.25)
            self.line_glow = Line(points=[], width=9)
            self.trail_color = Color(1, 0.82, 0.25, 1)
            self.line_curve = Line(points=[], width=3.2)

            # Spark particles
            self.spark_colors = [Color(1, 0.8, 0.2, 0) for _ in range(25)]
            self.spark_dots = [Ellipse(size=(3, 3)) for _ in range(25)]

            # --- Animated Rocket Container ---
            PushMatrix()
            self.trans = Translate(0, 0)
            self.rot = Rotate(angle=30, origin=(0, 0))

            # Thruster flame (drawn behind rocket)
            self.flame_outer_color = Color(1, 0.45, 0.1, 0.9)
            self.flame_outer = Triangle(points=[-17, -8, -35, 0, -17, 8])
            self.flame_inner_color = Color(1, 0.95, 0.4, 1)
            self.flame_inner = Triangle(points=[-17, -4, -26, 0, -17, 4])

            # Rocket engine nozzle
            self.nozzle_color = Color(0.22, 0.24, 0.3, 1)
            self.nozzle = RoundedRectangle(pos=(-23, -6), size=(7, 12), radius=[2])

            # Stabilizer fins (top & bottom)
            self.fin_color = Color(0.85, 0.2, 0.25, 1)
            self.top_fin = Triangle(points=[-15, 9, 0, 9, -17, 21])
            self.bot_fin = Triangle(points=[-15, -9, 0, -9, -17, -21])

            # Fuselage (main body)
            self.hull_color = Color(0.92, 0.94, 0.98, 1)
            self.hull = RoundedRectangle(
                pos=(-16, -10), size=(32, 20), radius=[3, 10, 10, 3]
            )

            # Aerodynamic nose cone
            self.nose_color = Color(0.88, 0.2, 0.25, 1)
            self.nose = Triangle(points=[15, -10, 36, 0, 15, 10])

            # Cockpit porthole (window)
            self.window_color = Color(0.2, 0.8, 1, 0.95)
            self.window = Ellipse(pos=(-1, -6), size=(12, 12))
            self.specular_color = Color(1, 1, 1, 0.85)
            self.specular = Ellipse(pos=(4, -1.5), size=(3.5, 3.5))

            PopMatrix()

            # Explosion shockwave on crash
            self.explosion_color = Color(1, 0.3, 0.1, 0)
            self.explosion_ring = Line(circle=(0, 0, 2), width=3)

        self.anim_event = None
        self.bind(pos=self.redraw, size=self.redraw)

    def start_animation(self):
        if self.anim_event is None:
            self.anim_event = Clock.schedule_interval(self.update_animation, 0.033)

    def stop_animation(self):
        if self.anim_event is not None:
            self.anim_event.cancel()
            self.anim_event = None

    def update_animation(self, dt):
        self.anim_time += dt
        w, h = self.width, self.height
        x0, y0 = self.x, self.y

        if w <= 10 or h <= 10:
            return

        # Speed factor based on flight state
        speed_factor = 1.0
        if self.is_flying and not self.crashed:
            speed_factor = max(1.5, min(6.0, len(self.points) * 0.15 + 1.5))

        # Update cosmic stars
        for i, s in enumerate(self.stars):
            if self.is_flying and not self.crashed:
                s["rx"] -= s["speed"] * speed_factor * dt * 0.25
                s["ry"] -= s["speed"] * speed_factor * dt * 0.12
                if s["rx"] < 0:
                    s["rx"] += 1.0
                    s["ry"] = random.random()
                if s["ry"] < 0:
                    s["ry"] += 1.0
            else:
                # Gentle idle drift
                s["rx"] -= 0.01 * dt
                if s["rx"] < 0:
                    s["rx"] += 1.0

            sx = x0 + s["rx"] * w
            sy = y0 + s["ry"] * h
            tw = (math.sin(self.anim_time * s["twinkle_speed"] + s["phase"]) + 1) * 0.5
            alpha = 0.3 + 0.6 * tw
            self.star_colors[i].a = alpha
            self.star_shapes[i].pos = (sx, sy)

            # High-speed streak effect
            if self.is_flying and not self.crashed and speed_factor > 2.0:
                streak_len = speed_factor * 3.5
                self.star_streaks[i].points = [sx, sy, sx + streak_len, sy + streak_len * 0.4]
            else:
                self.star_streaks[i].points = [0, 0, 0, 0]

        # Update thruster flame pulse & sparks
        if not self.crashed:
            flame_pulse = math.sin(self.anim_time * 26) * 4
            flame_len = 18 + flame_pulse + (speed_factor * 2.5)

            if self.cashed_out:
                self.flame_outer_color.rgba = (0.2, 0.9, 0.4, 0.9)
                self.flame_inner_color.rgba = (0.7, 1, 0.8, 1)
            else:
                self.flame_outer_color.rgba = (1, 0.45, 0.1, 0.9)
                self.flame_inner_color.rgba = (1, 0.95, 0.4, 1)

            self.flame_outer.points = [-17, -8, -17 - flame_len, 0, -17, 8]
            self.flame_inner.points = [
                -17,
                -4,
                -17 - flame_len * 0.6,
                0,
                -17,
                4,
            ]

            # Idle hover when waiting on launchpad
            if not self.is_flying:
                hover_y = math.sin(self.anim_time * 2.8) * 3.5
                self.trans.xy = (self.rocket_pos[0], self.rocket_pos[1] + hover_y)
                self.rot.angle = self.rocket_angle + math.sin(self.anim_time * 1.5) * 2.0

            # Emit sparks during flight
            if self.is_flying and random.random() < 0.6:
                angle_rad = math.radians(self.rocket_angle)
                cos_a = math.cos(angle_rad)
                sin_a = math.sin(angle_rad)
                # Tail position in world coordinates
                tail_x = self.rocket_pos[0] - 22 * cos_a
                tail_y = self.rocket_pos[1] - 22 * sin_a
                vx = -cos_a * random.uniform(40, 100) + random.uniform(-15, 15)
                vy = -sin_a * random.uniform(40, 100) + random.uniform(-15, 15)
                self.sparks.append([tail_x, tail_y, vx, vy, 0.4, 0.4])

        # Update sparks
        surviving_sparks = []
        for spark in self.sparks:
            spark[4] -= dt
            if spark[4] > 0:
                spark[0] += spark[2] * dt
                spark[1] += spark[3] * dt
                surviving_sparks.append(spark)
        self.sparks = surviving_sparks[:25]

        for idx, dot in enumerate(self.spark_dots):
            if idx < len(self.sparks):
                sp = self.sparks[idx]
                dot.pos = (sp[0] - 1.5, sp[1] - 1.5)
                self.spark_colors[idx].a = max(0.0, sp[4] / sp[5])
            else:
                self.spark_colors[idx].a = 0

        # Update explosion if active
        if self.explosion_active:
            self.explosion_r += dt * 90
            self.explosion_alpha = max(0.0, self.explosion_alpha - dt * 1.5)
            self.explosion_color.rgba = (1, 0.35, 0.1, self.explosion_alpha)
            self.explosion_ring.circle = (
                self.rocket_pos[0],
                self.rocket_pos[1],
                self.explosion_r,
            )
            if self.explosion_alpha <= 0:
                self.explosion_active = False

    def redraw(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        w, h = self.width, self.height
        x0, y0 = self.x, self.y

        # Update radar grid
        for i in range(5):
            gy = y0 + (h / 5) * (i + 1)
            self.grid_lines[i].points = [x0 + 10, gy, x0 + w - 10, gy]

        self.update_curve(self.curve_progress)

    def update_curve(self, progress):
        self.curve_progress = progress
        x0 = self.x + 24
        y0 = self.y + 24
        avail_w = self.width - 48
        avail_h = self.height - 48

        if not self.points or len(self.points) < 2:
            tip_x = x0 + 16
            tip_y = y0 + 16
            self.line_curve.points = [x0 + 4, y0 + 8, tip_x, tip_y]
            self.line_glow.points = [x0 + 4, y0 + 8, tip_x, tip_y]
            self.rocket_pos = (tip_x, tip_y)
            self.rocket_angle = 35.0
            self.trans.xy = (tip_x, tip_y)
            self.rot.angle = self.rocket_angle
            return

        current_mult = self.points[-1]
        max_displayed = max(2.0, current_mult * 1.15)

        pts = []
        for val in self.points:
            x_prog = 1.0 - math.exp(-0.85 * (val - 1.0))
            px = x0 + 16 + x_prog * (avail_w * 0.78)
            y_prog = min(1.0, (val - 1.0) / (max_displayed - 1.0))
            py = y0 + 16 + y_prog * (avail_h * 0.76)
            pts.extend([px, py])

        self.line_curve.points = pts
        self.line_glow.points = pts

        if len(pts) >= 2:
            tip_x, tip_y = pts[-2], pts[-1]
            self.rocket_pos = (tip_x, tip_y)

            # Compute angle tangent from previous curve point
            if len(pts) >= 4:
                prev_x, prev_y = pts[-4], pts[-3]
                dx = tip_x - prev_x
                dy = tip_y - prev_y
                target_angle = math.degrees(math.atan2(dy, dx))
            else:
                target_angle = 35.0

            # Smooth angle transition
            self.rocket_angle += (target_angle - self.rocket_angle) * 0.4
            self.trans.xy = (tip_x, tip_y)
            self.rot.angle = self.rocket_angle

    def set_crashed(self):
        self.crashed = True
        self.is_flying = False
        self.trail_color.rgba = (0.9, 0.2, 0.2, 1)
        self.trail_glow.rgba = (0.9, 0.1, 0.1, 0.35)

        # Hide rocket and trigger explosion shockwave
        self.hull_color.a = 0
        self.nose_color.a = 0
        self.fin_color.a = 0
        self.window_color.a = 0
        self.flame_outer_color.a = 0
        self.flame_inner_color.a = 0
        self.nozzle_color.a = 0
        self.specular_color.a = 0

        self.explosion_active = True
        self.explosion_r = 6.0
        self.explosion_alpha = 1.0

    def set_cashed_out(self):
        self.cashed_out = True
        self.trail_color.rgba = (0.2, 0.9, 0.4, 1)
        self.trail_glow.rgba = (0.1, 0.9, 0.3, 0.35)

    def reset(self):
        self.points = [1.0]
        self.crashed = False
        self.cashed_out = False
        self.is_flying = False
        self.trail_color.rgba = GOLD
        self.trail_glow.rgba = (1, 0.82, 0.25, 0.25)

        # Restore rocket visibility
        self.hull_color.a = 1
        self.nose_color.a = 1
        self.fin_color.a = 1
        self.window_color.a = 1
        self.flame_outer_color.a = 0.9
        self.flame_inner_color.a = 1
        self.nozzle_color.a = 1
        self.specular_color.a = 0.85
        self.explosion_active = False
        self.explosion_color.a = 0
        self.redraw()


class CrashHistoryBadge(GLabel):
    def __init__(self, mult, **kwargs):
        super().__init__(text=f"{mult:.2f}x", **kwargs)
        self.font_size = 16
        self.size_hint = (None, None)
        self.size = (75, 34)
        color = GOLD if mult >= 2.0 else (SOFT_RED if mult < 1.5 else WHITE)
        self.color = color
        with self.canvas.before:
            Color(0.12, 0.16, 0.24, 0.95)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
            Color(1, 1, 1, 0.1)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 10), width=1)
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, 10)


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

        title = GLabel(text="CRASH РАКЕТА", font_size=36, color=GOLD, size_hint_y=0.08)
        root.add_widget(title)

        # History row
        self.history_row = BoxLayout(spacing=6, size_hint_y=0.05)
        root.add_widget(self.history_row)

        # Main graph display with animated flying rocket background
        self.graph = CrashGraph(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        graph_box = FloatLayout(size_hint_y=0.40)
        graph_box.add_widget(self.graph)

        self.mult_label = GLabel(
            text="1.00x",
            font_size=58,
            color=GOLD,
            pos_hint={"center_x": 0.5, "center_y": 0.55},
            size_hint=(None, None),
            outline_width=4,
            outline_color=(0, 0, 0, 1),
        )
        graph_box.add_widget(self.mult_label)
        root.add_widget(graph_box)

        self.message_label = MessageLabel(size_hint_y=0.09)
        root.add_widget(self.message_label)

        # Controls
        self.bet_button = RoundButton(btn_color=GRAY, size_hint_y=0.09)
        self.bet_button.font_size = 24
        self.bet_button.bind(on_release=self.change_bet)
        root.add_widget(self.bet_button)

        self.action_button = RoundButton(
            text="СТАРТ", btn_color=GREEN, size_hint_y=0.15
        )
        self.action_button.font_size = 32
        self.action_button.bind(on_release=self.on_action)
        root.add_widget(self.action_button)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.graph.start_animation()
        self.update_labels()
        self.refresh_history()
        self.message_label.color = WHITE
        self.message_label.text = "Сделай ставку и жми СТАРТ"
        self.graph.reset()
        self.mult_label.text = "1.00x"
        self.mult_label.color = GOLD

    def on_leave(self, *args):
        self.graph.stop_animation()
        if self.tick_event is not None:
            self.tick_event.cancel()
            self.tick_event = None

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
        self.graph.is_flying = True

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
