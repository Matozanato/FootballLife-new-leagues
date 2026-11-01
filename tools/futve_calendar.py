r"""python tools/futve_calendar.py [--src out/futve/world-finals] [--out out/futve/world-calendar]

Fase 4 (31.10.2026, Felix): the Liga FUTVE from January to December, as the real 2026 season --
Apertura from February to June, Clausura from August to November, each with its two groups of four
and its final, the Final del FUTVE in December. Built from the phase-3 world (world-finals), which is
left untouched; output in out/futve/world-calendar (fl26world.txt and common\etc\pesdb).

Only fl26world.txt changes (the three Competition*.bin are copied as they are):
  - `season 29 1`: region 29 (Venezuela, our region) plays January-December (fl26joindll/fl26join,
    fl26swiss calyear);
  - `splitdays 191|192 d,d,...`: the days of the Apertura's and the Clausura's 13 rounds (the phase-4
    fl26swiss.dll dates the split phases on them instead of the Scottish August-May line);
  - the play-offs (259/260): fill day, group days, final; the Final del FUTVE (263): its two legs;
  - the Copa Venezuela (255) and the Supercopa (256) dated as a January-December country's cups
    (leaguebuilder: ENGLAND_D1_CUP with seven days, JAPAN_SUPER_CUP at the end of January).
Days are of the year, 1 January = 0 (2026: Saturdays are d % 7 == 2).
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

REGION = 29
LEAGUE_REG, LEAGUE_NAME = 11, "Liga FUTVE"
# 31.10. (second pass, the phase-4 fl26swiss.dll's clash report on the game's own days): the
# national teams' windows of the game are days 88 91 94 | 153 156 159 | 182..203 (the summer
# tournaments' block) | 244 247 | 279 282 | 314 317; the Libertadores' 34 41 | 62 76 83 104 118 139 |
# 163 223 258 265 296 303 324 331, the Club World Cup's 348..352. Every Venezuelan day below is at
# least two days from all of them and from every other Venezuelan day.
APERTURA = [44, 51, 58, 65, 72, 79, 86, 100, 107, 111, 114, 121, 128]     # Sat 14 Feb .. Sat 9 May (not 93: window; Wed 22 Apr instead)
CLAUSURA = [205, 212, 219, 226, 233, 236, 240, 254, 261, 268, 271, 275, 289]   # Sat 25 Jul .. Sat 17 Oct (not 247/282: windows; Wed 26 Aug, 30 Sep instead)
AP_FILL, AP_GDAYS, AP_FINAL = 129, [132, 135, 142, 146, 149, 151], 167    # groups 13 May .. 1 Jun (before the June window), final Wed 17 Jun
CL_FILL, CL_GDAYS, CL_FINAL = 290, [293, 300, 307, 310, 320, 327], 335    # groups 21 Oct .. 24 Nov (not 314/317: window), final Wed 2 Dec
FF_DAYS = [342, 345]                                 # Final del FUTVE: Wed 9 and Sat 12 Dec (Club World Cup from 348)
COPA_LIKE, COPA_DAYS = 23, [69, 97, 125, 174, 230, 251, 286]             # FA Cup row, Wednesdays clear of all the above
SUPER_LIKE, SUPER_DAYS = 97, [30]                    # Japan Super Cup row, Sat 31 Jan

def csv(v):
    return ",".join(str(x) for x in v)

def setkey(line, key, val):
    parts = line.rstrip("\r\n").split(" ")
    eol = line[len(line.rstrip("\r\n")):]
    for i, p in enumerate(parts):
        if p.startswith(key + "="):
            parts[i] = "%s=%s" % (key, val)
            return " ".join(parts) + eol
    # before name= (which takes the rest of the line)
    for i, p in enumerate(parts):
        if p.startswith("name="):
            return " ".join(parts[:i] + ["%s=%s" % (key, val)] + parts[i:]) + eol
    return " ".join(parts + ["%s=%s" % (key, val)]) + eol

def build(src, out):
    txt = open(os.path.join(src, "fl26world.txt"), encoding="utf-8", newline="").read()
    lines = txt.splitlines(True)
    eol = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    res, done = [], set()
    for ln in lines:
        w = ln.split()
        if not w:
            res.append(ln); continue
        if w[0] == "season" and len(w) > 1 and w[1] == str(REGION):
            continue                                   # ours below
        if w[0] == "splitdays":
            continue
        if w[0] == "league" and w[1] == "11":
            # the Copa Venezuela as the league's national cup (cup=): fl26joindll then puts it in
            # the season the game builds at New Year, as Mod Studio's January-December cups. Without
            # it the Copa (255) entered no season at all in the first test (31.10.)
            ln = setkey(ln, "cup", 255); done.add("cup")
        elif w[0] == "ccup" and w[1] == "259":
            ln = setkey(setkey(setkey(ln, "fill", AP_FILL), "gdays", csv(AP_GDAYS)), "days", AP_FINAL); done.add("259")
        elif w[0] == "ccup" and w[1] == "260":
            ln = setkey(setkey(setkey(ln, "fill", CL_FILL), "gdays", csv(CL_GDAYS)), "days", CL_FINAL); done.add("260")
        elif w[0] == "ccup" and w[1] == "263":
            ln = setkey(ln, "days", csv(FF_DAYS)); done.add("263")
        elif w[0] == "dates" and w[1] == "255":
            ln = "dates 255 like=%d days=%s%s" % (COPA_LIKE, csv(COPA_DAYS), eol); done.add("255")
        elif w[0] == "dates" and w[1] == "256":
            ln = "dates 256 like=%d days=%s%s" % (SUPER_LIKE, csv(SUPER_DAYS), eol); done.add("256")
        res.append(ln)
        if w[0] == "split" and w[1] == "11":
            res.append("season %d 1%s" % (REGION, eol))
            res.append("splitdays 191 %s%s" % (csv(APERTURA), eol))
            res.append("splitdays 192 %s%s" % (csv(CLAUSURA), eol))
            done.add("split")
    missing = {"259", "260", "263", "255", "256", "split", "cup"} - done
    if missing:
        raise SystemExit("world-finals lacks: %s" % ", ".join(sorted(missing)))
    db = os.path.join(out, "common", "etc", "pesdb")
    os.makedirs(db, exist_ok=True)
    for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"):
        shutil.copy2(os.path.join(src, "common", "etc", "pesdb", n), os.path.join(db, n))
    # 31.10. (Felix): the league's own name again in Select Team -- regulation 11 is "Liga FUTVE",
    # not phase 3's "Tabla acumulada FUTVE"; the title the game gives the accumulated table's
    # leader is taken out of the Palmares by the phase-4 fl26swiss.dll (honours/cabinet).
    sys.path.insert(0, HERE)
    import mkleague as M
    C, R, E = (M.load(db, n) for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    R = bytearray(R)
    hit = 0
    for i in range(len(R) // M.REG):
        if int.from_bytes(R[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little") == LEAGUE_REG:
            row = bytearray(R[i * M.REG:(i + 1) * M.REG])
            M.put_names(row, 0, LEAGUE_NAME, skip=(9,))       # slot 9 is the internal label
            R[i * M.REG:(i + 1) * M.REG] = row
            hit += 1
    if hit != 1:
        raise SystemExit("regulation %d: %d rows" % (LEAGUE_REG, hit))
    M.write_tables(out, bytes(C), bytes(R), bytes(E))
    with open(os.path.join(out, "fl26world.txt"), "w", encoding="utf-8", newline="") as f:
        f.write("".join(res))
    print("world-calendar: %s (season %d 1, Apertura %d..%d, Clausura %d..%d, finals %d/%d, Final del FUTVE %s)"
          % (out, REGION, APERTURA[0], APERTURA[-1], CLAUSURA[0], CLAUSURA[-1], AP_FINAL, CL_FINAL, csv(FF_DAYS)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(REPO, "out", "futve", "world-finals"))
    ap.add_argument("--out", default=os.path.join(REPO, "out", "futve", "world-calendar"))
    a = ap.parse_args()
    if os.path.abspath(a.src) == os.path.abspath(a.out):
        raise SystemExit("--out must not be the phase-3 world")
    build(a.src, a.out)

if __name__ == "__main__":
    main()
