"""Rules of the city meta-game. No Kivy imports here, so it can be tested without a screen.

The idea: chips won in the casino are spent on building a Las Vegas strip.
Buildings earn chips every SECOND. The income piles up (even while the player is away,
up to CAP_HOURS of it) until the player collects it; landmarks are big one-time goals
that boost all income.
"""

import math
import random
import time

PLOT_COUNT = 12
MAX_LEVEL = 5
CAP_HOURS = 8  # how many hours of income can pile up before the player collects it
CAP_SECONDS = CAP_HOURS * 3600
COST_GROWTH = 2  # every next level costs this many times more
LANDMARK_BONUS = 0.10  # +10% income per landmark

# The player can never spend the last CITY_RESERVE chips on the city (equals START_BALANCE).
# Without it: spend everything -> the game refills 1000 chips for free -> spend again, forever.
CITY_RESERVE = 1000

# cost - price of level 1, income - chips per SECOND at level 1 (level N gives N times more)
# shape/width/height only change how the building is drawn
BUILDINGS = {
    "diner": {
        "name": "Закусочная",
        "cost": 1000,
        "income": 2,
        "color": (0.93, 0.5, 0.2, 1),
        "shape": "peak",
        "width": 0.8,
        "height": 0.26,
    },
    "motel": {
        "name": "Мотель",
        "cost": 3000,
        "income": 6,
        "color": (0.2, 0.62, 0.78, 1),
        "shape": "flat",
        "width": 0.84,
        "height": 0.3,
    },
    "bar": {
        "name": "Бар",
        "cost": 6000,
        "income": 12,
        "color": (0.75, 0.25, 0.7, 1),
        "shape": "peak",
        "width": 0.6,
        "height": 0.4,
    },
    "hotel": {
        "name": "Отель",
        "cost": 15000,
        "income": 28,
        "color": (0.28, 0.5, 0.92, 1),
        "shape": "spire",
        "width": 0.55,
        "height": 0.5,
    },
    "theater": {
        "name": "Театр",
        "cost": 40000,
        "income": 70,
        "color": (0.85, 0.2, 0.3, 1),
        "shape": "dome",
        "width": 0.78,
        "height": 0.4,
    },
}
BUILDING_ORDER = ["diner", "motel", "bar", "hotel", "theater"]

LANDMARKS = [
    {"id": "fountain", "name": "Фонтан", "cost": 25000, "symbol": "♨"},
    {"id": "wheel", "name": "Колесо обозрения", "cost": 150000, "symbol": "◎"},
    {"id": "sign", "name": "Неоновая вывеска", "cost": 500000, "symbol": "★"},
    {"id": "tower", "name": "Башня", "cost": 1500000, "symbol": "♜"},
    {"id": "resort", "name": "Мегакурорт", "cost": 5000000, "symbol": "♛"},
]

# (min score, title). Score = sum of all building levels + 10 per landmark
RANKS = [
    (0, "Пустырь"),
    (1, "Посёлок"),
    (10, "Городок"),
    (25, "Город"),
    (50, "Мегаполис"),
    (80, "Столица Вегаса"),
]


# ----- map geometry -----
# All numbers are in dp. The origin is the centre of the map, y goes up.
# The casino stands in the middle, the plots are around it: the first 8 are close
# (cheap to reach), the last 4 are on the far edges, so the player has to scroll for them.
#
# Everything below is plain maths (no Kivy, no Pillow), because two programs read it:
# make_city_map.py paints the ground picture from it, and city.py puts trees, lamps and
# cars on it. So the picture and the game can never disagree about where a road is.

MAP_W = 1200
MAP_H = 1200
CASINO_W = 240
CASINO_H = 200
PLOT_SIZE = 110
PLOT_OFFSETS = [
    (0, 210), (225, 0), (0, -210), (-225, 0),
    (225, 210), (225, -210), (-225, -210), (-225, 210),
    (0, 400), (430, 0), (0, -400), (-430, 0),
]
assert len(PLOT_OFFSETS) == PLOT_COUNT

ROAD_WIDTH = 26  # the two avenues
ROAD_X = [-112, 112]  # vertical avenues
ROAD_Y = [-105, 105]  # horizontal avenues
PAVE = 7  # pavement on each side of a paved road
RING_HALF = 525  # the ring road around the whole city is a rounded square this big
RING_RADIUS = 130  # roundness of its corners
RING_WIDTH = 24
SIDE_WIDTH = 20  # curved side roads
DIRT_WIDTH = 14
STREAM_WIDTH = 16
PLAZA_R = 156  # the paved square around the casino
DESERT_EDGE = 548  # beyond this (square distance from the centre) the land is desert

PARK = (-395, 445, 190, 120)  # centre x, centre y, width, height
PARKING = (425, -440, 150, 110)


def _spline(points, steps=10):
    """Smooth curve through the points (Catmull-Rom), the ends stay where they are."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t
                       + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                       + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3)
                for c in (0, 1)))
    out.append(tuple(points[-1]))
    return out


def rounded_square(half, radius, steps=14):
    """Closed path of a rounded square, clockwise (the top side goes left to right)."""
    c = half - radius
    pts = []
    for cx, cy, a0, a1 in ((c, c, 90, 0), (c, -c, 0, -90), (-c, -c, -90, -180), (-c, c, 180, 90)):
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return pts


def blob(cx, cy, rx, ry, seed, wobble=0.16, count=44):
    """An uneven oval (a lake, a patch of sand) as a list of points."""
    rng = random.Random(seed)
    phases = [(rng.uniform(0, 6.28), rng.uniform(0.5, 1.0)) for _ in range(3)]
    pts = []
    for i in range(count):
        a = 2 * math.pi * i / count
        f = 1.0
        for k, (ph, amp) in enumerate(phases):
            f += wobble * amp * math.sin((k + 2) * a + ph) / (k + 1.5)
        pts.append((cx + rx * f * math.cos(a), cy + ry * f * math.sin(a)))
    return pts


def _rotated(points):
    return [(-x, -y) for x, y in points]


# roads: kind, width (dp), points (a closed shape for the ring)
RING = rounded_square(RING_HALF, RING_RADIUS)
SIDE_ROAD_1 = _spline([(-112, 330), (-230, 365), (-320, 335), (-375, 260), (-380, 170), (-372, 105)])
SIDE_ROAD_2 = _rotated(SIDE_ROAD_1)
DIRT_ROAD = _spline([(-112, -330), (-200, -390), (-300, -350), (-380, -260), (-460, -300), (-525, -255)])
STREAM = _spline([(450, 345), (500, 322), (525, 300), (560, 285), (620, 280)])
BRIDGE_AT = (525, 300)  # where the stream crosses the ring road

ROADS = [
    {"id": "ring", "kind": "ring", "width": RING_WIDTH, "points": RING, "closed": True},
    {"id": "av_l", "kind": "avenue", "width": ROAD_WIDTH, "points": [(-112, -RING_HALF), (-112, RING_HALF)]},
    {"id": "av_r", "kind": "avenue", "width": ROAD_WIDTH, "points": [(112, -RING_HALF), (112, RING_HALF)]},
    {"id": "av_b", "kind": "avenue", "width": ROAD_WIDTH, "points": [(-RING_HALF, -105), (RING_HALF, -105)]},
    {"id": "av_t", "kind": "avenue", "width": ROAD_WIDTH, "points": [(-RING_HALF, 105), (RING_HALF, 105)]},
    {"id": "side1", "kind": "side", "width": SIDE_WIDTH, "points": SIDE_ROAD_1},
    {"id": "side2", "kind": "side", "width": SIDE_WIDTH, "points": SIDE_ROAD_2},
    {"id": "dirt", "kind": "dirt", "width": DIRT_WIDTH, "points": DIRT_ROAD},
]

LAKE = blob(385, 365, 85, 62, 5)
BEACH = blob(385, 365, 120, 94, 6, wobble=0.1)
DESERT_PATCH = blob(-410, -400, 270, 220, 9, wobble=0.2, count=60)

# animated traffic drives on the ring road, one lane each way
CAR_LANE = 6


def car_route(direction):
    """Closed path for cars: direction 1 = clockwise (inner lane), -1 = the other way."""
    half = RING_HALF - CAR_LANE * direction
    radius = max(10, RING_RADIUS - CAR_LANE * direction)
    pts = rounded_square(half, radius, steps=10)
    return pts if direction == 1 else pts[::-1]


class Route:
    """A closed path. at(distance) gives (x, y, heading in degrees)."""

    def __init__(self, points):
        self.points = list(points)
        self.lengths = []
        total = 0.0
        for i, (x0, y0) in enumerate(self.points):
            x1, y1 = self.points[(i + 1) % len(self.points)]
            total += math.hypot(x1 - x0, y1 - y0)
            self.lengths.append(total)
        self.total = total

    def at(self, distance):
        distance %= self.total
        lo, hi = 0, len(self.lengths) - 1
        while lo < hi:  # first segment that ends after `distance`
            mid = (lo + hi) // 2
            if self.lengths[mid] > distance:
                hi = mid
            else:
                lo = mid + 1
        x0, y0 = self.points[lo]
        x1, y1 = self.points[(lo + 1) % len(self.points)]
        start = self.lengths[lo - 1] if lo > 0 else 0.0
        seg = max(1e-9, self.lengths[lo] - start)
        t = (distance - start) / seg
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                math.degrees(math.atan2(y1 - y0, x1 - x0)))


# ----- little geometry helpers -----


def seg_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def path_distance(px, py, points, closed=False):
    best = 1e9
    n = len(points)
    for i in range(n if closed else n - 1):
        ax, ay = points[i]
        bx, by = points[(i + 1) % n]
        best = min(best, seg_distance(px, py, ax, ay, bx, by))
    return best


def in_polygon(px, py, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > py) != (y1 > py) and px < (x1 - x0) * (py - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def near_polygon(px, py, poly, margin):
    return in_polygon(px, py, poly) or path_distance(px, py, poly, closed=True) < margin


def in_rect(px, py, rect, margin=0):
    cx, cy, w, h = rect
    return abs(px - cx) < w / 2 + margin and abs(py - cy) < h / 2 + margin


def road_clearance(px, py, skip=None):
    """How far (dp) the point is from the edge of the nearest paved road or path."""
    best = 1e9
    for road in ROADS:
        if road["id"] == skip:
            continue
        reach = road["width"] / 2 + (0 if road["kind"] == "dirt" else PAVE)
        best = min(best, path_distance(px, py, road["points"], road.get("closed", False)) - reach)
    best = min(best, path_distance(px, py, STREAM) - STREAM_WIDTH / 2)
    return best


def in_desert(px, py):
    return max(abs(px), abs(py)) > DESERT_EDGE or (
        in_polygon(px, py, DESERT_PATCH) and not near_polygon(px, py, BEACH, 0))


def blocked(px, py, radius):
    """True if something of this radius can't stand here (a road, a plot, the lake...)."""
    if max(abs(px), abs(py)) > MAP_W / 2 - radius:
        return True
    if road_clearance(px, py) < radius + 3:
        return True
    if math.hypot(px, py) < PLAZA_R + radius:
        return True
    if in_rect(px, py, (0, 0, CASINO_W, CASINO_H), 30 + radius):
        return True
    for dx, dy in PLOT_OFFSETS:
        if in_rect(px, py, (dx, dy, PLOT_SIZE, PLOT_SIZE), 14 + radius):
            return True
    if near_polygon(px, py, LAKE, radius + 6):
        return True
    if in_rect(px, py, PARK, radius + 4) or in_rect(px, py, PARKING, radius + 12):
        return True
    return False


# ----- what stands on the map -----
# kind -> (width, height) in dp. The bottom of the picture stands slightly below the point.
DECOR_SIZE = {
    "round": (52, 52), "pine": (50, 56), "pink": (52, 52), "bush": (30, 30),
    "palm": (58, 76), "cactus": (30, 50), "barrel": (26, 26), "rock": (34, 26),
    "dry": (30, 24), "lamp": (18, 46), "bench": (36, 22), "umbrella": (40, 40),
    "billboard": (84, 76),
}


def _fixed_decor():
    items = []
    # street lamps on both pavements of every avenue
    for x in ROAD_X:
        for y in (-420, -300, -190, 190, 300, 420):
            for side in (-1, 1):
                items.append(("lamp", x + side * (ROAD_WIDTH / 2 + 5), y))
    for y in ROAD_Y:
        for x in (-440, -330, -210, 210, 330, 440):
            for side in (-1, 1):
                items.append(("lamp", x, y + side * (ROAD_WIDTH / 2 + 5)))
    # palm avenues along the vertical avenues
    for x in ROAD_X:
        for y in (-470, -400, -330, -260, -195, 195, 260, 330, 400, 470):
            for side in (-1, 1):
                items.append(("palm", x + side * 40, y + 12 * side))
    # the park, the lake, the parking
    cx, cy, w, h = PARK
    items += [("bench", cx - 88, cy - 4), ("bench", cx + 88, cy - 4),
              ("round", cx - 55, cy + 32), ("pink", cx + 72, cy + 38),
              ("pink", cx - 72, cy - 40), ("round", cx + 74, cy - 38)]
    items += [("umbrella", 285, 380), ("umbrella", 398, 448), ("umbrella", 352, 284),
              ("palm", 262, 345), ("palm", 305, 440), ("palm", 470, 420), ("palm", 440, 285)]
    items += [("billboard", 303, -452), ("lamp", 350, -380), ("lamp", 500, -380)]
    return items


def decor_spots(seed=7):
    """Everything that stands on the ground: (kind, x, y). Sorted so lower things come last."""
    rng = random.Random(seed)
    items = []
    for kind, x, y in _fixed_decor():
        if kind == "lamp":
            ok = (not (abs(x) > MAP_W / 2 or abs(y) > MAP_H / 2) and not math.hypot(x, y) < PLAZA_R + 6
                  and road_clearance(x, y) > -PAVE - 4)
            parent = next((r["id"] for r in ROADS if r["kind"] == "avenue"
                           and path_distance(x, y, r["points"]) < ROAD_WIDTH / 2 + PAVE + 1), None)
            ok = ok and parent is not None and road_clearance(x, y, skip=parent) > 8
            if not (ok and not any(in_rect(x, y, (dx, dy, PLOT_SIZE, PLOT_SIZE), 6) for dx, dy in PLOT_OFFSETS)):
                continue
        elif kind == "palm":
            if (math.hypot(x, y) < PLAZA_R + 24 or road_clearance(x, y) < 14
                    or any(in_rect(x, y, (dx, dy, PLOT_SIZE, PLOT_SIZE), 8) for dx, dy in PLOT_OFFSETS)):
                continue
        items.append((kind, x, y))

    taken = [(x, y, 16) for _, x, y in items]

    def free(x, y, r):
        return (not blocked(x, y, r)
                and not any((x - tx) ** 2 + (y - ty) ** 2 < (r + tr) ** 2 for tx, ty, tr in taken))

    half = MAP_W / 2
    target = {"green": 62, "desert": 60}
    counts = {"green": 0, "desert": 0}
    attempts = 0
    while attempts < 6000 and (counts["green"] < target["green"] or counts["desert"] < target["desert"]):
        attempts += 1
        x = rng.uniform(-half + 14, half - 14)
        y = rng.uniform(-half + 14, half - 14)
        if near_polygon(x, y, BEACH, 0):
            continue
        zone = "desert" if in_desert(x, y) else "green"
        if counts[zone] >= target[zone]:
            continue
        if zone == "desert":
            kind = rng.choice(["cactus", "cactus", "barrel", "rock", "rock", "dry", "dry"])
            r = 11
        else:
            kind = rng.choice(["round", "pine", "pink", "bush", "bush", "round"])
            r = 9 if kind == "bush" else rng.uniform(11, 16)
        if free(x, y, r):
            items.append((kind, x, y))
            taken.append((x, y, r))
            counts[zone] += 1
    items.sort(key=lambda item: -item[2])
    return items


def clamp_offset(offset, view, world):
    """Where the map's lower edge may be on one axis, so the player never scrolls past the map.

    If the map is smaller than the screen it just stays centred.
    """
    if view >= world:
        return (view - world) / 2
    return max(view - world, min(0, offset))


def centered_offset(view, world):
    return (view - world) / 2


# ----- save data -----


def new_city():
    return {
        "plots": [None] * PLOT_COUNT,
        "landmarks": [],
        "stored": 0.0,  # income already settled, waiting to be collected
        "last_collect": 0.0,  # moment from which income keeps piling up
    }


def sanitize_city(raw):
    """Turns whatever was in the save file into a valid city (old saves have no city at all)."""
    city = new_city()
    if not isinstance(raw, dict):
        return city

    plots = raw.get("plots")
    if isinstance(plots, list):
        for index in range(min(PLOT_COUNT, len(plots))):
            plot = plots[index]
            if not isinstance(plot, dict):
                continue
            type_id = plot.get("type")
            try:
                level = int(plot.get("level", 1))
            except (TypeError, ValueError):
                continue
            if type_id in BUILDINGS:
                city["plots"][index] = {
                    "type": type_id,
                    "level": max(1, min(MAX_LEVEL, level)),
                }

    known = [item["id"] for item in LANDMARKS]
    landmarks = raw.get("landmarks")
    if isinstance(landmarks, list):
        for landmark_id in landmarks:
            if landmark_id in known and landmark_id not in city["landmarks"]:
                city["landmarks"].append(landmark_id)

    for key in ("stored", "last_collect"):
        try:
            city[key] = max(0.0, float(raw.get(key, 0)))
        except (TypeError, ValueError):
            city[key] = 0.0
    return city


# ----- numbers -----


def upgrade_cost(type_id, level):
    """Price of going from `level` to `level + 1`. Level 0 means building from scratch."""
    return BUILDINGS[type_id]["cost"] * COST_GROWTH**level


def building_income(type_id, level):
    return BUILDINGS[type_id]["income"] * level


def income_multiplier(city):
    return 1 + LANDMARK_BONUS * len(city["landmarks"])


def income_per_second(city):
    total = 0
    for plot in city["plots"]:
        if plot is not None:
            total += building_income(plot["type"], plot["level"])
    return total * income_multiplier(city)


def capacity(city):
    return income_per_second(city) * CAP_SECONDS


def pending(city, now=None):
    """How many chips are waiting to be collected right now (a float)."""
    if now is None:
        now = time.time()
    rate = income_per_second(city)
    if rate <= 0:
        return 0.0
    elapsed = 0.0
    if city["last_collect"] > 0:
        elapsed = max(0.0, now - city["last_collect"])  # clock moved back = 0, not negative
    return min(capacity(city), city["stored"] + rate * elapsed)


def settle(city, now=None):
    """Saves the piled-up income. Must be called before anything changes the income rate."""
    if now is None:
        now = time.time()
    city["stored"] = pending(city, now)
    city["last_collect"] = now


def score(city):
    total = 10 * len(city["landmarks"])
    for plot in city["plots"]:
        if plot is not None:
            total += plot["level"]
    return total


def rank_name(city):
    value = score(city)
    name = RANKS[0][1]
    for min_score, title in RANKS:
        if value >= min_score:
            name = title
    return name


def can_afford(balance, cost):
    return balance - cost >= CITY_RESERVE


# ----- actions (every one returns a result code, "ok" means it worked) -----


def buy_building(wallet, index, type_id, now=None):
    city = wallet.city
    if type_id not in BUILDINGS or not 0 <= index < PLOT_COUNT:
        return "unknown"
    if city["plots"][index] is not None:
        return "occupied"
    cost = upgrade_cost(type_id, 0)
    if not can_afford(wallet.balance, cost):
        return "reserve"
    settle(city, now)
    city["plots"][index] = {"type": type_id, "level": 1}
    wallet.take(cost)  # saves the wallet together with the city
    return "ok"


def upgrade_building(wallet, index, now=None):
    city = wallet.city
    if not 0 <= index < PLOT_COUNT or city["plots"][index] is None:
        return "unknown"
    plot = city["plots"][index]
    if plot["level"] >= MAX_LEVEL:
        return "max"
    cost = upgrade_cost(plot["type"], plot["level"])
    if not can_afford(wallet.balance, cost):
        return "reserve"
    settle(city, now)
    plot["level"] += 1
    wallet.take(cost)
    return "ok"


def buy_landmark(wallet, landmark_id, now=None):
    city = wallet.city
    item = next((x for x in LANDMARKS if x["id"] == landmark_id), None)
    if item is None:
        return "unknown"
    if landmark_id in city["landmarks"]:
        return "owned"
    if not can_afford(wallet.balance, item["cost"]):
        return "reserve"
    settle(city, now)
    city["landmarks"].append(landmark_id)
    wallet.take(item["cost"])
    return "ok"


def collect(wallet, now=None):
    """Moves the piled-up income to the balance. Returns how many chips were collected."""
    city = wallet.city
    if now is None:
        now = time.time()
    total = pending(city, now)
    amount = int(total)
    city["stored"] = total - amount  # the fraction stays, nothing is lost
    city["last_collect"] = now
    if amount > 0:
        wallet.add(amount)  # saves the wallet together with the city
    else:
        wallet.save()
    return amount
