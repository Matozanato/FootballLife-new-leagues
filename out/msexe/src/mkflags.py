"""python mkflags.py --root <livecpk root> [--base <pesdb dir>] [--countries FILE] [--write]

Give every league of ours its country's flag, in the Select Team list and in the country
list above it.

Neither the league record nor the regulation record carries a country.  The game works a
country out at runtime, in two places, and both answer "none" for a league we added:

  * the Select Team list asks 0x140c950d0(slot): 23 {slot, country} pairs built on the stack,
    0xffff for any other slot -- so no flag next to any league on a slot of ours.
    sider/experimental/fl26comptab.lua hooks it with an ID_COUNTRY table this tool writes.
  * the country list asks 0x1414cdbe0(region): 25 {country, region} pairs, the same way.
    sider/experimental/fl26catlist.lua hooks it with a COUNTRY table this tool writes.

The country value is the flag id: common/render/symbol/flag/flag_<id>.png, the same id
Country.bin carries in bits 10-18 of its first dword.  So a country the game already
draws needs no new art at all.

Where the country comes from, per league, first match wins:
  1. the --countries file, one line per league:
        <regulation id | league name | region N> = <country name | flag id>
     Country names are matched against every language in Country.bin, so "Croatia",
     "Hrvatska" is not there but "CROATIE" and "KROATIEN" are.  '#' starts a comment.
  2. a guess from the league's own name: "Croatian League" -> CROATIA, "Swedish League" ->
     SWEDEN.  Every guess is printed; a name that fits two countries is not guessed.
  3. nothing: the league keeps no flag, as before.

Watch the regions below 29.  The exe's region table still answers for four regions no
shipped league uses -- 11 Poland, 13 Sweden, 14 Norway, 20 Mexico -- so a league of ours
placed there by spreadregions shows THAT country's flag.  That is how a Lithuanian league
came to wear a Scandinavian one (issue #11).  For those regions this tool writes the
league's own country, or 0xfffe ("no country", what the exe itself answers for Germany)
when it has none.

A region that holds a shipped competition is left to the game: a league of ours sitting on
England's region is shown as English, whatever this tool is told.

Without --write it only reports.  With --write it rewrites the two tables in place, in
sider/experimental/ next to this folder unless --modules says otherwise; copy the two .lua
files into SiderAddons/modules afterwards.

Country.bin is not shipped here: extract it with
    python cpkx.py <game>/download/data_s2526.cpk <dir> pesdb/Country.bin
and point --base (or FL26_PESDB) at <dir>/common/etc/pesdb.

The idea, the slot hook and the first working version came from Stagnant09 (issue #11).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague

COUNTRY_REC = 1420
COUNTRY_NAMES = range(148, COUNTRY_REC - 69, 70)   # 18 language columns of 70 bytes
COUNTRY_EN = 288
NO_COUNTRY = 0xfffe

# The exe's own {region: country} pairs, read off the stack table at 0x1414cdbe0.  The four
# it answers although no shipped league sits there are the ones that bite: 11, 13, 14, 20.
# 22/23/24 answer "no country" for Germany, the USA and Japan.  (10 and 28 answer Switzerland
# and Thailand, though the shipped data puts Greece and Saudi Arabia there; that is the
# game's business and nothing here touches it.)
EXE_REGION_COUNTRY = {2: 204, 3: 208, 4: 236, 5: 215, 6: 228, 7: 224, 8: 197, 9: 230,
                      10: 238, 11: 227, 12: 203, 13: 237, 14: 226, 15: 232, 16: 146, 17: 144,
                      18: 147, 19: 148, 20: 124, 21: 7, 22: 0xfffe, 23: 0xfffd, 24: 0xfffc,
                      27: 190, 28: 36}


def table(name, dirs):
    for d in dirs:
        p = os.path.join(d, name + ".bin")
        if os.path.exists(p):
            raw = open(p, "rb").read()
            return pesdb.wesys_unpack(raw) if raw[3:8] == b"WESYS" else raw
    raise SystemExit("%s.bin not found in %s -- see the note on Country.bin in --help"
                     % (name, ", ".join(dirs) or "<nothing: pass --base or set FL26_PESDB>"))


def countries(raw):
    """{flag id: (English name, {every name in every language, upper case})}"""
    out = {}
    for r in pesdb.rows(raw, COUNTRY_REC):
        fid = (int.from_bytes(r[:4], "little") >> 10) & 0x1ff
        names = {pesdb.cstr(r[o:o + 70]).strip().upper() for o in COUNTRY_NAMES}
        names.discard("")
        out[fid] = (pesdb.cstr(r[COUNTRY_EN:COUNTRY_EN + 70]).strip(), names)
    return out


def title(name):
    return " ".join(w.capitalize() if w not in ("OF", "AND") else w.lower() for w in name.split())


def by_name(cty, text):
    """flag id for a country name in any language, or None"""
    t = text.strip().upper()
    hits = [fid for fid, (_, names) in cty.items() if t in names]
    return hits[0] if len(hits) == 1 else None


def words(s):
    return re.findall(r"[A-Z]+", s.upper())


def fits(word, cname):
    """how well a word of a league name stands for a word of a country's name, 0 = not at all

    CROATIAN/CROATIA and AUSTRALIAN/AUSTRALIA are whole-word fits; SWEDISH/SWEDEN is a loose
    one (the shared start, at least four letters and all but the last two).  The number is
    the length of the shared start, so AUSTRALIAN fits AUSTRALIA better than AUSTRIA."""
    if len(cname) < 4:
        return 99 if word == cname else 0
    if word.startswith(cname):
        return len(cname) + 1
    n = 0
    while n < min(len(word), len(cname)) and word[n] == cname[n]:
        n += 1
    return n if n >= 4 and n >= len(cname) - 2 else 0


# a first word this common says nothing on its own: SOUTH AFRICA is not South Korea
VAGUE = {"NORTH", "SOUTH", "EAST", "WEST", "NEW", "UNITED", "REPUBLIC", "CENTRAL", "SAUDI"}
# and these are not names at all -- "AND" is also Andorra's three-letter code
FILLER = {"AND", "THE", "OF", "DE", "DEL", "DU", "LA", "LE", "DI", "LEAGUE", "LIGA", "CUP",
          "OTHER", "TEAMS"}


def guess(cty, league):
    """(flag id, why) from the league's name, or (None, why)

    Every language Country.bin carries is tried, best fit first: all the words of a country's
    name, exactly (AUSTRALIA, not AUSTRIA); all of them loosely (SWEDISH for SWEDEN); then one
    telling word (MACEDONIAN for NORTH MACEDONIA, CZECHIA for CZECH REPUBLIC) -- but only a
    word no other country's name uses, so KOREAN guesses neither Korea."""
    lw = [w for w in words(league) if len(w) >= 3 and w not in FILLER]
    owners = {}
    for fid, (_, names) in cty.items():
        for nm in names:
            for c in words(nm):
                owners.setdefault(c, set()).add(fid)

    def best_fit(c):
        return max((fits(w, c) for w in lw), default=0)

    top, ranked = (0, 0), []
    for fid, (_, names) in cty.items():
        s = (0, 0)
        for nm in names:
            cw = words(nm)
            if not cw:
                continue
            q = [best_fit(c) for c in cw]
            if all(c in lw for c in cw):
                s = max(s, (3, sum(q)))
            elif all(q):
                s = max(s, (2, sum(q)))
            else:
                for c in (max(cw, key=len), cw[0]):
                    telling = len(c) >= 6 or (c is cw[0] and len(cw) > 1 and len(c) >= 5)
                    if telling and c not in VAGUE and len(owners.get(c, ())) == 1 and best_fit(c):
                        s = max(s, (1, best_fit(c)))
        if s > top:
            top, ranked = s, [fid]
        elif s[0] and s == top:
            ranked.append(fid)
    if len(ranked) == 1:
        return ranked[0], "guessed from the name"
    if ranked:
        return None, "name fits %s -- say which in --countries" % " / ".join(title(cty[f][0]) for f in ranked)
    return None, "no country in the name"


def read_countries_file(path, cty):
    """[(kind, key, flag id)] with kind 'id', 'region' or 'name'"""
    out = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise SystemExit("%s:%d: expected '<league> = <country>'" % (path, n))
        k, v = (x.strip() for x in line.split("=", 1))
        fid = int(v) if v.isdigit() else by_name(cty, v)
        if fid is None or fid not in cty:
            raise SystemExit("%s:%d: no country called %r in Country.bin" % (path, n, v))
        m = re.fullmatch(r"region\s+(\d+)", k, re.I)
        if m:
            out.append(("region", int(m.group(1)), fid))
        elif k.isdigit():
            out.append(("id", int(k), fid))
        else:
            out.append(("name", k.upper(), fid))
    return out


def our_leagues(root, base_dirs):
    """[(regulation id, region, name)] for every league in <root> the shipped tables lack"""
    p = os.path.join(root, "common", "etc", "pesdb")
    regs = pesdb.reg_rows(table("CompetitionRegulation", [p]))
    comp = pesdb.comp_rows(table("Competition", [p]))
    shipped = {r["id"] for r in pesdb.reg_rows(table("CompetitionRegulation", base_dirs))}
    region = {c["id"]: mkleague.dec_region(c["raw"][3]) for c in comp}
    out = [(r["id"], region.get(r["comp"]), r["name"])
           for r in regs if r["type"] == 4 and r["id"] not in shipped]
    return sorted(out), comp


def shipped_regions(base_dirs):
    return {mkleague.dec_region(c["raw"][3]): c["code"]
            for c in pesdb.comp_rows(table("Competition", base_dirs))}


def render(name, entries):
    lines = ["local %s = {" % name]
    for k in sorted(entries):
        fid, note = entries[k]
        lines.append("  [%d] = %d,%s-- %s" % (k, fid, " " * max(1, 6 - len(str(fid))), note))
    lines.append("}")
    return "\n".join(lines)


def rewrite(path, name, entries):
    src = open(path, encoding="utf-8").read()
    pat = re.compile(r"local %s = \{.*?\n\}" % name, re.S)
    if not pat.search(src):
        raise SystemExit("no 'local %s = {' table in %s" % (name, path))
    new = pat.sub(lambda m: render(name, entries), src, count=1)
    if new != src:
        open(path, "w", encoding="utf-8", newline="\n").write(new)
    return new != src


def main():
    a = sys.argv[1:]

    def opt(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    root = opt("--root")
    if not root or "--help" in a:
        print(__doc__)
        return 1
    base_dirs = [opt("--base")] if opt("--base") else list(pesdb.PESDB_DIRS)
    cty = countries(table("Country", [os.path.join(root, "common", "etc", "pesdb")] + base_dirs))
    rules = read_countries_file(opt("--countries"), cty) if opt("--countries") else []
    leagues, _ = our_leagues(root, base_dirs)
    shipped = shipped_regions(base_dirs)
    print("%d leagues of ours, %d countries in Country.bin\n" % (len(leagues), len(cty)))

    id_country, per_region = {}, {}
    for rid, region, name in leagues:
        fid, why = None, None
        for kind, key, f in rules:
            if (kind == "id" and key == rid) or (kind == "region" and key == region) \
                    or (kind == "name" and key == name.upper()):
                fid, why = f, "from --countries"
                break
        if fid is None:
            fid, why = guess(cty, name)
        shown = title(cty[fid][0]) if fid is not None else "-"
        print("  reg %3d  region %2s  %-32s %-22s %s" % (rid, region, name[:32], shown, why))
        if fid is not None:
            id_country[rid] = (fid, "%s (%s)" % (title(cty[fid][0]), name))
        per_region.setdefault(region, set()).add(fid)

    region_country = {}
    print()
    for region in sorted(r for r in per_region if r is not None):
        got = per_region[region] - {None}
        exe = EXE_REGION_COUNTRY.get(region)
        if region in shipped:
            print("  region %2d holds %s: left to the game" % (region, shipped[region]))
        elif len(got) > 1:
            print("  region %2d: leagues of %s share it -- one region, one country; "
                  "move one with spreadregions" % (region, " and ".join(title(cty[f][0]) for f in got)))
        elif got:
            f = got.pop()
            region_country[region] = (f, title(cty[f][0]))
        elif exe is not None and exe < 0xfff0:
            region_country[region] = (NO_COUNTRY, "no country (the exe alone would say %s)"
                                      % title(cty.get(exe, ("?", None))[0]))
    for region, (f, note) in sorted(region_country.items()):
        exe = EXE_REGION_COUNTRY.get(region)
        extra = ""
        if exe is not None and exe < 0xfff0 and exe != f:
            extra = "   <- overrides %s" % title(cty.get(exe, ("?", None))[0])
        print("  region %2d -> %-5s %s%s" % (region, f, note, extra))

    if "--write" not in a:
        print("\nreport only; --write rewrites COUNTRY in fl26catlist.lua and ID_COUNTRY in fl26comptab.lua")
        return 0
    mods = opt("--modules", os.path.join(os.path.dirname(HERE), "sider", "experimental"))
    for f, name, entries in (("fl26catlist.lua", "COUNTRY", region_country),
                             ("fl26comptab.lua", "ID_COUNTRY", id_country)):
        p = os.path.join(mods, f)
        print("%s %s (%d entries)" % ("rewrote" if rewrite(p, name, entries) else "unchanged", p, len(entries)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
