"""Read native fixture records from the dedicated Central American Cup FL27 process."""

import argparse
from collections import Counter, defaultdict
import ctypes
import json
from pathlib import Path
import re
import struct

def read_fixtures(pid, executable, regs, *, match_ids=None, day_lists=None, inspect=None):
    from livedump import Mem, OWNER_FIELD, OWNER_PTR

    mem = Mem(pid)
    try:
        query_path = ctypes.WinDLL("kernel32", use_last_error=True).QueryFullProcessImageNameW
        query_path.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p,
                               ctypes.POINTER(ctypes.c_uint))
        name = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_uint(len(name))
        if not query_path(mem.h, 0, name, ctypes.byref(size)) or Path(name.value).resolve() != executable:
            raise SystemExit("PID does not belong to the dedicated FL27 executable")
        blk = mem.u64(mem.u64(OWNER_PTR) + OWNER_FIELD)
        if inspect is not None:
            inspect(mem, blk)
        bs, cs = mem.read(0x1413146e8, 7), mem.read(0x14131471b, 6)
        assert bs[:3] == b"\x48\x8d\x88" and cs[:2] == b"\x81\xff"
        base, cap = struct.unpack_from("<I", bs, 3)[0], struct.unpack_from("<I", cs, 2)[0]
        assert 0 < cap <= 200000
        elem = 4
        if day_lists is not None:
            first = mem.read(0x140AED7B8, 7)
            today = mem.read(0x140AED7B0, 8)
            append = mem.read(0x141350347, 5)
            if first[:3] != b"\x48\x81\xc1" or today[:4] != b"\x44\x0f\xb7\x89":
                raise ValueError("Unrecognized native calendar layout")
            elem = 4 if append[:4] == b"\x44\x89\x24\x83" else 0
            if append == b"\x66\x44\x89\x24\x43":
                elem = 2
            offset = int.from_bytes(first[3:], "little")
            size, remainder = divmod(int.from_bytes(today[4:], "little") - offset, 365)
            if not elem or remainder or not 0x94 < size < 40000 or (size-0x94) % elem:
                raise ValueError("Invalid native calendar dimensions")
            raw = mem.read(blk + offset, size*365)
            for day in range(365):
                values = []
                for (value,) in struct.iter_unpack("<I" if elem == 4 else "<H",
                                                   raw[day*size:(day+1)*size-0x94]):
                    if value == 0xffff:
                        break
                    values.append(value)
                day_lists.append(values)
        stride = 0x254
        for start in range(0, cap, 1024):
            chunk = mem.read(blk + base + start * stride, min(1024, cap - start) * stride)
            for i in range(0, len(chunk), stride):
                slot, reg, stage, flags, year, month, day = struct.unpack_from("<IHBBHBB", chunk, i)
                if slot & 0xffff == 0xffff or reg not in regs:
                    continue
                h, a = struct.unpack_from("<II", chunk, i + 0x14)
                if match_ids is not None:
                    match_ids.append(slot if elem == 4 else slot & 0xffff)
                yield reg, stage, (year, month, day), flags, h >> 14, a >> 14, tuple(chunk[i + 0x1c:i + 0x22])
    finally:
        mem.close()


def pairs(rows, require_played):
    ties = defaultdict(list)
    for row in rows:
        ties[frozenset(row[4:6])].append(row)
    series = {}
    for key, legs in ties.items():
        assert len(key) == 2 and len(legs) == 2, (key, legs)
        first, second = sorted(legs, key=lambda r: r[2])
        assert first[4:6] == second[4:6][::-1] and first[2] < second[2], legs
        assert (first[3] & 0x30, second[3] & 0x30) == (0, 0x10), legs
        if not require_played:
            continue
        assert first[3] & 0x40 and second[3] & 0x40, legs
        x, y = first[6], second[6]
        votes = (x[0] + y[3] - x[3] - y[0], y[3] - x[3], y[4] - y[1], y[5] - y[2])
        result = next((v for v in votes if v), 0)
        assert result, legs
        winner, loser = first[4:6] if result > 0 else first[4:6][::-1]
        series[key] = winner, loser
    return series


def qualification(lines, year, fields, expected=None):
    """Match the latest complete native qualification trace to current fixtures."""
    draw, result = None, None
    for line in lines:
        marker = re.search(r"CA (qualification begin|qualification end|ranking|entrant) (.*)", line)
        if marker:
            kind, attrs = marker.groups()
            values = dict(re.findall(r"(\w+)=([\w:]+)", attrs))
            if kind == "qualification begin":
                draw = {"draw": values, "rankings": [], "entrants": [], "groups": {}}
            elif draw is not None and kind == "qualification end":
                if values["edition"] == draw["draw"]["edition"] == str(year):
                    if [sorted(draw["groups"].get(chr(65 + g), [])) for g in range(4)] == fields:
                        result = draw
                draw = None
            elif draw is not None:
                draw["rankings" if kind == "ranking" else "entrants"].append(values)
        elif draw is not None:
            group = re.search(r"Central American Cup: group ([A-D]) ((?:\d+ +){4}\d+)", line)
            if group:
                draw["groups"][group[1]] = list(map(int, group[2].split()))
    assert result is not None, "No complete qualification trace matches the native edition"
    entries = result["entrants"]
    by_club = {int(record["club"]): record for record in entries}
    assert len(entries) == len(by_club) == 20
    assert set(by_club) == {club for field in fields for club in field}
    rankings = {(r["association"], r["rank"]): r for r in result["rankings"]}
    for record in entries:
        if record["basis"] != "cup":
            ranked = rankings[(record["association"], record["rank"])]
            assert (record["club"], record["basis"]) == (ranked["club"], ranked["basis"])
            record["source_period"] = ranked["period"]
            record["completed"] = ranked["completed"]
            if record["basis"] == "annual":
                assert result["draw"]["creation"] <= ranked["completed"] <= result["draw"]["cutoff"], record
        if expected:
            assert record["basis"] == expected, record
    for group in result["groups"].values():
        assert [int(by_club[club]["pot"]) for club in group] == list(range(1, 6))
    return result


def check(rows, config, checkpoint, edition=None):
    group, main, helper = (config[k] for k in ("group", "knockout", "helper"))
    group_ids = [group + 1024 * i for i in range(1, 5)]
    helper_ids = [helper + 1024 * i for i in range(3)]
    assert not any(row[0] == group for row in rows), "Group master owns a fixture"
    if checkpoint == "pre-draw":
        assert edition is not None
        assert all(row[2][0] < edition for row in rows), "Current-edition fixtures already exist"
        return
    years = {r[2][0] for r in rows}
    assert len(years) == 1, years
    if edition is not None:
        assert years == {edition}, years
    fields = config["groups"]
    if "annual_sources" in config:
        fields = [sorted({club for row in rows if row[0] == reg for club in row[4:6]})
                  for reg in group_ids]
        for field in fields:
            countries = Counter(config["club_countries"][club] for club in field)
            assert max(countries.values(), default=0) <= 2, countries
    assert len(fields) == 4 and all(len(field) == 5 for field in fields), fields
    assert len({club for field in fields for club in field}) == 20, fields
    stats = defaultdict(lambda: [0] * 6)

    def score(row):
        first, second = row[4:6]
        x, y = row[6][0], row[6][3]
        for club, gf, ga, away in ((first, x, y, 0), (second, y, x, 1)):
            values = (3 if gf > ga else int(gf == ga), gf - ga, gf, gf * away,
                      gf > ga, int(gf > ga) * away)
            stats[club] = [a + b for a, b in zip(stats[club], values)]

    def priority(club):
        return (*stats[club], -club)

    group_rank = []
    for reg, field in zip(group_ids, fields):
        items = [r for r in rows if r[0] == reg]
        assert len(items) == 10
        assert {frozenset(r[4:6]) for r in items} == {
            frozenset((a, b)) for a in field for b in field if a < b}
        assert Counter(r[4] for r in items) == Counter(r[5] for r in items) == dict.fromkeys(field, 2)
        assert Counter(r[2][1:] for r in items) == {(7, 29): 2, (8, 5): 2, (8, 12): 2,
                                                    (8, 19): 2, (8, 26): 2}
        if checkpoint == "groups":
            continue
        for row in items:
            assert row[3] & 0x40
            score(row)
        head = defaultdict(lambda: [0, 0, 0])
        for _, _, _, _, h, a, s in items:
            if stats[h][:3] != stats[a][:3]:
                continue
            for club, gf, ga in ((h, s[0], s[3]), (a, s[3], s[0])):
                for i, value in enumerate((3 if gf > ga else int(gf == ga), gf - ga, gf)):
                    head[club][i] += value
        group_rank.append(sorted(field, key=lambda c: (*stats[c][:3], *head[c], -c), reverse=True))

    knockout = [r for r in rows if r[0] == main]
    play = [r for r in rows if r[0] in helper_ids]
    if checkpoint == "groups":
        assert not knockout and not play, "Early knockout or helper fixtures"
        return fields
    rounds = {stage: [r for r in knockout if r[1] == stage] for stage in (46, 52, 53)}
    assert sum(map(len, rounds.values())) == len(knockout), "Unexpected main knockout stage"

    def ordered_round(items, scheduled, dates, played):
        assert len(items) == 2 * len(scheduled), items
        first = [r for r in items if r[2][1:] == dates[0]]
        second = [r for r in items if r[2][1:] == dates[1]]
        assert Counter(r[4:6] for r in first) == Counter(scheduled), first
        assert Counter(r[4:6] for r in second) == Counter((a, h) for h, a in scheduled), second
        return pairs(items, played)

    seeds = [team for i in range(2) for team in
             sorted((g[i] for g in group_rank), key=priority, reverse=True)]
    qf = [(seeds[7], seeds[0]), (seeds[4], seeds[3]), (seeds[6], seeds[1]), (seeds[5], seeds[2])]
    qf_results = ordered_round(rounds[46], qf, ((9, 9), (9, 16)), checkpoint != "qf")
    if checkpoint == "qf":
        assert not play, "Play-in exists before all quarterfinal outcomes"
        return
    for row in rounds[46]:
        score(row)
    winners, losers = zip(*(qf_results[frozenset(t)] for t in qf))
    sf = [tuple(sorted(winners[i:i + 2], key=priority)) for i in (0, 2)]
    play_pairs = [tuple(sorted(losers[i:i + 2], key=priority)) for i in (0, 2)]
    for row in play:
        tie = next((i for i, clubs in enumerate(play_pairs) if set(clubs) == set(row[4:6])), -1)
        assert tie >= 0 and row[0] in (helper, helper_ids[tie + 1]), row
    complete = checkpoint == "complete"
    play_results = ordered_round(play, play_pairs, ((10, 21), (10, 28)), complete)
    sf_results = ordered_round(rounds[52], sf, ((10, 21), (10, 28)), complete)
    if not complete:
        return
    for row in rounds[52]:
        score(row)
    finalists = tuple(sorted((v[0] for v in sf_results.values()), key=priority))
    final = ordered_round(rounds[53], [finalists], ((12, 2), (12, 6)), True)
    assert len(rows) == 58
    print("Play-in winners:", *(v[0] for v in play_results.values()))
    print("Champion and runner-up:", next(iter(final.values())))
    return (*next(iter(final.values())),
            *(sf_results[frozenset(t)][1] for t in sf),
            *(play_results[frozenset(t)][0] for t in play_pairs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pid", type=int)
    parser.add_argument("checkpoint", choices=("pre-draw", "groups", "qf", "play-in", "complete"))
    parser.add_argument("--prototype", type=Path, default=Path("out/central-american-probe/validation"))
    parser.add_argument("--qualification-log", type=Path)
    parser.add_argument("--expect", choices=("annual", "bootstrap"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--edition", type=int)
    args = parser.parse_args()
    if args.checkpoint == "pre-draw" and args.edition is None:
        parser.error("pre-draw requires --edition")
    if any((args.expect, args.snapshot, args.compare)) and not args.qualification_log:
        parser.error("--expect, --snapshot and --compare require --qualification-log")
    if args.qualification_log and args.checkpoint != "groups":
        parser.error("--qualification-log requires the groups checkpoint")
    config = json.loads((args.prototype / "edition.json").read_text(encoding="utf-8"))
    if "annual_sources" in config:
        from central_probe import DB, WORLD
        from leaguebuilder import club_countries

        database = args.prototype / "FL27-offline/SiderAddons/livecpk" / WORLD / DB
        config["club_countries"] = club_countries(str(database))
    regs = {config["knockout"], *(config["group"] + 1024 * i for i in range(5)),
            *(config["helper"] + 1024 * i for i in range(3))}
    fixtures = sorted(read_fixtures(args.pid, (args.prototype / "FL27-offline/FL_2027.exe").resolve(), regs))
    for fixture in fixtures:
        print(fixture)
    fields = check(fixtures, config, args.checkpoint, args.edition)
    if args.checkpoint == "pre-draw":
        print(f"No native fixtures exist for edition {args.edition} or later.")
        raise SystemExit(0)
    if args.qualification_log:
        assert not any(row[3] & 0x40 for row in fixtures), "Run the draw audit before the first group match"
        report = qualification(args.qualification_log.read_text(encoding="utf-8", errors="replace").splitlines(),
                               fixtures[0][2][0], [sorted(field) for field in fields], args.expect)
        if args.compare:
            assert report == json.loads(args.compare.read_text(encoding="utf-8")), "Qualification changed after reload"
        if args.snapshot:
            with args.snapshot.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2)
        print(json.dumps(report, indent=2))
    print(f"Verified {args.checkpoint} in edition {fixtures[0][2][0]} using {len(fixtures)} native records.")
