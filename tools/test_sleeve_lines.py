"""B396 (10.11.2026): SmokePatch's common\\SleeveBadge.lua stops with a Lua error at every match of
a competition its content\\SleeveBadge\\map.txt has no line for ("attempt to concatenate local
'folder' (a nil value)", line 367) -- every league and cup a world adds.

    python tools/test_sleeve_lines.py

A Switch on (lbservers.write) gives each of the world's competitions with no line there a line of
ours to the folder <world>; a line of SmokePatch's or of the player's own is never switched off; the
next world's Switch on takes the lines out again; with no SleeveBadge folder nothing is written.
The Lua's own map reader (the pattern of its load_map) must read our lines.
"""
import os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbservers

N = 0


def ok(what, cond):
    global N
    if not cond:
        print("FAIL", what)
        sys.exit(1)
    N += 1
    print("ok  ", what)


THEIRS = """# SP football Life badge map

\t#UEFA Champions League
\t2, "UCL"
\t1026, "UCL"
\t122, "belc"
#\t77, "old"
"""
WORLD_FILE = """world _FL26Test
league 355 cid=263 region=8 country=197 tier=2 above=115 cup=122 scup=128 kickoff=88 name=Challenger Pro League
league 74 cid=169 region=55 country=240 tier=1 cup=303 scup=304 name=Uzbekistan Super League
league 2 cid=170 region=56 country=241 tier=1 name=A league on an id their map has
qround 12 1 536
poff 756 up=96 low=252 entry=252:2,955:2
lpre 614 cup=622 fill=36 days=40,40 entry=67:7
gsuper 612 league=29 cup=31 region=16 conf=4
split 61 regular=191 groups=192,193
ccup 615 ko=616 groups=8 entry=143:1 comp=6 name=CAF Champions League
"""


def lua_map(path):
    """what SleeveBadge.lua's load_map reads: comments cut, then  %s*(.+)%s*,%s*["]([^"]+)["]"""
    out = {}
    for line in open(path, encoding="utf-8"):
        line = re.sub(r"#.*$", "", line.rstrip("\n"))
        m = re.match(r"\s*(.+)\s*,\s*\"([^\"]+)\"", line)
        if m and m.group(1).strip().isdigit():
            out[int(m.group(1))] = m.group(2)
    return out


tmp = tempfile.mkdtemp(prefix="sleeve_")
sider = os.path.join(tmp, "SiderAddons")
root = os.path.join(sider, "livecpk", "_FL26Test")
os.makedirs(root)
os.makedirs(os.path.join(sider, "modules"))
with open(os.path.join(sider, "sider.ini"), "w") as f:
    f.write("[sider]\n")
with open(os.path.join(root, "fl26world.txt"), "w", encoding="utf-8") as f:
    f.write(WORLD_FILE)
pl = {"world": "_FL26Test", "leagues": [{"name": "Challenger Pro League", "rid": 355, "teams": []},
                                        {"name": "Uzbekistan Super League", "rid": 74, "teams": []},
                                        {"name": "A league on an id their map has", "rid": 2, "teams": []}]}
said = []

# 1. no SleeveBadge folder: nothing written, nothing made
lbservers.write(pl, sider, said.append, root)
ok("no content/SleeveBadge: nothing is made", not os.path.exists(os.path.join(sider, lbservers.SLEEVES)))

# 2. their map: our competitions get a line each, theirs stay
os.makedirs(os.path.join(sider, lbservers.SLEEVES))
mp = os.path.join(sider, lbservers.SLEEVES, "map.txt")
with open(mp, "w", encoding="utf-8", newline="") as f:
    f.write(THEIRS.replace("\n", "\r\n"))
lbservers.write(pl, sider, said.append, root)
m = lua_map(mp)
ok("the league, its cup and super cup, the continental cup and its knockout get a line: %s" % sorted(m),
   all(m.get(i) == "_FL26Test" for i in (355, 74, 303, 304, 128, 615, 616)))
ok("their lines stay as they were (2, 1026, 122)", m.get(2) == "UCL" and m.get(1026) == "UCL" and m.get(122) == "belc")
text = open(mp, encoding="utf-8", newline="").read()
ok("no line of theirs switched off", lbservers.OFF not in text and "#\t77" in text.replace(" ", ""))
ok("their line ends kept (CRLF)", "\r\n" in text and "\n" not in text.replace("\r\n", ""))
ok("every line of ours carries the tag", sum(lbservers.TAG in l for l in text.splitlines()) == len(m) - 3)
ok("the log says how many", any("sleeve badges: %d" % (len(m) - 3) in t for t in said))
# 2b. 11.11.2026: a cup's match carries its id + 1024 x tie / round / group -- the Conference League's
#     first qualifying round (qround ... 536) came as 2584 at the first match of a career
ok("a European qualifying round and its later ties: 536, 2584, 24088 (Build 5), 536 + 63 x 1024",
   all(m.get(i) == "_FL26Test" for i in (536, 536 + 1024, 2584, 24088, 536 + 63 * 1024)))
ok("a play-off, a preliminary round, a group super cup and their later ties",
   all(m.get(i + 1024 * k) == "_FL26Test" for i in (756, 614, 612) for k in (0, 1, 7)))
ok("a split's regular phase and groups get a line, with no later ids (they are leagues)",
   all(m.get(i) == "_FL26Test" for i in (191, 192, 193)) and 191 + 1024 not in m)
ok("a national cup, a super cup and a continental cup with their later ties",
   all(m.get(i + 1024 * k) == "_FL26Test" for i in (303, 304, 128, 615, 616) for k in (1, 2, 12, 63)))
ok("a league has no later ids", 355 + 1024 not in m and 74 + 1024 not in m)
ok("a later id their map has stays theirs (1026 of 2), none past 65535", m.get(1026) == "UCL" and max(m) <= 65535)

# 3. a second Switch on writes the same lines once
lbservers.write(pl, sider, said.append, root)
ok("written again: the same file", open(mp, encoding="utf-8", newline="").read() == text)

# 4. another world goes on: the first world's lines go, its own come
root2 = os.path.join(sider, "livecpk", "_FL26Other")
os.makedirs(root2)
with open(os.path.join(root2, "fl26world.txt"), "w", encoding="utf-8") as f:
    f.write("world _FL26Other\nleague 400 cid=130 name=Other League\n")
lbservers.write({"world": "_FL26Other", "leagues": [{"name": "Other League", "rid": 400, "teams": []}]},
                sider, said.append, root2)
m = lua_map(mp)
ok("the next world: its line in, the first world's out: %s" % sorted(m),
   m == {2: "UCL", 1026: "UCL", 122: "belc", 400: "_FL26Other"})

# 5. a world with nothing of its own leaves their file as it came
lbservers.write({"world": "_FL26Empty", "leagues": []}, sider, said.append, None)
back = open(mp, encoding="utf-8", newline="").read()
ok("a world with no competition: their file as it came", back == THEIRS.replace("\n", "\r\n"))
shutil.rmtree(tmp, ignore_errors=True)
print("all %d checks passed" % N)
