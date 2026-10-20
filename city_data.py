"""Rules of the city meta-game. No Kivy imports here, so it can be tested without a screen.

The idea: chips won in the casino are spent on building a Las Vegas strip.
Buildings pay a small income that piles up while the player is away (up to CAP_HOURS),
landmarks are big one-time goals that boost all income.
"""

import random
import time

PLOT_COUNT = 12
MAX_LEVEL = 5
CAP_HOURS = 8  # how many hours of income can pile up before the player collects it
COST_GROWTH = 2  # every next level costs this many times more
LANDMARK_BONUS = 0.10  # +10% income per landmark

# The player can never spend the last CITY_RESERVE chips on the city (equals START_BALANCE).
# Without it: spend everything -> the game refills 1000 chips for free -> spend again, forever.
CITY_RESERVE = 1000

# cost - price of level 1, income - chips per hour at level 1 (level N gives N times more)
# shape/width/height only change how the building is drawn
BUILDINGS = {
    "diner": {
        "name": "Закусочная",
        "cost": 1000,
        "income": 25,
        "color": (0.93, 0.5, 0.2, 1),
        "shape": "peak",
        "width": 0.8,
        "height": 0.26,
    },
    "motel": {
        "name": "Мотель",
        "cost": 3000,
        "income": 70,
        "color": (0.2, 0.62, 0.78, 1),
        "shape": "flat",
        "width": 0.84,
        "height": 0.3,
    },
    "bar": {
        "name": "Бар",
        "cost": 6000,
        "income": 140,
        "color": (0.75, 0.25, 0.7, 1),
        "shape": "peak",
        "width": 0.6,
        "height": 0.4,
    },
    "hotel": {
        "name": "Отель",
        "cost": 15000,
        "income": 330,
        "color": (0.28, 0.5, 0.92, 1),
        "shape": "spire",
        "width": 0.55,
        "height": 0.5,
    },
    "theater": {
        "name": "Театр",
        "cost": 40000,
        "income": 850,
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
ROAD_WIDTH = 26
ROAD_X = [-112, 112]  # vertical roads
ROAD_Y = [-105, 105]  # horizontal roads
assert len(PLOT_OFFSETS) == PLOT_COUNT


def clamp_offset(offset, view, world):
    """Where the map's lower edge may be on one axis, so the player never scrolls past the map.

    If the map is smaller than the screen it just stays centred.
    """
    if view >= world:
        return (view - world) / 2
    return max(view - world, min(0, offset))


def centered_offset(view, world):
    return (view - world) / 2


def tree_spots(count=90, seed=7):
    """Fixed random trees (x, y, radius), never on roads, plots or the casino square."""
    rng = random.Random(seed)
    half_w = MAP_W / 2
    half_h = MAP_H / 2
    keep_out = [(0, 0, CASINO_W / 2 + 40, CASINO_H / 2 + 40)]
    for dx, dy in PLOT_OFFSETS:
        keep_out.append((dx, dy, PLOT_SIZE / 2 + 14, PLOT_SIZE / 2 + 14))

    spots = []
    attempts = 0
    while len(spots) < count and attempts < count * 60:
        attempts += 1
        radius = rng.uniform(9, 17)
        x = rng.uniform(-half_w + radius, half_w - radius)
        y = rng.uniform(-half_h + radius, half_h - radius)
        if any(abs(x - road) < ROAD_WIDTH / 2 + radius + 4 for road in ROAD_X):
            continue
        if any(abs(y - road) < ROAD_WIDTH / 2 + radius + 4 for road in ROAD_Y):
            continue
        if any(abs(x - cx) < hw + radius and abs(y - cy) < hh + radius for cx, cy, hw, hh in keep_out):
            continue
        if any((x - tx) ** 2 + (y - ty) ** 2 < (radius + tr) ** 2 for tx, ty, tr in spots):
            continue
        spots.append((x, y, radius))
    return spots


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


def income_per_hour(city):
    total = 0
    for plot in city["plots"]:
        if plot is not None:
            total += building_income(plot["type"], plot["level"])
    return total * income_multiplier(city)


def capacity(city):
    return income_per_hour(city) * CAP_HOURS


def pending(city, now=None):
    """How many chips are waiting to be collected right now (a float)."""
    if now is None:
        now = time.time()
    rate = income_per_hour(city)
    if rate <= 0:
        return 0.0
    elapsed = 0.0
    if city["last_collect"] > 0:
        elapsed = max(0.0, now - city["last_collect"])  # clock moved back = 0, not negative
    return min(capacity(city), city["stored"] + rate * elapsed / 3600)


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
