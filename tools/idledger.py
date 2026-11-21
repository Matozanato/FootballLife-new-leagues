r"""The id ledger of a shared world: every id a career of it holds, so the next version keeps them.

mato 17.11.2026 ("the most important thing of all, we may have many updates"; then "every pack must
be updatable this way, not only ours"): a Master League career holds the world's ids -- the team ids
of its clubs (the game's save, fl26swiss-state.bin and the Edit side file name them), the player
ids, and the regulation and competition ids of its leagues and cups. A new version of a world that
hands any of them to something else, or drops one, breaks the careers of the version before.

Build already keeps the ids of the LAST BUILD on this PC (leaguebuilder.prev_pins, used_tids,
lbplayers._keep_ids). That is not what the players have: GigaPack beta 2 and beta 3 gave 88 and
15 clubs new ids against the zip before them, and 91 squad places named since beta 3 would have
taken new player ids. The ledger pins a Build to the version that was SHARED instead:

    export      Export the world (installer.export_world) writes the world's ledger into the zip
                (SiderAddons\livecpk\<world>\fl26ids-ledger.json) and the author's Mod Studio keeps
                a copy of every version it shared, <recipes>\ledgers\<world>.<lineage>.<n>.fl26ids
                (store_save), unless the export is a test zip.
    Build       a recipe with a ledger (find) is planned from the ledger's plan, not the last Build's:
                its leagues and cups keep their ids, and no league, cup or club takes an id any
                version of the world ever gave (the ledger's "spent"); its players keep the ledger's
                ids, followed by their clubs' team ids (leaguebuilder.follow_tids). At the end every
                id of the ledger must still be there and mean the same thing -- or be in the
                recipe's "id_retire" list, with a reason -- else the Build stops
                (leaguebuilder.LedgerProblems) and says which.
    Install     update_verdict: a zip of the same world (the same "lineage", a later number) whose
                ledger keeps every id of the version installed, and retires no club, league or cup
                of it, is an Update: the careers stay. A world installed from a zip without a ledger
                is the same world when its ids are those of a version in the new ledger's "chain"
                (its digest), else when nearly all its clubs and leagues have the same names under
                the same ids (SAME_NAMES).

A ledger: {"format", "format_version", "world", "version", "number", "made", "lineage" (made at the
first export, kept by every version after it), "digest" (of its ids), "chain" [{version, number,
made, digest}] of the versions before it, "after" (the one right before), "plan" (slim_plan),
"players" (fl26playerids.json), "retire" {kind: {id: reason}}, "spent" {"rids": [...], "cids":
[...]}: every regulation and competition id a league or cup of any version had, and "rows"
(rowkeep.rows_of, 18.11.2026 evening; a ledger of before has none): the rows of its competition
tables, which the next version's Build keeps at their index (rowkeep.keep)}.

The recipe's keys (leaguebuilder.RECIPE_SETTINGS keeps them in the plan):
    "id_retire":   {"players": {"<id>": "why"}, "clubs": {...}, "leagues": {"<rid>": ...},
                    "cups": {"<cup key>": ...}} -- ids that may go, each with its reason
    "pack_version": the version name export offers ("GigaPack beta 4"); without it, a number
                    one up from the ledger's and the date
    "id_lineage":  the lineage of the world's ledgers: only those pin a Build of this recipe
    "id_ledger":    a ledger file to pin to (relative to the recipe's folder or to the recipes folder)
    "id_not_lineages": lineages the author said are another world of the same name (find leaves
                    their ledgers out; Build's "A different world")
    "id_tables":   the world zip (or the world folder) of the version shared last, for a ledger of
                    before 18.11.2026 evening that has no "rows": Build reads the order of its
                    competition tables there (rowkeep.prev_rows), relative like id_ledger

    python tools/idledger.py make <world folder> --version "GigaPack beta 3" --out <file> [--number 3] [--lineage <hex>]
    python tools/idledger.py compare <old: ledger or world folder> <new: ledger or world folder>
"""
import datetime, glob, hashlib, json, os, re, sys, uuid

LEDGER = "fl26ids-ledger.json"            # in the world folder of a world zip
EXT = ".fl26ids"                          # the author's copy (not .json: nothing takes it for a recipe)
FORMAT, FORMAT_VERSION = "fl26ids-ledger", 2     # 2: lineage, digest, chain, spent (1: 17.11. morning, never shared)
PLAN = "leaguebuilder-plan.json"
PLAYER_IDS = "fl26playerids.json"
KINDS = ("clubs", "players", "leagues", "cups")
RETIRE_KEY = "id_retire"
VERSION_KEY = "pack_version"
LEDGER_KEY = "id_ledger"
LINEAGE_KEY = "id_lineage"
NOT_LINEAGES_KEY = "id_not_lineages"
TABLES_KEY = "id_tables"                  # rowkeep.prev_rows: the zip of the version shared last (its rows)
ROWS_KEY = "rows"                         # rowkeep.rows_of of the version (export: world_ledger)
ISSUED = ".issued"                        # <world>.<lineage>.issued: every number an export gave (next_number)
SPENT_KEY = "_id_spent"                   # pinned_recipe -> leaguebuilder.plan: ids no league may take
SAME_NAMES = 0.9                          # update_verdict: a world without a ledger is the same one
                                          # when this share of its clubs and leagues have their names
SAME_NAMES_IDS = 0.5                      # ... or this share, when it keeps every id of the one installed
RECIPE_LIKE = 0.6                         # find: a ledger of no lineage the recipe names pins it when
                                          # this share of its leagues or clubs are the recipe's
RECIPE_UNLIKE = 0.2                       # ... and is left out below this share; in between, find stops
                                          # (a league replaced or a world of the same name? id_lineage says)
MASS_SHARE, MASS_MIN = 0.5, 5             # mass_losses: a club still there that lost this many players
_PLAN_TOP = ("world", "game", "retired_tids", "cup_ids")
_PLAN_LISTS = ("leagues", "others", "away_leagues")
_LIST_KEYS = ("teams", "club_names", "built_as")
_DICT_KEYS = ("split", "game_clubs", "newlife_tid", "promo")
SHAPE = ("clubs", "legs", "split", "above", "exchange", "relegate", "promo", "calendar")


class LedgerError(Exception):
    """a ledger file that cannot be read or is not one"""


class LedgerAsk(LedgerError):
    """find: a ledger of the world's name whose leagues and clubs are half this recipe's -- the author
    says whether it is that world (id_lineage) or another (id_not_lineages): .lineage, .version, .path"""
    def __init__(self, text, lineage, version, path):
        super().__init__(text)
        self.lineage, self.version, self.path = lineage, version, path

    def __reduce__(self):
        return (LedgerAsk, (str(self), self.lineage, self.version, self.path))


# ---- what the ledger holds ----

def _slim_league(q):
    """the parts of a plan's league (or group of other clubs) Build pins by: its numbers and flags,
    its name, its clubs' team ids and names, its split, play-off and places of game clubs (no
    pictures, no squads, no path of the PC it was built on)"""
    s = {k: v for k, v in q.items() if v is None or isinstance(v, (bool, int, float))}
    if isinstance(q.get("name"), str):
        s["name"] = q["name"]
    for k in _LIST_KEYS:
        if isinstance(q.get(k), list):
            s[k] = list(q[k])
    for k in _DICT_KEYS:
        if isinstance(q.get(k), dict):
            s[k] = q[k]
    return s


def slim_plan(plan):
    """the plan Build pins a world's leagues, cups and clubs by (leaguebuilder.plan's prev): what
    prev_pins, away_leagues, prev_clubs, used_tids, low_cids and the cups' ids read of it"""
    out = {k: plan[k] for k in _PLAN_TOP if k in plan}
    for key in _PLAN_LISTS:
        out[key] = [_slim_league(q) for q in plan.get(key) or [] if isinstance(q, dict)]
    return out


def club_tids(plan):
    """{"<league>/<k>": team id} of a plan's new clubs (its leagues, other clubs and the leagues it
    kept away): the key fl26playerids.json files a club's players under (lbplayers.new_key)"""
    out = {}
    for key in ("away_leagues", "others", "leagues"):          # a league's own last: it wins
        for q in (plan or {}).get(key) or []:
            if not isinstance(q, dict) or not q.get("name"):
                continue
            game = {int(k) for k in (q.get("game_clubs") or {}) if str(k).isdigit()}
            for k, t in enumerate(q.get("teams") or []):
                if isinstance(t, int) and k not in game:
                    out["%s/%d" % (q["name"], k)] = t
    return out


def newlife_pins(led):
    """{NewLife club id as text: team id} of the ledger's NewLife clubs (the plan's newlife_tid)"""
    out = {}
    for key in ("leagues", "others"):
        for q in (led.get("plan") or {}).get(key) or []:
            for nl, t in ((q or {}).get("newlife_tid") or {}).items():
                if str(nl).strip().isdigit() and isinstance(t, int):
                    out.setdefault(str(nl).strip(), t)
    return out


def pinned_recipe(recipe, led):
    """the recipe as Build plans it with ledger `led` (a copy; the recipe itself is not changed):
    its NewLife clubs' pins (newlife_ids) are the ledger's where the ledger has the club, and
    SPENT_KEY holds every regulation and competition id a version of the world gave (spent_of), so
    no league takes one that is not its own"""
    out = dict(recipe)
    pins = newlife_pins(led)
    if pins:
        out["newlife_ids"] = dict(recipe.get("newlife_ids") or {}, **pins)
    sp = spent_of(led)
    out[SPENT_KEY] = {"rids": sorted(sp["rids"]), "cids": sorted(sp["cids"])}
    return out


def _player_part(playerids):
    return {k: v for k, v in (playerids or {}).items() if k != "world"}


def empty_retire():
    return {k: {} for k in KINDS}


def retire_of(*lists):
    """{kind: {id as text: reason}} of the retirement lists given (a ledger's "retire", a recipe's
    "id_retire"), the first one's reason where two give one"""
    out = empty_retire()
    for r in lists:
        r = r.get("retire", r) if isinstance(r, dict) and "format" in r else r
        if not isinstance(r, dict):
            continue
        for kind in KINDS:
            for k, why in (r.get(kind) or {}).items():
                out[kind].setdefault(str(k).strip(), str(why or "").strip() or "retired")
    return out


def _cup_regs(w):
    return sorted(v for f, v in w.items() if f != "cid" and isinstance(v, int))


def spent_of(led_or_plan):
    """{"rids": set, "cids": set}: every regulation and competition id a league or cup of the
    ledger's world has, and (a ledger's "spent") every one a version before it had"""
    plan = led_or_plan.get("plan") if "format" in led_or_plan else led_or_plan
    rids, cids = set(), set()
    old = led_or_plan.get("spent") if "format" in led_or_plan else None
    if isinstance(old, dict):
        rids |= {r for r in old.get("rids") or [] if isinstance(r, int)}
        cids |= {c for c in old.get("cids") or [] if isinstance(c, int)}
    for q in (plan or {}).get("leagues") or []:
        if isinstance(q, dict):
            if isinstance(q.get("rid"), int):
                rids.add(q["rid"])
            if isinstance(q.get("cid"), int):
                cids.add(q["cid"])
    for w in ((plan or {}).get("cup_ids") or {}).values():
        if isinstance(w, dict):
            if isinstance(w.get("cid"), int):
                cids.add(w["cid"])
            rids |= set(_cup_regs(w))
    return {"rids": rids, "cids": cids}


def digest(ids):
    """a short hash of a world's ids (ids_of): two worlds with the same one are the same version"""
    h = hashlib.sha1()
    for t, (nm, lg) in sorted(ids["clubs"].items()):
        h.update(("c%d=%s|%s\n" % (t, nm, lg)).encode("utf-8"))
    for r, q in sorted(ids["leagues"].items()):
        h.update(("l%d=%s|%s|%s\n" % (r, q.get("name"), q.get("cid"), q.get("region"))).encode("utf-8"))
    for k, w in sorted(ids["cups"].items()):
        h.update(("u%s=%s|%s\n" % (k, w.get("cid"), _cup_regs(w))).encode("utf-8"))
    for p, club in sorted(ids["players"].items()):
        h.update(("p%d=%s\n" % (p, club)).encode("utf-8"))
    return h.hexdigest()[:20]


def make(plan, playerids, world, version, number=None, prev=None, retire=None, made=None, lineage=None,
         test=False, rows=None):
    """the ledger of a built world: its plan (slim_plan) and ids file (fl26playerids.json), the
    version name, its number (one up from prev's when not given; an export gives next_number), its
    lineage (prev's; a new one for the first version), the chain of versions before it, every id any
    version spent, and, as "retire", the ids retired up to now -- prev's and the recipe's (retire) --
    that this world does not have: an id that is there again is no longer retired. test: a test zip's
    ("test": true), never the version a Build or export follows (find, store_save). rows: the rows of
    the world's competition tables (rowkeep.rows_of), which the next version's Build keeps"""
    if number is None:
        number = int((prev or {}).get("number") or 0) + 1
    led = {"format": FORMAT, "format_version": FORMAT_VERSION, "world": world, "version": str(version),
           "number": int(number), "made": made or datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
           "lineage": lineage or (prev or {}).get("lineage") or uuid.uuid4().hex,
           "plan": slim_plan(plan), "players": _player_part(playerids)}
    if test:
        led["test"] = True
    now = ids_of(led["plan"], led["players"])
    led["digest"] = digest(now)
    chain = list((prev or {}).get("chain") or [])
    if prev:
        led["after"] = {k: prev.get(k) for k in ("version", "number", "made")}
        chain.append(dict(led["after"], digest=prev.get("digest") or digest(of_ledger(prev))))
    led["chain"] = chain
    gone = retire_of(prev.get("retire") if prev else {}, retire or {})
    led["retire"] = {kind: {k: why for k, why in gone[kind].items() if not _present(now, kind, k)}
                     for kind in KINDS}
    sp = spent_of(prev) if prev else {"rids": set(), "cids": set()}
    mine = spent_of(led["plan"])
    led["spent"] = {"rids": sorted(sp["rids"] | mine["rids"]), "cids": sorted(sp["cids"] | mine["cids"])}
    if rows is not None:
        led[ROWS_KEY] = rows
    return led


def _present(ids, kind, key):
    if kind in ("clubs", "players", "leagues"):
        return key.isdigit() and int(key) in ids[kind]
    return key in ids[kind]


def shape(q):
    """what a league plays: its size, legs, split, the league above, how many go up and down, its
    play-off and its season (calendar): {field: value} of the fields the plan has"""
    out = {}
    for k in SHAPE:
        if k == "clubs" and isinstance(q.get("teams"), list):
            out[k] = len(q["teams"])
        elif k in q:
            out[k] = q[k]
    return out


def ids_of(plan, playerids):
    """{"clubs": {team id: (name, league)}, "players": {player id: club key}, "leagues": {rid:
    {"name", "cid", "region", "was", "shape"}}, "cups": {cup key: {"cid", "reg", ...}}} of a world's
    plan (whole or slim) and ids file. The clubs are the world's own: not a club of the game in one of
    its leagues (game_clubs), whose id is the game's anyway. The players are those of the world's new
    clubs and the players it added to the game's clubs ("+n"); a game club's own players are the
    game's. "was": the league's names before (built_as), lower case"""
    clubs, leagues = {}, {}
    for key in ("leagues", "others"):
        for q in plan.get(key) or []:
            if not isinstance(q, dict):
                continue
            game = {int(k) for k in (q.get("game_clubs") or {}) if str(k).isdigit()}
            names = q.get("club_names") or []
            for k, t in enumerate(q.get("teams") or []):
                if isinstance(t, int) and k not in game:
                    clubs[t] = (str((names[k] if k < len(names) else "") or ""), str(q.get("name") or ""))
            # review 18.11.2026: a new club taking a game club's places elsewhere (a swap) is the
            # world's own club too -- its id is in a career like any other
            for g in (q.get("game_clubs") or {}).values():
                if isinstance(g, dict) and isinstance(g.get("swap"), dict) and isinstance(g.get("swap_id"), int):
                    clubs.setdefault(g["swap_id"], (str(g["swap"].get("name") or ""),
                                                    "in place of %s" % g.get("id")))
            if key == "leagues" and isinstance(q.get("rid"), int):
                leagues[q["rid"]] = {"name": str(q.get("name") or ""), "cid": q.get("cid"), "region": q.get("region"),
                                     "was": [str(x).strip().lower() for x in q.get("built_as") or []],
                                     "shape": shape(q)}
    cups = {k: dict(v) for k, v in (plan.get("cup_ids") or {}).items() if isinstance(v, dict)}
    players = {}
    for club, keys in ((playerids or {}).get("clubs") or {}).items():
        if not isinstance(keys, dict):
            continue
        game_club = str(club).isdigit()
        for pk, pid in keys.items():
            if game_club and not str(pk).startswith("+"):
                continue
            try:
                players.setdefault(int(pid), club)
            except (TypeError, ValueError):
                pass
    return {"clubs": clubs, "players": players, "leagues": leagues, "cups": cups}


def of_ledger(led):
    """ids_of a ledger, with its "spent" ids (compare: no new league or cup may take one)"""
    out = ids_of(led.get("plan") or {}, led.get("players") or {})
    out["spent"] = spent_of(led)
    return out


def _same_league(o, n):
    """the league under one regulation id in two versions is the same league: the same name, or
    the new one was built as the old one's name (a rename, project.rename_league)"""
    on, nn = str(o.get("name") or "").strip().lower(), str(n.get("name") or "").strip().lower()
    return on == nn or on in (n.get("was") or [])


def _cup_league(key):
    kind, _, name = str(key).partition(":")
    return kind, name


def compare(old, new, retire=None):
    """what of world `old` (ids_of, of_ledger) world `new` does not keep: {kind: [(id, what it was,
    why)]}, why "gone" or what changed; nothing listed in retire (retire_of) counts. A league under
    the same regulation id must be the same league (_same_league). Also "reused": an id of old's
    "spent" (an id a league or cup of an earlier version had) or of `retire` that new gives to
    something else. {} when the careers of old go on in new. Only a "gone" id can be retired"""
    retire = retire or empty_retire()
    out = {}

    def bad(kind, key, what, why):
        out.setdefault(kind, []).append((key, what, why))
    for t, (nm, lg) in sorted(old["clubs"].items()):
        if t not in new["clubs"] and str(t) not in retire["clubs"]:
            bad("clubs", t, "%s (%s)" % (nm, lg) if lg else nm, "gone")
    for rid, o in sorted(old["leagues"].items()):
        n = new["leagues"].get(rid)
        if str(rid) in retire["leagues"] and (n is None or not _same_league(o, n)):
            continue                      # retired; another league on its id is "reused" below
        if n is None:
            bad("leagues", rid, o["name"], "gone")
        elif not _same_league(o, n):
            bad("leagues", rid, o["name"], "its regulation id is %s's now" % n.get("name"))
        elif n.get("cid") != o.get("cid"):
            bad("leagues", rid, o["name"], "competition id %s -> %s" % (o.get("cid"), n.get("cid")))
        elif o.get("region") is not None and n.get("region") is not None and n["region"] != o["region"]:
            bad("leagues", rid, o["name"], "region %s -> %s" % (o["region"], n["region"]))
    # a cup is keyed by its league's name ("cup:<league>"): a renamed league's cup is found under
    # the new name of the league that has the same regulation id
    renamed = {}
    for rid, n in new["leagues"].items():
        o = old["leagues"].get(rid)
        if o and _same_league(o, n) and o["name"] != n["name"]:
            renamed[n["name"]] = o["name"]
    as_old = {}
    for key, n in new["cups"].items():
        kind, name = _cup_league(key)
        as_old["%s:%s" % (kind, renamed[name]) if name in renamed else key] = (key, n)
    for key, o in sorted(old["cups"].items()):
        got = as_old.get(key)
        if got is None:
            if key not in retire["cups"]:
                bad("cups", key, key, "gone")
            continue
        n = got[1]
        if n.get("cid") != o.get("cid") or _cup_regs(n) != _cup_regs(o):
            bad("cups", key, key, "ids %s/%s -> %s/%s" % (o.get("cid"), _cup_regs(o), n.get("cid"), _cup_regs(n)))
    for pid, club in sorted(old["players"].items()):
        if pid not in new["players"] and str(pid) not in retire["players"]:
            bad("players", pid, club, "gone")
    # ids given to something else: a retired club or player id, a league's or cup's id of old (or
    # of any version before it: spent) on another league or cup
    for kind in ("clubs", "players"):
        for k in retire[kind]:
            if k.isdigit() and int(k) in new[kind] and int(k) not in old[kind]:
                bad("reused", "%s %s" % (kind[:-1], k), str(new[kind][int(k)]), "a retired id given again")
    spent = old.get("spent") or {"rids": set(), "cids": set()}
    rid_of, cid_of = {}, {}
    for rid, o in old["leagues"].items():
        rid_of[rid] = ("league", rid, o["name"])
        if isinstance(o.get("cid"), int):
            cid_of[o["cid"]] = ("league", rid, o["name"])
    for key, o in old["cups"].items():
        if isinstance(o.get("cid"), int):
            cid_of[o["cid"]] = ("cup", key, key)
        for r in _cup_regs(o):
            rid_of[r] = ("cup", key, key)
    for rid, n in sorted(new["leagues"].items()):
        mine = ("league", rid)
        was = rid_of.get(rid)
        if (was is None and rid in spent["rids"] or str(rid) in retire["leagues"]
                and (rid not in old["leagues"] or not _same_league(old["leagues"][rid], n))):
            bad("reused", "league %s" % rid, n["name"], "a regulation id an earlier version gave")
        elif was is not None and was[:2] != mine:
            bad("reused", "league %s" % rid, n["name"], "the regulation id of %s" % was[2])
        c = n.get("cid")
        owner = cid_of.get(c)
        o = old["leagues"].get(rid)
        same_owner = owner is not None and owner[0] == "league" and (owner[1] == rid or (o and _same_league(o, n)))
        if owner is not None and not same_owner:
            bad("reused", "league %s" % rid, n["name"], "competition id %s of %s" % (c, owner[2]))
        elif owner is None and c in spent["cids"]:
            bad("reused", "league %s" % rid, n["name"], "competition id %s an earlier version gave" % c)
    for ko, (key, n) in sorted(as_old.items()):
        for r in _cup_regs(n):
            owner = rid_of.get(r)
            if owner is not None and owner[:2] != ("cup", ko):
                bad("reused", "cup %s" % key, key, "regulation id %s of %s" % (r, owner[2]))
            elif owner is None and r in spent["rids"]:
                bad("reused", "cup %s" % key, key, "regulation id %s an earlier version gave" % r)
        c = n.get("cid")
        owner = cid_of.get(c)
        if owner is not None and owner[:2] != ("cup", ko):
            bad("reused", "cup %s" % key, key, "competition id %s of %s" % (c, owner[2]))
        elif owner is None and c in spent["cids"]:
            bad("reused", "cup %s" % key, key, "competition id %s an earlier version gave" % c)
    return out


def structure_changes(old, new):
    """[(rid, league name now, [fields])] of the leagues both versions have whose shape (size,
    legs, split, the league above, up and down, play-off, season) differs: a career of the old one
    has a season of that league running, laid out the old way"""
    out = []
    for rid, o in sorted(old["leagues"].items()):
        n = new["leagues"].get(rid)
        if not n or not _same_league(o, n):
            continue
        a, b = o.get("shape") or {}, n.get("shape") or {}
        diff = [k for k in SHAPE if k in a and k in b and a[k] != b[k]]
        if diff:
            out.append((rid, n["name"], diff))
    return out


def renamed(old, new):
    """[(team id, old name, new name)] of the clubs that kept their id under another name"""
    return [(t, o[0], new["clubs"][t][0]) for t, o in sorted(old["clubs"].items())
            if t in new["clubs"] and o[0] and new["clubs"][t][0] and o[0] != new["clubs"][t][0]]


def same_names(old, new):
    """(clubs, leagues): the share of old's clubs that have the same name under the same team id in
    new, and of its leagues under the same regulation id (_same_league); 1.0 for none"""
    def share(n, of):
        return n / of if of else 1.0
    c = sum(1 for t, (nm, _lg) in old["clubs"].items()
            if t in new["clubs"] and nm.strip().lower() == new["clubs"][t][0].strip().lower())
    lg = sum(1 for r, o in old["leagues"].items() if r in new["leagues"] and _same_league(o, new["leagues"][r]))
    return share(c, len(old["clubs"])), share(lg, len(old["leagues"]))


def counts(probs):
    return {k: len(v) for k, v in probs.items()}


def problem_lines(probs, limit=20):
    """the problems of compare, as lines: the first `limit` of each kind"""
    out = []
    label = {"clubs": "club", "players": "player", "leagues": "league", "cups": "cup", "reused": "id"}
    for kind in ("leagues", "cups", "clubs", "players", "reused"):
        rows = probs.get(kind) or []
        for key, what, why in rows[:limit]:
            out.append("%s %s: %s -- %s" % (label[kind], key, what, why))
        if len(rows) > limit:
            out.append("... and %d more %s" % (len(rows) - limit, kind))
    return out


def summary(probs):
    """"3 clubs, 298 players" """
    order = ("leagues", "cups", "clubs", "players", "reused")
    word = {"reused": ("id given again", "ids given again")}
    return ", ".join("%d %s" % (len(probs[k]), word.get(k, (k[:-1], k))[len(probs[k]) != 1])
                     for k in order if probs.get(k))


def retire_entries(probs, reason):
    """the recipe's "id_retire" entries that let the ids compare found gone go, with `reason`.
    Only an id that is gone can go: one whose number changed, or that another league has now, is
    not listed (it has to be put back)"""
    out = {}
    for kind in KINDS:
        for key, _what, why in probs.get(kind) or []:
            if why == "gone":
                out.setdefault(kind, {})[str(key)] = reason
    return out


def add_retire(recipe, entries):
    """the entries (retire_entries) into recipe["id_retire"]; returns how many were new"""
    have = recipe.setdefault(RETIRE_KEY, {})
    n = 0
    for kind, rows in entries.items():
        mine = have.setdefault(kind, {})
        for k, why in rows.items():
            if k not in mine:
                mine[k] = why
                n += 1
    return n


def unknown_retire(recipe_retire, old, led_retire=None):
    """{kind: [id]} of the recipe's id_retire entries that name an id the ledger's version does not
    have and no version before it retired: they say nothing (a typo, or an id of another world), and
    are left out of the check (a retired id that is somebody's would read as "given again")"""
    led_retire = retire_of(led_retire or {})
    out = {}
    for kind, rows in retire_of(recipe_retire or {}).items():
        for k in rows:
            if not _present(old, kind, k) and k not in led_retire[kind]:
                out.setdefault(kind, []).append(k)
    return out


def drop_entries(retire, unknown):
    """retire (retire_of) less the unknown entries"""
    return {kind: {k: v for k, v in rows.items() if k not in set(unknown.get(kind) or [])}
            for kind, rows in retire.items()}


def mass_losses(probs, led, new):
    """[(team id, club name, players gone, players it had)] of the clubs of the ledger's version that
    are still in the world (new: ids_of) and lost most of their players (MASS_SHARE, at least
    MASS_MIN): a sign that their squad moved to another key Build did not follow, not of players
    taken out on purpose -- retiring them would lose a whole squad's ids"""
    kt = club_tids(led.get("plan") or {})
    old = ids_of(led.get("plan") or {}, led.get("players") or {})
    had, lost = {}, {}

    def tid(club):
        return int(club) if str(club).isdigit() else kt.get(club)
    for pid, club in old["players"].items():
        t = tid(club)
        if t is not None:
            had[t] = had.get(t, 0) + 1
    for pid, club, why in probs.get("players") or []:
        t = tid(club)
        if t is not None and why == "gone":
            lost[t] = lost.get(t, 0) + 1
    out = []
    for t, n in sorted(lost.items()):
        still = t in new["clubs"] or not str(t) in {str(x) for x in old["clubs"]}
        if still and n >= MASS_MIN and n >= MASS_SHARE * had.get(t, n):
            nm = (new["clubs"].get(t) or old["clubs"].get(t) or (str(t), ""))[0]
            out.append((t, nm, n, had.get(t, n)))
    return out


# ---- Check the plan, before a Build ----

def plan_warnings(pl, led, retire=None):
    """what a Build of plan `pl` pinned to ledger `led` will most likely find gone, said before the
    Build (Check the plan): the leagues and cups that are not in the plan or have other ids, and
    the clubs no league of the plan keeps (its name is in the world no more, and its place in its
    league is gone or taken by a club of another name that was there too). The players are counted
    by Build itself; this is a warning, Build's check is the one that counts"""
    retire = retire_of(led.get("retire") or {}, retire or {})
    old = ids_of(led.get("plan") or {}, led.get("players") or {})
    new_leagues = {p["rid"]: {"name": p.get("name"), "cid": p.get("cid"), "region": p.get("region"),
                              "was": [str(x).strip().lower() for x in p.get("built_as") or []]}
                   for p in pl.get("leagues") or [] if isinstance(p.get("rid"), int)}
    probs = compare(dict(old, clubs={}, players={}, cups={}),
                    {"clubs": {}, "players": {}, "leagues": new_leagues, "cups": {}}, retire)
    probs.pop("reused", None)
    names_now = {}
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):
        for x in p.get("club_names") or []:
            x = str(x or "").strip().lower()
            if x:
                names_now[x] = names_now.get(x, 0) + 1
    kept = set()
    for p in (pl.get("leagues") or []) + (pl.get("others") or []):
        prev, was = p.get("prev_teams") or [], p.get("prev_names") or []
        cur = [str(x or "").strip().lower() for x in p.get("club_names") or []]
        for k, nm in enumerate(cur):
            if nm and nm in was:
                j = was.index(nm)
            elif k < len(was) and not names_now.get(was[k]):
                j = k
            else:
                j = None
            if j is not None and j < len(prev) and isinstance(prev[j], int):
                kept.add(prev[j])
    moved = {str(nm).strip().lower(): t for nm, t in (pl.get("prev_clubs") or {}).items()}
    kept |= {t for nm, t in moved.items() if names_now.get(nm) == 1}
    for t, (nm, lg) in sorted(old["clubs"].items()):
        if t not in kept and str(t) not in retire["clubs"]:
            probs.setdefault("clubs", []).append((t, "%s (%s)" % (nm, lg), "not in the plan"))
    return probs


# ---- where the ledger is ----

def store_dir():
    """<APPDATA>\\FL26ModStudio\\recipes\\ledgers: the ledgers of the worlds this PC shared.
    FL26_LEDGER_STORE (review 3, 18.11.2026: for the tests) puts it elsewhere -- an export of a test
    must never land in this PC's real history"""
    if os.environ.get("FL26_LEDGER_STORE"):
        return os.environ["FL26_LEDGER_STORE"]
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FL26ModStudio", "recipes", "ledgers")


def store_path(world):
    """the one copy a Mod Studio of 17.11.2026 kept (before the history): read, never written"""
    return os.path.join(store_dir(), world + EXT)


def store_file(led):
    """<world>.<lineage, 12 letters>.<number>.fl26ids: one file a version (store_save)"""
    return os.path.join(store_dir(), "%s.%s.%d%s" % (led["world"], str(led.get("lineage") or "none")[:12],
                                                     int(led.get("number") or 0), EXT))


_STORE_NAME = re.compile(r"^(?P<world>.+)\.(?P<lin>[0-9a-z]{1,12})\.(?P<n>\d+)" + re.escape(EXT) + "$")


def store_files(world):
    """[(number, lineage prefix, path)] of the versions of `world` this PC keeps, the legacy single
    copy as (0, None, path) -- the number of that one is in the file"""
    out = []
    d = store_dir()
    # review 18.11.2026: the world's folder is the same one whatever the case of its name (Windows):
    # "_FL26mine" finds the ledgers of "_FL26Mine"
    # review 3, 18.11.2026: any *.fl26ids put in the folder counts (the stop text says "put the file of
    # the version shared last in ..."; a copy keeps its own name, _FL26Megapack-beta3.fl26ids): a file
    # without the history's name is told by what it says of itself (world, lineage, number)
    for p in glob.glob(os.path.join(glob.escape(d), "*" + EXT)):
        base = os.path.basename(p)
        m = _STORE_NAME.match(base)
        if m:
            if m.group("world").lower() == world.lower():
                out.append((int(m.group("n")), m.group("lin"), p))
            continue
        if base.lower() == (world + EXT).lower():
            out.append((0, None, p))          # the legacy single copy: its number is in the file
            continue
        head = _head(p)
        if head and str(head.get("world") or "").lower() == world.lower():
            lin = str(head.get("lineage") or "")[:12] or None
            out.append((int(head.get("number") or 0), lin, p))
    return sorted(out, key=lambda x: x[0])


_HEAD = {k: re.compile(r'"%s"\s*:\s*(?:"((?:[^"\\]|\\.)*)"|(\d+))' % k) for k in ("world", "lineage", "number")}


def _head(path, size=8192):
    """{world, lineage, number} a ledger file says at its start (save() writes them first), without
    reading the rest -- a GigaPack ledger is 26 MB. A file whose start does not say its world is read
    whole; one that is not a ledger gives None"""
    try:
        with open(path, "rb") as f:
            text = f.read(size).decode("utf-8", "replace")
    except OSError:
        return None
    if '"fl26ids-ledger"' not in text:
        return None
    out = {}
    for k, rx in _HEAD.items():
        m = rx.search(text)
        if m:
            out[k] = json.loads('"%s"' % m.group(1)) if m.group(1) is not None else int(m.group(2))
    if "world" in out and "lineage" in out:
        return out
    try:
        with open(path, encoding="utf-8") as f:
            led = json.load(f)
    except (OSError, ValueError):
        return None
    return {k: led.get(k) for k in ("world", "lineage", "number")} if isinstance(led, dict) else None


def store_save(led):
    """the ledger into this PC's history of the versions it shared; the path. A test zip's is not
    kept (it is never the version a Build or export follows)"""
    if led.get("test"):
        raise LedgerError("version %s is a test zip: its ledger is not kept as a version shared" % led.get("version"))
    note_issued(led)
    return save(led, store_file(led))


def issued_file(world, lineage):
    """<world>.<lineage, 12 letters>.issued: the numbers exports of the lineage gave"""
    return os.path.join(store_dir(), "%s.%s%s" % (world, str(lineage or "none")[:12], ISSUED))


def issued(world, lineage):
    """the numbers exports of `lineage` gave on this PC (test zips and zips not kept too)"""
    try:
        with open(issued_file(world, lineage), encoding="utf-8") as f:
            got = json.load(f)
    except (OSError, ValueError):
        return set()
    return {n for n in (got.get("numbers") if isinstance(got, dict) else None) or []
            if isinstance(n, int) and not isinstance(n, bool)}


def note_issued(led):
    """the ledger's number into issued(): no later export of the lineage gives it again"""
    have = issued(led["world"], led.get("lineage"))
    n = int(led.get("number") or 0)
    if n in have:
        return
    save({"world": led["world"], "lineage": led.get("lineage"), "numbers": sorted(have | {n})},
         issued_file(led["world"], led.get("lineage")))


def next_number(world, prev):
    """the number of the version an export after `prev` makes: one up from prev's and from every
    number its lineage gave on this PC -- a test zip's, a zip not kept, a version whose file is gone
    (review 18.11.2026: two zips of a lineage under one number, an Update between them went wrong)"""
    lin = (prev or {}).get("lineage")
    top = int((prev or {}).get("number") or 0)
    if lin:
        top = max([top] + list(issued(world, lin)) +
                  [n for n, l, _p in store_files(world) if l and lin.startswith(l)])
    return top + 1


def _need(led, path):
    for k, kind in (("world", str), ("version", str), ("number", int), ("plan", dict), ("players", dict)):
        if not isinstance(led.get(k), kind) or (kind is int and isinstance(led.get(k), bool)):
            raise LedgerError("%s is not a whole id ledger (%s)" % (path, k))
    for k in ("leagues", "others", "away_leagues"):
        if not isinstance(led["plan"].get(k, []), list) or not all(isinstance(q, dict) for q in led["plan"].get(k) or []):
            raise LedgerError("%s is not a whole id ledger (plan %s)" % (path, k))
    if not isinstance(led["plan"].get("cup_ids", {}), dict):
        raise LedgerError("%s is not a whole id ledger (plan cup_ids)" % path)
    if not isinstance(led.get("retire", {}), dict) or not isinstance(led.get("chain", []), list):
        raise LedgerError("%s is not a whole id ledger (retire, chain)" % path)
    # review 18.11.2026: a ledger that is JSON but not whole (chain ["x"]) stopped Install with an
    # AttributeError -- every part is checked here
    if not all(isinstance(c, dict) for c in led.get("chain") or []):
        raise LedgerError("%s is not a whole id ledger (chain)" % path)
    if not all(isinstance(v, dict) for v in (led.get("retire") or {}).values()):
        raise LedgerError("%s is not a whole id ledger (retire)" % path)
    for k in ("lineage", "digest", "made"):
        if led.get(k) is not None and not isinstance(led[k], str):
            raise LedgerError("%s is not a whole id ledger (%s)" % (path, k))
    sp = led.get("spent", {})
    if not isinstance(sp, dict) or not all(isinstance(sp.get(k, []), list) for k in ("rids", "cids")):
        raise LedgerError("%s is not a whole id ledger (spent)" % path)
    if not isinstance(led["players"].get("clubs", {}), dict):
        raise LedgerError("%s is not a whole id ledger (players)" % path)


def load(path, world=None):
    """the ledger in `path` (None when there is no file); LedgerError when it is not one, or one
    of another world"""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            led = json.load(f)
    except (OSError, ValueError) as e:
        raise LedgerError("%s cannot be read: %s" % (path, e))
    if not isinstance(led, dict) or led.get("format") != FORMAT:
        raise LedgerError("%s is not an id ledger of a world" % path)
    try:
        fv = int(led.get("format_version") or 0)
    except (TypeError, ValueError):
        raise LedgerError("%s is not an id ledger of a world (format_version)" % path)
    if fv < 1:
        raise LedgerError("%s is not an id ledger of a world (format_version)" % path)
    if fv > FORMAT_VERSION:
        raise LedgerError("%s is an id ledger of a newer Mod Studio" % path)
    _need(led, path)
    if world and str(led.get("world")).lower() != world.lower():
        raise LedgerError("%s is the id ledger of %s, not of %s" % (path, led.get("world"), world))
    return led


def save(led, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    return path


def recipe_like(led, recipe):
    """(leagues, clubs): the share of the ledger's leagues the recipe has (by name, or a name it was
    built as) and of its clubs' names the recipe's leagues list"""
    names, clubs = set(), set()
    for L in recipe.get("leagues") or []:
        if not isinstance(L, dict):
            continue
        names.add(str(L.get("name") or "").strip().lower())
        names |= {str(x).strip().lower() for x in L.get("built_as") or []}
        clubs |= {str(x or "").strip().lower() for x in L.get("club_names") or [] if str(x or "").strip()}
    ln = [str(q.get("name") or "").strip().lower() for q in (led.get("plan") or {}).get("leagues") or []]
    cn = [str(x or "").strip().lower() for q in (led.get("plan") or {}).get("leagues") or []
          for x in q.get("club_names") or [] if str(x or "").strip()]
    return (sum(1 for x in ln if x in names) / len(ln) if ln else 0.0,
            sum(1 for x in cn if x in clubs) / len(cn) if cn else 0.0)


def recipe_of_world(livecpk, world):
    """what find() tells a world's ledgers by, of the world built in livecpk/<world> (its plan): its
    leagues' names, names before and clubs, and the recipe's id_lineage and id_ledger the plan kept
    (RECIPE_SETTINGS) -- for an export of a world that is not the recipe open now. {"world"} when
    it has no plan"""
    plan, _p = world_ids(os.path.join(livecpk, world)) if livecpk else (None, None)
    if not isinstance(plan, dict):
        return {"world": world}
    out = {k: v for k, v in (plan.get("settings") or {}).items()
           if k in (LINEAGE_KEY, LEDGER_KEY, VERSION_KEY, NOT_LINEAGES_KEY)}
    if not own_ledger_there(out):
        out.pop(LEDGER_KEY, None)         # a path of another PC (an export cuts it to "source/..."): not a stop
    out["world"] = world
    out["leagues"] = [{"name": q.get("name"), "built_as": list(q.get("built_as") or []),
                       "club_names": list(q.get("club_names") or [])}
                      for q in plan.get("leagues") or [] if isinstance(q, dict)]
    del plan
    return out


def own_ledger_there(recipe):
    """whether the recipe's id_ledger, as a built plan kept it (an absolute path), is a file of this PC"""
    own = str(recipe.get(LEDGER_KEY) or "").strip()
    return bool(own) and os.path.isabs(own) and os.path.isfile(own)


def absolute_ledger(recipe, recipe_path=None):
    """the recipe with its id_ledger as the absolute path find() takes it from (review 3, 18.11.2026):
    plan() keeps the key in the world's plan (RECIPE_SETTINGS), and an export of the world without
    its recipe (release.py, coldstart) finds the ledger by it. The recipe itself as it is when the key
    is not set or not found. The same for id_tables (a zip or a world folder)"""
    out = recipe
    for key in (LEDGER_KEY, TABLES_KEY):
        own = str(recipe.get(key) or "").strip()
        if not own or os.path.isabs(own):
            continue
        tries = []
        if recipe_path:
            tries.append(os.path.join(os.path.dirname(os.path.abspath(recipe_path)), own))
        tries.append(os.path.join(os.path.dirname(store_dir()), own))
        there = next((p for p in tries if os.path.isfile(p) or (key == TABLES_KEY and os.path.isdir(p))), None)
        if there:
            out = dict(out, **{key: os.path.abspath(there)})
    return out


def stamp_plan(root, settings):
    """the built plan of the world in `root` (leaguebuilder-plan.json) gets `settings` ({key: value},
    None takes a key out) in its "settings", so recipe_of_world reads them: the lineage an export
    gave the world, or what the author said of a lineage (Build's question). True when it changed"""
    import bigjson
    path = os.path.join(root, PLAN)
    try:
        with open(path, encoding="utf-8") as f:
            plan = bigjson.load(f)
    except (OSError, ValueError):
        return False
    if not isinstance(plan, dict):
        return False
    st = plan.setdefault("settings", {})
    if all(st.get(k) == v for k, v in settings.items()):
        return False
    for k, v in settings.items():
        if v is None:
            st.pop(k, None)
        else:
            st[k] = v
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1)      # as Build writes it
    os.replace(tmp, path)
    return True


def find(recipe, recipe_path=None, livecpk=None, notes=None):
    """(path, ledger) a Build of `recipe` pins to, or (None, None). The candidates: the recipe's
    "id_ledger" (a path relative to the recipe's folder, else to the kept recipes' folder), this
    PC's history of the versions of the world it shared (store_files), and -- a world from a zip
    made editable here -- the ledger its zip brought (livecpk\\<world>\\fl26ids-ledger.json). Only
    the ledgers of the recipe's lineage ("id_lineage", else the one of its id_ledger) count; a recipe
    with neither takes those whose leagues or clubs are its own (recipe_like, RECIPE_LIKE) -- another
    author's world of the same name is not. Of those the latest version (number, then made).
    notes: a list that gets a line for each ledger left out and for a ledger taken from livecpk"""
    notes = notes if notes is not None else []
    world = str(recipe.get("world") or "").strip()
    if not world:
        return None, None
    own = str(recipe.get(LEDGER_KEY) or "").strip()
    tries = []
    if own:
        if os.path.isabs(own):
            tries.append(own)
        else:
            if recipe_path:
                tries.append(os.path.join(os.path.dirname(os.path.abspath(recipe_path)), own))
            tries.append(os.path.join(os.path.dirname(store_dir()), own))
    named = next(((p, led) for p in tries for led in [load(p, world)] if led is not None), (None, None))
    if own and named[0] is None:
        raise LedgerError("the recipe's id_ledger %s is not there" % own)
    if named[1] is not None and named[1].get("test"):
        raise LedgerError("the recipe's id_ledger %s is the ledger of a test zip (%s): a test zip is never the "
                          "version a Build follows -- name the ledger of the version shared last"
                          % (named[0], named[1].get("version")))
    lineage = str(recipe.get(LINEAGE_KEY) or "").strip() or (named[1] or {}).get("lineage")
    nots = {str(x).strip() for x in recipe.get(NOT_LINEAGES_KEY) or [] if str(x).strip()}
    cands = [named] if named[1] is not None else []
    # review 18.11.2026: only the newest readable version of each lineage is read (a GigaPack ledger
    # is 8.5 MB: Check the plan read every one). The newest one that cannot be read stops Build and
    # export: past it, the next export would take that version's number again
    groups = {}
    for n, lin, p in store_files(world):
        if lineage and lin and not lineage.startswith(lin):
            notes.append("ids: %s is left out: another lineage of %s, not this recipe's" % (p, world))
            continue
        if lin and any(x.startswith(lin) for x in nots):
            notes.append("ids: %s is left out: the recipe says that lineage is another world (id_not_lineages)" % p)
            continue
        groups.setdefault(lin, []).append((n, p))
    for lin, files in groups.items():
        for k, (n, p) in enumerate(sorted(files, reverse=True)):
            try:
                led = load(p, world)
            except LedgerError as e:
                if lin is None:           # the one copy of 17.11. (store_path): it never had a number
                    notes.append("ids: %s is left out: %s" % (p, e))
                    break
                raise LedgerError("%s cannot be used: %s. It is the newest version this PC keeps of %s (number %d): "
                                  "put a good copy of it back, or move it out of %s if that version was never "
                                  "shared, and Build or export again" % (p, e, world, n, store_dir()))
            if led.get("test"):
                notes.append("ids: %s is left out: version %s is a test zip" % (p, led.get("version")))
                continue
            cands.append((p, led))
            break
    store_any = bool(cands)
    if livecpk:
        p = os.path.join(livecpk, world, LEDGER)
        try:
            led = load(p, world)
        except LedgerError as e:
            notes.append("ids: %s is left out: %s" % (p, e))
            led = None
        if led is not None and led.get("test"):
            notes.append("ids: %s is left out: version %s is a test zip" % (p, led.get("version")))
        elif led is not None:
            cands.append((p, led))
    keep, between = [], []
    for i, (p, led) in enumerate(cands):
        if lineage:
            if led.get("lineage") != lineage:
                notes.append("ids: %s is left out: another lineage of %s (version %s), not this recipe's"
                             % (p, world, led.get("version")))
                continue
        elif led.get("lineage") in nots:
            notes.append("ids: %s is left out: the recipe says that lineage is another world (id_not_lineages)" % p)
            continue
        elif not (i == 0 and named[1] is not None):
            like = recipe_like(led, recipe)
            if max(like) < RECIPE_UNLIKE:
                notes.append("ids: %s is left out: version %s has other leagues and clubs (%d%% of its leagues, "
                             "%d%% of its clubs are this recipe's) -- another world of the same name"
                             % (p, led.get("version"), round(100 * like[0]), round(100 * like[1])))
                continue
            if max(like) < RECIPE_LIKE:
                between.append((p, led, like))
                continue
        keep.append((p, led))
    if not keep and between:
        # review 17.11.2026: half the leagues replaced reads like another world -- left out, the
        # Build would hand the old leagues' ids to the new ones without a word. Stop and ask instead
        p, led, like = max(between, key=lambda x: _order(x[1]))
        raise LedgerAsk("version %s of %s (%s) has %d%% of this recipe's leagues and %d%% of its clubs: is this "
                        "recipe that world (its next version), or another world of the same name? Mod Studio asks; "
                        "in the recipe itself: \"id_lineage\": \"%s\" for that world, \"id_not_lineages\": [\"%s\"] for another"
                        % (led.get("version"), world, p, round(100 * like[0]), round(100 * like[1]),
                           led.get("lineage"), led.get("lineage")),
                        led.get("lineage"), led.get("version"), p)
    for p, led, like in between:
        notes.append("ids: %s is left out: version %s has other leagues and clubs (%d%% of its leagues, "
                     "%d%% of its clubs are this recipe's) -- another world of the same name"
                     % (p, led.get("version"), round(100 * like[0]), round(100 * like[1])))
    if not keep:
        if lineage:
            # review 18.11.2026: a recipe that names its lineage was shared before. Without a ledger of
            # it (another PC, APPDATA new, the world's name changed) the export started a new lineage
            # and every player of the version before got "another world"
            raise LedgerError("the recipe's id_lineage is %s, but this PC has no id ledger of it: put the .fl26ids "
                              "file of the version shared last in %s (or set the recipe's id_ledger to it) and Build "
                              "or export again. To start over as a new world (careers of the versions shared before "
                              "do not go on), take id_lineage out of the recipe" % (lineage, store_dir()))
        return None, None
    path, led = max(keep, key=lambda x: _order(x[1]))
    if livecpk and os.path.normcase(os.path.abspath(path)) == os.path.normcase(
            os.path.abspath(os.path.join(livecpk, world, LEDGER))):
        notes.append("ids: this PC keeps no version of %s it shared%s; pinned to the ledger its zip brought "
                     "(%s, version %s)" % (world, "" if not store_any else " of this lineage", path, led.get("version")))
    return path, led


def _order(led):
    return (int(led.get("number") or 0), str(led.get("made") or ""))


def default_version(recipe, prev):
    """the version name export offers: the recipe's "pack_version", else the number after the
    last shared one's and the date ("2 (17.11.2026)")"""
    v = str(recipe.get(VERSION_KEY) or "").strip()
    if v:
        return v
    n = int((prev or {}).get("number") or 0) + 1
    return "%d (%s)" % (n, datetime.date.today().strftime("%d.%m.%Y"))


# ---- a built world ----

def world_ids(root):
    """(plan, ids file) of the world folder `root` (leaguebuilder-plan.json, fl26playerids.json);
    the plan is None without one"""
    import bigjson
    try:
        with open(os.path.join(root, PLAN), encoding="utf-8") as f:
            plan = bigjson.load(f)
    except (OSError, ValueError):
        plan = None
    try:
        with open(os.path.join(root, PLAYER_IDS), encoding="utf-8") as f:
            pids = json.load(f)
    except (OSError, ValueError):
        pids = {}
    return plan, pids if isinstance(pids, dict) else {}


def of_world(root, world, version, prev=None, retire=None, number=None, lineage=None, made=None):
    """the ledger of the built world in folder `root` (make); None when it has no plan"""
    plan, pids = world_ids(root)
    if not isinstance(plan, dict):
        return None
    led = make(plan, pids, world, version, number=number, prev=prev, retire=retire, lineage=lineage, made=made)
    del plan
    return led


def installed_ids(root):
    """ids_of the world installed in `root`: of the ledger its zip brought (of_ledger), else of its
    plan and ids file (a world from a zip of before the ledger); (None, None) when neither is there"""
    try:
        led = load(os.path.join(root, LEDGER))
    except LedgerError:
        led = None
    if led is not None:
        return of_ledger(led), led
    plan, pids = world_ids(root)
    if not isinstance(plan, dict):
        return None, None
    return ids_of(plan, pids), None


def update_verdict(old, old_led, new_led):
    """can a world whose ledger is `new_led` go in over the one installed (old: installed_ids, and
    its ledger or None) as an Update -- do the careers of the installed version go on in it?
    {"ok", "why", "to", "from", "first", "gone": {kind: n}, "retired": {kind: n}, "reasons": [the
    author's reasons of the retired ids, a few], "retired_names": {kind: [names]}, "changed": [league
    names whose shape differs], "match": how the worlds were told to be one ("lineage", "digest",
    "names"), "new_leagues" / "new_cups": how many the installed version does not have}. why: None
    (an Update), "plan" (the installed world's ids cannot be read), "other" (another world of the
    same name), "older" / "same" (not a later version), "broken" (ids of the installed version gone
    or changed), "retired" (a club, league or cup of it retired: a career that has it does not go
    on); installer.update_check adds "rows" (rowkeep: its competition rows moved or changed)."""
    out = {"to": new_led.get("version"), "from": (old_led or {}).get("version"), "first": not new_led.get("after"),
           "gone": {}, "retired": {}, "reasons": [], "retired_names": {}, "changed": [], "match": None, "why": None,
           "new_leagues": 0, "new_cups": 0}
    if old is None:
        return dict(out, ok=False, why="plan", gone={"plan": 1})
    chain = {c.get("digest") for c in new_led.get("chain") or [] if c.get("digest")}
    if old_led is not None and old_led.get("lineage") and new_led.get("lineage"):
        if old_led["lineage"] != new_led["lineage"]:
            return dict(out, ok=False, why="other")
        out["match"] = "lineage"
        if int(new_led.get("number") or 0) < int(old_led.get("number") or 0):
            return dict(out, ok=False, why="older")
        if _order(new_led) == _order(old_led) and (old_led.get("digest") or digest(old)) == new_led.get("digest"):
            return dict(out, ok=False, why="same")
        # review 18.11.2026: two zips of one lineage can both follow one version (a test zip and the
        # real one; a world made editable and shared on another PC): the newer number is not this
        # one's next version unless the installed one is in its chain (or the ids are the same)
        od = old_led.get("digest") or digest(old)
        if od != new_led.get("digest") and od not in chain:
            return dict(out, ok=False, why="diverged", test=bool(old_led.get("test")))
    else:
        d = (old_led or {}).get("digest") or digest(old)
        # review 3, 18.11.2026: the installed world (from a zip without a ledger) has the ids of this
        # zip: the same one only when this is the lineage's first version; a later one (a fix with the
        # same ids: kits, crests, ratings) goes on from it -- an Update
        later = bool(new_led.get("after") or new_led.get("chain"))
        if d == new_led.get("digest") and not later:
            return dict(out, ok=False, why="same", match="digest")
        if d == new_led.get("digest") or d in chain:
            out["match"] = "digest"
            if not out["from"]:           # the installed one's name: the version of the chain with its ids
                was = [c for c in new_led.get("chain") or [] if c.get("digest") == d]
                aft = new_led.get("after") or {}
                out["from"] = (was[-1].get("version") if was else
                               aft.get("version") if aft.get("digest") == d else None)
        else:
            new_ids = ids_of(new_led["plan"], new_led["players"])
            c, lg = same_names(old, new_ids)
            out["same_names"] = (round(c, 3), round(lg, 3))
            if lg < SAME_NAMES:
                return dict(out, ok=False, why="other")
            if c < SAME_NAMES:
                # review 18.11.2026: clubs renamed under their ids (3 of 20) read as "another world";
                # when every id of the installed one is kept and at least half its clubs have their
                # names, it is the same world with clubs renamed
                if c < SAME_NAMES_IDS or compare(dict(old, spent=old.get("spent") or {"rids": set(), "cids": set()}), new_ids,
                           retire_of(new_led.get("retire") or {})):
                    return dict(out, ok=False, why="other")
                out["match"] = "ids"
            else:
                out["match"] = "names"
            del new_ids
    new = of_ledger(new_led)
    out["renamed"] = renamed(old, new)
    # 18.11.2026 evening: the leagues and cups the installed version does not have (Install: they come
    # only in a new Master League)
    out["new_leagues"] = len(set(new["leagues"]) - set(old["leagues"]))
    out["new_cups"] = len(set(new["cups"]) - set(old["cups"]))
    retire = retire_of(new_led.get("retire") or {})
    probs = compare(dict(old, spent=old.get("spent") or spent_of({"leagues": [], "cup_ids": {}})), new, retire)
    out["gone"] = counts(probs)
    reasons = []
    for kind in KINDS:
        ids = [k for k in retire[kind] if _present(old, kind, k) and not _present(new, kind, k)]
        if ids:
            out["retired"][kind] = len(ids)
            for k in ids:
                if retire[kind][k] not in reasons:
                    reasons.append(retire[kind][k])
            if kind == "clubs":
                out["retired_names"][kind] = [old["clubs"][int(k)][0] for k in ids[:10]]
            elif kind == "leagues":
                out["retired_names"][kind] = [old["leagues"][int(k)]["name"] for k in ids[:10]]
            elif kind == "cups":
                out["retired_names"][kind] = ids[:10]
    out["reasons"] = reasons[:3]
    out["changed"] = [nm for _r, nm, _d in structure_changes(old, new)]
    if probs:
        return dict(out, ok=False, why="broken")
    if any(out["retired"].get(k) for k in ("clubs", "leagues", "cups")):
        return dict(out, ok=False, why="retired")
    return dict(out, ok=True)


def _side(path):
    """a ledger file or a world folder, for the command line: (ids, ledger or None)"""
    if os.path.isdir(path):
        if os.path.isfile(os.path.join(path, LEDGER)):
            led = load(os.path.join(path, LEDGER))
            return of_ledger(led), led
        plan, pids = world_ids(path)
        if plan is None:
            raise LedgerError("%s has no %s" % (path, PLAN))
        return ids_of(plan, pids), None
    led = load(path)
    if led is None:
        raise LedgerError("%s is not there" % path)
    return of_ledger(led), led


def main(argv):
    get = lambda k: argv[argv.index(k) + 1] if k in argv else None
    if len(argv) >= 2 and argv[0] == "make":
        root = argv[1]
        plan, pids = world_ids(root)
        if plan is None:
            print("error: %s has no %s" % (root, PLAN))
            return 2
        world = plan.get("world") or os.path.basename(os.path.normpath(root))
        num = get("--number")
        led = make(plan, pids, world, get("--version") or default_version({}, None),
                   number=int(num) if num else None, made=get("--made"), lineage=get("--lineage"))
        out = get("--out") or os.path.join(root, LEDGER)
        save(led, out)
        ids = ids_of(led["plan"], led["players"])
        print("%s: %s, version %r number %d lineage %s: %d clubs, %d players, %d leagues, %d cups"
              % (out, world, led["version"], led["number"], led["lineage"], len(ids["clubs"]), len(ids["players"]),
                 len(ids["leagues"]), len(ids["cups"])))
        return 0
    if len(argv) >= 3 and argv[0] == "compare":
        old, oled = _side(argv[1])
        new, nled = _side(argv[2])
        probs = compare(old, new, retire_of(nled.get("retire") if nled else {}))
        for line in problem_lines(probs, int(get("--limit") or 20)):
            print(line)
        rn = renamed(old, new)
        print("renamed, same id: %d" % len(rn))
        for rid, nm, diff in structure_changes(old, new):
            print("league %s (%s): another %s" % (rid, nm, ", ".join(diff)))
        print("careers go on" if not probs else "careers break: " + summary(probs))
        return 0 if not probs else 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
