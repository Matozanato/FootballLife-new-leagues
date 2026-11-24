"""Domestic access and table generation for the Caribbean Cup."""
import concacaf as Q
import mkccup as K
import mkleague as M

CODE = "FL_CARIBBEAN_CUP"
NAME = "CONCACAF Caribbean Cup"
MODULE = "module:caribbean_cup"
QUOTAS = {"jamaica": 2, "dominican republic": 2, "trinidad and tobago": 2,
          "haiti": 1, "suriname": 1}
FILL = 208
GROUP_DAYS = (216, 230, 244, 251, 258)
KNOCKOUT_DAYS = (286, 293, 334, 338)


def association(name):
    name = name.strip().casefold().replace("&", "and")
    return "haiti" if name == "haïti" else name


def sources(plan):
    """One top-flight ranking per association, in the published quota order."""
    if plan["configuration"].get("version") in (2, 3):
        grouped = Q.group_regional_places(plan["access"]["sources"])
        return [(key, plan["sources"][key], ranks) for key, ranks in grouped.items()]
    selected = []
    extra = [association(c) for c in plan["configuration"].get("caribbean_associations", ())]
    if len(set(extra))!=len(extra) or set(extra)&QUOTAS.keys():
        raise Q.QualificationError("Caribbean redistribution associations must be distinct additional countries")
    for country, quota in (*QUOTAS.items(), *((country, 0) for country in extra)):
        leagues = [(key, source) for key, source in plan["sources"].items()
                   if source["kind"] == "league" and source["region"] == "caribbean"
                   and association(source.get("country", "")) == country]
        if len(leagues) > 1:
            raise Q.QualificationError(f"Caribbean Cup has ambiguous top divisions for {country}")
        if leagues:
            key, source = leagues[0]
            selected.append((key, source, quota))
        elif not quota:
            raise Q.QualificationError(f"Caribbean redistribution association {country} has no eligible domestic league")
    eligible = {club for key, source, _ in selected for club in
                source.get("teams", [(key, n) for n in range(source["capacity"])])}
    if len(eligible) < 10:
        raise Q.QualificationError(f"Caribbean Cup needs 10 unique Caribbean clubs; available capacity is {len(eligible)}")
    return selected


def select(pools):
    """Fill quotas, then give one extra place per association per pass."""
    field, used = [], set()
    counts = [0] * len(pools)

    def take(i):
        club = next((club for club in pools[i][0] if club not in used), None)
        if club is None:
            return False
        used.add(club)
        field.append(club)
        counts[i] += 1
        return True

    for i, (_, quota) in enumerate(pools):
        for _ in range(quota):
            if not take(i):
                break
    while len(field) < 10:
        any_added = False
        for i in sorted(range(len(pools)), key=counts.__getitem__):
            any_added |= take(i)
            if len(field) == 10:
                return field
        if not any_added:
            raise Q.QualificationError("Caribbean Cup cannot fill ten unique places")
    return field


def generate(db, root, plan, cid, group, knockout, log, name=NAME, cup_regs=None):
    cr, rr, er = [K.rows(M.load(db, name), size) for name, size in
                  (("Competition.bin", M.COMP), ("CompetitionRegulation.bin", M.REG),
                   ("CompetitionEntry.bin", M.ENT))]
    regs = {K.rid(row): row for row in rr}
    if {group, group + 1024, group + 2048, knockout} & regs.keys():
        raise Q.QualificationError("Caribbean Cup regulation family collides with the world")
    if cid in {M.comp_cid(row) for row in cr}:
        raise Q.QualificationError("Caribbean Cup competition ID collides with the world")
    domestic = sources(plan)
    titles = plan["configuration"].get("caribbean_titles", {})
    if set(titles) - {association(source["country"]) for _, source, _ in domestic}:
        raise Q.QualificationError("Caribbean domestic title route has no matching top division")
    for title in titles.values():
        if title not in regs or regs[title][M.R_TYPE] != 3:
            raise Q.QualificationError(f"Caribbean title source {title} is not a domestic knockout")
    explicit = plan["configuration"].get("version") in (2, 3)
    pools, tables, selected_cups = [], {}, {}
    for key, source, quota in domestic:
        membership = regs[int(source.get("membership_reg", key))]
        home = M.reg_cid(membership)
        teams = [int.from_bytes(row[:4], "little") for row in
                 sorted((r for r in er if M.ent_cid(r) == home), key=lambda r: r[M.E_ORDER])]
        if explicit:
            tables[key] = teams
            selected_cups[key] = Q.regional_cup_reg(key, quota, plan["sources"], cup_regs or {}, regs)
        else:
            pools.append((teams, quota))
        country = association(source["country"])
        route = f"domestic title regulation {titles[country]}" if country in titles else (
            "standings proxy" if country in ("haiti", "dominican republic") else "domestic league ranking")
        log(f"  Caribbean Cup: {source['country']} regulation {key}, {route} ({quota} base places)")
    clubs = Q.initial_regional_field({key: ranks for key, _source, ranks in domestic}, tables) if explicit else select(pools)
    if len(set(clubs)) != 10:
        raise Q.QualificationError("Caribbean Cup inaugural league access cannot supply ten distinct clubs")
    comp = bytearray(next(row for row in cr if M.comp_cid(row) == 5))
    M.set_comp_cid(comp, cid)
    M.put(comp, M.CODE_OFF, CODE, M.COMP - M.CODE_OFF)
    comp[M.REGION_OFF] = M.enc_region(1)
    comp[M.FLAG_OFF] = (comp[M.FLAG_OFF] & ~7) | 6
    cr.append(comp)
    for original, reg, n in ((9, group, 10), (1033, group + 1024, 5),
                             (2057, group + 2048, 5), (6, knockout, 4)):
        row = bytearray(regs[original])
        row[:2] = bytes(2)
        row[2:4] = reg.to_bytes(2, "little")
        M.set_reg_cid(row, cid)
        row[M.R_TEAMS] = (row[M.R_TEAMS] & ~63) | n
        rules = int.from_bytes(row[16:20], "little") & ~(7 << 9)
        if reg == knockout:
            rules = (rules & ~(1 << 29)) | (2 << 9) | (1 << 28) | (3 << 24)
        elif reg == group:
            row[K.R_GROUPS] = (row[K.R_GROUPS] & ~31) | 2
        else:
            row[6:8] = group.to_bytes(2, "little")
        row[16:20] = rules.to_bytes(4, "little")
        M.put_names(row, 0, name)
        rr.append(row)
    eid = max(int.from_bytes(r[M.E_EID:M.E_EID + 4], "little") for r in er)
    for i, club in enumerate(clubs, 1):
        row = bytearray(M.ENT)
        row[:4] = club.to_bytes(4, "little")
        row[4:8] = (eid + i).to_bytes(4, "little")
        M.set_ent_cid(row, cid)
        row[M.E_ORDER] = i
        er.append(row)
    M.write_tables(root, b"".join(cr), b"".join(rr), b"".join(er))
    version = 3 if explicit else 1
    words = [version, group, knockout, len(domestic)]
    for key, source, quota in domestic:
        words.extend((int(key), int(source.get("membership_reg", key)), 0 if explicit else quota,
                      selected_cups[key] if explicit else titles.get(association(source["country"]), 0)))
    if explicit:
        words.extend(index * 64 + rank for index, (_key, _source, ranks) in enumerate(domestic) for rank in ranks)
        # Generic registry entry count describes the UI shape; the explicit
        # contract supplies participants and bypasses the generic fill.
        entries = ",".join(f"{key}:{rank or 1}" for key, _, ranks in domestic for rank in ranks)
    else:
        entries = ",".join(f"{domestic[0][0]}:{i}" for i in range(1, 11))
    return [f"ccup {group} ko={knockout} groups=2 comp=13 fill={FILL} entry={entries} name={name}",
            f"caribbean {version} data=" + ",".join(map(str, words))]
