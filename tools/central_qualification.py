"""Build the opt-in Central American Cup annual-source contract."""

ASSOCIATIONS = ((112, 4), (119, 4), (121, 3), (116, 3), (128, 3), (127, 2), (108, 1))
MAX_PHASES = 4
CALENDAR_REGIONS = {16, 18, 19, 21, 23, 24, 28}


def database_phase_shapes(regulations):
    """Read scheduled round-robin shapes from the exported regulation rows."""
    return {rid: (row[0x0B] & 63, (int.from_bytes(row[16:20], "little") >> 12) & 7)
            for rid, row in regulations.items() if row[9] == 4}


def contract(lines, phase_shapes=None, cup_berths=None):
    """Resolve configured top divisions and annual phase links from world metadata.

    Native phases without a league directive need their trusted (clubs, legs)
    provided by the world builder. A cup berth maps a country to its national
    cup regulation explicitly. Ordinary league cup settings grant no berth.
    """
    shapes = dict(phase_shapes or {})
    cups = dict(cup_berths or {})
    countries = {country for country, _ in ASSOCIATIONS}
    if cups.keys() - countries:
        raise ValueError("Central American Cup: cup berth outside Central America")
    tops, seasons, annual, split_totals = {}, {}, {}, set()
    for line in lines:
        fields = line.split(" name=", 1)[0].split()
        if len(fields) < 3 or fields[0] not in {"league", "season", "seasonsum", "split", "gsplit"}:
            continue
        kind, rid = fields[0], int(fields[1])
        attrs = dict(word.split("=", 1) for word in fields[2:] if "=" in word)
        if kind == "league":
            if "clubs" in attrs and "legs" in attrs:
                shapes.setdefault(rid, (int(attrs["clubs"]), int(attrs["legs"])))
            country = int(attrs.get("country", 0))
            if country in countries and attrs.get("tier") == "1" and not any(
                    int(attrs.get(key, 0)) for key in ("above", "exhibition")):
                tops.setdefault(country, []).append((rid, int(attrs.get("region", 0))))
        elif kind == "season":
            seasons[rid] = int(fields[2])
        else:
            if kind == "seasonsum":
                parts = [(int(part), 0) for part in attrs["parts"].split(",")]
            else:
                regular = int(attrs["regular"])
                groups = list(map(int, attrs["groups"].split(",")))
                halves = len(groups) == 1 and attrs.get("carry") == "0"
                if not halves and not 2 <= len(groups) <= 3:
                    raise ValueError(f"Central American Cup: unsupported split phases for {rid}")
                parts = [(regular, 0), *[(part, 0 if halves else i + 1)
                                          for i, part in enumerate(groups)]]
                split_totals.add(rid)
            if rid in annual and annual[rid] != parts:
                raise ValueError(f"Central American Cup: conflicting annual phases for {rid}")
            annual[rid] = parts
    owner = {}
    for total, parts in annual.items():
        for phase, _ in parts:
            if phase in owner and owner[phase] != total:
                raise ValueError(f"Central American Cup: phase {phase} belongs to multiple annual sources")
            owner[phase] = total
    sources = []
    for country, _ in ASSOCIATIONS:
        top_rows = tops.get(country, ())
        configured = sorted({owner.get(rid, rid) for rid, _ in top_rows})
        if not configured:
            if country in cups:
                raise ValueError(f"Central American Cup: cup berth without top division for {country}")
            sources.append([0] * (3 + 4 * MAX_PHASES))
            continue
        if len(configured) != 1:
            raise ValueError(f"Central American Cup: ambiguous top division for {country}: {configured}")
        total = configured[0]
        parts = annual.get(total, [(total, 0)])
        if not 1 <= len(parts) <= MAX_PHASES:
            raise ValueError(f"Central American Cup: unsupported phase count for {total}")
        membership = total if total in split_totals else parts[0][0]
        calendar = {seasons.get(region, int(region in CALENDAR_REGIONS)) for _, region in top_rows}
        if len(calendar) > 1 or calendar - {0, 1}:
            raise ValueError(f"Central American Cup: conflicting annual calendar for {total}")
        cup = cups.get(country, 0)
        if country in cups and not 0 < cup <= 1023:
            raise ValueError(f"Central American Cup: invalid cup regulation for {country}")
        source = [membership, next(iter(calendar), 0), cup]
        for rid, tier in parts:
            clubs, legs = shapes.get(rid, (0, 0))
            if not (0 < rid <= 65535 and 2 <= clubs <= 40 and 1 <= legs <= 7):
                raise ValueError(f"Central American Cup: unknown or invalid schedule for phase {rid}")
            source.extend((rid, clubs, legs, tier))
        source.extend([0] * (4 * (MAX_PHASES - len(parts))))
        sources.append(source)
    if sum(bool(source[0]) for source in sources) < 3:
        raise ValueError("Central American Cup: too few configured associations for 20 places")
    return sources
