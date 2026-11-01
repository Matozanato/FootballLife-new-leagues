r"""python futve_conmebol.py [--game <folder>] [--live <world folder>] [--tables <folder>] [--out <folder>]

Fase 5 of the Liga FUTVE branch: the modern CONMEBOL competitions (Libertadores phases 1-3, the
Copa Sudamericana with its national first stage and post-group play-off, the Recopa) put into the
world of fase 4 WITHOUT rebuilding it. The world was built by Mod Studio and then changed by the
FUTVE tools (futve_world, futve_finals, futve_calendar), so a Mod Studio Build would lose those
changes -- and give the new cups regulations 261-263 and competition 142, the finals' own.

What it does:
  1. the world's recipe is read back from its leaguebuilder-plan.json (recipe_from_plan), the
     places below are put in (ALLOC: Venezuela with its real places, the rest of the 26/13/6/12/32
     to the game's leagues and to the associations' clubs the game has), and plan() is run;
  2. on a copy of fase 4's tables (out/futve/world-calendar) the classic Copa Sudamericana (its
     competition and regulations) is taken out and the builder's own modern-CONMEBOL steps are run:
     prepare_sudamericana_first, continental (Sudamericana + Recopa), the first stage's, the
     play-off's and the Libertadores qualifying's lpre lines, no away goals. Ids come from what the
     copy leaves free, so nothing of the Liga FUTVE is reused;
  3. the world file: fase 4's, with the South American uefa lines, the Sudamericana's ccup line,
     the Recopa's and the four lpre lines replaced or added -- every other line as it was;
  4. the emblems of the new competitions;
  5. a check: against fase 4, only CONMEBOL rows and lines may differ. Anything else stops it.

Output: <out> (default out/futve/world-phase5) with common\etc\pesdb, the emblems and fl26world.txt,
for futve_test.py --phase 5. Nothing of the game is written.
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import leaguebuilder as B
import mkleague as M
import pesdb

ART = os.path.join(REPO, "out", "futve")
G, F2, F1, SG, S1 = 3, 17, 16, 9, 19          # Libertadores groups, phase 2, phase 1, Suda groups, first stage
SUDA_CID, SUDA_REGS = 133, (257, 258)
SPO_DAYS = (144, 161)   # fase 4's Apertura group days 142/146/149/151 and the FIFA window 153-159 kept clear


def seq(*parts):
    out, pos = [], 1
    for comp, n in parts:
        for _ in range(n):
            out.append([pos, comp])
            pos += 1
    return out


# Felix 01.11.: Venezuela as real (2 + 1 + 1 Libertadores, 4 Sudamericana first stage); the game's
# leagues take what the associations without a league cannot fill (they have 14 clubs in the game)
ALLOC = {
    "venezuela": seq((G, 2), (F2, 1), (F1, 1), (S1, 4)),
    "game": {
        "29": seq((G, 5), (F2, 3), (F1, 1), (SG, 6), (S1, 4)),     # Brasil
        "30": seq((G, 5), (F2, 3), (SG, 6), (S1, 4)),              # Argentina
        "67": seq((G, 2), (F2, 2), (F1, 1), (S1, 10)),             # Chile
        "168": seq((G, 2), (F2, 2), (F1, 1), (S1, 10)),            # Colombia
    },
    "assoc": {
        "Bolivia": seq((G, 2)),
        "Uruguay": seq((G, 2)),
        "Ecuador": seq((G, 2), (F2, 1), (F1, 1)),
        "Paraguay": seq((G, 2), (F2, 1)),
        "Peru": seq((G, 2), (F1, 1)),
    },
}


def no_missing_paths(x):
    """the recipe's pictures are paths of the PC Mod Studio ran on: one this tool cannot read is
    left out (pictures play no part in the tables)"""
    if isinstance(x, dict):
        return {k: no_missing_paths(v) for k, v in x.items()}
    if isinstance(x, list):
        return [no_missing_paths(v) for v in x]
    if isinstance(x, str) and re.match(r"^([A-Za-z]:\\|/)", x) and not os.path.exists(x):
        return None
    return x


def rows(db, n, size):
    b = M.load(db, n)
    return [bytes(b[i:i + size]) for i in range(0, len(b), size)]


def write(db, n, rs):
    raw = open(os.path.join(db, n), "rb").read()
    data = b"".join(rs)
    open(os.path.join(db, n), "wb").write(pesdb.wesys_pack(data, raw[:3]) if raw[3:8] == b"WESYS" else data)


def regid(r):
    return int.from_bytes(r[M.R_ID:M.R_ID + 2], "little")


def keep_order(old, new):
    """every row of fase 4 stays at its place in the three tables -- the Sudamericana's rebuilt rows
    where its old ones were, the new competitions' after the rest (01.11., Felix: the Final del
    Apertura won, no title: with 133's rows moved to the end the game wrote none)"""
    oc, nc = rows(old, "Competition.bin", M.COMP), rows(new, "Competition.bin", M.COMP)
    byc = {r[M.CID_OFF]: r for r in nc}
    seen = [r[M.CID_OFF] for r in oc]
    write(new, "Competition.bin", [byc[c] for c in seen] + [r for r in nc if r[M.CID_OFF] not in seen])
    orr, nr = rows(old, "CompetitionRegulation.bin", M.REG), rows(new, "CompetitionRegulation.bin", M.REG)
    byr = {regid(r): r for r in nr}
    seen_r = [regid(r) for r in orr]
    missing = [g for g in seen_r if g not in byr]
    if missing:
        raise SystemExit("regulations of fase 4 missing after the build: %s" % missing)
    write(new, "CompetitionRegulation.bin", [byr[g] for g in seen_r] + [r for r in nr if regid(r) not in seen_r])
    oe, ne = rows(old, "CompetitionEntry.bin", M.ENT), rows(new, "CompetitionEntry.bin", M.ENT)
    sud_new = [r for r in ne if r[M.E_CID] == SUDA_CID]
    old_cids = {r[M.E_CID] for r in oe}
    out, put = [], False
    for r in oe:
        if r[M.E_CID] == SUDA_CID:
            if not put:
                out += sud_new
                put = True
            continue
        out.append(r)
    out += [r for r in ne if r[M.E_CID] not in old_cids]
    if Counter(out) != Counter(ne):
        raise SystemExit("the entry table lost or gained rows in the reordering")
    write(new, "CompetitionEntry.bin", out)


def check(old, new, cids, regs):
    """only the CONMEBOL rows differ: new competitions/regulations, the Sudamericana's, and the
    away-goals bit (0x13) of the Libertadores' rows"""
    bad = []
    co, cn = {r[M.CID_OFF]: r for r in rows(old, "Competition.bin", M.COMP)}, {r[M.CID_OFF]: r for r in rows(new, "Competition.bin", M.COMP)}
    for c in set(co) | set(cn):
        if co.get(c) != cn.get(c) and c not in cids and c != SUDA_CID:
            bad.append("competition %d" % c)
    ro, rn = {regid(r): r for r in rows(old, "CompetitionRegulation.bin", M.REG)}, {regid(r): r for r in rows(new, "CompetitionRegulation.bin", M.REG)}
    for g in set(ro) | set(rn):
        a, b = ro.get(g), rn.get(g)
        if a == b or (g & 0x3ff) in regs or (g & 0x3ff) in SUDA_REGS:
            continue
        if a and b and [i for i in range(M.REG) if a[i] != b[i]] == [0x13] and (g & 0x3ff) in (8, 9, 10):
            continue
        bad.append("regulation %d" % g)
    oc, ncr = rows(old, "Competition.bin", M.COMP), rows(new, "Competition.bin", M.COMP)
    if [r[M.CID_OFF] for r in oc] != [r[M.CID_OFF] for r in ncr[:len(oc)]]:
        bad.append("the order of the competitions changed")
    orr, nrr = rows(old, "CompetitionRegulation.bin", M.REG), rows(new, "CompetitionRegulation.bin", M.REG)
    if [regid(r) for r in orr] != [regid(r) for r in nrr[:len(orr)]]:
        bad.append("the order of the regulations changed")
    eo, en = Counter(rows(old, "CompetitionEntry.bin", M.ENT)), Counter(rows(new, "CompetitionEntry.bin", M.ENT))
    for r in (eo - en) + (en - eo):
        if r[M.E_CID] != SUDA_CID and r[M.E_CID] not in cids:
            bad.append("entry of competition %d" % r[M.E_CID])
    return sorted(set(bad))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--live", help="the world folder with leaguebuilder-plan.json (default <game>/SiderAddons/livecpk/_FL26MyWorld)")
    ap.add_argument("--tables", default=os.path.join(ART, "base-tables"))
    ap.add_argument("--src", default=os.path.join(ART, "world-calendar"), help="fase 4's world")
    ap.add_argument("--out", default=os.path.join(ART, "world-phase5"))
    ap.add_argument("--logos", default=os.environ.get("FL26_LOGOS", r"G:\Downloads"),
                    help="COPA_SUDAMERICANA.png, RECOPA_SUDAMERICANA.png, CONFERENCE_LEAGUE.png (any of them)")
    a = ap.parse_args()
    if not a.game:
        raise SystemExit("--game or FL26_DIR")
    live = a.live or os.path.join(a.game, "SiderAddons", "livecpk", "_FL26MyWorld")
    base = os.path.join(a.tables, "common", "etc", "pesdb")
    if not os.path.exists(os.path.join(base, "Team.bin")):
        print("unpacking the game's tables into %s" % a.tables)
        base = B.unpack_tables(a.game, a.tables)
    B.flpaths.use_game(a.game, B.siderdir.find(a.game))
    prev = json.load(open(os.path.join(live, "leaguebuilder-plan.json"), encoding="utf-8"))
    R = no_missing_paths(B.recipe_from_plan(prev, base))
    futve = [L for L in R["leagues"] if L.get("name") == "Liga FUTVE"]
    if len(futve) != 1:
        raise SystemExit("the recipe has no Liga FUTVE")
    R["conmebol"] = "modern"
    futve[0]["europe"] = ALLOC["venezuela"]
    R["game_europe"] = ALLOC["game"]
    R["conmebol_associations"] = ALLOC["assoc"]
    pl = B.plan(R, base, prev)
    for x in pl.get("conmebol_associations") or []:
        if x["unresolved"]:
            raise SystemExit("%s: %d place(s) without a club" % (x["name"], x["unresolved"]))

    shutil.copytree(a.src, a.out, dirs_exist_ok=True)      # fase 4's files over any earlier output
    db = os.path.join(a.out, "common", "etc", "pesdb")
    write(db, "Competition.bin", [r for r in rows(db, "Competition.bin", M.COMP) if r[M.CID_OFF] != SUDA_CID])
    write(db, "CompetitionRegulation.bin", [r for r in rows(db, "CompetitionRegulation.bin", M.REG) if (regid(r) & 0x3ff) not in SUDA_REGS])
    write(db, "CompetitionEntry.bin", [r for r in rows(db, "CompetitionEntry.bin", M.ENT) if r[M.E_CID] != SUDA_CID])
    cups = [c for c in pl["ccups"] if c["number"] in (B.SUDAM, -1)]
    B.SPO_DAYS = SPO_DAYS
    B.prepare_sudamericana_first(pl, a.out, db)
    lines = B.continental(cups, a.out, db, print, B.alt_from(pl), pl.get("prev_cup_ids"), pl.get("low_cids"))
    lines += B.sudamericana_first_line(pl)
    lines += B.sudamericana_playoffs(pl, a.out, db)
    lines += B.libertadores_qualifying(pl, a.out, db)
    B.modern_conmebol_no_away_goals(pl, db)
    keep_order(os.path.join(a.src, "common", "etc", "pesdb"), db)
    sud = next(c for c in cups if c["number"] == B.SUDAM)
    rec = next(c for c in cups if c["number"] == -1)
    if (sud["cid"], sud["reg"], sud["ko"]) != (SUDA_CID,) + SUDA_REGS:
        raise SystemExit("the Copa Sudamericana did not keep its ids: %s" % ((sud["cid"], sud["reg"], sud["ko"]),))
    helpers = {k: v for k, v in (pl.get("cup_ids") or {}).items() if k.startswith("conmebol:")}
    new_cids = {rec["cid"]} | {v["cid"] for v in helpers.values()}
    new_regs = {rec["reg"], rec["ko"]} | {r for v in helpers.values() for f, r in v.items() if f != "cid" and isinstance(r, int)}
    new_regs |= {int(m) for l in lines if l.startswith("lpre ") for m in [l.split()[1]]}
    futve_ids = {129, 131, 132, 134, 135, 142, 175} | set(range(255, 264))
    if new_cids & futve_ids or new_regs & futve_ids:
        raise SystemExit("a new CONMEBOL id is one of the Liga FUTVE's: %s" % sorted((new_cids | new_regs) & futve_ids))

    # the world file
    src = open(os.path.join(a.src, "fl26world.txt"), encoding="utf-8").read().splitlines()
    sam = {29, 30, 67, 168, 11} | {x["source"] for x in pl.get("conmebol_associations") or []}
    import fl26world
    uefa, _over = fl26world.uefa_places(B.all_places(pl), pl.get("game_replace") or [], bool(pl.get("uecl")))
    want_uefa = None
    out, put = [], False
    # the uefa lines as a Build of this plan writes them: fase 4's, with the South American ones
    # replaced (the European ones are the same lines in the same order -- checked below)
    sam_new = [l for l in fl26world_uefa_lines(pl) if int(l.split()[1]) in sam]
    for l in src:
        if l.startswith("uefa ") and int(l.split()[1]) in sam:
            if not put:
                out += sam_new
                put = True
            continue
        if l.startswith("ccup %d " % SUDA_REGS[0]):
            out.append(next(x for x in lines if x.startswith("ccup %d " % SUDA_REGS[0])))
            continue
        out.append(l)
        if l.startswith("ccup 263 "):
            out += [x for x in lines if not x.startswith("ccup %d " % SUDA_REGS[0])]
    if not put:
        raise SystemExit("fase 4's world has no South American uefa line")
    open(os.path.join(a.out, "fl26world.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

    # the emblems: the Sudamericana's for itself, its first stage and play-off, the Libertadores'
    # for its qualifying, the Recopa's; and the Conference League's (174). A picture in --logos
    # (Felix 01.11.) replaces the stored set of that kind (out/futve/phase5/emblems/<kind>_*.png).
    emb = os.path.join(a.out, "common", "render", "symbol", "emblemLc")
    os.makedirs(emb, exist_ok=True)
    pics = os.path.join(ART, "phase5", "emblems")
    import lbassets
    for k, pic, cid, name in (("suda", "COPA_SUDAMERICANA.png", SUDA_CID, "Copa Sudamericana"),
                              ("recopa", "RECOPA_SUDAMERICANA.png", rec["cid"], "Recopa Sudamericana"),
                              ("uecl", "CONFERENCE_LEAGUE.png", 174, "Conference League")):
        pic_path = os.path.join(a.logos, pic)
        if not os.path.isfile(pic_path):
            continue
        tmp = os.path.join(a.out, "_logo_" + k)
        lbassets.league_logo(tmp, cid, name, pic_path)
        made = os.path.join(tmp, *lbassets.EMBLEM_DIR)
        for v in ("l", "ll", "b_l", "b_ll", "w_l", "w_ll"):
            shutil.copy2(os.path.join(made, "emb_%04d_%s.png" % (cid, v)), os.path.join(pics, "%s_%s.png" % (k, v)))
        print("emblem %s from %s" % (k, pic_path))
    kind = {helpers["conmebol:" + B.SAM_FIRST_CODE]["cid"]: "suda", helpers["conmebol:" + B.SPO_CODE]["cid"]: "suda",
            helpers["conmebol:" + B.LIBQ_CODE]["cid"]: "libq", rec["cid"]: "recopa"}
    if os.path.isfile(os.path.join(pics, "suda_l.png")):
        kind[SUDA_CID] = "suda"
    if os.path.isfile(os.path.join(pics, "uecl_l.png")):
        kind[174] = "uecl"
    files = []
    for cid, k in sorted(kind.items()):
        for v in ("l", "ll", "b_l", "b_ll", "w_l", "w_ll"):
            n = "emb_%04d_%s.png" % (cid, v)
            shutil.copy2(os.path.join(pics, "%s_%s.png" % (k, v)), os.path.join(emb, n))
            files.append(n)
    json.dump({"files": files, "cids": sorted(kind)}, open(os.path.join(a.out, "emblems.json"), "w"), indent=1)

    # the check
    bad = check(os.path.join(a.src, "common", "etc", "pesdb"), db, new_cids, new_regs)
    a_lines, b_lines = Counter(src), Counter(out)
    for l in (a_lines - b_lines) + (b_lines - a_lines):
        w = l.split()
        ok = (w[0] == "uefa" and int(w[1]) in sam) or (w[0] == "ccup" and int(w[1]) in {SUDA_REGS[0], rec["reg"]}) \
            or (w[0] == "lpre" and int(w[1]) in new_regs)
        if not ok:
            bad.append("world line: " + l[:100])
    keep = [l for l in out if not (l.startswith("uefa ") and int(l.split()[1]) in sam)]
    keep_src = [l for l in src if not (l.startswith("uefa ") and int(l.split()[1]) in sam)]
    if [l for l in keep if l in keep_src] != [l for l in keep_src if l in keep]:
        bad.append("the order of the other lines changed")
    print("\n".join(lines))
    print("new competitions %s, regulations %s" % (sorted(new_cids), sorted(new_regs)))
    if bad:
        print("CHECK FAILED -- not CONMEBOL:\n  " + "\n  ".join(bad))
        return 1
    print("check: against fase 4 only CONMEBOL rows and lines differ -- %s" % a.out)
    return 0


def fl26world_uefa_lines(pl):
    """the uefa lines a Build of this plan writes (fl26world.uefa_places, as build() does)"""
    import fl26world
    uefa, _over = fl26world.uefa_places(B.all_places(pl), pl.get("game_replace") or [], bool(pl.get("uecl")))
    return fl26world.uefa_lines(uefa) if hasattr(fl26world, "uefa_lines") else [
        "uefa %d %d %d %d" % tuple(e[:4]) for e in uefa]


if __name__ == "__main__":
    sys.exit(main())
