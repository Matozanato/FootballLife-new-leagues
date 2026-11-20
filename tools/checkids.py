r"""python tools/checkids.py <published world> <new world> [--json out.json] [--allow file]

The ids of a world must not change when the world is updated (pop1806, 14.11.2026): people hang
kits, crests, faces, stadiums and their own edits on a league's, a club's and a player's id. Run before every world zip goes out, the last
PUBLISHED zip against the new one; exit code 0 only when nothing moved.

A world is a world zip (fl26worldpack.json inside) or a world folder (livecpk\<world>). Read from
it: leaguebuilder-plan.json (leagues, clubs) and fl26playerids.json (the world's own players).

  leagues   by name: the competition id and the regulation id.
  clubs     who is who: the same NewLife club id; else the same name where the world has one club
            of that name; else the same name in the same league; else the same place of the same
            league (a club renamed where it stands).
            FAIL: a club whose id changed; an id that belonged to a club that is gone and is now
            another club's (REUSED).
  players   who is who: the same NewLife player id; else the same club (by the club's id), name
            and birth date; else the same club and name where one player has it.
            FAIL: a player whose id changed; an id of a player who is gone now somebody else's.

--allow: a text file of lines `club <old id> <new id>`, `player <old id> <new id>`, `league <name>`
or `reused <id>`: changes that were decided and announced; they are listed but do not fail.
"""
import io, json, os, sys, zipfile

PLAN, PIDS = "leaguebuilder-plan.json", "fl26playerids.json"


def read_world(path):
    """(plan, player ids file or {}) of a world zip or a world folder"""
    if os.path.isdir(path):
        def get(name):
            try:
                with open(os.path.join(path, name), encoding="utf-8") as f:
                    return json.load(f)
            except OSError:
                return None
    else:
        z = zipfile.ZipFile(path)
        names = z.namelist()

        def get(name):
            hit = [n for n in names if n.endswith("/" + name) and "/livecpk/" in "/" + n]
            return json.load(io.TextIOWrapper(z.open(hit[0]), encoding="utf-8")) if hit else None
    plan = get(PLAN)
    if plan is None:
        raise SystemExit("%s: no %s in it -- not a built world" % (path, PLAN))
    return plan, get(PIDS) or {}


def norm(s):
    return str(s or "").strip().lower()


def clubs_of(plan):
    """[{tid, league, slot, name, nl, game}] of the world's leagues and other clubs"""
    out = []
    for p in list(plan.get("leagues") or []) + list(plan.get("others") or []):
        nl = (p.get("newlife") or {}).get("clubs") or []
        gc = p.get("game_clubs") or {}
        names = p.get("club_names") or []
        for k, t in enumerate(p.get("teams") or []):
            if not isinstance(t, int):
                continue
            out.append({"tid": t, "league": p.get("name") or "", "slot": k, "name": names[k] if k < len(names) else "",
                        "nl": nl[k] if k < len(nl) and nl[k] is not None else None,
                        "game": str(k) in gc or k in gc})
    return out


def match_clubs(old, new):
    """{index in old: index in new} -- who is who"""
    out, used = {}, set()

    def stage(key):
        a, b = {}, {}
        for i, r in enumerate(old):
            if i not in out and key(r) is not None:
                a.setdefault(key(r), []).append(i)
        for j, r in enumerate(new):
            if j not in used and key(r) is not None:
                b.setdefault(key(r), []).append(j)
        for k, ii in a.items():
            jj = b.get(k) or []
            if len(ii) == 1 and len(jj) == 1:
                out[ii[0]] = jj[0]
                used.add(jj[0])
    stage(lambda r: ("nl", r["nl"]) if r["nl"] is not None else None)
    stage(lambda r: (norm(r["league"]), norm(r["name"])) if norm(r["name"]) else None)
    stage(lambda r: norm(r["name"]) or None)
    stage(lambda r: (norm(r["league"]), r["slot"], r["tid"]))
    # what is left on both sides in the same place of the same league: the club was renamed (or
    # another took its place) -- and its id went with the name, which is the thing looked for
    stage(lambda r: (norm(r["league"]), r["slot"]) if not r["game"] else None)
    return out


def people_of(pids, club_tid):
    """[{id, club (team id or the key), key, name, nl, born}] of the world's own players"""
    out = []
    names, people = pids.get("names") or {}, pids.get("people") or {}
    for club, keys in (pids.get("clubs") or {}).items():
        if not isinstance(keys, dict):
            continue
        nm = names.get(club) if isinstance(names.get(club), dict) else {}
        pp = people.get(club) if isinstance(people.get(club), dict) else {}
        for key, pid in keys.items():
            if not isinstance(pid, int):
                continue
            who = pp.get(key) if isinstance(pp.get(key), dict) else {}
            out.append({"id": pid, "club": club_tid.get(club, club), "key": club + "#" + key, "name": norm(nm.get(key)),
                        "nl": str(who.get("nl") or "") or None, "born": who.get("born") or None})
    return out


def match_people(old, new):
    out, used = {}, set()

    def stage(key):
        a, b = {}, {}
        for i, r in enumerate(old):
            if i not in out and key(r) is not None:
                a.setdefault(key(r), []).append(i)
        for j, r in enumerate(new):
            if j not in used and key(r) is not None:
                b.setdefault(key(r), []).append(j)
        for k, ii in a.items():
            jj = b.get(k) or []
            if len(ii) == 1 and len(jj) == 1:
                out[ii[0]] = jj[0]
                used.add(jj[0])
    stage(lambda r: ("nl", r["nl"]) if r["nl"] else None)
    stage(lambda r: (r["club"], r["name"], r["born"]) if r["name"] and r["born"] else None)
    stage(lambda r: (r["club"], r["name"]) if r["name"] else None)
    stage(lambda r: (r["key"], r["id"]) if not r["name"] and not r["nl"] else None)   # a placeholder in its place
    return out


def read_allow(path):
    out = {"club": set(), "player": set(), "league": set(), "reused": set()}
    if not path:
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            w = line.split("#")[0].split()
            if not w:
                continue
            if w[0] in ("club", "player") and len(w) >= 3:
                out[w[0]].add((int(w[1]), int(w[2])))
            elif w[0] == "reused" and len(w) >= 2:
                out["reused"].add(int(w[1]))
            elif w[0] == "league":
                out["league"].add(norm(" ".join(w[1:])))
    return out


def compare(old_world, new_world, allow=None):
    """the report: {"leagues": [...], "clubs": [...], "reused": [...], "players": [...],
    "players_reused": [...], "counts": {...}, "fail": n}"""
    allow = allow or read_allow(None)
    (pa, ia), (pb, ib) = old_world, new_world
    rep = {"leagues": [], "clubs": [], "reused": [], "players": [], "players_reused": [], "allowed": [], "counts": {}}
    # leagues
    la = {norm(p.get("name")): p for p in pa.get("leagues") or []}
    lb = {norm(p.get("name")): p for p in pb.get("leagues") or []}
    for n in sorted(set(la) & set(lb)):
        a, b = la[n], lb[n]
        if (a.get("cid"), a.get("rid")) != (b.get("cid"), b.get("rid")):
            row = {"league": a.get("name"), "old": [a.get("cid"), a.get("rid")], "new": [b.get("cid"), b.get("rid")]}
            (rep["allowed"] if n in allow["league"] else rep["leagues"]).append(row)
    rep["counts"]["leagues"] = [len(la), len(lb), len(set(la) & set(lb))]
    # clubs
    ca, cb = clubs_of(pa), clubs_of(pb)
    m = match_clubs(ca, cb)
    now = {r["tid"]: r for r in cb}
    for i, j in sorted(m.items()):
        a, b = ca[i], cb[j]
        if a["tid"] != b["tid"]:
            row = {"old": a, "new": b}
            (rep["allowed"] if (a["tid"], b["tid"]) in allow["club"] else rep["clubs"]).append(row)
    moved_from = {ca[i]["tid"] for i, j in m.items() if ca[i]["tid"] != cb[j]["tid"]}
    for i, a in enumerate(ca):
        if a["game"]:
            continue                        # a club of the game: its id is the game's, any club may take its place
        b = now.get(a["tid"])
        if b is None or b["game"]:
            continue
        if (i not in m) or a["tid"] in moved_from:
            if i in m and cb[m[i]]["tid"] == a["tid"]:
                continue
            row = {"id": a["tid"], "was": a, "now": b}
            (rep["allowed"] if a["tid"] in allow["reused"] else rep["reused"]).append(row)
    rep["counts"]["clubs"] = [len(ca), len(cb), len(m)]
    rep["gone_clubs"] = [ca[i] for i in range(len(ca)) if i not in m]
    # players
    def tids(plan):
        return {"%s/%d" % (p.get("name"), k): t for p in list(plan.get("leagues") or []) + list(plan.get("others") or [])
                for k, t in enumerate(p.get("teams") or []) if isinstance(t, int)}
    qa, qb = people_of(ia, tids(pa)), people_of(ib, tids(pb))
    pm = match_people(qa, qb)
    pnow = {r["id"]: r for r in qb}
    for i, j in pm.items():
        if qa[i]["id"] != qb[j]["id"]:
            row = {"old": qa[i], "new": qb[j]}
            (rep["allowed"] if (qa[i]["id"], qb[j]["id"]) in allow["player"] else rep["players"]).append(row)
    matched_new = {qb[j]["id"] for j in pm.values()}
    for i, a in enumerate(qa):
        if i in pm:
            continue
        b = pnow.get(a["id"])
        if b is not None and (a["name"] or a["nl"]) and (b["name"], b["nl"]) != (a["name"], a["nl"]):
            rep["players_reused"].append({"id": a["id"], "was": a, "now": b})
    rep["counts"]["players"] = [len(qa), len(qb), len(pm)]
    rep["fail"] = sum(len(rep[k]) for k in ("leagues", "clubs", "reused", "players", "players_reused"))
    return rep


def club_text(r):
    return "%s / %s%s" % (r["league"], r["name"] or "(place %d)" % (r["slot"] + 1), " [NewLife %s]" % r["nl"] if r["nl"] is not None else "")


def describe(rep, limit=40):
    c = rep["counts"]
    out = ["leagues: %d published, %d new, %d in both -- %d with another id" % (*c["leagues"], len(rep["leagues"])),
           "clubs:   %d published, %d new, %d found again -- %d with another id, %d ids now another club's"
           % (*c["clubs"], len(rep["clubs"]), len(rep["reused"])),
           "players: %d published, %d new, %d found again -- %d with another id, %d ids now another player's"
           % (*c["players"], len(rep["players"]), len(rep["players_reused"]))]
    for r in rep["leagues"][:limit]:
        out.append("  LEAGUE  %s: competition/regulation %s -> %s" % (r["league"], r["old"], r["new"]))
    for r in rep["clubs"][:limit]:
        out.append("  CLUB    %d -> %d  %s  ->  %s" % (r["old"]["tid"], r["new"]["tid"], club_text(r["old"]), club_text(r["new"])))
    for r in rep["reused"][:limit]:
        out.append("  REUSED  %d  was %s, now %s" % (r["id"], club_text(r["was"]), club_text(r["now"])))
    for r in rep["players"][:limit]:
        out.append("  PLAYER  %d -> %d  %s (%s)" % (r["old"]["id"], r["new"]["id"], r["old"]["name"], r["old"]["key"]))
    for r in rep["players_reused"][:limit]:
        out.append("  REUSED  player id %d  was %s (%s), now %s (%s)"
                   % (r["id"], r["was"]["name"], r["was"]["key"], r["now"]["name"], r["now"]["key"]))
    for k in ("leagues", "clubs", "reused", "players", "players_reused"):
        if len(rep[k]) > limit:
            out.append("  ... %d more of %s (see --json)" % (len(rep[k]) - limit, k))
    if rep["allowed"]:
        out.append("allowed changes (decided, not counted): %d" % len(rep["allowed"]))
    if rep.get("gone_clubs"):
        out.append("clubs of the published world not found in the new one (taken out): %d" % len(rep["gone_clubs"]))
    out.append("ids: the new world keeps every id of the published one" if not rep["fail"]
               else "ids: %d CHANGED -- the world must not go out like this" % rep["fail"])
    return "\n".join(out)


def main(a):
    def opt(name):
        if name in a:
            i = a.index(name)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return None
    js, allow = opt("--json"), opt("--allow")
    if len(a) != 2:
        print(__doc__)
        return 2
    rep = compare(read_world(a[0]), read_world(a[1]), read_allow(allow))
    print(describe(rep))
    if js:
        with open(js, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
    return 1 if rep["fail"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
