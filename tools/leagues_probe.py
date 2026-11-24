"""Build or audit a standalone FL27 Leagues Cup Phase One mechanics world."""

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import shutil

from central_probe import DB, FILE_SIZES, rows
from central_probe_audit import read_fixtures
import lbplayers
import leaguebuilder as B
import mkccup as K
import mkeuropo
import mkleague as M
import mkworld as W


WORLD = "_FL26LeaguesProbe"
YEAR = 2026
DAYS = (6, 6, 13, 13, 20, 20)
WINDOW = (1, 31)
KNOCKOUT = ((706, 4), (707, 2), (708, 2))
# The final 2026 field, resolved in the archived FL27 validation database.
# These IDs are edition fixtures for this test, never career qualification.
MLS = (5740, 5832, 4148, 5737, 4151, 4153, 5738, 5741, 5063,
       5739, 5061, 5062, 4159, 4160, 4161, 6084, 4163, 4166)
MX = (73241, 1264, 73247, 73242, 1265, 73250, 73248, 73245, 1778,
      73243, 73251, 73246, 73252, 73253, 73244, 1782, 73254, 73249)
PENALTIES = 1 << 27
OTHER_RULES = (1 << 24) | (1 << 25) | (1 << 28) | (7 << 9)


def schedule(clubs):
    if len(clubs) != 36 or len(set(clubs)) != 36 or any(not 0 < c < 0x3ffff for c in clubs):
        raise ValueError("Need 36 distinct valid club IDs")
    return [[(mx, mls) if (t + b // 2) % 2 else (mls, mx)
             for t in range(9)
             for mls, mx in [(clubs[(b % 2) * 9 + t],
                              clubs[18 + (b % 2) * 9 + (t + b // 2) % 9])]]
            for b in range(6)]


def verify_field(base):
    clubs = MLS + MX
    mls = next((set(teams) for rid, _, _, teams in B.game_leagues(str(base)) if rid == 166), set())
    countries = B.club_countries(str(base))
    mexico = next((n for name, n in B.country_ids(str(base)) if name.lower() == "mexico"), None)
    missing = [c for c in MLS if c not in mls]
    missing += [c for c in MX if not mexico or countries.get(c) != mexico]
    if missing:
        raise ValueError(f"Fixed 2026 field is unavailable in this database: {missing}")
    raw = M.load(str(base), "Team.bin")
    names = {}
    for i in range(0, len(raw), W.T_REC):
        team = raw[i:i+W.T_REC]
        cid = int.from_bytes(team[W.T_ID:W.T_ID+4], "little")
        if cid in clubs:
            if cid in names:
                raise ValueError(f"Duplicate team record {cid}")
            name = bytes(team[W.T_NAME:W.T_NAME+W.T_NAME_LEN]).split(b"\0", 1)[0]
            try:
                names[cid] = name.decode("utf-8")
            except UnicodeDecodeError:
                names[cid] = name.decode("cp1252")
    squads = lbplayers.squad_counts(str(base), clubs)
    if set(names) != set(clubs) or any(not names.get(c) or squads.get(c, 0) < 18 for c in clubs):
        raise ValueError("A fixed participant has no usable team record or squad")
    return names


def generate_tables(db, root, cids, knockouts, log=print, regs=tuple(range(700, 706)), finals=KNOCKOUT, name="Leagues Cup"):
    """Emit the same stage tables in a probe or a staged Mod Studio world."""
    families = [(reg, 9) for reg in regs] + (list(finals) if knockouts else [])
    comp, rules, _ = rows(db)
    used = {K.rid(row) for row in rules}
    owned = {reg + i * 1024 for reg, ties in families for i in range(ties + 1)}
    if len(cids) != 6 + int(knockouts) or len(set(cids)) != len(cids) or owned & used or set(cids) & {M.comp_cid(row) for row in comp}:
        raise ValueError("Leagues Cup competition slots or owned regulation IDs are occupied")
    for b, (cid, reg) in enumerate(zip(cids, regs), 1):
        mkeuropo.prerounds_single(str(db), str(root), cid, f"FL_LC_PHASE1_{b}",
                                  name if b == 1 else f"{name} Phase One {b}",
                                  [(reg, 9)], log=log, region=1, confederation=0)
    if knockouts:
        mkeuropo.prerounds_single(str(db), str(root), cids[-1], "FL_LC_KO",
                                  name, finals, log=log, region=1, confederation=0)
    comps, rules, entries = rows(db)
    for row in rules:
        if K.rid(row) in owned:
            word = int.from_bytes(row[16:20], "little")
            row[16:20] = ((word & ~OTHER_RULES) | PENALTIES).to_bytes(4, "little")
    M.write_tables(str(root), *(b"".join(table) for table in (comps, rules, entries)))


def build(base, stock, metadata, dest, window=WINDOW, domestic_world=None, knockouts=False,
          annual=False, champions=False, logo=None):
    if not 1 <= window[0] <= window[1] <= 31:
        raise ValueError("Leagues Cup window must lie inside August")
    if dest.exists():
        raise ValueError("Use a new destination for the isolated overlay")
    if annual and not (domestic_world and knockouts) or champions and not annual:
        raise ValueError("Annual play requires the domestic world and knockout stages")
    names = verify_field(base)
    W.set_cid_wide(True)
    game, = (line for line in metadata.read_text(encoding="utf-8").splitlines() if line.startswith("game fl27 "))
    shipped = stock
    if domestic_world:
        metadata = domestic_world / "fl26world.txt"
        stock = domestic_world / DB
        mexico, membership = next(((reg, teams) for reg, _, name, teams in B.game_leagues(str(stock))
                                   if name.casefold() == "liga mx"), (0, ()))
        if set(membership) != set(MX):
            raise ValueError("Generated Liga MX must contain exactly the fixed 18 Mexican clubs")
    comps, rules, _ = rows(stock)
    stock_mls = next((set(teams) for rid, _, _, teams in B.game_leagues(str(stock)) if rid == 166), set())
    if not set(MLS) <= stock_mls:
        raise ValueError("The stock competition tables do not contain the fixed MLS field")
    used_cids = {M.comp_cid(c) for c in comps}
    used_regs = {K.rid(r) for r in rules}
    cids = [c for c in range(768, 1024) if c not in used_cids][:6+int(knockouts)]
    regs = list(range(700, 706))
    if len(cids) != 6+int(knockouts) or any(r+1024*i in used_regs for r in regs for i in range(10)):
        raise ValueError("Leagues Cup competition slots or owned regulation IDs are occupied")
    # Keep the selected 2026 table dimensions and large-database support.
    overlay = dest / DB
    overlay.mkdir(parents=True)
    stock_tables = {name for name, _ in FILE_SIZES} | {"CompetitionKind.bin"}
    for file in base.glob("*.bin"):
        if file.name not in stock_tables:
            shutil.copy2(file, overlay / file.name)
    for name in stock_tables:
        source = stock / name
        shutil.copy2(source if source.is_file() else shipped / name, overlay / name)
    if domestic_world:
        shutil.copytree(domestic_world / "common", dest / "common", dirs_exist_ok=True)
    generate_tables(overlay, dest, cids, knockouts)
    clubs = MLS + MX
    knockout_regs = [reg for reg, _ in KNOCKOUT] if knockouts else []
    sources = [mexico] if annual else []
    contract = ",".join(map(str, [*regs, *clubs, window[0]+211, window[1]+211, *knockout_regs, *sources]))
    contract_lines = [f"# fl26world 1\nworld {WORLD}\n", game+"\n"]
    if domestic_world:
        contract_lines.extend(line+"\n" for line in metadata.read_text(encoding="utf-8").splitlines()
                              if line and not line.startswith(("#", "world ", "game ")))
    contract_lines.append(f"leagues_probe 1 data={contract}\n")
    if annual:
        from lbassets import league_logo
        for cid in cids:
            league_logo(dest, cid, "Leagues Cup", logo)
    if champions:
        import concacaf as Q
        import mkconcacaf as G
        leagues = [(51, "USA", "mls", sorted(stock_mls)), (mexico, "Mexico", "liga_mx", membership)]
        sources = [dict(id=str(reg), country=country, region="north", roles=[role], kind="league",
                        conf=6, capacity=len(teams), teams=list(teams))
                   for reg, country, role, teams in leagues]
        sources.append(dict(id="54", country="USA", region="north", roles=["us_open_cup"],
                            kind="cup", conf=6, capacity=0))
        plan = Q.plan({"modules": {"leagues_cup": True}}, sources)
        cid, helper = [c for c in range(768, 1024) if c not in used_cids and c not in cids][:2]
        contract_lines.append("seasonsum 51 parts=166,167\n")
        mexican_halves = next((m.groups() for line in contract_lines
                               if (m := re.match(rf"split {mexico} regular=(\d+) groups=(\d+) carry=0\s*$",
                                                 line))), None)
        if mexican_halves:
            contract_lines.append(f"seasonsum {mexico} parts={','.join(mexican_halves)}\n")
        contract_lines.extend(line+"\n" for line in
                              G.generate(str(overlay), str(dest), plan, cid, 709, helper, 710,
                                         cup_regs={"module:leagues_cup": 708}))
    (dest / "fl26world.txt").write_text("".join(contract_lines), encoding="utf-8")
    fixtures = {}
    for day, pairs in zip(DAYS, schedule(clubs)):
        fixtures.setdefault(f"2026-08-{day:02}", []).extend(pairs)
    inventory = dict(year=YEAR, masters=regs, competitions=cids[:6], knockout=knockout_regs,
                     mls=[(c, names[c]) for c in MLS], liga_mx=[(c, names[c]) for c in MX],
                     fixtures=fixtures, window=list(window), dates_are_preferences=True,
                     liga_mx_domestic=bool(domestic_world), annual=annual,
                     champions_cup=champions, liga_mx_reg=mexico if domestic_world else None)
    (dest / "edition.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return inventory


def tables(fixtures, masters, clubs, window=WINDOW, year=YEAR):
    expected = {(b, frozenset((h, a))): t for b, pairs in enumerate(schedule(clubs))
                for t, (h, a) in enumerate(pairs, 1)}
    out = {c: Counter(dict.fromkeys(("P", "RW", "PW", "PL", "RL", "GF", "GA", "GD", "Pts"), 0)) for c in clubs}
    days = {}
    for reg, _, day, flags, h, a, score in fixtures:
        b = masters.index(reg & 1023)
        tie = expected.pop((b, frozenset((h, a))), None)
        if (not tie or reg >> 10 not in (0, tie) or day[:2] != (year, 8)
                or not window[0] <= day[2] <= window[1] or days.setdefault(b, day[2]) != day[2]):
            raise ValueError(f"Unexpected, duplicate or misdated native match: {reg}, {day}, {h}, {a}")
        if not flags & 0x40:
            continue
        hg, he, hp, ag, ae, ap = score
        if 255 in score or he or ae or (hp == ap if hg == ag else hp or ap):
            raise ValueError(f"Invalid shootout, extra time or score for {h} vs {a}: {score}")
        for club, gf, ga, pf, pa in ((h, hg, ag, hp, ap), (a, ag, hg, ap, hp)):
            result, points = ("RW", 3) if gf > ga else ("RL", 0) if gf < ga else (
                ("PW", 2) if pf > pa else ("PL", 1))
            row = out[club]
            row.update({"P": 1, result: 1, "GF": gf, "GA": ga, "GD": gf-ga, "Pts": points})
    if expected:
        raise ValueError(f"Missing {len(expected)} of 54 native fixtures")
    if any(days[b]-days[b-2] < 3 for b in range(2, 6)):
        raise ValueError("Leagues Cup masters violate round order or three-day rest")
    # Contract order is display order until a final tiebreak policy is implemented.
    return dict(MLS={c: out[c] for c in clubs[:18]}, LigaMX={c: out[c] for c in clubs[18:]})


def audit_report(fixtures, masters, clubs, require_complete=False, window=WINDOW, year=YEAR):
    standings = tables(fixtures, masters, clubs, window, year)
    results = []
    played = 0
    for reg, _, day, flags, home, away, score in fixtures:
        complete = bool(flags & 0x40)
        played += complete
        result = dict(master=reg & 1023, date=list(day), home=home, away=away, played=complete)
        if complete:
            hg, he, hp, ag, ae, ap = score
            result.update(regulation=[hg, ag], extra_time=[he, ae],
                          penalties=[hp, ap] if hg == ag else None,
                          shootout_winner=(home if hp > ap else away) if hg == ag else None)
        results.append(result)
    if require_complete and played != 54:
        raise ValueError(f"Expected 54 played fixtures, found {played}")
    results.sort(key=lambda row: (row["date"], row["home"], row["away"]))
    by_league = {league: {str(c): row for c, row in table.items()} for league, table in standings.items()}
    return dict(scheduled=len(results), played=played, fixtures=results, standings=by_league,
                ranking={league: rank_table(table) for league, table in by_league.items()})


def rank_table(table):
    return sorted(table, key=lambda c: (-table[c]["Pts"], -table[c]["GD"],
                                       -table[c]["GF"], -table[c]["RW"], int(c)))


def knockout_report(phase, fixtures, masters, year=YEAR):
    """Validate each emitted native showpiece against winners of the previous stage."""
    if phase["played"] != 54:
        if fixtures:
            raise ValueError("Knockout fixtures have no completed Phase One")
        return dict(fixtures=[], podium=None)
    mls, mx = (list(map(int, rank_table(phase["standings"][k])[:4])) for k in ("MLS", "LigaMX"))
    pairs = list(zip(mls, reversed(mx)))
    previous = max(date(*row["date"]) for row in phase["fixtures"])
    report = dict(fixtures=[], podium=None)
    for stage, master in enumerate(masters):
        rows = [r for r in fixtures if r[0] & 1023 == master]
        if not rows:
            if any(r[0] & 1023 in masters[stage+1:] for r in fixtures):
                raise ValueError("Knockout stages are out of order")
            return report
        if len(rows) != len(pairs):
            raise ValueError(f"Incomplete or inconsistent knockout master {master}")
        first, last = min(date(*r[2]) for r in rows), max(date(*r[2]) for r in rows)
        if first.year != year or last > date(year, 10, 31) or (first-previous).days < 3:
            raise ValueError(f"Knockout master {master} violates date or rest rules")
        previous = last
        wins, losses = [], []
        for t, pair in enumerate(pairs, 1):
            tie = [r for r in rows if r[0] >> 10 in (0, t) and set(r[4:6]) == set(pair)]
            if len(tie) != 1:
                raise ValueError(f"Incorrect pair for knockout master {master} tie {t}")
            r = tie[0]
            winner = None
            hg, he, hp, ag, ae, ap = r[6]
            if r[3] & 0x40:
                if 255 in r[6] or he or ae or (hp == ap if hg == ag else hp or ap):
                    raise ValueError("Invalid native knockout score")
                winner = r[4] if (hg, hp) > (ag, ap) else r[5]
            wins.append(winner)
            losses.append(next((c for c in pair if c != winner), None) if winner else None)
            report["fixtures"].append(dict(master=master, tie=t, date=list(r[2]), home=r[4],
                                           away=r[5], winner=winner, score=list(r[6])))
        if not all(wins):
            if any(r[0] & 1023 in masters[stage+1:] for r in fixtures):
                raise ValueError("Knockout advanced from unfinished results")
            return report
        if stage == 0:
            pairs = [(wins[0], wins[3]), (wins[1], wins[2])]
        elif stage == 1:
            pairs = [tuple(losses), tuple(wins)]
        else:
            report["podium"] = dict(champion=wins[1], runner_up=losses[1], third=wins[0])
    return report


def knockout_view(phase, knockout, masters, year):
    """Read-only reference topology for comparing native bracket captures."""
    qf, sf, finals = masters
    seeds = (None,) * 8
    if phase["played"] == 54:
        mls, mx = (list(map(int, phase["ranking"][league][:4])) for league in ("MLS", "LigaMX"))
        seeds = tuple(club for pair in zip(mls, reversed(mx)) for club in pair)
    sources = (
        ("quarterfinal", qf, 1, ()), ("quarterfinal", qf, 2, ()),
        ("quarterfinal", qf, 3, ()), ("quarterfinal", qf, 4, ()),
        ("semifinal", sf, 1, ((qf, 1, "winner"), (qf, 4, "winner"))),
        ("semifinal", sf, 2, ((qf, 2, "winner"), (qf, 3, "winner"))),
        ("third_place", finals, 1, ((sf, 1, "loser"), (sf, 2, "loser"))),
        ("final", finals, 2, ((sf, 1, "winner"), (sf, 2, "winner"))),
    )
    fixtures = {(row["master"], row["tie"]): row for row in knockout["fixtures"]}
    outcomes = {}
    nodes = []
    for stage, master, tie, parents in sources:
        key = master, tie
        fixture = fixtures.get(key)
        clubs = ([outcomes.get((reg, slot), {}).get(result) for reg, slot, result in parents]
                 if parents else list(seeds[2*(tie-1):2*tie]))
        result = None
        if fixture and fixture["winner"] is not None:
            home, away, winner = fixture["home"], fixture["away"], fixture["winner"]
            hg, _, hp, ag, _, ap = fixture["score"]
            outcomes[key] = dict(winner=winner, loser=away if winner == home else home)
            result = dict(home=home, away=away, goals=[hg, ag],
                          penalties=[hp, ap] if hg == ag else None, winner=winner)
        nodes.append(dict(stage=stage, master=master, tie=tie, sources=parents, clubs=clubs,
                          date=fixture["date"] if fixture else None, result=result))
    return dict(year=year, nodes=nodes)


def calendar_conflicts(fixtures, masters, clubs, days=DAYS, year=YEAR):
    """Return existing fixtures less than three days from a club's Phase One match."""
    conflicts = []
    for master, day, pairs in zip(masters, days, schedule(clubs)):
        batch = {club for pair in pairs for club in pair}
        for reg, _, match_day, _, home, away, _ in fixtures:
            if (reg & 1023) in masters and reg >> 10 <= 9:
                continue
            affected = sorted(batch.intersection((home, away)))
            if not affected:
                continue
            try:
                gap = abs((date(*match_day)-date(year, 8, day)).days)
            except ValueError:
                continue
            if gap >= 3:
                continue
            conflicts.append(dict(master=master, date=f"{year}-08-{day:02}",
                                  regulation=reg, native_date=date(*match_day).isoformat(),
                                  home=home, away=away, clubs=affected))
    return conflicts


def check_day_lists(fixtures, match_ids, day_lists):
    owned = set(match_ids)
    if len(owned) != len(match_ids):
        raise ValueError("Duplicate native Leagues Cup match ID")
    expected = {i: (date(YEAR, *row[2][1:])-date(YEAR, 1, 1)).days
                for i, row in zip(match_ids, fixtures, strict=True)}
    for day, ids in enumerate(day_lists):
        for match_id in ids:
            if match_id not in expected:
                if match_id in owned:
                    raise ValueError(f"Duplicate calendar entry for match {match_id}")
                continue
            if expected.pop(match_id) != day:
                raise ValueError(f"Calendar entry for match {match_id} is on the wrong day")
    if expected:
        raise ValueError(f"Missing {len(expected)} native calendar entries")


def check_knockout_rest(knockout, native, excluded):
    for row in knockout["fixtures"]:
        day = date(*row["date"])
        clubs = {row["home"], row["away"]}
        for reg, _, when, _, home, away, _ in native:
            if reg in excluded or not clubs.intersection((home, away)):
                continue
            try:
                gap = abs((date(*when)-day).days)
            except ValueError:
                continue
            if gap < 3:
                raise ValueError(f"Knockout master {row['master']} conflicts with regulation {reg} on {when}")


def inspect_competition_info(mem, block, regs):
    """Capture the current selection, presentation call targets and regulation records."""
    import struct

    def operand(address, prefix):
        raw = mem.read(address, len(prefix) + 4)
        if not raw or not raw.startswith(prefix):
            raise ValueError(f"Unknown FL27 instruction at {address:#x}")
        return struct.unpack_from("<i", raw, len(prefix))[0]

    selection = operand(0x140AED39C, b"\xf2\x0f\x10\x81")
    count_offset = operand(0x1414BB070, b"\x8b\x81")
    base = operand(0x1414BB076, b"\x48\x8d\x93")
    stride = operand(0x1414BB07D, b"\x48\x69\xc8")
    count = mem.u32(block + count_offset)
    if not count or count > 65536 or stride != 0x314:
        raise ValueError("Unknown FL27 regulation layout")
    selected = mem.read(block + selection, 8)
    if selected is None:
        raise ValueError("Competition Info selection is unreadable")
    comp, reg = struct.unpack_from("<IH", selected)
    rows = {}
    for start in range(0, count, 256):
        page = mem.read(block+base+start*stride, min(256, count-start)*stride)
        if page is None:
            raise ValueError("Native regulation records are unreadable")
        for offset in range(0, len(page), stride):
            rid, = struct.unpack_from("<H", page, offset)
            owner, = struct.unpack_from("<I", page, offset+0x80)
            if rid in regs or (comp != 0xffffffff and owner == comp) or (
                    reg != 0xffff and (rid & 1023) == (reg & 1023)):
                rows[str(rid)] = page[offset:offset+stride].hex()
    # Decode the loaded fixture array operands so widened FL27 builds use
    # the actual array and capacity, not the stock disk offsets.
    fixture_base = operand(0x141579F83, b"\x48\x8d\x96")
    fixture_stride = operand(0x141579F8A, b"\x48\x69\xc8")
    fixture_capacity = operand(0x141579F7A, b"\x3d")
    if fixture_base <= 0 or fixture_stride != 0x208 or not 0 < fixture_capacity <= 65536:
        raise ValueError("Unknown FL27 fixture layout")
    rounds = []
    relevant = set(map(int, rows))
    for start in range(0, fixture_capacity, 256):
        page = mem.read(block+fixture_base+start*fixture_stride,
                        min(256, fixture_capacity-start)*fixture_stride)
        if page is None:
            raise ValueError("Native fixture records are unreadable")
        for offset in range(0, len(page), fixture_stride):
            rid, = struct.unpack_from("<H", page, offset)
            if rid not in relevant:
                continue
            flags, = struct.unpack_from("<I", page, offset+0x204)
            kind, count = flags >> 26, flags & 0xff
            if not 0 < count <= 16:
                continue
            slots = [page[offset+4+32*i:offset+36+32*i] for i in range(count)]
            rounds.append(dict(index=start+offset//fixture_stride, regulation=rid,
                               kind=kind, flags=flags, slots=[
                                   dict(clubs=struct.unpack_from("<II", slot),
                                        match_ids=struct.unpack_from("<HH", slot, 8),
                                        key=struct.unpack_from("<I", slot, 0x0c)[0],
                                        destinations=struct.unpack_from("<II", slot, 0x10),
                                        sources=struct.unpack_from("<II", slot, 0x18),
                                        raw=slot.hex()) for slot in slots]))
    call_sites = (0x140AEDC74, 0x140AEDD37, 0x140AEE0F5, 0x140AEE4FA, 0x14154236A,
                  0x140AF9882, 0x140AF9906, 0x140AF993E, 0x140AF994E,
                  0x140AF9990, 0x140CA5F03, 0x140B32BB8, 0x140B32C39, 0x140B32C4F,
                  0x140B3304C, 0x140B3306D, 0x140B330C7, 0x140B346D8,
                  0x140B34BF8, 0x140B34C22, 0x140B34EE9, 0x140B34FB4)
    return dict(competition=comp, regulation=reg, records=rows, rounds=rounds,
                call_targets={hex(site): hex(site+5+operand(site, b"\xe8")) for site in call_sites})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    builder = sub.add_parser("build")
    for key in ("base", "stock", "metadata", "output"):
        builder.add_argument(f"--{key}", type=Path, required=True)
    builder.add_argument("--window", type=int, nargs=2, default=WINDOW, metavar=("FIRST", "LAST"))
    builder.add_argument("--domestic-world", type=Path)
    builder.add_argument("--knockouts", action="store_true")
    builder.add_argument("--annual", action="store_true")
    builder.add_argument("--champions", action="store_true")
    builder.add_argument("--logo", type=Path)
    audit = sub.add_parser("audit")
    audit.add_argument("--pid", type=int, required=True)
    audit.add_argument("--exe", type=Path, required=True)
    audit.add_argument("--edition", type=Path, required=True)
    audit.add_argument("--calendar", action="store_true")
    audit.add_argument("--bracket-view", action="store_true")
    audit.add_argument("--require-complete", action="store_true")
    audit.add_argument("--snapshot", type=Path)
    audit.add_argument("--compare", type=Path)
    audit.add_argument("--journal", type=Path)
    audit.add_argument("--ui-snapshot", type=Path)
    args = parser.parse_args()
    if args.mode == "build":
        build(args.base, args.stock, args.metadata, args.output, args.window, args.domestic_world,
              args.knockouts, args.annual, args.champions, args.logo)
        return
    cfg = json.loads(args.edition.read_text(encoding="utf-8"))
    masters = cfg["masters"]
    ids = {m+1024*i for m in masters for i in range(10)}
    knockout_masters = cfg.get("knockout", [])
    ko_ids = {m+1024*i for m, ties in KNOCKOUT if m in knockout_masters for i in range(ties+1)}
    clubs = [c for c, _ in cfg["mls"] + cfg["liga_mx"]]
    match_ids, day_lists = [], []
    ui_snapshot = {}

    def inspect(mem, block):
        ui_snapshot.update(inspect_competition_info(mem, block, ids | ko_ids))

    fixtures = list(read_fixtures(args.pid, args.exe.resolve(strict=True), range(65536),
                                 match_ids=match_ids, day_lists=day_lists,
                                 inspect=inspect if args.ui_snapshot else None))
    if args.ui_snapshot:
        snapshot_regs = {int(reg) for reg in ui_snapshot["records"]}
        ui_snapshot["matches"] = [dict(slot=slot, record=row) for row, slot in zip(fixtures, match_ids)
                                  if row[0] in snapshot_regs]
        with args.ui_snapshot.open("x", encoding="utf-8") as stream:
            json.dump(ui_snapshot, stream, indent=2)
    owned = [(row, slot) for row, slot in zip(fixtures, match_ids) if row[0] in ids]
    years = {row[2][0] for row, _ in owned}
    if len(years)>1:
        raise ValueError("Fixtures from multiple editions share the active regulations")
    year = next(iter(years), YEAR)
    if year!=YEAR:
        if not cfg.get("annual") or not args.journal:
            raise ValueError("Annual edition audit requires the active profile's sporting journal")
        from central_phase2b_audit import journal
        candidates = {field for _, day, reg, kind, field in journal(args.journal)
                      if day//365==year and reg==(0xb402|(year&1)) and kind==0 and len(field)==36}
        if len(candidates)!=1:
            raise ValueError("Annual edition has no unique retained 36-club field")
        clubs = list(candidates.pop())
    if args.bracket_view and (args.calendar or len(knockout_masters)!=3):
        raise ValueError("--bracket-view needs the three knockout masters and a fixture audit")
    if args.calendar:
        report = dict(native_records=len(fixtures), owned_records=len(owned),
                      window=cfg["window"], day_list_load=[len(day) for day in day_lists],
                      participant_fixtures=[row for row in fixtures if set(row[4:6]).intersection(clubs)],
                      us_open_cup=[row for row in fixtures if row[0] & 1023 == 54])
    else:
        rows = [row for row, _ in owned]
        report = audit_report(rows, masters, clubs, args.require_complete, cfg["window"], year)
        check_day_lists(rows, [slot for _, slot in owned], day_lists)
        dates = {row["master"]: row["date"][2] for row in report["fixtures"]}
        conflicts = calendar_conflicts(fixtures, masters, clubs, [dates[m] for m in masters], year)
        if conflicts:
            raise ValueError(f"Registered calendar violates three-day rest: {conflicts}")
        report["master_dates"] = {str(m): dates[m] for m in masters}
        if knockout_masters:
            ko = [(row, slot) for row, slot in zip(fixtures, match_ids) if row[0] in ko_ids]
            report["knockout"] = knockout_report(report, [row for row, _ in ko], knockout_masters, year)
            check_day_lists([row for row, _ in ko], [slot for _, slot in ko], day_lists)
            check_knockout_rest(report["knockout"], fixtures, ids | ko_ids)
            if args.bracket_view:
                report["bracket_view"] = knockout_view(report, report["knockout"], knockout_masters, year)
            if args.require_complete and report["knockout"]["podium"] is None:
                raise ValueError("Leagues Cup knockout is incomplete")
    if args.compare and json.loads(args.compare.read_text(encoding="utf-8")) != report:
        raise SystemExit("Reload audit differs from the baseline fixture and standings snapshot")
    if args.snapshot:
        with args.snapshot.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
