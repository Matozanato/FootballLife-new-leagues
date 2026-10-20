r"""python tools/test_game_crest.py [game folder]

B108 (David 17.10.): on the Leagues page a club of the game in a league of yours (Zamora and
Deportivo Tachira in the Liga FUTVE) showed a dash, not a crest: the world holds only the crests
Build drew. modstudio/gamecrest.crest() finds the game's:
  - a folder sider.ini switches on (a crest pack) comes first, the licensed _r picture before _f;
  - else a copy already in the cache;
  - no game folder or no team id: None.
With a game folder (default E:\instalacija when it is there) also from its .cpk files, read only:
Zamora (899, the game's own _f crest) and Deportivo Tachira (2218, _r), into a temp cache.
"""
import os, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from modstudio import gamecrest as G

N = 0


def ok(name, cond):
    global N
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        N += 1


def put(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(b"\x89PNG")


def main():
    T = tempfile.mkdtemp(prefix="gamecrest-")
    game = os.path.join(T, "game")
    sider = os.path.join(game, "SiderAddons")
    os.makedirs(os.path.join(game, "Data"))
    os.makedirs(sider)
    with open(os.path.join(sider, "sider.ini"), "w") as f:
        f.write(r'cpk.root = ".\livecpk\CrestPack"' + "\n" + r';cpk.root = ".\livecpk\Off"' + "\n")
    flag = ["common", "render", "symbol", "flag"]
    put(os.path.join(sider, "livecpk", "CrestPack", *flag, "e_000899_f.png"))
    put(os.path.join(sider, "livecpk", "CrestPack", *flag, "e_000899_r_l.png"))
    put(os.path.join(sider, "livecpk", "Off", *flag, "e_000700_r_l.png"))
    cache = os.path.join(T, "cache")
    put(os.path.join(cache, *flag, "e_000500_r.png"))
    g = types.SimpleNamespace(folder=game, sider_dir=sider)
    p = G.crest(g, 899, cache)
    ok("a crest pack switched on comes first, licensed before the game's own",
       p and p.endswith("e_000899_r_l.png") and "CrestPack" in p)
    ok("a folder switched off in sider.ini is not read", G.crest(g, 700, cache) is None)
    ok("a copy in the cache is used", (G.crest(g, 500, cache) or "").endswith("e_000500_r.png"))
    ok("no team id: None", G.crest(g, None, cache) is None)
    ok("no game folder: None", G.crest(types.SimpleNamespace(folder="", sider_dir=""), 899, cache) is None)
    real = sys.argv[1] if len(sys.argv) > 1 else "E:/instalacija"
    if os.path.isdir(os.path.join(real, "Data")):
        rg = types.SimpleNamespace(folder=real, sider_dir="")       # the game's .cpk only
        c2 = os.path.join(T, "cache2")
        z = G.crest(rg, 899, c2) or ""
        d = G.crest(rg, 2218, c2) or ""
        ok("from the game's .cpk: Zamora's own crest (%s)" % os.path.basename(z),
           z.endswith("e_000899_f_l.png") and os.path.getsize(z) > 1000)
        ok("from the game's .cpk: Deportivo Tachira's (%s)" % os.path.basename(d),
           d.endswith("e_002218_r_l.png") and os.path.getsize(d) > 1000)
    else:
        print("SKIP the game's .cpk (no game folder)")
    print("ALL OK" if not N else "%d FAILED" % N)
    return N


if __name__ == "__main__":
    sys.exit(main())
