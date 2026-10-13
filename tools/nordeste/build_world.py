"""Build a combined Sul/Libertadores/Nordeste LAB world in this workspace.

Never installs into a game directory. The package remains experimental until
its live adapter, discipline and calendar are validated.
"""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import leaguebuilder as L
import mkleague as M
import mkphases as P
import pesdb


def rows(data, size):
    assert len(data) % size == 0
    return [bytearray(data[i:i + size]) for i in range(0, len(data), size)]


LOGO = None                      # build_world.py --logo <picture>: the cup's emblem (else a drawn one)
UEL_KO = 6                       # the knockout row to copy (mkccup's): a knockout of 2 x groups clubs


def add_competition(root, participants):
    base = root / "common/etc/pesdb"
    comp, regs, ents = (bytearray(M.load(str(base), name)) for name in
                       ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    cr, rr = rows(comp, M.COMP), rows(regs, M.REG)
    by_id = {P.rid_of(r): r for r in rr}
    cids = {r[M.CID_OFF] for r in cr}
    cid = next(i for i in range(175, 256) if i not in cids)
    carrier = next(i for i in range(cid + 1, 256) if i not in cids)
    phases = next(list(range(i, i + 3)) for i in range(560, 596)
                  if not any(i + p + 1024 * k in by_id for p in range(3) for k in range(5)))
    groups, matches, knockout = phases
    # The competition row of the Copa do Brasil (cid 24, BRAZIL_D1_CUP): a national cup of Brazil,
    # listed with Brazil's competitions. The first build copied the Libertadores' (cid 5) and the
    # cup sat with the continental competitions.
    c = bytearray(next(c for c in cr if c[M.CID_OFF] == 24))
    c[M.CID_OFF] = cid
    M.put(c, M.CODE_OFF, "FL_NORDESTE_2026", M.COMP - M.CODE_OFF)
    comp += c
    # the carrier: the same row, its own id and code; fl26swiss leaves it out of the Info Database
    c2 = bytearray(c)
    c2[M.CID_OFF] = carrier
    M.put(c2, M.CODE_OFF, "FL_NORDESTE_JOGOS", M.COMP - M.CODE_OFF)
    comp += c2
    added = []

    def clone(template, reg, parent, group, shape, name, single=False, into=None):
        r = bytearray(by_id[template])
        r[0:2] = bytes(2)
        r[M.R_ID:M.R_ID + 2] = reg.to_bytes(2, "little")
        r[6:8] = parent.to_bytes(2, "little")
        r[M.R_CID] = cid if into is None else into
        r[0x0a] = group
        P.apply_phase(r, shape)
        flags = int.from_bytes(r[0x10:0x14], "little")
        flags = (flags & ~(7 << 12)) | (1 << 12)  # single group turn
        if single:
            flags &= ~(7 << 9)
        if shape[0] == 1:
            flags = (flags & ~((1 << 24) | (1 << 25))) | (1 << 27)
        r[0x10:0x14] = flags.to_bytes(4, "little")
        M.put_names(r, 0, name)
        added.append(r)

    # The group stage as shown: a master of 20 and four groups of five, A-D. No matches: the runtime
    # writes their tables from the carrier's results (Competition Info: Group stage, L1/R1).
    clone(9, groups, 0, 255, (2, 20, 4, 4), "Copa do Nordeste")
    for g in range(4):
        clone(1033, groups + 1024 * (g + 1), groups, g, (2, 5, 4, 4), "Copa do Nordeste")
    # The matches, in the carrier: a master of 20 in two groups and two group rows of ten, A/B and C/D,
    # each playing only its cross matches (the runtime's schedule).
    clone(9, matches, 0, 255, (2, 20, 2, 4), "Copa do Nordeste", into=carrier)
    for g in range(2):
        clone(1033, matches + 1024 * (g + 1), matches, g, (2, 10, 2, 4), "Copa do Nordeste", into=carrier)
    # The knockout of eight: the Europa League's knockout row (mkccup's), legs mode 2 (every round two
    # legs; the runtime answers the quarter-finals one match), no away goals, no extra time,
    # penalties, no third place.
    k = bytearray(by_id[UEL_KO])
    k[0:2] = bytes(2)
    k[M.R_ID:M.R_ID + 2] = knockout.to_bytes(2, "little")
    k[6:8] = bytes(2)
    k[0x0a] = 255
    k[M.R_CID] = cid
    k[M.R_TEAMS] = (k[M.R_TEAMS] & ~0x3f) | 8
    flags = int.from_bytes(k[0x10:0x14], "little")
    flags = (flags & ~(7 << 9)) | (2 << 9)
    flags &= ~((1 << 24) | (1 << 25) | (1 << 28) | (1 << 29))
    flags |= 1 << 27
    k[0x10:0x14] = flags.to_bytes(4, "little")
    M.put_names(k, 0, "Copa do Nordeste")
    added.append(k)
    assert len(added) == 9
    assert len(rr) + len(added) <= 600, "regulation row capacity exceeded"
    regs += b"".join(added)
    eid = max(int.from_bytes(r[M.E_EID:M.E_EID + 4], "little") for r in rows(ents, M.ENT))
    for i, club in enumerate(participants):
        e = bytearray(M.ENT)
        e[M.E_TEAM:M.E_TEAM + 4] = club["team_id"].to_bytes(4, "little")
        e[M.E_EID:M.E_EID + 4] = (eid + i + 1).to_bytes(4, "little")
        e[M.E_CID], e[M.E_ORDER] = cid, i + 1
        ents += e
    M.write_tables(str(root), comp, regs, ents)
    import lbassets
    for c_ in (cid, carrier):
        lbassets.league_logo(str(root), c_, "Copa do Nordeste", str(LOGO) if LOGO else None)
    return cid, phases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="the game's unpacked pesdb tables (common/etc/pesdb)")
    parser.add_argument("--reuse-assets", action="store_true")
    parser.add_argument("--recipe", type=Path, default=HERE / "sul_recipe.json",
                        help="the South American cups' recipe the world starts from (the game's own leagues and clubs)")
    parser.add_argument("--logo", type=Path, help="a picture for the cup's emblem (none: a drawn emblem)")
    parser.add_argument("--dll", type=Path, default=TOOLS / "native/fl26swiss.dll",
                        help="fl26swiss.dll built from tools/native (build-swiss.sh)")
    args = parser.parse_args()
    global LOGO
    LOGO = args.logo
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    recipe["world"] = "_FL26Nordeste2026"
    recipe["leagues"] += json.loads((HERE / "clubs.recipe.json").read_text(encoding="utf-8"))["leagues"]
    (HERE / "combined.recipe.json").write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    package = HERE / "package"
    asset_root = HERE / "combined-assets/SiderAddons/livecpk" / recipe["world"]
    if not args.reuse_assets:
        with (HERE / "build_world.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
            asset_root = Path(L.build(L.plan(recipe, str(args.base)), str(args.base), str(HERE / "combined-assets"), replace=True))
    assert (asset_root / "fl26world.txt").exists(), "build assets first"
    root = package / "SiderAddons/livecpk" / recipe["world"]
    shutil.copytree(asset_root, root, dirs_exist_ok=True)
    teams = pesdb.team_rows(pesdb.load("Team", str(root / "common/etc/pesdb")))
    spec = json.loads((HERE / "nordeste2026.json").read_text(encoding="utf-8"))
    for p in spec["participants"]:
        candidates = [t for t in teams.values() if t["name"] == p["database_name"]]
        assert len(candidates) == 1, (p["name"], candidates)
        p["team_id"] = candidates[0]["id"]
    cid, phases = add_competition(root, spec["participants"])
    # Day-of-year values, zero based. These candidate dates still require live collision audit.
    # January to April: off the Copa do Brasil (16..86), the continental group days (62, 76, 83,
    # 104, 118), the Libertadores qualifying (34, 41) and the Sudamericana play-off (146, 153); the
    # Brazilian leagues keep their rounds off these (2026-10-12: the old May-June dates met the
    # Sudamericana groups and the Brasileirao)
    # the first round on day 25, not 27: the Libertadores qualifying phase 2 plays its second leg on
    # day 27, and a Brazilian club can be in both
    days = [25, 47, 54, 68, 74, 90, 93, 100, 107, 113]
    config = dict(competition=cid, phases=phases, days=days,
                  participants=spec["participants"], status="experimental_not_live_validated",
                  limitations=["disciplinary data adapter and card reset missing",
                               "Copa do Brasil berth not integrated", "live calendar/save/rollover validation pending"])
    modules = package / "SiderAddons/modules"
    modules.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.dll, modules / "fl26swiss.dll")
    shutil.copy2(REPO / "sider/fl26join.dll", modules)
    shutil.copy2(REPO / "sider/fl26caps.lua", modules)
    for path in (root / "modules").glob("*"):
        if path.is_file():
            shutil.copy2(path, modules)
    shutil.copy2(root / "fl26world.txt", modules)
    loader = (REPO / "sider/experimental/fl26swiss.lua").read_text(encoding="utf-8")
    assert loader.count('  if status == 0 then\n') == 1
    call = '''
    ffi.cdef([[
      typedef int (*fl26_nd_engine_config_t)(const uint16_t*, const uint32_t*, const uint16_t*);
      typedef int (*fl26_nd_engine_install_t)(void);
    ]])
    local nc = ffi.C.GetProcAddress(h, "fl26_nd_engine_config")
    local ni = ffi.C.GetProcAddress(h, "fl26_nd_engine_install")
    if nc == nil or ni == nil then error("Nordeste DLL/config mismatch") end
    local nr = ffi.new("uint16_t[3]", { PHASES })
    local nt = ffi.new("uint32_t[20]", { CLUBS })
    local nd = ffi.new("uint16_t[10]", { DAYS })
    if ffi.cast("fl26_nd_engine_config_t", nc)(nr,nt,nd) ~= 1 then error("Nordeste invalid configuration") end
    if ffi.cast("fl26_nd_engine_install_t", ni)() ~= 1 then log("nordeste: a patch of the cup's own is not in (see above)") end
    log("nordeste: enabled -- groups A-D shown, matches in A/B and C/D, knockout A1-C2 B1-D2 C1-A2 D1-B2")
'''.replace("PHASES", ",".join(map(str, phases))).replace("CLUBS", ",".join(str(p["team_id"]) for p in spec["participants"])).replace("DAYS", ",".join(map(str, days)))
    loader = loader.replace('  if status == 0 then\n', '  if status == 0 then\n' + call, 1)
    (modules / "fl26swiss.lua").write_text(loader, encoding="utf-8")
    (package / "nordeste-runtime.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in package.rglob("*") if p.is_file() and p.name != "manifest.json"}
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Built {root}; cid={cid}, phases={phases}; NOT installed. See runtime limitations.")


if __name__ == "__main__":
    main()
