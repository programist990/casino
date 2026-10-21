import sys, types, json, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# stub kivy so common.py (Wallet) can be imported without a display
class Any:
    def __init__(self,*a,**k): pass
    def __getattr__(self,n): return Any()
    def __call__(self,*a,**k): return Any()
def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m
for name in ["kivy","kivy.animation","kivy.core","kivy.core.audio","kivy.graphics","kivy.graphics.texture",
             "kivy.metrics","kivy.properties","kivy.uix","kivy.uix.boxlayout","kivy.uix.button","kivy.uix.image","kivy.uix.label","kivy.utils"]:
    stub(name)
sys.modules["kivy.animation"].Animation = Any
sys.modules["kivy.core.audio"].SoundLoader = Any
for n in ["Color","Rectangle","RoundedRectangle"]: setattr(sys.modules["kivy.graphics"], n, Any)
sys.modules["kivy.graphics.texture"].Texture = Any
sys.modules["kivy.metrics"].dp = lambda x: x
sys.modules["kivy.properties"].NumericProperty = lambda *a, **k: 0
sys.modules["kivy.uix.boxlayout"].BoxLayout = type("BoxLayout",(),{"__init__":lambda s,**k:None})
sys.modules["kivy.uix.button"].Button = type("Button",(),{})
sys.modules["kivy.uix.image"].Image = type("Image",(),{})
sys.modules["kivy.uix.label"].Label = type("Label",(),{})
sys.modules["kivy.utils"].platform = "linux"

import city_data as cd
from common import Wallet

d = tempfile.mkdtemp(); path = os.path.join(d, "save.json")
w = Wallet(path)
w.balance = 1000  # the game may start with more (test money): the rules below need exactly the reserve
assert w.city["plots"] == [None]*12

# reserve rule: cannot spend the last 1000
assert cd.buy_building(w, 0, "diner") == "reserve" and w.balance == 1000
w.balance = 2000
assert cd.buy_building(w, 0, "diner", now=1000.0) == "ok" and w.balance == 1000
assert cd.buy_building(w, 0, "motel", now=1000.0) == "occupied"
assert cd.buy_building(w, 1, "diner", now=1000.0) == "reserve"   # balance 1000, would drop below reserve

# income piles up: diner lvl1 = 25/h
assert cd.income_per_second(w.city) == 2          # a diner earns 2 chips every second
assert abs(cd.pending(w.city, 1000.0 + 10) - 20) < 1e-9
# cap at 8h
assert abs(cd.pending(w.city, 1000.0 + 3600*100) - 2*3600*8) < 1e-9
# clock moved back -> no negative / no change
assert cd.pending(w.city, 500.0) == 0

# upgrade settles the old rate first, then uses the new one
w.balance = 5000
assert cd.upgrade_building(w, 0, now=1000.0 + 60) == "ok"     # cost 1000*2^1 = 2000
assert w.balance == 3000 and w.city["plots"][0]["level"] == 2
assert abs(w.city["stored"] - 120) < 1e-9                       # 60 s * 2
assert cd.income_per_second(w.city) == 4
assert abs(cd.pending(w.city, 1000.0 + 120) - 360) < 1e-9       # 120 settled + 60 s * 4

# collect keeps the fraction and pays out an int
before = w.balance
got = cd.collect(w, now=1000.0 + 120 + 30)                      # 120 + 60*4 + 30*4 = 480
assert got == 480 and w.balance == before + 480
assert cd.collect(w, now=1000.0 + 120 + 30) == 0

# max level
for _ in range(10):
    w.balance = 10**9
    r = cd.upgrade_building(w, 0, now=5000.0)
    if r != "ok": break
assert r == "max" and w.city["plots"][0]["level"] == 5

# landmarks: +10% each, one time only
w.balance = 10**9
assert cd.buy_landmark(w, "fountain", now=6000.0) == "ok"
assert cd.buy_landmark(w, "fountain", now=6000.0) == "owned"
assert abs(cd.income_per_second(w.city) - 2*5*1.1) < 1e-9
assert cd.buy_landmark(w, "nope") == "unknown"

# the exploit is closed: spending everything and getting refilled is impossible
w2 = Wallet(os.path.join(d, "x.json")); w2.balance = cd.CITY_RESERVE
for t in cd.BUILDING_ORDER:
    assert cd.buy_building(w2, 0, t) == "reserve"
assert w2.balance == cd.CITY_RESERVE

# save -> load round trip
w.save()
w3 = Wallet(path)
assert w3.city == w.city and w3.balance == w.balance

# old save without "city" and garbage in "city" both load fine
json.dump({"balance": 777, "last_daily": 0, "stats": {}}, open(path, "w"))
assert Wallet(path).city == cd.new_city() and Wallet(path).balance == 777
json.dump({"balance": 5, "city": {"plots": [{"type":"zzz","level":99}, {"type":"bar","level":99}, 5, None],
           "landmarks": ["fountain","fountain","bogus"], "stored": "abc"}}, open(path, "w"))
c = Wallet(path).city
assert c["plots"][0] is None and c["plots"][1] == {"type":"bar","level":5}
assert c["landmarks"] == ["fountain"] and c["stored"] == 0.0 and len(c["plots"]) == 12

# ranks
assert cd.rank_name(cd.new_city()) == "Пустырь"
print("all city tests passed; max-level total costs:",
      {t: sum(cd.upgrade_cost(t, l) for l in range(5)) for t in cd.BUILDING_ORDER})

# ---- map geometry: the picture and the game agree ----
import math
spots = cd.decor_spots()
assert len(spots) > 150 and all(k in cd.DECOR_SIZE for k, _, _ in spots)
assert cd.decor_spots() == spots                                  # same map every time
for kind, x, y in spots:
    assert abs(x) < 600 and abs(y) < 600
    assert not (kind in ("cactus", "barrel", "rock", "dry", "round", "pine", "pink", "bush")
                and cd.in_polygon(x, y, cd.LAKE))               # nothing grows in the lake
    for dx, dy in cd.PLOT_OFFSETS:                                # nothing stands on a building plot
        if kind in ("round", "pine", "pink", "bush", "cactus", "barrel", "rock", "dry"):
            assert not cd.in_rect(x, y, (dx, dy, cd.PLOT_SIZE, cd.PLOT_SIZE))
for kind, x, y in cd.decor_spots():
    if kind in ("round", "pine", "pink", "bush", "cactus", "barrel", "rock", "dry"):
        assert cd.road_clearance(x, y) > 0                        # trees never grow on a road
route = cd.Route(cd.car_route(1))
x0, y0, _ = route.at(0)
x1, y1, _ = route.at(route.total)
assert abs(x0 - x1) < 1e-6 and abs(y0 - y1) < 1e-6              # the route is a closed loop
for d_ in range(0, int(route.total), 25):
    x, y, _ = route.at(d_)
    assert cd.path_distance(x, y, cd.RING, True) < cd.RING_WIDTH / 2   # cars stay on the road
print("geometry tests passed;", len(spots), "things on the map")

# ---- vibration: harmless on a computer, and Sfx.play never breaks because of it ----
from common import Haptics, Sfx
Haptics.buzz("win"); Sfx.play("win"); Sfx.play("click", volume=0.5)
assert Haptics._failed is True and Haptics._vibrator is None
print("haptics tests passed")

# ---- inspections and guards ----
import random as _random
w4 = Wallet(os.path.join(d, "insp.json")); w4.balance = 100000
assert w4.city["guards"] == 0 and w4.city["inspections"] == {"passed": 0, "failed": 0, "fines": 0}
assert not cd.inspections_allowed(w4.city)                       # nothing built yet = no inspectors
w4.city["plots"][0] = {"type": "diner", "level": 1}
assert cd.inspections_allowed(w4.city)

# fine: 8% of the balance, min 300, guards cut it, never more than half of the chips
assert cd.inspection_fine(w4) == 8000
w4.balance = 1000; assert cd.inspection_fine(w4) == 300
w4.balance = 400;  assert cd.inspection_fine(w4) == 200          # half of 400
w4.balance = 100000; w4.city["guards"] = 2
assert cd.inspection_fine(w4) == int(8000 * 0.7)
w4.city["guards"] = 0

# failing writes the fine off and records it; passing costs nothing
before = w4.balance
assert cd.finish_inspection(w4, False) == 8000 and w4.balance == before - 8000
assert cd.finish_inspection(w4, True) == 0 and w4.balance == before - 8000
assert w4.city["inspections"] == {"passed": 1, "failed": 1, "fines": 8000}

# hiring: price list, reserve rule, maximum
w5 = Wallet(os.path.join(d, "guards.json")); w5.balance = 5500
assert cd.hire_guard(w5) == "reserve"                            # 5000 would leave 500 < reserve
w5.balance = 6000
assert cd.hire_guard(w5) == "ok" and w5.balance == 1000 and w5.city["guards"] == 1
assert cd.hire_guard(w5) == "reserve"
w5.balance = 10**7
assert cd.hire_guard(w5) == "ok" and cd.hire_guard(w5) == "ok" and cd.hire_guard(w5) == "max"
assert w5.city["guards"] == cd.MAX_GUARDS and cd.guard_cost(3) is None
w5.save(); assert Wallet(os.path.join(d, "guards.json")).city["guards"] == 3   # saved
# garbage in the save file
json.dump({"balance": 5, "city": {"guards": 99, "inspections": {"passed": -4, "failed": "x", "fines": 7}}}, open(path, "w"))
c = Wallet(path).city
assert c["guards"] == 3 and c["inspections"] == {"passed": 0, "failed": 0, "fines": 7}

# the mini-game: the zone grows with guards, the slider covers the whole bar
assert cd.zone_width(0) < cd.zone_width(1) < cd.zone_width(3) <= cd.ZONE_MAX
assert abs(cd.slider_at(0, 1.5) - 0) < 1e-9 and abs(cd.slider_at(0.75, 1.5) - 1) < 1e-9
assert abs(cd.slider_at(1.5, 1.5) - 0) < 1e-9
assert all(0 <= cd.slider_at(t / 10, 1.3) <= 1 for t in range(200))
assert cd.slider_period(2) < cd.slider_period(0)
rng = _random.Random(1)
for g in range(4):
    for _ in range(200):
        wz = cd.zone_width(g); cz = cd.random_zone_center(wz, rng)
        assert 0 <= cz - wz / 2 and cz + wz / 2 <= 1
assert cd.in_zone(0.5, 0.5, 0.1) and not cd.in_zone(0.7, 0.5, 0.1)
# without guards pure luck passes ~ rarely, with 3 guards much more often
def luck(g, n=4000):
    r = _random.Random(5); ok = 0
    for _ in range(n):
        hits = 0
        for a in range(cd.ATTEMPTS):
            wz = cd.zone_width(g); cz = cd.random_zone_center(wz, r)
            hits += cd.in_zone(r.random(), cz, wz)
        ok += hits >= cd.HITS_TO_PASS
    return ok / n
print("pass by luck: 0 guards %.0f%%, 3 guards %.0f%%" % (100 * luck(0), 100 * luck(3)))
assert luck(0) < luck(3)
assert all(cd.INSPECTION_MIN_GAP <= cd.next_inspection_gap(rng) <= cd.INSPECTION_MAX_GAP for _ in range(100))

# people: routes start at the edge, end at the door, stay out of the casino and off the plots
for r_ in cd.ARRIVAL_ROUTES:
    assert r_[-1] == cd.DOOR and cd.route_length(r_) > 300
    L = cd.route_length(r_)
    for step in range(0, int(L) + 1, 6):
        x, y = cd.point_on_route(r_, step)
        assert not cd.in_rect(x, y, (0, 0, cd.CASINO_W, cd.CASINO_H), -2) or (abs(x) < 25 and y < -90)
        for dx, dy in cd.PLOT_OFFSETS:
            assert not cd.in_rect(x, y, (dx, dy, cd.PLOT_SIZE, cd.PLOT_SIZE))
        assert abs(x) < cd.MAP_W / 2 and abs(y) < cd.MAP_H / 2
for a_, b_ in cd.STROLL_PATHS:
    L = cd.route_length([a_, b_])
    for step in range(0, int(L) + 1, 6):
        x, y = cd.point_on_route([a_, b_], step)
        assert not cd.in_rect(x, y, (0, 0, cd.CASINO_W, cd.CASINO_H), 6)
        assert math.hypot(x, y) > cd.PLAZA_R - 2
        for dx, dy in cd.PLOT_OFFSETS:
            assert not cd.in_rect(x, y, (dx, dy, cd.PLOT_SIZE, cd.PLOT_SIZE))
assert cd.point_on_route(cd.ARRIVAL_ROUTES[0], -5) == cd.ARRIVAL_ROUTES[0][0]
assert cd.point_on_route(cd.ARRIVAL_ROUTES[0], 10**6) == cd.DOOR
print("inspection tests passed;", len(cd.STROLL_PATHS), "stroll paths")
