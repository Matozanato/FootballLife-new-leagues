r"""Kits (Kit Server) and scoreboards (Scoreboard Server) of the recipe's new leagues.

A league can carry its clubs' Kit Server folders and its own Scoreboard Server folder:

    league["kit_folders"] = ["...\\Club A", "", ...]   one per club: a folder with p1, p2, g1 ...
    league["scoreboard"]  = "...\\HNL"                  a scoreboard folder

They come with a league package (lbpackage, parts "kitfiles" and "scoreboards") or from the
world as it is in the game (collect()).  A new club's team id and a league's regulation id are
known only once the world is built, so the folders are copied and the map lines written when a
world is switched on, the way lbstadiums does the home stadiums:

    content\kit-server\<world>\<league>\<club>\...      map.txt:  <team id>, "<world>\<league>\<club>"
    content\scoreboard-server\<world>\<league>\...      map_competitions.txt:  <regulation id>, <world>\<league>

  - every line written before (it ends with "# FL26 Mod Studio: ...") goes, whatever world it
    was for, so only the live world has lines of ours;
  - a club with a kit line of your own (switched on, or switched off by us) to a folder that is
    in the library gets no kit of ours, neither a package's nor a made one, and that line is on;
  - any other line of your own for a club or league that now gets one of ours is switched off (a
    # in front and OFF at its end), and back on when it no longer gets ours.

The scoreboard line is keyed by the league's regulation id, as the FL26 Modpack's are.
Without Kit Server or Scoreboard Server nothing is written for it.

Kit Server and Scoreboard Server come in two kinds each: kserv.lua reads content\kit-server and
ScoreboardServer.lua content\scoreboard-server, SPFL26's own ones (common\kits.lua and
common\scoreboards.lua, the ones a clean install loads) read content\kits and content\scoreboards,
the same files.  Ours go where the module sider.ini loads reads them (GitHub #129: the made kits
went to kit-server, which that game never read).
"""
import os, re, shutil

import lbstadiums

KITS = os.path.join("content", "kit-server")
SPFL_KITS = os.path.join("content", "kits")       # SPFL26's own Kit Server, common\kits.lua
BOARDS = os.path.join("content", "scoreboard-server")
SPFL_BOARDS = os.path.join("content", "scoreboards")   # and its common\scoreboards.lua
MENUS = os.path.join("content", "menu-server")       # Menu Server: no Build writes it, world zips bring lines
SLEEVES = os.path.join("content", "SleeveBadge")     # SmokePatch's common\SleeveBadge.lua (FL 2026 and 2027)
TAG = lbstadiums.TAG
OFF = lbstadiums.OFF
LINE = re.compile(r"^\s*(#\s*)?(\d+)\s*,\s*\"?([^\"#]*)")


def _live_modules(sider):
    """the modules the live lua.module lines of sider.ini load: names without folder and .lua"""
    mods = set()
    try:
        with open(os.path.join(sider, "sider.ini"), encoding="utf-8-sig", errors="replace") as f:
            for l in f:
                s = l.strip()
                if s.startswith("lua.module") and "=" in s:
                    n = os.path.basename(s.split("=", 1)[1].split(";")[0].strip().strip('"').replace("\\", "/")).lower()
                    mods.add(n[:-4] if n.endswith(".lua") else n)
    except OSError:
        pass
    return mods


ROOT_LINE = re.compile(r'^\s*local\s+\w*root\s*=\s*"\.?[\\/]*content[\\/]+([^"\\/]+)', re.M)


def _reads(sider, base):
    r"""the content folder (lower case) the live module base reads, from its own root line
    (local kroot = ".\\content\\kit-server\\"), or None (modstudio.servers.module_reads)"""
    try:
        with open(os.path.join(sider, "sider.ini"), encoding="utf-8-sig", errors="replace") as f:
            for l in f:
                s = l.strip()
                if s.startswith("lua.module") and "=" in s:
                    rel = s.split("=", 1)[1].split(";")[0].strip().strip('"')
                    n = os.path.basename(rel.replace("\\", "/")).lower()
                    if (n[:-4] if n.endswith(".lua") else n) == base:
                        with open(os.path.join(sider, "modules", rel), encoding="utf-8", errors="replace") as m:
                            hit = ROOT_LINE.search(m.read())
                        return hit.group(1).lower() if hit else None
    except OSError:
        pass
    return None


def _pick(sider, mods, ours, theirs, our_mod, their_mod, files):
    """ours or SPFL26's folder, as Install mods picks it (modstudio.servers.Server.pick): first
    the one the module sider.ini loads says it reads (B165, NedimMM 19.10.: a common\\kits.lua
    that reads content\\kit-server; the kits written into content\\kits never reached the game)"""
    live = [m for m in (their_mod, our_mod) if m in mods]
    reads = _reads(sider, live[0]) if len(live) == 1 else None
    for d in (theirs, ours):
        if reads == os.path.basename(d).lower() and os.path.isdir(os.path.join(sider, d)):
            return d
    there = os.path.join(sider, theirs)
    if os.path.isdir(there) and their_mod in mods and our_mod not in mods:
        return theirs
    if not os.path.isdir(os.path.join(sider, ours)) and any(
            os.path.isfile(os.path.join(there, f)) for f in files):
        return theirs
    return ours


def libs(sider):
    r"""(kits folder, scoreboards folder) the game reads: SPFL26's own when sider.ini loads its
    module and not ours and the folder is there, else content\kit-server and
    content\scoreboard-server -- the folders Install mods merges a world zip's lines into.  B158
    (jibibi 19.10.): common\kits.lua on, no content\kits: Install put eu4's 1138 kit lines into
    kit-server\map.txt, and its Switch on took them all out again, writing for content\kits"""
    mods = _live_modules(sider)
    return (_pick(sider, mods, KITS, SPFL_KITS, "kserv", "kits", ("map.txt", "config.txt")),
            _pick(sider, mods, BOARDS, SPFL_BOARDS, "scoreboardserver", "scoreboards",
                  ("map_competitions.txt", "config.ini")))


def safe(name):
    """a folder name Sider can read back from a map line (no quote, comma, # or path signs)"""
    return re.sub(r'[\\/:*?"<>|,#]+', "_", str(name)).strip(" .") or "x"


def is_kit_folder(d):
    return os.path.isdir(d) and any(re.fullmatch(r"[pg]\d", n, re.I) and os.path.isdir(os.path.join(d, n))
                                    for n in os.listdir(d))


def wanted(pl):
    """([(team id, club key, folder)], [(regulation id, league name, folder)]) of the plan"""
    kits, boards = [], []
    for p in pl.get("leagues") or []:
        teams = p.get("teams") or []
        for k, f in enumerate(p.get("kit_folders") or []):
            if f and k < len(teams) and teams[k] is not None:
                kits.append((int(teams[k]), "%s/%d" % (p["name"], k), f))
        if p.get("scoreboard") and p.get("rid") is not None:
            boards.append((int(p["rid"]), p["name"], p["scoreboard"]))
    return kits, boards


GAME = "Clubs of the game"          # the made kits of game clubs whose place went to another club


def replaced_clubs(pl):
    """{team id: (name, home words, own crest)} of the clubs of the game whose place the world gave
    another club (NewLife's "Bring the game's leagues to this season": edits.clubs with "kit",
    newlife.refresh_game_leagues, B57). The id stays the game's, so the game's kit for it -- and a
    kit pack's Kit Server line for it (5009, "Bundesliga\\Heidenheim") -- is the kit of the club
    that left: B176 (quicksite, NedimMM 20.10.), Europack eu4's Schalke 04 (5009), SC Paderborn
    (4139) and SV Elversberg (232) in the Bundesliga wore Heidenheim's, St. Pauli's and
    Wolfsburg's kits. Such a club gets a kit made from its colours and crest, as a new club does.
    "replaced_kits": false (Vicentico12 23.10.) leaves them none: the game's kit, or the kit pack's
    line for the id, stays"""
    out = {}
    if pl.get("replaced_kits") is False:
        return out
    for tid, v in ((pl.get("edits") or {}).get("clubs") or {}).items():
        if isinstance(v, dict) and "kit" in v and str(tid).isdigit():
            out[int(tid)] = (v.get("name") or "", v.get("kit") or "", bool(v.get("crest")))
    return out


def to_make(pl, root):
    """[(team id, league, place, home words, away words, crest picture, seed)] of the new clubs that
    get a kit made (kitmaker): no Kit Server folder of their own, and a crest drawn by the Build.
    Their shirt in words, or their crest picture's colours; a club with neither (a numbered badge)
    gets colours picked by its name (kitpatterns.generated_home) and no crest on the kit. seed:
    the club's name, which picks its patterns and the colours of its other kits. A club of the game
    keeps its kits -- unless the world gave its place to another club (replaced_clubs): that
    club's kit is made under GAME, its place the team id. "make_kits": false makes none."""
    import kitmaker, kitpatterns
    if pl.get("make_kits") is False:
        return []
    out = []
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):
        teams, folders = p.get("teams") or [], p.get("kit_folders") or []
        game = {int(k) for k in (p.get("game_clubs") or {})}
        home, away = p.get("club_kits") or [], p.get("club_away_kits") or []
        third = p.get("club_third_kits") or []
        crests = p.get("club_crests") or []
        names = p.get("club_names") or []
        league = p.get("name") or "Other clubs"
        for k, tid in enumerate(teams):
            if tid is None or k in game or (k < len(folders) and folders[k]):
                continue
            crest = os.path.join(root, "common", "render", "symbol", "flag", "e_%06d_r_ll.png" % int(tid))
            if not os.path.isfile(crest):
                continue                      # no crest drawn: not a club of this Build's
            seed = (names[k] if k < len(names) and names[k] else "%s/%d" % (league, k)).strip()
            words = kitmaker.words(home[k] if k < len(home) else "")
            own = k < len(crests) and crests[k]
            if not words and own:
                words = kitmaker.crest_kit(crest)
            if not words:
                # a numbered placeholder badge (every new club gets its kits, asked for 06.11.):
                # colours picked by its name, and the badge is not put on the shirt
                words, crest = kitpatterns.generated_home(seed), None
            out.append((int(tid), league, k, words,
                        kitmaker.words(away[k] if k < len(away) else ""), crest, seed,
                        kitmaker.words(third[k] if k < len(third) else "")))
    have = {x[0] for x in out}
    for tid, (name, kit, own) in sorted(replaced_clubs(pl).items()):
        crest = os.path.join(root, "common", "render", "symbol", "flag", "e_%06d_r_ll.png" % tid)
        words = kitmaker.words(kit)
        if tid in have or not os.path.isfile(crest) or not (words or own):
            continue                          # no colours and a badge of initials: the game's kit stays
        if not words:
            words = kitmaker.crest_kit(crest)
            if not words:
                continue
        out.append((tid, GAME, tid, words, None, crest, (name or "club %d" % tid).strip(), None))
    return out


def numbers_kit(lib, ours):
    """a kit of the library to lend back numbers, leg numbers and a name font: the first, by name,
    whose p1 has all three, outside the folders we write"""
    for d, subs, files in sorted(os.walk(lib)):
        rel = os.path.relpath(d, lib)
        if rel.split(os.sep)[0] == ours:
            subs[:] = []
            continue
        if os.path.basename(d).lower() == "p1":
            names = [f.lower() for f in files]
            if all(any(n.endswith(s + ".ftex") for n in names) for s in ("_back", "_leg", "_name")):
                return os.path.dirname(d)
    return None


LIGHT, DARK, LOOK = 0.6, 0.05, 40      # B214: numbers this light / this dark; kits looked at at most


def numbers_kits(lib, ours, made=False):
    """B214: the kits of the library to lend numbers from, [] when none has them: numbers_kit's
    first, then the first by name whose numbers are light and the first whose are dark (when the
    first's are not already), so every drawn kit finds numbers that stand out from its shirt.
    One walk of the library, as numbers_kit's (a Switch on is timed, B104).
    A kit Mod Studio drew (kitmaker.txt) lends none, its numbers are lent ones: another world's
    made kits sort before ours at times, and the lending kits changed with every world built or
    installed after ours (our test 06.11.: _FL26Comb150 built, then the Switch on of _FL26Lim120k
    drew its 779 made kits again, 597 s). made: those too, as before (the stamps written so)"""
    import kitpics
    out, want, seen = [], {"light", "dark"}, 0
    for d, subs, files in sorted(os.walk(lib)):
        rel = os.path.relpath(d, lib)
        if rel.split(os.sep)[0] == ours:
            subs[:] = []
            continue
        if os.path.basename(d).lower() != "p1":
            continue
        if not made and os.path.isfile(os.path.join(os.path.dirname(d), "kitmaker.txt")):
            continue
        names = [f.lower() for f in files]
        if not all(any(n.endswith(s + ".ftex") for n in names) for s in ("_back", "_leg", "_name")):
            continue
        if not out:
            out.append(os.path.dirname(d))
        if not want or seen >= LOOK:
            break
        seen += 1
        c = kitpics.ink(d)
        lum = kitpics._lum(c) if c else None
        kind = None if lum is None else "light" if lum >= LIGHT else "dark" if lum <= DARK else None
        if kind in want:
            want.discard(kind)
            if os.path.dirname(d) not in out:
                out.append(os.path.dirname(d))
    return out


# B213 (Dolokhov, 23.10.): how the kits are drawn. 0.2.4 turned the shorts crest a quarter (B138),
# but a kit is drawn again only when its stamp changes, and the stamp held the colours and the
# crest alone: every kit drawn before kept its crest lying on its side. The drawing is in the
# stamp now; a Build draws a kit of an older drawing again, a Switch on keeps it (B104: every kit
# of a world drawn at a Switch on is minutes with the window not answering).
# 3 (B214): the numbers picked for each kit from a few numbers kits (numbers_kits)
# 4: the kits of the pattern library (kitpatterns): what is drawn -- the four kits in words -- is in
#    the stamp, so a club whose kits the library picks differently is drawn again
DRAWING = 4


def _stamps(words, away, crest, numbers, lib=None, drawing=DRAWING, seed=None, third=None):
    """the kitmaker.txt stamps that count as "made from these": the first is the one written now,
    with the numbers kit by its folder inside the kit library. B104: the stamp had the numbers
    kit's whole path, so on every other PC (and on this one with the other slash) every made kit
    of a world was drawn again at its first Switch on -- 728 for the Modpack, many minutes with
    the window not answering. The others are the stamps written before, with this PC's path.
    drawing 1: the stamps of the drawing before B213, which did not name it. numbers: a folder,
    or numbers_kits' list -- drawing 3 names them all, the drawings before it the first (B214)."""
    import hashlib, kitmaker
    names, drawn = _drawing(words, away, numbers, lib, drawing, seed, third)
    pic = open(crest, "rb").read() if crest else b""
    if drawing >= 4:
        drawn += (("crest",) if crest else ("no crest",))
    out = []
    for n in names:
        h = hashlib.md5()
        for x in (words, away or "", n or "", os.path.getsize(kitmaker.MASK)) + \
                 (("drawing %d" % drawing,) if drawing > 1 else ()) + drawn + \
                 (("third %s" % third,) if third else ()):         # only a recipe's own third kit
            h.update(str(x).encode("utf-8") + b"\0")
        h.update(pic)
        if h.hexdigest() not in out:
            out.append(h.hexdigest())
    return out


def _drawing(words, away, numbers, lib=None, drawing=DRAWING, seed=None, third=None):
    """(the numbers kit's names, the kits planned in words) of _stamps"""
    import kitmaker

    def inside(k):
        if k and lib:
            try:
                return os.path.relpath(k, lib).replace(os.sep, "/")
            except ValueError:                # on another drive: the path as it is
                pass
        return k or ""
    if isinstance(numbers, (list, tuple)) and drawing >= 3:
        names = ["|".join(inside(k) for k in numbers)]
    else:
        if isinstance(numbers, (list, tuple)):
            numbers = numbers[0] if numbers else None
        names = [inside(numbers)] + ([numbers, numbers.replace("/", os.sep), numbers.replace(os.sep, "/")]
                                     if numbers else [""])
    if not numbers:
        # no kit lends numbers: the kit gets our own (kitnumbers), and a kit stamped before them,
        # which has none, is drawn again at the next Build
        import kitnumbers
        names = [kitnumbers.NAME]
    drawn = ()
    if drawing >= 4:
        try:
            kits = kitmaker.plan(words, away, seed, third)
        except Exception:                    # a shirt the library cannot read: the words alone
            kits = {}
        drawn = tuple("%s=%s" % (v, kits[v]) for v in sorted(kits))
    return names, drawn


def _env(words, away, numbers, lib=None, seed=None, third=None):
    """the fourth line of kitmaker.txt: what the stamp is made of besides what the second line
    says (the numbers kit, the mask, the drawing, the kits planned). With both lines as they
    were when the kit was drawn, its stamp is the same: the crest is not read again for it"""
    import hashlib, kitmaker
    names, drawn = _drawing(words, away, numbers, lib, DRAWING, seed, third)
    h = hashlib.md5()
    for x in (names[0] or "", os.path.getsize(kitmaker.MASK), "drawing %d" % DRAWING) + drawn:
        h.update(str(x).encode("utf-8") + b"\0")
    return h.hexdigest()


def _made(tid, words, away, crest, dst, numbers, log, lib=None, ready=False, redraw=False,
          seed=None, third=None):
    """the kit folder dst made from words and crest, unless it was made from the same ones.
    ready: the world came ready from a zip (Install mods) with its made kits in it -- a kit
    folder with a stamp is kept as it came, whatever PC drew it (B104). redraw (a Build): a kit
    whose stamp is not that of these colours, crest, numbers and drawing is drawn again; at a
    Switch on any kit Mod Studio drew is kept (B213, B374).
    seed: the club's name (kitpatterns.plan); crest None: no crest on the kit. numbers: a folder,
    numbers_kits' list, or a function giving it (write: the library is walked only when a kit
    needs it)"""
    import kitmaker, kitpics, tempfile
    stamp = os.path.join(dst, "kitmaker.txt")
    had, had_given, had_crest, had_env = _read_stamp(stamp)
    # B374: a Switch on draws a kit Mod Studio drew again only when what it is drawn from
    # changed (a crest put in the world's folder) -- not for another drawing (B213; B360 drew
    # the third kits anew on 09.11.: _FL26MegaNP's first Switch on drew one kit in three
    # again, minutes with the window busy) or other kits lending numbers (06.11.: a world built
    # since, 779 kits, 597 s); those are drawn at the next Build. A stamp from before 09.11.
    # does not say what the kit was drawn from: kept too. B376: asked before the stamps are
    # worked out (their drawing plan was 66 s of the 75 s Switch on of _FL26Megapack's 4345
    # kits) and the crest is read only when its file changed (its 4345 crests are 683 MB)
    if had and (ready or (not redraw and not had_given)):
        return False
    crest_md5, crest_line = _crest_md5(crest, had_crest)
    given = _given(words, away, crest, third, crest_md5)
    if had and not redraw and had_given == given:
        return False
    if callable(numbers):
        numbers = numbers()
    # mato 09.11. (jibibi: 27 minutes for a Build): a Build worked out every kit's stamp, reading
    # each crest whole -- 4345 just written ones for _FL26Megapack, a minute -- while the kit had
    # been drawn from the same of everything; the fourth line says so without the crest
    env = _env(words, away, numbers, lib, seed=seed, third=third)
    if had and had_given == given and had_env == env:
        _restamp(stamp, [had, given, crest_line, env], [had, had_given, had_crest, had_env])
        return False
    stamps = _stamps(words, away, crest, numbers, lib, seed=seed, third=third)
    if had in stamps:
        _restamp(stamp, [had, given, crest_line, env], [had, had_given, had_crest, had_env])
        return False
    # B166: a made kit whose files were changed after it was drawn (a kit put in its folder by
    # hand) is the player's: never drawn over
    try:
        made = int(os.path.getmtime(stamp))
        if had and any(t > made + SLACK for _s, t in _files(dst).values()):
            log("  kit of %s: its files were changed by you, kept (delete the folder to have it drawn "
                "again)" % dst)
            return False
    except OSError:
        pass
    tmp = tempfile.mkdtemp(prefix="fl26kit")
    try:
        pics = kitmaker.pictures(tmp, words, away, crest, seed=seed, **({"third": third} if third else {}))
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        kitpics.make_kit(pics, tid, dst, numbers)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(stamps[0] + "\n" + given + "\n" + crest_line + "\n" + env + "\n")
    _note_stamp(stamp, [stamps[0], given, crest_line, env])
    return True


# mato 09.11.: a Build opened all 4345 kitmaker.txt of _FL26Megapack, each one read by the virus
# scan (6 ms an open, 29 s): what they hold is kept in one file of the world's kits,
# kitmaker-index.json, and a stamp's lines are used while its file has the size and time they
# were read at
STAMPS = {}                  # {normcase(path): [mtime_ns, size, lines]}
INDEX = "kitmaker-index.json"


def _read_stamp(stamp):
    """the four lines of a kitmaker.txt ("" for those it has not), through STAMPS"""
    try:
        st = os.stat(stamp)
    except OSError:
        return [""] * 4
    k = os.path.normcase(stamp)
    c = STAMPS.get(k)
    if c and c[0] == st.st_mtime_ns and c[1] == st.st_size:
        return list(c[2])
    try:
        lines = (open(stamp, encoding="utf-8").read().split() + [""] * 4)[:4]
    except OSError:
        return [""] * 4
    STAMPS[k] = [st.st_mtime_ns, st.st_size, lines]
    return list(lines)


def _note_stamp(stamp, lines):
    """STAMPS after a kitmaker.txt was written"""
    try:
        st = os.stat(stamp)
        STAMPS[os.path.normcase(stamp)] = [st.st_mtime_ns, st.st_size, (list(lines) + [""] * 4)[:4]]
    except OSError:
        STAMPS.pop(os.path.normcase(stamp), None)


def _load_index(path):
    import json
    STAMPS.clear()
    try:
        with open(path, encoding="utf-8") as f:
            for k, v in json.load(f).items():
                if isinstance(v, list) and len(v) == 3 and isinstance(v[2], list):
                    STAMPS[os.path.normcase(os.path.join(os.path.dirname(path), k))] = v
    except (OSError, ValueError, AttributeError):
        pass


def _save_index(path):
    import json
    base = os.path.normcase(os.path.dirname(path)) + os.sep
    out = {k[len(base):]: v for k, v in STAMPS.items() if k.startswith(base)}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f)
    except OSError:
        pass


def _restamp(stamp, lines, had):
    """kitmaker.txt of a kit kept, brought up to date (the crest's file times, the fourth line)
    with its time left as it was: B166 and coldstart tell by it when the kit was drawn"""
    if lines == had:
        return
    try:
        st = os.stat(stamp)
        with open(stamp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.utime(stamp, ns=(st.st_atime_ns, st.st_mtime_ns))
    except OSError:
        pass
    _note_stamp(stamp, lines)


def _given(words, away, crest, third=None, crest_md5=None):
    """the second line of kitmaker.txt (B374): what the kit is drawn from -- the colours, the
    crest picture, a third kit of the recipe's own -- without the drawing and the numbers kit"""
    import hashlib
    h = hashlib.md5()
    for x in (words, away or "", third or ""):
        h.update(str(x).encode("utf-8") + b"\0")
    h.update((crest_md5 if crest_md5 is not None else _crest_md5(crest)[0]).encode("ascii"))
    return h.hexdigest()


# {crest path: (size, mtime_ns, md5)} of the crests a Build just wrote (leaguebuilder.write_manifest
# hashed them), so the kits' check after it does not read 4345 new files again
CREST_MD5 = {}


def _crest_md5(crest, had=""):
    """(the crest picture's md5, the third line of kitmaker.txt): the line holds the picture's
    size and times with its md5, so a Switch on reads a crest only when its file changed (B376).
    had: that line as the kit's stamp has it"""
    if not crest:
        return "", "-"
    import hashlib
    st = os.stat(crest)
    sig = "%d.%d.%d" % (st.st_size, st.st_mtime_ns, getattr(st, "st_birthtime_ns", 0) or 0)
    old_sig, _c, old = had.partition(":")
    if old_sig == sig and len(old) == 32:
        return old, had
    known = CREST_MD5.get(os.path.normcase(os.path.abspath(crest)))
    if known and known[:2] == (st.st_size, st.st_mtime_ns):
        return known[2], sig + ":" + known[2]
    md5 = hashlib.md5(open(crest, "rb").read()).hexdigest()
    return md5, sig + ":" + md5


COPIED = "modstudio-copy.txt"       # in a copied kit folder: what Mod Studio put there, file by file
SLACK = 30                          # seconds: a file this much newer than ours was changed after


def _files(d):
    """{path inside d: (size, whole seconds of its time)} of d's files, our own notes left out"""
    out = {}
    for x, _s, files in os.walk(d):
        for f in files:
            p = os.path.join(x, f)
            r = os.path.relpath(p, d).replace(os.sep, "/")
            if r not in (COPIED, "kitmaker.txt"):
                st = os.stat(p)
                out[r] = (st.st_size, int(st.st_mtime))
    return out


def _changed(have, was):
    """True when the files have differ from the files was (what Mod Studio put there): one more,
    one gone, another size or a time more than SLACK apart"""
    return set(have) != set(was) or any(
        have[r][0] != was[r][0] or abs(have[r][1] - was[r][1]) > SLACK for r in have)


def _unpacked(d, have, was):
    """True when the files have of d are what Mod Studio copied there (was, COPIED), only with
    other times: a world zip brings COPIED along with the times of the PC that built it, and
    Install gives its files the time they came out of the zip (GigaPack beta 4, 18.11.2026: HNL's
    scoreboard of Thunder105 never went in, its copy from beta 1's zip 29 days "newer" than its
    note). Untouched: the same files, each of the note's size and none newer than the note itself,
    which came out of the zip with them. A file changed by hand after that is newer than the note"""
    try:
        noted = int(os.path.getmtime(os.path.join(d, COPIED)))
    except OSError:
        return False
    return set(have) == set(was) and all(
        have[r][0] == was[r][0] and have[r][1] <= noted + SLACK for r in have)


def _copy(src, dst, log=None):
    """src's files into dst: dst made again only when they differ (a size), and only when dst is
    still what Mod Studio copied there. B166 (LaraCroft 19.10.): SV Ried's kit, changed by hand in
    its folder of the world, was put back to the package's at the next Build / Switch on (a size
    differed: rmtree + copytree). Now a copy leaves COPIED in dst, and a folder whose files are no
    longer those is the player's and stays; a copy from before COPIED counts as changed when one
    of its files is newer than the package's (a copy keeps the package's times).
    Returns "same", "copied" or "kept"."""
    if os.path.isdir(dst):
        want, have = _files(src), _files(dst)
        if all(r in have and have[r][0] == want[r][0] for r in want):
            return "same"
        was = None
        try:
            with open(os.path.join(dst, COPIED), encoding="utf-8") as f:
                was = {}
                for l in f:
                    r, _t, rest = l.rstrip("\n").partition("\t")
                    size, _t, t = rest.partition("\t")
                    if r and size.isdigit() and t.lstrip("-").isdigit():
                        was[r] = (int(size), int(t))
        except OSError:
            pass
        if was is not None:
            # GigaPack 1.1 (21.11.2026): the 1.0 zip's note on Serie C's boards named _chk.png and
            # _tmp_score.bin, scoreboard maker's leftovers the zip no longer carried, so the folder
            # read as "changed by you, kept" and Thunder105's new board never went in. A file the note
            # names that is gone and that the package does not bring either is no work of the player's
            was = {r: v for r, v in was.items() if r in have or r in want}
            mine = _changed(have, was) and not _unpacked(dst, have, was)
        elif os.path.isfile(os.path.join(dst, "kitmaker.txt")):
            # B367 (09.11.): a kit Mod Studio drew there, the club's stand-in until a package
            # brings its kit, was kept as the player's (its files newer than the package's)
            mine = False
            if log:
                log("  kit folder %s: the kit drawn from colours gives way to the package's" % dst)
        else:
            mine = any(r not in want or have[r][1] > want[r][1] + SLACK for r in have)
        if mine:
            if log:
                log("  kit folder %s: changed by you, kept (the package's kit is not copied over it; "
                    "delete the folder to have it again)" % dst)
            return "kept"
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    try:
        with open(os.path.join(dst, COPIED), "w", encoding="utf-8") as f:
            for r, (size, t) in sorted(_files(dst).items()):
                f.write("%s\t%d\t%d\n" % (r, size, t))
    except OSError:
        pass
    return "copied"


def prune(root, world, file="map.txt", log=print):
    """B452 (13.11.2026): a club renamed in the recipe got a kit folder under its new name at the
    next Build, and the one under its old name stayed -- 209 renamed clubs of the GigaPack left
    342 MB of kits no map line names, and Export packed them into the zip. A Build now takes out
    the club folders under <world> that no line of the map names (on or off), and only those
    Mod Studio put there itself: a copy whose files are still the ones it copied (COPIED), or a
    kit it drew (kitmaker.txt). A folder changed by hand, or one with neither note, stays.
    -> the folders taken out"""
    base = os.path.join(root, world)
    if not os.path.isdir(base):
        return 0
    named = set()
    for l in lbstadiums.read(os.path.join(root, file))[0]:
        m = LINE.match(l)
        if m:
            named.add(m.group(3).strip().replace("/", "\\").rstrip("\\").lower())
    if not any(n.startswith(world.lower() + "\\") for n in named):
        return 0                                   # a map with no line of this world: nothing is judged
    out = 0
    for league in sorted(os.listdir(base)):
        ld = os.path.join(base, league)
        if not os.path.isdir(ld):
            continue
        for club in sorted(os.listdir(ld)):
            d = os.path.join(ld, club)
            rel = ("%s\\%s\\%s" % (world, league, club)).lower()
            if not os.path.isdir(d) or rel in named or any(n.startswith(rel + "\\") for n in named):
                continue
            ours = os.path.isfile(os.path.join(d, "kitmaker.txt"))
            if not ours:
                try:
                    was = {}
                    with open(os.path.join(d, COPIED), encoding="utf-8") as f:
                        for x in f:
                            r, _t, rest = x.rstrip("\n").partition("\t")
                            size, _t, t = rest.partition("\t")
                            if r and size.isdigit() and t.lstrip("-").isdigit():
                                was[r] = (int(size), int(t))
                    # a world zip brings the note along with the times of the PC that built it, and
                    # Install gives the files today's (_unpacked)
                    have = _files(d)
                    ours = not _changed(have, was) or _unpacked(d, have, was)
                except OSError:
                    ours = False
            if ours:
                shutil.rmtree(d, ignore_errors=True)
                out += not os.path.isdir(d)
        try:
            if not os.listdir(ld):
                os.rmdir(ld)
        except OSError:
            pass
    if out:
        log("kits: %d kit folder(s) of %s that no map line names any more taken out (renamed or removed clubs)" % (out, world))
    return out


def carried(l, world):
    """a line Install mods put in from the world's own zip: a kit or a scoreboard of another pack
    the world carries under <world>\\_kits or <world>\\_packs (installer.export_world).  It ends
    in our tag like a line Build wrote, but Build did not write it and must not take it out:
    Switch on, run at the end of Install mods, wiped every modpack scoreboard that way (Vran,
    14.10.: "no scoreboards with the modpack")"""
    m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
    if not m:
        return False
    f = m.group(3).strip().lower().replace("/", "\\")
    w = safe(world).lower() + "\\"
    return f.startswith((w + "_kits\\", w + "_packs\\"))


def carrier(l):
    """the world (lower case) whose zip put this line in (carried), or None: switching another
    world on took such a line out for good, and switching the modpack back on did not bring its
    86 scoreboards back (night test 15.10.) -- now it stays, switched off, until its world is on"""
    if TAG not in l:
        return None
    m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
    if not m:
        return None
    parts = m.group(3).strip().lower().replace("/", "\\").split("\\")
    return parts[0] if len(parts) > 2 and parts[1] in ("_kits", "_packs") else None


def _key(l):
    """the team or competition id a map line is keyed by, or None"""
    m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
    return int(m.group(2)) if m else None


def world_ids(pl, root=None):
    """(team ids, competition ids) of the world as built: the clubs of its leagues and its clubs in
    no league (the plan's teams), and every id its world file in root names for a competition --
    a league's own, its cid=, cup= and scup=, a ccup line's and its ko= -- the ids a line the world
    carries from another pack is keyed by (installer.borrowed_kits / world_competitions).  (None,
    None) when there is no built world (root and its world file) to read: then nothing is taken"""
    teams = {int(t) for p in (pl.get("leagues") or []) + (pl.get("others") or [])
             for t in p.get("teams") or [] if str(t).isdigit()}
    comps = None
    if root:
        try:
            with open(os.path.join(root, "fl26world.txt"), encoding="utf-8", errors="replace") as f:
                comps = set()
                for line in f:
                    w = line.split()
                    if w[:1] in (["league"], ["ccup"]) and len(w) > 1 and w[1].isdigit():
                        comps.add(int(w[1]))
                        for t in w[2:]:
                            k, _s, v = t.partition("=")
                            if k in ("cid", "cup", "scup", "ko") and v.isdigit():
                                comps.add(int(v))
        except OSError:
            comps = None
    return (None, None) if comps is None else (teams, comps)


def _map(path, mine, log, what, world="", sider=None, keep=None):
    """our lines (key, text) into a map file: earlier ones of ours out, clashing ones of yours
    off; a line a world zip carries from another pack (carrier) stays: on while its world is on,
    switched off (#) while another one is.  While its own world goes on, such a line stays only
    while its key is still one of the world's (keep: None = every one): a league or club taken
    out of the world takes its carried line with it, else it would give its scoreboard or kit to
    whatever league or club a later Build hands that free id (editing a ready world)"""
    lines, nl, bom, enc = lbstadiums.read(path)
    if not mine and not any(TAG in l or l.endswith(OFF) for l in lines):
        return 0
    rows = []
    for l in lines:
        w0 = carrier(l)
        if w0 is not None:                     # another pack's line a world zip brought: on with its world
            mine_w = bool(world) and w0 == safe(world).lower()
            if mine_w and keep is not None and _key(l) not in keep:
                continue                       # its league or club is no longer in the world
            l = re.sub(r"^(\s*)#\s*", r"\1", l[:-len(OFF)] if l.endswith(OFF) else l, count=1)
            rows.append(l if mine_w else "#" + l)
            continue
        if TAG in l:
            continue
        if l.endswith(OFF):
            l = re.sub(r"^(\s*)#\s*", r"\1", l[:-len(OFF)], count=1)
        rows.append(l)
    taken = {key for key, _t in mine}
    out, off = [], 0
    for l in rows:
        m = LINE.match(l)
        if m and not m.group(1) and int(m.group(2)) in taken:
            l = "#" + l + OFF
            off += 1
        out.append(l)
    while out and not out[-1].strip():
        out.pop()
    out += [t for _k, t in mine]
    # a restore point in SiderAddons\ModStudio\backups, no map.txt.before-builder / .prev next to
    # the map any more (mato 15.10.)
    lbstadiums.keep_before(path, "Switch on: %s map" % what, sider)
    data = (nl.join(out) + nl).encode(enc, "replace")
    with open(path + ".tmp", "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + data)
    os.replace(path + ".tmp", path)
    log("%s: %d -> %s%s" % (what, len(mine), path, ", %d line(s) of your own switched off for them" % off if off else ""))
    return len(mine)


# words of a club's name that do not tell which club it is
GENERIC = set("""fc sc sv cf ac as afc cd ud sd fk nk hnk kf ks fks sk bk ik if ff vfl vfb tsg bsc rb
    club clube clubul klub kulubu calcio football futbol futebol fussball sport sports sporting
    sportif spor esporte esportes sportverein verein borussia united city town county athletic
    athletico atletico atletica atletico real deportivo deportiva deportes union olympique
    olympic racing inter dynamo dinamo lokomotiv spartak rapid stade wanderers rovers albion
    universidad universitario estudiantes independiente nacional academica associacao
    asociacion sociedad san santa saint the and de del la des der los las""".split())


def name_words(name):
    """the words of a club's (or a kit folder's) name that tell the club: lower case, no accents"""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return {w for w in re.split(r"[^a-z0-9]+", s) if len(w) > 2 and not w.isdigit() and w not in GENERIC}


def _yours(sider, klib, world="", names=None):
    """team ids that have a kit line of your own in map.txt (one Build did not write), switched on
    or switched off by us, whose folder is in the library: a line to a kit that is not installed
    gives the club nothing, so ours goes in for it (22 clubs of the modpack world, 13.10.).  A
    kit the world carries from another pack (carried) counts as one of yours: no kit is made
    over it.  names {team id: name}: the clubs of the game whose place the world gave another
    club (replaced_clubs) -- a line for one of them counts only when its folder names that club.
    A kit pack's line for the id is the kit of the club that left (B176: 5009,
    "Bundesliga\\Heidenheim" under Schalke 04), and is switched off for ours while the world is on"""
    out = set()
    names = names or {}
    for l in lbstadiums.read(os.path.join(sider, klib, "map.txt"))[0]:
        if TAG in l and not (world and carried(l, world)):
            continue
        m = LINE.match(l[:-len(OFF)] if l.endswith(OFF) else l)
        if m and (not m.group(1) or l.endswith(OFF)) and m.group(3).strip() \
                and os.path.isdir(os.path.join(sider, klib, m.group(3).strip())):
            tid = int(m.group(2))
            folder = m.group(3).strip().replace("/", "\\").rstrip("\\").rsplit("\\", 1)[-1]
            if tid in names and not name_words(names[tid]) & name_words(folder):
                continue
            out.add(tid)
    return out


def made_rel(pl, world, league, k):
    """the kit library folder (world\\league\\club) of the kit made for place k of league; for
    GAME, k is the club's team id"""
    if league == GAME:
        name = (replaced_clubs(pl).get(k) or ("",))[0]
        return "%s\\%s\\%s" % (world, safe(GAME), safe(name or "club %d" % k))
    cn = [p for p in (pl.get("leagues") or []) + (pl.get("others") or [])
          if (p.get("name") or "Other clubs") == league][0].get("club_names") or []
    return "%s\\%s\\%s" % (world, safe(league), safe(cn[k] if k < len(cn) and cn[k] else "club %d" % k))


def restamp(pl, sider, root, log=print):
    """a ready world from a zip made editable on this PC (installer.make_editable): its made kits
    were drawn on the PC that built it, and their kitmaker.txt holds that PC's stamp. Each made
    kit folder with a stamp gets the stamp of this PC for the colours and crest of the world as it
    came, so the Switch on after a Build keeps it (as it did while the world was ready, B104) and a
    club whose colours or crest are changed since gets its kit drawn again. Returns how many
    stamps were written."""
    klib, _blib = libs(sider)
    lib = os.path.join(sider, klib)
    if not os.path.isdir(lib):
        return 0
    world = safe(pl.get("world") or "FL26 world")
    numbers = numbers_kits(lib, world)
    n = 0
    for tid, league, k, words, away, crest, seed, third in to_make(pl, root):
        stamp = os.path.join(lib, made_rel(pl, world, league, k), "kitmaker.txt")
        try:
            had = open(stamp, encoding="utf-8").read().strip()
        except OSError:
            continue
        mine = _stamps(words, away, crest, numbers, lib, seed=seed, third=third)[0]
        if had and had != mine:
            with open(stamp, "w", encoding="utf-8") as f:
                f.write(mine + "\n")
            n += 1
    log("kits made from colours and crests: %d stamped as made on this PC" % n)
    return n


# B227 (antonimus, 24.10.): the Libertadores' phases 1 and 2 of a modern CONMEBOL world are a
# competition of their own (leaguebuilder.libq, "Pre-Libertadores"), so the Scoreboard Server,
# keyed by regulation id, gave their matches no board where the game's qualifying round has one.
# They wear the board your map gives that round (regulation 8): a phase's regulation and its ties'
# (reg + 1024 * k, mkeuropo.prerounds_single), each a line of ours, gone with the next Switch on.
LIBQ_KEY, LIBQ_PARENT = "conmebol:FL_LIBQ", 8
LIBQ_TIES = (("reg", 3), ("reg2", 8))          # leaguebuilder.libq: [(m1, 3), (m2, 8)]


def helper_boards(pl, path, taken=()):
    """[(regulation id, map line)] giving the Pre-Libertadores' regulations the folders the map at
    path gives the game's Libertadores qualifying round -- every one of them, the server picks one
    of a competition's boards at random -- or [] when the world has no such phases or the map no
    line for that round; a regulation a line of yours (or taken) keys already is left out"""
    ids = (pl.get("cup_ids") or {}).get(LIBQ_KEY) or {}
    if not ids or not os.path.isfile(path):
        return []
    boards, have = [], set()                       # the round's folders; keys of your own lines
    for l in lbstadiums.read(path)[0]:
        m = LINE.match(l)
        if not m or m.group(1) or TAG in l:
            continue
        have.add(int(m.group(2)))
        f = m.group(3).strip()
        if int(m.group(2)) == LIBQ_PARENT and f and f not in boards:
            boards.append(f)
    out = []
    for field, ties in LIBQ_TIES if boards else ():
        reg = ids.get(field)
        if not isinstance(reg, int):
            continue
        for k in range(ties + 1):
            key = reg + 1024 * k
            if key not in taken and key not in have:
                out += [(key, "%d, %s   %s Pre-Libertadores (as %d)" % (key, f, TAG, LIBQ_PARENT))
                        for f in boards]
    return out


def libq_keys(pl):
    """the Pre-Libertadores' regulation ids: each phase's and its ties' (reg + 1024 * k)"""
    ids = (pl.get("cup_ids") or {}).get(LIBQ_KEY) or {}
    return [ids[f] + 1024 * k for f, ties in LIBQ_TIES if isinstance(ids.get(f), int)
            for k in range(ties + 1)]


# B230 (antonimus 25.10.): the scoreboard alone was not enough -- Menu Server's themes, balls,
# referees, referee kits, commentary and goal songs go by the competition id too, so the
# Pre-Libertadores' matches got the generic menu where the game's qualifying round has the
# Libertadores one. Every content\<server>\map_competitions.txt but the scoreboards' (helper_boards)
# gives the phases what it gives regulation 8; Soundtrack Server's music, kept in folders named
# by the id, gets a folder of the round's tracks for each (hard links, no copies of the music).
HELPER_SKIP = {BOARDS.lower(), SPFL_BOARDS.lower()}
SOUNDTRACK = os.path.join("content", "soundtrack-server")
SOUND_SPECIFIC = ("4_Competitions_Specific", "6_Results_Specific", "8_Highlights_Specific")
SOUND_PARENT = "CCL"                 # SoundtrackServer.lua: regulation 8 and its ties play the "CCL" folder
SOUND_MARK = "made by FL26 Mod Studio.txt"
REST = re.compile(r"^\s*(\d+)\s*,(.*?)\s*(#.*)?$")


def helper_lines(pl, path, taken=()):
    """[(regulation id, map line)] giving the Pre-Libertadores' regulations what the map at path
    (any server's map_competitions.txt) gives the game's Libertadores qualifying round, every line
    of it, or [] when the world has no such phases or the map no line for that round; a key a line
    of yours (or taken) has already is left out"""
    keys = libq_keys(pl)
    if not keys or not os.path.isfile(path):
        return []
    rests, have = [], set()
    for l in lbstadiums.read(path)[0]:
        m = REST.match(l)
        if not m or TAG in l:
            continue
        have.add(int(m.group(1)))
        if int(m.group(1)) == LIBQ_PARENT and m.group(2).strip() and m.group(2) not in rests:
            rests.append(m.group(2))
    return [(key, "%d,%s   %s Pre-Libertadores (as %d)" % (key, r, TAG, LIBQ_PARENT))
            for key in keys if key not in taken and key not in have for r in rests]


HELPER_MARK = "Pre-Libertadores (as %d)" % LIBQ_PARENT


def _helper_map(path, mine, log, what, sider=None):
    """our Pre-Libertadores lines (helper_lines) into a server's map: the earlier ones out, the
    rest of the file as it was -- other lines of ours (a world zip's menu themes) are menus()' and
    the stadiums', and no line of yours is switched off (helper_lines leaves out a key you have)"""
    lines, nl, bom, enc = lbstadiums.read(path)
    rows = [l for l in lines if not (TAG in l and HELPER_MARK in l)]
    if not mine and len(rows) == len(lines):
        return 0
    while rows and not rows[-1].strip():
        rows.pop()
    rows += [t for _k, t in mine]
    lbstadiums.keep_before(path, "Switch on: %s map" % what, sider)
    data = (nl.join(rows) + nl).encode(enc, "replace")
    with open(path + ".tmp", "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + data)
    os.replace(path + ".tmp", path)
    log("Pre-Libertadores (%s): %d line(s) as regulation %d" % (what, len(mine), LIBQ_PARENT))
    return len(mine)


def helper_servers(pl, sider, world, log=print):
    """the Pre-Libertadores' lines into every other server's map_competitions.txt and their
    music folders into Soundtrack Server's (helper_lines, B230); a world without the phases takes
    ours out again. Returns the lines written"""
    content = os.path.join(sider, "content")
    n = 0
    try:
        dirs = sorted(os.listdir(content))
    except OSError:
        dirs = []
    for d in dirs:
        rel = os.path.join("content", d)
        path = os.path.join(sider, rel, "map_competitions.txt")
        if rel.lower() in HELPER_SKIP or not os.path.isfile(path):
            continue
        n += _helper_map(path, helper_lines(pl, path), log, d, sider)
    keys = libq_keys(pl)
    for sub in SOUND_SPECIFIC:
        top = os.path.join(sider, SOUNDTRACK, sub)
        if not os.path.isdir(top):
            continue
        src = os.path.join(top, SOUND_PARENT)
        tracks = [f for f in os.listdir(src) if f.lower().endswith(".mp3")] if os.path.isdir(src) else []
        made = 0
        for name in os.listdir(top):
            dst = os.path.join(top, name)
            if os.path.isfile(os.path.join(dst, SOUND_MARK)) and (not tracks or not name.isdigit()
                                                                  or int(name) not in keys):
                shutil.rmtree(dst, ignore_errors=True)
        for key in keys if tracks else ():
            dst = os.path.join(top, str(key))
            if os.path.isdir(dst) and not os.path.isfile(os.path.join(dst, SOUND_MARK)):
                continue                        # a folder of your own for the id
            os.makedirs(dst, exist_ok=True)
            for f in tracks:
                if not os.path.exists(os.path.join(dst, f)):
                    try:
                        os.link(os.path.join(src, f), os.path.join(dst, f))
                    except OSError:
                        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            with open(os.path.join(dst, SOUND_MARK), "w") as f:
                f.write("Pre-Libertadores: the tracks of %s (regulation %d), for regulation %d\n"
                        % (SOUND_PARENT, LIBQ_PARENT, key))
            made += 1
        if made:
            log("Pre-Libertadores (soundtrack %s): %d folder(s) with the %s tracks" % (sub, made, SOUND_PARENT))
    return n


def write(pl, sider, log=print, root=None, redraw=False):
    """the plan's kits and scoreboards into Kit Server and Scoreboard Server, and a kit made for
    every other new club with colours or a crest (root: the world's folder, for the crests);
    (kits, scoreboards) written. redraw: a Build's, kits of an older drawing drawn again (B213)"""
    kits, boards = wanted(pl)
    world = safe(pl.get("world") or "FL26 world")
    wroot = root                         # the loop below takes the name `root` for a library's folder
    teams, comps = world_ids(pl, root)
    klib, blib = libs(sider)
    # B130: kserv.lua, when sider.ini loads it, stops at its start when content\kit-server has no
    # map_comp.txt, and the game then shows no kit of Kit Server at all (laracroft7826, 18.10.: his
    # kit-server folder held map.txt alone) -- an empty one is put there, as Kit Server's own
    # download has it. B265 (NedimMM 28.10.): SPFL26's common\kits.lua stops the same way in the
    # folder it reads (his read content\kit-server, B165), so the check is made in the folder the
    # live module reads, for either module
    comp = os.path.join(sider, klib, "map_comp.txt")
    if {"kserv", "kits"} & _live_modules(sider) and os.path.isdir(os.path.dirname(comp)) and not os.path.exists(comp):
        try:
            open(comp, "w").close()
            log("kits: %s had no map_comp.txt, which Kit Server needs -- an empty one made" % klib)
        except OSError:
            pass
    make = to_make(pl, root) if root and os.path.isdir(os.path.join(sider, klib)) else []
    # B104: a world that came ready from a zip brought its made kits along, drawn on the PC it was
    # built on -- they are kept, not drawn again
    ready = bool(root) and os.path.exists(os.path.join(root, ".modstudio"))
    # a club with a kit line of your own keeps that kit: no kit made for it, and none of a league
    # package either (pepponeee98, 14.10.: his Serie C lines were switched off at every Build for
    # the package's kits, which went into a folder of the world again each time)
    yours = _yours(sider, klib, world, {t: v[0] for t, v in replaced_clubs(pl).items()}) \
        if (make or kits) else set()
    kept = sorted({x[0] for x in kits if x[0] in yours} | {x[0] for x in make if x[0] in yours})
    kits = [x for x in kits if x[0] not in yours]
    make = [x for x in make if x[0] not in yours]
    if kept:
        log("kits: %d club(s) keep a kit line of your own (%s)" % (len(kept), ", ".join(map(str, kept))))
    done = []
    for lib, file, items, what in ((klib, "map.txt", kits, "kits"),
                                   (blib, "map_competitions.txt", boards, "scoreboards")):
        root = os.path.join(sider, lib)
        if not os.path.isdir(root):
            if items:
                log("NOTE: %d %s come with the world, but %s is not installed -- not written" % (len(items), what, lib))
            done.append(0)
            continue
        mine = []
        # B259: the folder each id has under this world now, switched on or off (gianito9, 27.10.:
        # the r12 Modpack made editable, its European leagues renamed -- Bulgarian First League to
        # Efbet League -- and a Build left Bulgaria in the lent kits of Other Latin American teams:
        # the source folders are on the PC that built the pack, and the zip's copies sit under the
        # league's old name)
        before = {}
        for l in lbstadiums.read(os.path.join(root, file))[0]:
            m = LINE.match(l)
            f = m.group(3).strip() if m else ""
            if f.lower().startswith(world.lower() + "\\") and os.path.isdir(os.path.join(root, f)):
                before.setdefault(int(m.group(2)), f)
        for key, name, src in items:
            if what == "kits":
                league, _s, k = name.rpartition("/")
                club = [p for p in pl["leagues"] if p["name"] == league][0]
                cname = (club.get("club_names") or [])[int(k)] if int(k) < len(club.get("club_names") or []) else ""
                rel = "%s\\%s\\%s" % (world, safe(league), safe(cname or "club %s" % k))
                text = '%d, "%s"   %s %s' % (key, rel, TAG, name)
            else:
                rel = "%s\\%s" % (world, safe(name))
                text = "%d, %s   %s %s" % (key, rel, TAG, name)
            if os.path.isdir(src):
                _copy(src, os.path.join(root, rel), log)
            elif not os.path.isdir(os.path.join(root, rel)) and before.get(key) \
                    and before[key].lower() != rel.lower():
                _copy(os.path.join(root, before[key]), os.path.join(root, rel), log)   # renamed: B259
            elif not os.path.isdir(os.path.join(root, rel)):
                log("  %s of %s: no folder %s, skipped" % (what, name, src))
                continue
            # else: the source is on the PC the world was built on, and the world's zip brought
            # the copy under <world>: the line stays (Install mods, whose Switch on dropped it)
            mine.append((key, text))
        if what == "kits" and make:
            # walked once, and only when a kit is worked out: a Switch on that keeps every kit
            # does not walk the library (9 s of _FL26Megapack's, B374)
            walked = []

            def numbers(lib=root):
                if not walked:
                    walked.append(numbers_kits(lib, world))
                return walked[0]
            new = later = 0
            index = os.path.join(root, world, INDEX)
            _load_index(index)
            for tid, league, k, words, away, crest, seed, third in make:
                rel = made_rel(pl, world, league, k)
                if crest is None and not redraw and not os.path.isdir(os.path.join(root, rel)):
                    # a club with no colours of its own, its kit never drawn (a world from before
                    # the pattern library, or a zip's): drawn at the next Build, not at a Switch on,
                    # which must stay quick (B104); till then it wears the kit Build lent it
                    later += 1
                    continue
                try:
                    drawn = _made(tid, words, away, crest, os.path.join(root, rel), numbers, log,
                                  lib=root, ready=ready, redraw=redraw, seed=seed, third=third)
                except Exception as e:               # one bad crest picture must not stop the Build
                    log("  kit of %s: not made (%s)" % (rel, e))
                    continue
                new += drawn
                if drawn and new % 50 == 0:          # B104: a long drawing says how far it is
                    log("kits drawn from colours and crests: %d so far (of at most %d)" % (new, len(make)))
                mine.append((tid, '%d, "%s"   %s %s/%d made' % (tid, rel, TAG, league, k)))
            if os.path.isdir(os.path.dirname(index)):
                _save_index(index)
            log("kits made from colours and crests: %d (%d new or changed)%s" % (
                len(make) - later, new, "" if not walked or walked[0] else "; no kit in the library lends back numbers, so Mod Studio's own are on them"))
            if later:
                log("kits: %d club(s) without colours of their own get kits at the next Build" % later)
        if what == "scoreboards":
            mine += helper_boards(pl, os.path.join(root, file), {k for k, _t in mine})
        done.append(_map(os.path.join(root, file), mine, log, what, world, sider,
                         teams if what == "kits" else comps))
        if what == "kits" and redraw:              # a Build's, not a Switch on's (which stays quick)
            prune(root, world, file, log)
    # B129: the other folder's map too (content\kits or content\kit-server, the one not picked
    # above): Install mods may have merged a world zip's lines there (servers.Server.pick decides
    # its folder its own way), and those lines of ours stayed on for the next world's clubs
    for lib, other, file, what in ((klib, (KITS, SPFL_KITS), "map.txt", "kits"),
                                   (blib, (BOARDS, SPFL_BOARDS), "map_competitions.txt", "scoreboards")):
        for o in other:
            path = os.path.join(sider, o, file)
            if o != lib and os.path.isfile(path):
                # B230: with both scoreboard modules on, the Libertadores line may be in this one
                # (antonimus: content\scoreboards), so the Pre-Libertadores goes by it here too
                _map(path, helper_boards(pl, path) if what == "scoreboards" else [], log,
                     what + " (" + o + ")", world, sider, teams if what == "kits" else comps)
    menus(sider, world, log)
    helper_servers(pl, sider, world, log)
    sleeves(pl, sider, world, wroot, log)
    return tuple(done)


# A knockout's or a group stage's match carries its regulation id plus 1024 for each tie, round or
# group after the first (SmokePatch's own map: Champions League 2 with 1026, 2050, 3074, 4098; the
# Libertadores groups up to 9 + 8 x 1024). 11.11.2026, Build 4 of the GigaPack: the first match of
# a career at AF Elbasani, the Conference League's first qualifying round (qround ... 536), came
# as tournament id 2584 = 536 + 2 x 1024 -- no line, SleeveBadge.lua's error again.
# 11.11., Build 5: the same match came as 24088 = 536 + 23 x 1024 -- the number is the tie's, not
# the round's, and a u16 id leaves six bits for it: every one of the 63 gets a line.
SLEEVE_STEP, SLEEVE_STEPS = 1024, 63
SLEEVE_KINDS = {"poff": "promotion play-off", "lpre": "preliminary round", "gsuper": "super cup"}


def sleeve_ids(pl, root=None):
    """[(tournament id, name)] of the world's own competitions a match is played in: its leagues
    (the regulation id, as the scoreboards' lines), and with the built world in root the cups, super
    cups, continental cups, European qualifying rounds, play-offs, preliminary rounds and split
    groups its world file names. A cup's id comes with the ids of its later ties, rounds and groups
    too (SLEEVE_STEP)"""
    out, seen = [], set()

    def add(i, name, rounds=False):
        if i not in seen:
            seen.add(i)
            out.append((i, name))
        for k in range(1, SLEEVE_STEPS + 1) if rounds else ():
            j = i + SLEEVE_STEP * k
            if j not in seen and j <= 65535:
                seen.add(j)
                out.append((j, "%s, +%d" % (name, k)))
    for q in pl.get("leagues") or []:
        if q.get("rid") is not None:
            add(int(q["rid"]), q.get("name") or "league")
    if root:
        try:
            with open(os.path.join(root, "fl26world.txt"), encoding="utf-8", errors="replace") as f:
                for line in f:
                    w = line.split()
                    kind = w[0] if w else ""
                    if kind == "qround" and len(w) == 4 and w[3].isdigit():
                        add(int(w[3]), "European qualifying round", True)
                        continue
                    if kind == "split" and len(w) > 1 and w[1].isdigit():
                        for t in w[2:]:
                            k, _s, v = t.partition("=")
                            for x in v.split(",") if k in ("regular", "groups") else ():
                                if x.isdigit():
                                    add(int(x), "league %s (split)" % w[1])
                        continue
                    if kind in SLEEVE_KINDS and len(w) > 1 and w[1].isdigit():
                        add(int(w[1]), SLEEVE_KINDS[kind], True)
                        continue
                    if kind not in ("league", "ccup") or len(w) < 2 or not w[1].isdigit():
                        continue
                    name = line.partition(" name=")[2].strip() or "competition %s" % w[1]
                    add(int(w[1]), name, kind == "ccup")
                    for t in w[2:]:
                        k, _s, v = t.partition("=")
                        if k == "name":
                            break
                        if k in ("cup", "scup", "ko") and v.isdigit():
                            add(int(v), "%s (%s)" % (name, {"cup": "cup", "scup": "super cup", "ko": "knockout"}[k]), True)
        except OSError:
            pass
    return out


def sleeves(pl, sider, world, root=None, log=print):
    """B396 (10.11.2026): SmokePatch's common\\SleeveBadge.lua stops with a Lua error ("attempt to
    concatenate local 'folder' (a nil value)", line 367) at every match of a competition its
    content\\SleeveBadge\\map.txt has no line for -- every league and cup a world adds. Each of the
    world's competitions with no line there gets one of ours, to the folder <world> (no badge in
    it: the match is played with no sleeve badge, as before, and with no error; a badge put in
    content\\SleeveBadge\\<world>\\badge is worn). A line of SmokePatch's or of yours is never
    switched off for one of ours. Returns how many lines were written."""
    path = os.path.join(sider, SLEEVES, "map.txt")
    if not os.path.isfile(path):
        return 0
    theirs = set()
    for l in lbstadiums.read(path)[0]:
        m = LINE.match(l)
        if m and not m.group(1) and TAG not in l and not l.endswith(OFF):
            theirs.add(int(m.group(2)))
    mine = [(i, '%d, "%s"   %s %s' % (i, world, TAG, name)) for i, name in sleeve_ids(pl, root) if i not in theirs]
    return _map(path, mine, log, "sleeve badges", world, sider)


def menus(sider, world, log=print):
    r"""the menu themes world zips brought (content\menu-server\map_competitions.txt, lines
    "<world>\..." with our tag): on while their world is in the game, switched off (#) while
    another one is. Switch on handled kits and scoreboards only, so the Modpack's menus stayed on
    under every other world (B72, our test 16.10.: 88 eu1 and the r7 lines live under
    _FL26MyWorld). Lines of your own are not touched; returns the lines changed"""
    path = os.path.join(sider, MENUS, "map_competitions.txt")
    # B112 (David.BDJ, 17.10.): MenuServer.lua, when sider.ini loads it, stops at its start when
    # content\menu-server has no map_competitions.txt (a world zip with no menus, a clean install
    # with the line switched on by hand) -- an empty one is put there, as for kserv.lua (B130)
    if "menuserver" in _live_modules(sider) and not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").close()
            log("menus: content\\menu-server had no map_competitions.txt, which MenuServer.lua needs -- "
                "an empty one made")
        except OSError:
            pass
    lines, nl, bom, enc = lbstadiums.read(path)
    live = os.path.join(sider, "livecpk")
    want = safe(world).lower() if world else ""
    out, changed = [], 0
    for l in lines:
        body = l[:-len(OFF)] if l.endswith(OFF) else l
        m = LINE.match(body) if TAG in l else None
        w0 = m.group(3).strip().replace("/", "\\").split("\\")[0] if m else ""
        if not w0 or not w0.lower().startswith("_fl26") or not os.path.isdir(os.path.join(live, w0)):
            out.append(l)
            continue
        body = re.sub(r"^(\s*)#\s*", r"\1", body, count=1)
        new = body if w0.lower() == want else "#" + body
        changed += new != l
        out.append(new)
    if changed:
        lbstadiums.keep_before(path, "Switch on: menus map", sider)
        data = (nl.join(out) + nl).encode(enc, "replace")
        with open(path + ".tmp", "wb") as f:
            f.write((b"\xef\xbb\xbf" if bom else b"") + data)
        os.replace(path + ".tmp", path)
        log("menus: %d line(s) of world zips switched %s" % (changed, "with %s" % world if world else "off"))
    return changed


def _read_map(path):
    """{key: folder} of the lines in effect in a map file"""
    lines, _nl, _b, _e = lbstadiums.read(path)
    out = {}
    for l in lines:
        m = LINE.match(l)
        if m and not m.group(1) and m.group(3).strip():
            out.setdefault(int(m.group(2)), m.group(3).strip())
    return out


def collect(recipe, pl, sider, names=None):
    """fill recipe leagues' kit_folders / scoreboard from the world in the game: the folders the
    Kit Server and Scoreboard Server maps give the built plan's team and regulation ids.  A
    league that has them already keeps its own.  Returns (kit folders, scoreboards) found."""
    built = {p["name"]: p for p in (pl or {}).get("leagues") or []}
    klib, blib = libs(sider)
    kmap = _read_map(os.path.join(sider, klib, "map.txt"))
    bmap = _read_map(os.path.join(sider, blib, "map_competitions.txt"))
    nk = nb = 0
    for L in recipe.get("leagues") or []:
        p = built.get(L["name"])
        if not p or (names is not None and L["name"] not in names):
            continue
        teams = p.get("teams") or []
        own = list(L.get("kit_folders") or [])
        # B148: a world from a zip has the folders of the PC that built it; one not on this PC
        # counts as none
        if teams and (not any(own) or not all(os.path.isdir(f) for f in own if f)):
            fs = []
            for k, tid in enumerate(teams):
                if k < len(own) and own[k] and os.path.isdir(own[k]):
                    fs.append(own[k])
                    continue
                rel = kmap.get(int(tid)) if tid is not None else None
                d = os.path.join(sider, klib, rel) if rel else ""
                fs.append(d if d and is_kit_folder(d) else "")
                nk += 1 if fs[-1] else 0
            L["kit_folders"] = fs
        if not (L.get("scoreboard") and os.path.isdir(L["scoreboard"])) and p.get("rid") is not None:
            rel = bmap.get(int(p["rid"]))
            d = os.path.join(sider, blib, rel) if rel else ""
            if d and os.path.isdir(d):
                L["scoreboard"] = d
                nb += 1
    return nk, nb
