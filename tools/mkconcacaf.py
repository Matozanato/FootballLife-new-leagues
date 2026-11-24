"""Dedicated 27-team Champions Cup tables and version-1 runtime contract.

The primary competition has only its sixteen-team knockout. A technical helper
owns Round One's master and eleven two-leg replicas; no second Champions Cup.
"""
import copy
import contextlib
import io
import os
import struct

import concacaf as Q
import mkleague as M
import mkeuropo

ABI = 1
HELPER_CODE, HELPER_NAME = "FL_CCC_R1", "CONCACAF Round One"
FILL = 1  # January 2, after the January career's day-zero initialization
PRE_DAYS = (33, 40)
KO_DAYS = (61, 68, 89, 96, 117, 124, 145)


def supported(pl, *, central=False, leagues=False):
    if (pl.get("format") != Q.FORMAT or pl.get("version") not in (1, 2, 3)
            or not isinstance(pl.get("modules"),dict) or set(pl["modules"]) != set(Q.MODULES)
            or any(type(v) is not bool for v in pl["modules"].values())):
        raise Q.QualificationError("CONCACAF needs a current 27-place plan; re-plan this recipe and start a new career")
    ready = {"caribbean_cup"}
    if central:
        ready.add("central_american_cup")
    if leagues:
        ready.add("leagues_cup")
    enabled = [k for k, v in pl["modules"].items() if v and k not in ready]
    if enabled:
        raise Q.QualificationError("CONCACAF feeder result providers are not implemented: " + ", ".join(enabled)
                                   + "; disable these modules for this milestone")


def vector(pl, ko, pre, cup_regs=None):
    """Encode sources, never fixed teams. Bounds match fl26concacaf.h."""
    supported(pl, central="module:central_american_cup" in (cup_regs or {}),
              leagues="module:leagues_cup" in (cup_regs or {}))
    sources = pl["sources"]
    keys = sorted(sources)
    if not 1 <= len(keys) <= 64:
        raise Q.QualificationError("CONCACAF supports 1..64 domestic sources")
    if not 176 <= ko <= 1023 or not 176 <= pre <= 1023 or ko == pre:
        raise Q.QualificationError("CONCACAF needs distinct free primary/helper regulations in 176..1023")
    index, records, by_reg, parents = {}, [], {}, {}
    for key in keys:
        s = sources[key]
        reg = (cup_regs or {}).get(key, s.get("runtime_reg", key))
        try:
            reg = int(reg)
        except (ValueError, TypeError) as e:
            raise Q.QualificationError("CONCACAF cup source %s has no generated domestic cup regulation" % key) from e
        capacity = s.get("capacity", 0)
        if s["kind"] == "regional" and key=="module:caribbean_cup":
            kind, capacity = 2, 4
        elif s["kind"] == "regional" and key=="module:central_american_cup":
            kind, capacity = 3, 6
        elif s["kind"] == "regional" and key=="module:leagues_cup":
            kind, capacity = 4, 3
        else:
            kind = {"league": 0, "cup": 1}.get(s["kind"])
        if kind is None or not 1 <= reg <= 1023 or reg in (ko,pre) or not 0 <= capacity <= 40:
            raise Q.QualificationError("CONCACAF source %s exceeds runtime limits" % key)
        record = [reg, kind, Q.REGIONS.index(s["region"]), capacity]
        if reg in by_reg:
            if records[by_reg[reg]] != record:
                raise Q.QualificationError("CONCACAF source aliases disagree about regulation %d" % reg)
            index[key] = by_reg[reg]
        else:
            index[key] = by_reg[reg] = len(records)
            records.append(record)
        if kind == 1 and pl["version"] == 3:
            parents[index[key]] = key.removeprefix("cup:")
    data = [pl["version"], ko, pre, FILL, *PRE_DAYS, len(records)]
    for i, record in enumerate(records):
        data += record
        if pl["version"] == 3:
            parent = parents.get(i)
            if parent and parent not in index:
                raise Q.QualificationError("Domestic cup needs its associated league source")
            data.append(index[parent] + 1 if parent else 0)
    for p in pl["places"]:
        preferred, fallback = p["preferred"], p["fallback"]
        if len(preferred) > 8:
            raise Q.QualificationError("CONCACAF supports at most eight preferred sources per place")
        local = sum(sources[k]["region"] == Q.PATH_REGION[p["path"]] for k in fallback)
        data += [int(p["stage"] == "round_of_16"), len(preferred), len(fallback), local]
        for ref in preferred:
            data += [index[ref["source"]], ref["rank"]]
        data += [index[k] for k in fallback]
    if (len(pl["places"]) != 27 or sum(p["stage"]=="round_of_16" for p in pl["places"]) != 5
            or any(type(x) is not int or not 0 <= x <= 65535 for x in data)):
        raise Q.QualificationError("invalid CONCACAF runtime contract")
    return data


def generate(base, out, pl, cid, ko, helper_cid, pre, name=Q.NAME, cup_regs=None, log=print):
    data = vector(pl, ko, pre, cup_regs)
    comp, regs, ents = (M.load(base, n) for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    cr = [bytearray(comp[i:i+M.COMP]) for i in range(0,len(comp),M.COMP)]
    rr = [bytearray(regs[i:i+M.REG]) for i in range(0,len(regs),M.REG)]
    if cid == helper_cid or any(M.comp_cid(c) in (cid, helper_cid) for c in cr):
        raise Q.QualificationError("CONCACAF competition ids are already in use")
    used = {int.from_bytes(r[2:4],"little") for r in rr}
    if used & ({ko} | {pre+1024*i for i in range(12)}):
        raise Q.QualificationError("CONCACAF regulation ids are already in use")
    template = next(r for r in rr if int.from_bytes(r[2:4],"little") == 6)
    rules = int.from_bytes(template[16:20],"little")
    # UEFA's established mode 1: two legs except a one-match final.
    if template[M.R_TYPE] != 3 or ((rules >> 9) & 7) != 1 or rules & (1 << 29):
        raise Q.QualificationError("unsupported Europa knockout template: expected two legs with single final")
    c = bytearray(next(c for c in cr if M.comp_cid(c) == 5))
    M.set_comp_cid(c, cid)
    c[M.REGION_OFF] = M.enc_region(1)
    c[M.FLAG_OFF] = (c[M.FLAG_OFF] & ~7) | 6
    M.put(c,M.CODE_OFF,Q.CODE,M.COMP-M.CODE_OFF)
    r = bytearray(template)
    r[M.R_BELOW:M.R_BELOW+2] = bytes(2)
    r[2:4] = ko.to_bytes(2,"little")
    M.set_reg_cid(r, cid)
    r[M.R_TEAMS] = (r[M.R_TEAMS] & ~63) | 16
    # No bronze match. Other scoring rules retain the established template.
    rules &= ~(1 << 28)
    r[16:20] = rules.to_bytes(4,"little")
    M.put_names(r,0,name)
    # Static database membership is an isolated first-season preview of all 27.
    preview = copy.deepcopy(pl)
    cid_of = {int.from_bytes(x[2:4],"little"):M.reg_cid(x) for x in rr}
    for key,s in preview["sources"].items():
        if s["kind"] != "league": continue
        source_cid = cid_of[int(s.get("membership_reg", key))]
        s["teams"] = [int.from_bytes(e[:4],"little") for e in sorted(
            (ents[i:i+M.ENT] for i in range(0,len(ents),M.ENT) if M.ent_cid(ents, i) == source_cid),
            key=lambda e:e[M.E_ORDER])]
        s["capacity"] = len(s["teams"])
    # An explicit world waits for its first real draw. No placeholders from
    # unconfigured domestic sources are written to CompetitionEntry.
    field = Q.resolve(preview,first_season=True) if pl["version"] == 1 else []
    eid = max((int.from_bytes(ents[i+4:i+8],"little") for i in range(0,len(ents),M.ENT)),default=0)
    extra = bytearray()
    for i,e in enumerate(field):
        row = bytearray(M.ENT); row[:4] = e["club"].to_bytes(4,"little")
        row[4:8] = (eid+i+1).to_bytes(4,"little"); M.set_ent_cid(row, cid); row[M.E_ORDER]=i+1
        extra += row
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(out,comp+c,regs+r,ents+extra)
    db = os.path.join(out,"common","etc","pesdb")
    mkeuropo.prerounds_single(db,out,helper_cid,HELPER_CODE,HELPER_NAME,[(pre,11)],
                             one_match=False,region=1,confederation=0,log=log)
    regulation_file = "CompetitionRegulation.bin"
    updated = concacaf_match_rules(M.load(db, regulation_file), ko, pre)
    with open(os.path.join(db, regulation_file), "wb") as f:
        f.write(M.pesdb.wesys_pack(updated))
    log("  CONCACAF: competition %d, knockout %d; technical Round One %d/%d, 11 two-leg ties; 27 places, contract v%d" %
        (cid,ko,helper_cid,pre,pl["version"]))
    league = next(int(k) for k,s in sorted(pl["sources"].items()) if s["kind"] == "league")
    # Generic registry supplies dates, knockout rounds, championship retention and teardown.
    # Its fill is explicitly intercepted by the dedicated runtime contract.
    ccup = "ccup %d ko=%d groups=0 comp=13 fill=%d days=%s entry=%s name=%s" % (
        ko,ko,FILL,",".join(map(str,KO_DAYS)),",".join("%d:%d"%(league,i+1) for i in range(16)),name)
    lpre = "lpre %d cup=%d fill=%d days=%s entry=%s" % (
        pre,ko,FILL,",".join(map(str,PRE_DAYS)),",".join("%d:%d"%(league,i+1) for i in range(22)))
    return [ccup,lpre,f"concacaf {pl['version']} data="+",".join(map(str,data))]


def concacaf_match_rules(regulations, ko, pre):
    """Set the native away-goals and extra-time options on CONCACAF rows only."""
    selected = {ko} | {pre + 1024 * tie for tie in range(12)}
    found = set()
    regs = bytearray(regulations)
    for i in range(0, len(regs), M.REG):
        reg = int.from_bytes(regs[i + 2:i + 4], "little")
        if reg in selected:
            found.add(reg)
            rules = int.from_bytes(regs[i + 16:i + 20], "little")
            regs[i + 16:i + 20] = (rules | (1 << 24) | (1 << 25)).to_bytes(4, "little")
    if found != selected:
        raise Q.QualificationError("CONCACAF match rules require the knockout and all Round One regulations")
    return bytes(regs)


def _pe_exports(dll):
    with open(dll,"rb") as f: raw=f.read()
    pe=struct.unpack_from("<I",raw,0x3c)[0]
    if raw[:2]!=b"MZ" or raw[pe:pe+4]!=b"PE\0\0" or struct.unpack_from("<H",raw,pe+24)[0]!=0x20b:
        raise Q.QualificationError("CONCACAF requires a 64-bit Windows DLL")
    ns, size = struct.unpack_from("<H",raw,pe+6)[0],struct.unpack_from("<H",raw,pe+20)[0]
    sections=[struct.unpack_from("<IIII",raw,pe+24+size+40*i+8) for i in range(ns)]
    def offset(rva):
        for vs,va,rs,ptr in sections:
            if va<=rva<va+rs: return ptr+rva-va
        raise Q.QualificationError("CONCACAF DLL has an invalid export address")
    directory=offset(struct.unpack_from("<I",raw,pe+24+112)[0])
    nf,nn,fa,na,oa=struct.unpack_from("<IIIII",raw,directory+20)
    exports={}
    for i in range(nn):
        start=offset(struct.unpack_from("<I",raw,offset(na)+4*i)[0])
        name=raw[start:raw.index(b"\0",start)].decode("ascii")
        ordinal=struct.unpack_from("<H",raw,offset(oa)+2*i)[0]
        if ordinal>=nf: raise Q.QualificationError("invalid DLL export ordinal")
        exports[name]=struct.unpack_from("<I",raw,offset(fa)+4*ordinal)[0]
    return exports, raw, offset


def check_runtime(dll, lua, caribbean=False, leagues=False, caribbean_access=False,
                  central_access=False, champions_access=False):
    """Inspect PE exports without running the modules."""
    exports, raw, offset = _pe_exports(dll)
    required = {
        "fl26_swiss_concacaf", "fl26_swiss_concacaf_version", "fl26_swiss_concacaf_abi",
        "fl26_swiss_seasonsum", "fl26_swiss_ccup_zone", "fl26_swiss_gsplits",
    }
    if caribbean or caribbean_access:
        required.add("fl26_swiss_ccup_caribbean")
    if leagues:
        required.add("fl26_swiss_leagues_probe")
    if central_access:
        required.add("fl26_swiss_central_probe")
    if not required<=exports.keys() or struct.unpack_from("<I",raw,offset(exports.get("fl26_swiss_concacaf_abi",0)))[0]!=ABI:
        raise Q.QualificationError("CONCACAF needs the 0.4.0 fl26swiss.dll with contract v1; rebuild/repackage the native module")
    with open(lua,encoding="utf-8") as f: text=f.read()
    if any('"%s"' % symbol not in text for symbol in required - {"fl26_swiss_concacaf_abi"}):
        raise Q.QualificationError("CONCACAF needs the matching fl26swiss.lua contract loader")
    if (caribbean_access or central_access or champions_access) and (
            "fl26_swiss_regional_places_abi" not in exports
            or struct.unpack_from("<I", raw, offset(exports["fl26_swiss_regional_places_abi"]))[0] != 1):
        raise Q.QualificationError("CONCACAF needs the native individual qualification places ABI")
    if caribbean_access and ("fl26_swiss_regional_places_abi" not in exports or "caribbean[1] == 3" not in text):
        raise Q.QualificationError("Caribbean Cup needs the matching explicit-access runtime")
    if central_access and ("fl26_swiss_regional_places_abi" not in exports or "central_probe[1] == 4" not in text):
        raise Q.QualificationError("Central American Cup needs the matching explicit-access runtime")
    if champions_access and ("fl26_swiss_regional_places_abi" not in exports or "cq[1] == 3" not in text):
        raise Q.QualificationError("Champions Cup needs the matching explicit-access runtime")
    if leagues:
        join, _, _ = _pe_exports(os.path.join(os.path.dirname(dll), "fl26join.dll"))
        if ("fl26_swiss_leagues_ids_abi" not in exports or
                not {"fl26_join_close_leagues_edition_ids", "fl26_join_rollback_leagues_stage_ids"} <= join.keys()):
            raise Q.QualificationError("Leagues Cup needs the matching allocated-ID runtime")
    return exports
