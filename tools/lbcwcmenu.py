r"""The Club World Cup of 32's menus and texts, into a world's livecpk root (feature/cwc32).

The ranking screens and buttons are fl26contrank's (in the pack, on with the world file's cwc32
line). What they need from the game's files goes into the world built with the Club World Cup
(leaguebuilder.build -> write), so it comes and goes with that world:

  common/script/flow/ML/MLMainManu.json        the ML menu flow + events leaguerankna/as/af/oc
  common/script/flow/League/LeagueMainMenu.json the League Mode menu flow, the same events
  common/script/flow/BL/BLMainMenu.json         the Become a Legend menu flow, the same events (21.11.)
  common/script/flow/Common/CmnLeagueRanking{NA,AS,AF,OC}.json
                                               copies of the game's CmnLeagueRankingEU.json
  <lang>/string/all.str                        every language's texts + ours in category 0x1a:
                                               0x2ac..0x2b0 UEFA .. CAF (buttons),
                                               0x2b1..0x2b5 "Ranking <confed>" (screen titles),
                                               0x2b6 the submenu ("Ranking CWC"),
                                               0x2b7 OFC (button), 0x2b8 "Ranking OFC" (21.11.)

FL27 (21.11.): its menu flows are in Data\dt16_all.cpk and its texts in data_s26271.cpk and
Data\dt20_<lang>_x64.cpk, which Sources reads as it reads FL26's; the category 0x1a ids from
0x2ac on are free there too (it ends at 0x2ab, as FL26's).

Each file is made from the one the game shows now: the first livecpk root of sider.ini that has
it (a Mod Studio world left out: they are ours), else the newest of the game's .cpk files. So a
modpack's own texts and menus are kept. A modpack that changes those files later is covered by
the world's copy until the next Build.
"""
import glob, json, os, re, struct, zlib

FLOW = "common/script/flow/"
# event short name -> unit; the button names fl26contrank gives (86/87 are the game's own events)
EVENTS = [("leaguerankeu", "Common/CmnLeagueRankingEU"), ("leagueranksa", "Common/CmnLeagueRankingSA"),
          ("leaguerankna", "Common/CmnLeagueRankingNA"), ("leaguerankas", "Common/CmnLeagueRankingAS"),
          ("leaguerankaf", "Common/CmnLeagueRankingAF"), ("leaguerankoc", "Common/CmnLeagueRankingOC")]
MENUS = ["ML/MLMainManu.json", "League/LeagueMainMenu.json", "BL/BLMainMenu.json"]
UNIT_SRC = "Common/CmnLeagueRankingEU.json"
UNITS = ["Common/CmnLeagueRankingNA.json", "Common/CmnLeagueRankingAS.json", "Common/CmnLeagueRankingAF.json",
         "Common/CmnLeagueRankingOC.json"]

CAT = 0x1a
CONF = ["UEFA", "CONMEBOL", "CONCACAF", "AFC", "CAF"]
SUBMENU = {"bra": "Ranking Copa de Clubes", "por": "Ranking Copa de Clubes",
           "spa": "Ranking Copa de Clubes", "mex": "Ranking Copa de Clubes"}
SUBMENU_DEFAULT = "Ranking CWC"
LANGS = ["ara", "bra", "chi", "eng", "fra", "ger", "gre", "ita", "jpn", "kor", "mex", "nld", "por",
         "rus", "spa", "swe", "tur", "zha"]
MARK = "fl26world.txt"


def texts(lang):
    t = {0x2ac + k: c for k, c in enumerate(CONF)}
    t.update({0x2b1 + k: "Ranking " + c for k, c in enumerate(CONF)})
    t[0x2b6] = SUBMENU.get(lang, SUBMENU_DEFAULT)
    t[0x2b7], t[0x2b8] = "OFC", "Ranking OFC"          # fl26contrank's OFC button and screen title
    return t


# ---- where the game's file comes from ----

def _cpk_key(path):
    m = re.match(r"data_s(\d{4})(\d*)([a-z]*)\.cpk$", os.path.basename(path).lower())
    return (0, int(m.group(1)), int(m.group(2) or 0), m.group(3)) if m else (1, 0, 0, os.path.basename(path).lower())


class Sources:
    """the game's files as the game sees them: livecpk roots first (sider.ini order), then the
    archives, the newest first"""

    def __init__(self, game, sider):
        self.roots = []
        ini = os.path.join(sider, "sider.ini")
        for line in open(ini, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(ini) else []:
            m = re.match(r'\s*cpk\.root\s*=\s*"([^"]+)"', line)
            if not m:
                continue
            p = m.group(1).strip()
            p = os.path.normpath(os.path.join(sider, p) if not os.path.isabs(p) else p)
            if os.path.isdir(p) and not os.path.exists(os.path.join(p, MARK)):
                self.roots.append(p)
        dl = os.path.join(game, "download")
        cpks = sorted(glob.glob(os.path.join(dl, "data_s2526*.cpk")) + glob.glob(os.path.join(dl, "data_s2627*.cpk")),
                      key=_cpk_key)
        cpks += sorted(glob.glob(os.path.join(dl, "data_extra*.cpk")))
        self.cpks = list(reversed(cpks)) + list(reversed(sorted(glob.glob(os.path.join(game, "Data", "*.cpk")))))
        self._toc = {}

    def _names(self, c):
        import cpkread
        if c not in self._toc:
            try:
                with open(c, "rb") as f:
                    base, rows = cpkread.toc(f)
                self._toc[c] = (base, {cpkread.path_of(r).lower(): r for r in rows})
            except (OSError, ValueError, KeyError, struct.error):
                self._toc[c] = (0, {})
        return self._toc[c]

    def read(self, rel):
        """(bytes, where) of <rel> (forward slashes), or (None, None)"""
        for r in self.roots:
            p = os.path.join(r, rel.replace("/", os.sep))
            if os.path.isfile(p):
                return open(p, "rb").read(), p
        import cpkread
        for c in self.cpks:
            base, rows = self._names(c)
            r = rows.get(rel.lower())
            if r is None:
                continue
            with open(c, "rb") as f:
                f.seek(base + r["FileOffset"])
                d = f.read(r["FileSize"])
            if r["ExtractSize"] > r["FileSize"] and d[:8] == b"CRILAYLA":
                d = cpkread.crilayla(d)
            return d, os.path.basename(c)
        return None, None


# ---- flows ----

def _events_span(t):
    """(start, end) of the "events" object's braces in the JSON text"""
    m = re.search(r'"events"\s*:\s*\{', t)
    if not m:
        raise ValueError("no events")
    i, depth, s = m.end() - 1, 0, False
    j = i
    while j < len(t):
        c = t[j]
        if s:
            if c == "\\":
                j += 1
            elif c == '"':
                s = False
        elif c == '"':
            s = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i, j
        j += 1
    raise ValueError("events not closed")


def add_events(text, events=EVENTS):
    """the menu flow <text> with an event "NN_<name>" -> unit for every name it lacks; (text, added)"""
    o = json.loads(text)
    ev = o["events"]
    have = {k.split("_", 1)[1] for k in ev if "_" in k}
    nums = [int(k.split("_", 1)[0]) for k in ev if k.split("_", 1)[0].isdigit()]
    n = max(nums) if nums else 0
    i, e = _events_span(text)
    k = e
    while text[k - 1].isspace():
        k -= 1
    add, names = "", []
    for name, unit in events:
        if name in have:
            continue
        n += 1
        key = "%02d_%s" % (n, name)
        names.append(key)
        add += (',\n\t\t"%s":{\n\t\t\t"to":"%s",\n\t\t\t"go":"forward",\n\t\t\t"clear":"all",\n'
                '\t\t\t"fadeStart":"",\n\t\t\t"fadeEnd":"do",\n\t\t\t"bgType":"none"\n\t\t}') % (key, unit)
    if not names:
        return text, []
    if text[k - 1] == "{":                 # no event at all
        add = add[1:]
    out = text[:k] + add + text[k:]
    chk = json.loads(out)["events"]
    assert list(chk)[:len(ev)] == list(ev) and len(chk) == len(ev) + len(names)
    return out, names


# ---- all.str ----

def _parse(blk):
    cnt, cat = struct.unpack_from("<2I", blk, 0)
    E = []
    for k in range(cnt):
        i, bl, _cl, o = struct.unpack_from("<IHHI", blk, 8 + 12 * k)
        E.append((i, blk[o:o + bl]))
    return cat, E


def _block(cat, E):
    hdr = struct.pack("<2I", len(E), cat)
    tab, body, base = b"", b"", 8 + 12 * len(E)
    for i, b in E:
        tab += struct.pack("<IHHI", i, len(b), len(b[:-1].decode("utf-8")), base + len(body))
        body += b
    return hdr + tab + body


def add_texts(raw, new):
    """all.str <raw> (WESYS header + zlib) with the ids of <new> {id: text} added to category
    0x1a where missing; (bytes, added ids, ids already there with another text)"""
    d = zlib.decompress(raw[16:])
    if len(d) != struct.unpack_from("<I", raw, 12)[0]:
        raise ValueError("all.str: size")
    n = struct.unpack_from("<I", d, 0)[0]
    B = [struct.unpack_from("<3I", d, 8 + 12 * i) for i in range(n)]
    blocks = [d[o:o + s] for o, s, _nm in B]
    for blk in blocks:
        if _block(*_parse(blk)) != blk:
            raise ValueError("all.str: a block this tool cannot rebuild as it was")
    ks = [k for k, blk in enumerate(blocks) if _parse(blk)[0] == CAT]
    if len(ks) != 1:
        raise ValueError("all.str: %d blocks of category 0x%x" % (len(ks), CAT))
    K = ks[0]
    cat, E = _parse(blocks[K])
    have = dict(E)
    other = [i for i, s in new.items() if i in have and have[i] != s.encode("utf-8") + b"\0"]
    add = [(i, s.encode("utf-8") + b"\0") for i, s in sorted(new.items()) if i not in have]
    if not add:
        return raw, [], other
    ordered = [a for a, _ in E] == sorted(a for a, _ in E)
    E = E + add
    if ordered:
        E.sort(key=lambda e: e[0])
    blocks[K] = _block(cat, E)
    out = bytearray(d[:B[0][0]])
    dir_ = []
    for k, blk in enumerate(blocks):
        while len(out) % 16:
            out.append(0)
        dir_.append((len(out), len(blk), B[k][2]))
        out += blk
    while len(out) % 16:
        out.append(0)
    for k, (o, s, nm) in enumerate(dir_):
        struct.pack_into("<3I", out, 8 + 12 * k, o, s, nm)
    nd = bytes(out)
    z = zlib.compress(nd, 9)
    return raw[:8] + struct.pack("<2I", len(z), len(nd)) + z, [i for i, _ in add], other


# ---- the Build step ----

def write(root, game, sider, log=print):
    """the flows and texts into the world's livecpk <root>; returns how many files"""
    src = Sources(game, sider)
    made = 0

    def put(rel, data):
        p = os.path.join(root, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)

    for rel in MENUS:
        raw, where = src.read(FLOW + rel)
        if raw is None:
            log("  WARNING: Club World Cup menus: the game has no %s -- that menu gets no ranking buttons" % rel)
            continue
        text = raw.decode("utf-8-sig")
        out, names = add_events(text)
        put(FLOW + rel, out.encode("utf-8"))
        made += 1
        log("  Club World Cup menus: %s from %s%s" % (rel, where, (", + " + ", ".join(names)) if names else ""))
    raw, where = src.read(FLOW + UNIT_SRC)
    if raw is None:
        log("  WARNING: Club World Cup menus: the game has no %s -- the CONCACAF, AFC, CAF and OFC screens "
            "will not open" % UNIT_SRC)
    else:
        for rel in UNITS:
            put(FLOW + rel, raw)
            made += 1
    langs = 0
    for lang in LANGS:
        rel = "%s/string/all.str" % lang
        raw, where = src.read(rel)
        if raw is None:
            continue
        try:
            out, added, other = add_texts(raw, texts(lang))
        except (ValueError, zlib.error, struct.error, UnicodeDecodeError) as e:
            log("  WARNING: Club World Cup texts: %s (%s) left as it is: %s" % (rel, where, e))
            continue
        if other:
            log("  WARNING: Club World Cup texts: %s (%s) already uses %s for other texts -- those "
                "buttons show them" % (rel, where, ", ".join("0x%x" % i for i in other)))
        put(rel, out)
        made += 1
        langs += 1
    log("  Club World Cup menus: %d flow file(s), the texts in %d language(s)" % (made - langs, langs))
    return made
