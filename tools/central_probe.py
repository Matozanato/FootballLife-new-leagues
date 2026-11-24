"""Assemble a dedicated FL27 feasibility world from local, already unpacked data."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess

import central_qualification
import leaguebuilder as B
import lbplayers
import mkccup as K
import mkeuropo
import mkleague as M
import realcal


DB = Path("common/etc/pesdb")
WORLD = "_FL26CentralProbe"
STEAM_ID = 20271129
PHASE2_STEAM_ID = 20271130
PHASE2B_STEAM_ID = 20271131
LEAGUES_STEAM_ID = 20271136
NAME = "CONCACAF Central American Cup"
FILE_SIZES = (("Competition.bin", M.COMP), ("CompetitionRegulation.bin", M.REG),
              ("CompetitionEntry.bin", M.ENT))
ASSOCIATIONS = ((217, 112, 4), (218, 119, 4), (219, 121, 3), (327, 116, 3),
                (222, 128, 3), (330, 127, 2), (489, 108, 1))


def rows(db):
    return [K.rows(M.load(str(db), filename), size) for filename, size in FILE_SIZES]


def generate_tables(db, root, cid, helper_cid, group, ko, helper, clubs, log=print, name=NAME):
    stock_rows = rows(db)
    comp, reg, entry = (b"".join(table) for table in stock_rows)
    regs = {K.rid(row): row for row in stock_rows[1]}
    owned = {group+1024*i for i in range(5)} | {ko} | {helper+1024*i for i in range(3)}
    if len(owned) != 9 or owned & regs.keys():
        raise ValueError("Central American Cup regulation family collides with the world")
    if cid == helper_cid or {cid, helper_cid} & {M.comp_cid(row) for row in stock_rows[0]}:
        raise ValueError("Central American Cup competition IDs collide with the world")
    if clubs and (len(clubs) != 20 or len(set(clubs)) != 20):
        raise ValueError("Central American Cup requires twenty distinct seed clubs")
    competition = bytearray(next(row for row in stock_rows[0] if M.comp_cid(row) == 5))
    M.set_comp_cid(competition, cid)
    competition[M.REGION_OFF] = M.enc_region(1)
    competition[M.FLAG_OFF] = (competition[M.FLAG_OFF] & ~7) | 6
    M.put(competition, M.CODE_OFF, "FL_CAC_PROBE", M.COMP - M.CODE_OFF)
    comp += competition
    for template, rid, count in [(9, group, 20), (6, ko, 8),
                                 *((1033 + i * 1024, group + (i + 1) * 1024, 5)
                                   for i in range(4))]:
        row = bytearray(regs[template])
        row[:2] = bytes(2)
        row[2:4] = rid.to_bytes(2, "little")
        M.set_reg_cid(row, cid)
        M.put_names(row, 0, name)
        row[M.R_TEAMS] = (row[M.R_TEAMS] & ~63) | count
        rules = int.from_bytes(row[16:20], "little") & ~(7 << 9)
        if rid == ko:
            # Caribbean's native two-leg mode and tie rules, with bronze disabled.
            rules = (rules & ~((1 << 28) | (1 << 29))) | (2 << 9) | (3 << 24)
        elif rid == group:
            rules = (rules & ~31) | 4
        else:
            row[6:8] = group.to_bytes(2, "little")
        row[16:20] = rules.to_bytes(4, "little")
        reg += row
    eid = max(int.from_bytes(r[4:8], "little") for r in K.rows(entry, M.ENT))
    for i, club in enumerate(clubs, 1):
        row = bytearray(M.ENT)
        row[:4] = club.to_bytes(4, "little")
        row[4:8] = (eid + i).to_bytes(4, "little")
        M.set_ent_cid(row, cid)
        row[M.E_ORDER] = i
        entry += row
    M.write_tables(str(root), comp, reg, entry)
    mkeuropo.prerounds_single(str(db), str(root), helper_cid, "FL_CAC_PLAYIN",
                             "Central America Play-In", [(helper, 2)],
                             log=log, one_match=False, region=1, confederation=0)
    comp_rows, reg_rows, entry_rows = rows(db)
    helper_regs = {helper + 1024 * i for i in range(3)}
    for row in reg_rows:
        if K.rid(row) in helper_regs:
            rules = int.from_bytes(row[16:20], "little") | (3 << 24)
            row[16:20] = rules.to_bytes(4, "little")
    M.write_tables(str(root), *(b"".join(table) for table in (comp_rows, reg_rows, entry_rows)))


def build_world(stock, assets, metadata, dest, dynamic=False, champions_plan=None):
    stock_rows = rows(stock)
    mega = rows(assets / DB)
    leagues = {r: (cid, name, clubs) for r, cid, name, clubs in B.game_leagues(str(assets / DB))}
    source_lines = metadata.read_text(encoding="utf-8").splitlines()
    countries = B.club_countries(str(assets / DB))
    nations = {number: name for name, number in B.country_ids(str(stock))}
    comp, reg, entry = (bytearray(b"".join(table)) for table in stock_rows)
    lines = ["# fl26world 1", f"world {WORLD}",
             next(line for line in source_lines if line.startswith("game fl27 "))]
    fixed = []
    if dynamic:
        configured = {}
        for rid, _, _, members in B.game_leagues(str(assets / DB)):
            country_set = {countries.get(club) for club in members}
            if len(country_set) == 1:
                country = next(iter(country_set))
                line = next((line for line in source_lines if line.startswith(f"league {rid} ")), "")
                if re.search(r"\btier=1\b", line.split(" name=", 1)[0]):
                    configured.setdefault(country, []).append(rid)
        selected = []
        for country, quota in central_qualification.ASSOCIATIONS:
            matches = configured.get(country, [])
            if len(matches) > 1:
                raise ValueError(f"Ambiguous configured top division for {country}: {matches}")
            if matches:
                selected.append((matches[0], country, quota))
    else:
        selected = ASSOCIATIONS
    for rid, country, quota in selected:
        cid, name, members = leagues[rid]
        assert len(members) == len(set(members)) and all(countries[c] == country for c in members)
        assert min(lbplayers.squad_counts(str(assets / DB), members).values()) >= 18
        original = next(row for row in mega[0] if M.comp_cid(row) == cid)
        M.add_league(comp, reg, entry, cid, rid, original[M.REGION_OFF], name,
                     f"FL_CA_D{rid}", members, quiet=True, tier=1)
        comp[-M.COMP:] = original
        line = next(s for s in source_lines if s.startswith(f"league {rid} "))
        # Playable, ordinary top divisions keep the validation schedule small.
        header, name_field = line.split(" name=", 1)
        fields = [word for word in header.split() if word.split("=")[0] not in
                  {"cup", "scup", "cupall", "cuptop", "cuplow", "cupn", "legs"}]
        if dynamic:
            fields.append("legs=2")
        lines.append(" ".join(fields) + " name=" + name_field)
        calendar = dynamic and country == 128
        if calendar:
            region = next(word.partition("=")[2] for word in fields if word.startswith("region="))
            lines.append(f"season {region} 1")
        lines.append(realcal.line(rid, realcal.calendar_of(nations[country], 1, 6, calendar=calendar)))
        if not dynamic:
            fixed.append(members[:quota])
    clubs = []
    if not dynamic:
        # Phase 1 compatibility for rebuilding the original validation package.
        pots = [fixed[0], fixed[1], [*fixed[2], fixed[3][0]],
                [*fixed[3][1:], *fixed[4][:2]], [fixed[4][2], *fixed[5], *fixed[6]]]
        clubs = [pot[(g + p) % 4] for g in range(4) for p, pot in enumerate(pots)]
        assert len(set(clubs)) == 20
        for g in range(4):
            associations = [countries[club] for club in clubs[g * 5:g * 5 + 5]]
            assert max(map(associations.count, associations)) <= 2

    sources = central_qualification.contract(lines) if dynamic else []
    cids = {M.comp_cid(row) for row in K.rows(comp, M.COMP)}
    cid, helper_cid = [c for c in range(768, 1024) if c not in cids][:2]
    regs = {K.rid(row): row for row in K.rows(reg, M.REG)}
    free = [r for r in range(700, 1024) if all(r + i * 1024 not in regs for i in range(5))]
    group, ko, helper = free[:3]
    M.write_tables(str(dest), comp, reg, entry)
    generate_tables(dest / DB, dest, cid, helper_cid, group, ko, helper, clubs)
    for source in stock.glob("*.bin"):
        if source.name not in dict(FILE_SIZES):
            candidate = assets / DB / source.name
            shutil.copy2(candidate if candidate.is_file() else source, dest / DB / source.name)
    vector = [group, ko, helper, *(word for source in sources for word in source)] if dynamic else [
        group, ko, helper, *clubs, *(r for r, _, _ in ASSOCIATIONS)]
    lines.append(f"central_probe {2 if dynamic else 1} data=" + ",".join(map(str, vector)))
    audit = dict(competition=cid, play_in_competition=helper_cid, group=group, knockout=ko,
                helper=helper, groups=[clubs[i:i + 5] for i in range(0, len(clubs), 5)],
                **({"annual_sources": sources} if dynamic else {}))
    if champions_plan is not None:
        extra, champions = add_champions_cup(dest, champions_plan, ko)
        included = {rid for rid, _, _ in selected}
        domestic = {int(source.get("membership_reg", key))
                    for key, source in champions_plan["sources"].items() if source["kind"] == "league"}
        # Additional domestic leagues supplied with the input database still
        # need their registration and calendars in the isolated world.
        regions = set()
        for line in source_lines:
            match = re.match(r"^(league|rcal) (\d+)\b", line)
            if match and int(match[2]) in domestic - included:
                lines.append(line)
                region = re.search(r"\bregion=(\d+)\b", line.split(" name=", 1)[0])
                if region:
                    regions.add(int(region[1]))
        for line in source_lines:
            match = re.match(r"^season (\d+)\b", line)
            if match and int(match[1]) in regions and line not in lines:
                lines.append(line)
        lines.extend(extra)
        audit["champions_cup"] = champions
    (dest / "fl26world.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit


def add_champions_cup(dest, plan, central_ko):
    """Extend a new Phase 2 world using the existing CONCACAF generators."""
    import caribbean
    import mkconcacaf

    db = dest / DB
    comp, regs, _ = rows(db)
    used_cids = {M.comp_cid(row) for row in comp}
    regrows = {K.rid(row): row for row in regs}
    used_regs = regrows.keys()
    mapping = {"module:central_american_cup": central_ko}
    mkconcacaf.supported(plan, central=True)
    if not plan["modules"]["central_american_cup"]:
        raise ValueError("a combined Phase 2B plan must enable the Central American Cup")
    missing = {int(source.get("membership_reg", key)) for key, source in plan["sources"].items()
               if source["kind"] == "league"} - used_regs
    if missing:
        raise ValueError(f"Champions Cup plan needs league regulations in the input world: {sorted(missing)}")
    car = plan["modules"]["caribbean_cup"]
    cids = [c for c in range(768, 1024) if c not in used_cids][:2 + car]
    free = [r for r in range(700, 1024) if all(r + i * 1024 not in used_regs for i in range(12))]
    if len(cids) != 2 + car or len(free) < 2 + 2 * car:
        raise ValueError("insufficient free competition or regulation IDs for the combined world")
    ko, pre = free[:2]
    totals = B.game_season_totals(regrows)
    sums = []
    for key, source in plan["sources"].items():
        if source["kind"] == "league" and "membership_reg" in source:
            total = int(key)
            parts = totals.get(total)
            if not parts or parts[0] != int(source["membership_reg"]):
                raise ValueError(f"Champions Cup plan has no matching whole-season source for {total}")
            sums.append((total, *parts))
    lines = B.seasonsum_lines({"season_sums": sums})
    if car:
        group, knockout = free[2:4]
        lines.extend(caribbean.generate(str(db), str(dest), plan, cids[2], group, knockout, print))
        mapping[caribbean.MODULE] = knockout
    lines.extend(mkconcacaf.generate(str(db), str(dest), plan, cids[0], ko, cids[1], pre,
                                     cup_regs=mapping))
    return lines, {"competition": cids[0], "knockout": ko, "round_one": pre,
                   "caribbean_knockout": mapping.get(caribbean.MODULE)}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def junction(link, target):
    assert target.is_dir()
    # mklink is used only to create new junctions under the dedicated install.
    subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(link), str(target)], check=True)
    assert link.lstat().st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    assert link.resolve() == target.resolve()


def prepare(args):
    B.W.set_cid_wide(True)
    root = args.output.resolve()
    world_arg = args.leagues_world or args.phase2b_world or args.phase2_world
    dynamic = world_arg is not None
    profile_id = ((args.leagues_profile or LEAGUES_STEAM_ID) if args.leagues_world else PHASE2B_STEAM_ID if args.phase2b_world
                  else PHASE2_STEAM_ID if dynamic else STEAM_ID)
    overlay_name = "_FL26LeaguesProbe" if args.leagues_world else WORLD
    runtime = args.runtime.resolve() if dynamic else root
    if dynamic and root.exists():
        raise SystemExit("Use a new isolated package directory")
    if dynamic:
        world = world_arg.resolve()
        audit = json.loads((world / "edition.json").read_text(encoding="utf-8"))
        if args.leagues_world:
            contract = (world / "fl26world.txt").read_text(encoding="utf-8").splitlines()
            if (audit.get("year") != 2026 or len(audit.get("masters", [])) != 6
                    or f"world {overlay_name}" not in contract
                    or sum(line.startswith("leagues_probe 1 data=") for line in contract) != 1):
                raise SystemExit("World edition does not match the Leagues Cup mechanics prototype")
            audit["leagues_phase_one"] = True
        elif not audit.get("annual_sources") or audit.get("groups") or (
                bool(audit.get("champions_cup")) != bool(args.phase2b_world)):
            raise SystemExit("World edition does not match the requested Phase 2 profile")
    clone = root / "FL27-offline"
    clone.mkdir(parents=True)
    src = args.seed.resolve()
    assets = (src / "SiderAddons/livecpk/MegapackAssets").resolve(strict=True)
    for name in ("Data", "download"):
        junction(clone / name, (src / name).resolve(strict=True))
    for name in ("FL_2027.exe", "amd_ags_x64.dll", "AnselSDK64.dll", "sdkencryptedappticket64.dll",
                 "steamclient64.dll", "steam_api64.dll", "version.ini", "xinput1_3.dll"):
        shutil.copy2(src / name, clone / name)
    sys_ini, count = re.subn(r"(?m)^SteamID=\d+$", f"SteamID={profile_id}",
                             (src / "sys.ini").read_text())
    assert count == 1
    (clone / "sys.ini").write_text(sys_ini, encoding="ascii")
    for name in ("save-resolver.exe", "save-resolver-native.exe"):
        shutil.copy2((src if dynamic else root) / name, clone / name)
    sider = clone / "SiderAddons"
    sider.mkdir()
    src_sider = src / "SiderAddons"
    for name in ("sider.exe", "sider.dll", "click.wav"):
        shutil.copy2(src_sider / name, sider / name)
    modules = sider / "modules"
    shutil.copytree(src_sider / "modules", modules, ignore=shutil.ignore_patterns(
        "*.log", "*.bin", "fl26match.stats", "fl26world.txt", "fl26swiss.dll",
        "fl26join.dll", "fl26swiss.lua"))
    for name in ("fl26swiss.dll", "fl26join.dll"):
        shutil.copy2(runtime / name, modules / name)
    repo = Path(__file__).resolve().parents[1]
    shutil.copy2(repo / "sider/experimental/fl26swiss.lua", modules / "fl26swiss.lua")
    if args.leagues_world:
        shutil.copy2(repo / "sider/fl26joindll.lua", modules / "fl26joindll.lua")
    dest = sider / "livecpk" / overlay_name
    if dynamic:
        shutil.copytree(world / "common", dest / "common")
        shutil.copy2(world / "fl26world.txt", dest / "fl26world.txt")
    else:
        audit = build_world(args.stock.resolve(), assets, args.metadata.resolve(), dest)
    shutil.copy2(dest / "fl26world.txt", modules / "fl26world.txt")
    junction(dest.parent / "MegapackAssets", assets)
    ini = [line for line in (src_sider / "sider.ini").read_text().splitlines()
           if not line.lstrip().startswith("cpk.root")]
    ini[1:1] = [f'cpk.root = ".\\livecpk\\{overlay_name}"', 'cpk.root = ".\\livecpk\\MegapackAssets"']
    (sider / "sider.ini").write_text("\n".join(ini) + "\n", encoding="utf-8")
    profile = root / "profile-seed"
    profile.mkdir()
    for name in ("SYSTEM00000000", "GRAPHICS000000"):
        if (args.settings / name).is_file():
            shutil.copy2(args.settings / name, profile / name)
    assert (profile / "SYSTEM00000000").is_file()
    audit["save_profile"] = profile_id
    audit["shared_assets"] = {str(p.relative_to(root)): str(p.resolve()) for p in
                              (clone / "Data", clone / "download", dest.parent / "MegapackAssets")}
    (root / "edition.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    files = [p for p in clone.iterdir() if p.is_file()]
    files += [p for p in sider.iterdir() if p.is_file()]
    files += [p for p in modules.rglob("*") if p.is_file()]
    files += [p for p in dest.rglob("*") if p.is_file()]
    files += [*profile.iterdir(), root / "edition.json"]
    (root / "checksums.json").write_text(json.dumps({str(p.relative_to(root)): digest(p)
                                                    for p in sorted(files)}, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    for key in ("seed", "settings", "assets", "stock", "metadata", "runtime"):
        parser.add_argument(f"--{key}", type=Path)
    world = parser.add_mutually_exclusive_group()
    world.add_argument("--phase2-world", type=Path)
    world.add_argument("--phase2b-world", type=Path)
    world.add_argument("--leagues-world", type=Path)
    parser.add_argument("--leagues-profile", type=int, choices=(20271136, 20271137))
    parser.add_argument("--dynamic", action="store_true", help="build only an offline Phase 2 world")
    parser.add_argument("--champions-plan", type=Path, help="add Champions Cup using a planned recipe JSON")
    args = parser.parse_args()
    if args.leagues_profile and not args.leagues_world:
        parser.error("--leagues-profile requires --leagues-world")
    if args.dynamic:
        if args.phase2_world or args.phase2b_world or args.leagues_world:
            parser.error("existing Phase 2 worlds are package inputs, not --dynamic inputs")
        if not all((args.assets, args.stock, args.metadata)) or args.output.exists():
            parser.error("--dynamic requires --assets, --stock, --metadata and a new --output directory")
        B.W.set_cid_wide(True)
        plan = json.loads(args.champions_plan.read_text(encoding="utf-8")) if args.champions_plan else None
        audit = build_world(args.stock, args.assets, args.metadata, args.output, dynamic=True,
                            champions_plan=plan)
        (args.output / "edition.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        print(json.dumps(audit, indent=2))
    else:
        if args.champions_plan:
            parser.error("--champions-plan requires --dynamic")
        if not all((args.seed, args.settings, *((args.runtime,) if args.phase2_world or args.phase2b_world or args.leagues_world else
                                                 (args.stock, args.metadata)))):
            parser.error("packages require --seed and --settings, plus --runtime with a Phase 2 world or --stock and --metadata")
        prepare(args)
