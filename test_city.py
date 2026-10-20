import sys, types, json, os, tempfile
sys.path.insert(0, "/home/claude/proj/casino_origin")

# stub kivy so common.py (Wallet) can be imported without a display
class Any:
    def __init__(self,*a,**k): pass
    def __getattr__(self,n): return Any()
    def __call__(self,*a,**k): return Any()
def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m
for name in ["kivy","kivy.animation","kivy.core","kivy.core.audio","kivy.graphics","kivy.graphics.texture",
             "kivy.metrics","kivy.properties","kivy.uix","kivy.uix.boxlayout","kivy.uix.button","kivy.uix.image","kivy.uix.label"]:
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

import city_data as cd
from common import Wallet

d = tempfile.mkdtemp(); path = os.path.join(d, "save.json")
w = Wallet(path)
assert w.balance == 1000 and w.city["plots"] == [None]*12

# reserve rule: cannot spend the last 1000
assert cd.buy_building(w, 0, "diner") == "reserve" and w.balance == 1000
w.balance = 2000
assert cd.buy_building(w, 0, "diner", now=1000.0) == "ok" and w.balance == 1000
assert cd.buy_building(w, 0, "motel", now=1000.0) == "occupied"
assert cd.buy_building(w, 1, "diner", now=1000.0) == "reserve"   # balance 1000, would drop below reserve

# income piles up: diner lvl1 = 25/h
assert cd.income_per_hour(w.city) == 25
assert abs(cd.pending(w.city, 1000.0 + 3600) - 25) < 1e-9
# cap at 8h
assert abs(cd.pending(w.city, 1000.0 + 3600*100) - 200) < 1e-9
# clock moved back -> no negative / no change
assert cd.pending(w.city, 500.0) == 0

# upgrade settles the old rate first, then uses the new one
w.balance = 5000
assert cd.upgrade_building(w, 0, now=1000.0 + 3600) == "ok"   # cost 1000*2^1 = 2000
assert w.balance == 3000 and w.city["plots"][0]["level"] == 2
assert abs(w.city["stored"] - 25) < 1e-9
assert cd.income_per_hour(w.city) == 50
assert abs(cd.pending(w.city, 1000.0 + 7200) - 75) < 1e-9     # 25 settled + 1h * 50

# collect keeps the fraction and pays out an int
before = w.balance
got = cd.collect(w, now=1000.0 + 7200 + 1800)                   # 25 + 50 + 25 = 100
assert got == 100 and w.balance == before + 100
assert cd.collect(w, now=1000.0 + 7200 + 1800) == 0

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
assert cd.income_per_hour(w.city) == 25*5*1.1
assert cd.buy_landmark(w, "nope") == "unknown"

# the exploit is closed: spending everything and getting refilled is impossible
w2 = Wallet(os.path.join(d, "x.json")); w2.balance = 1000
for t in cd.BUILDING_ORDER:
    assert cd.buy_building(w2, 0, t) == "reserve"
assert w2.balance == 1000

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
