"""Build a separate FL26 world with Brazilian state competitions from a JSON recipe."""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import fl26world
import mkleague as m
import mkeuropo

TOOLS = Path(__file__).resolve().parent
DB = Path("common/etc/pesdb")
TABLES = ("Competition.bin","CompetitionRegulation.bin","CompetitionEntry.bin")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def run(tool, *args):
    subprocess.run([sys.executable,"-B",str(TOOLS/tool),*map(str,args)],check=True)


def load_tables(db):
    return [m.load(db,name) for name in TABLES]


def add_state(world, state, days, revision=5):
    db = world/DB
    comp, regs, entries = load_tables(db)
    a,b,playoff = state["cids"]
    top,lower,semi,final = state["regulations"]
    clubs = state["a1"]+state["a2"]
    name, code = state["name"], state["code"]
    require(re.fullmatch(r"[A-Z0-9_]{1,12}",code) and name.strip() and
            not any(c in name for c in "\r\n|"),"Invalid name/code")
    require(len(state["a1"])==12 and len(state["a2"])==8 and len(set(clubs))==20,"Expected 12 + 8 distinct clubs")
    require(len({a,b,playoff})==3 and all(0<i<255 for i in (a,b,playoff)), "Invalid competition IDs")
    require(len(set(state["regulations"]))==4 and top in fl26world.DEFAULT_SLOT and lower in fl26world.DEFAULT_SLOT
            and 175<semi<1024 and 175<final<1024,"Invalid regulation IDs")
    existing_slots=set(map(int,re.findall(r"^league .*?\bslot=(\d+)",(world/"fl26world.txt").read_text(),re.M)))
    require(not existing_slots.intersection(fl26world.DEFAULT_SLOT[i] for i in (top,lower)), "Select Team slot taken")
    teams = m.load(db,"Team.bin")
    known = {struct.unpack_from("<I",teams,i+8)[0] for i in range(0,len(teams),1532)}
    counts = dict.fromkeys(clubs,0)
    for i in range(0,len(entries),m.ENT):
        t = struct.unpack_from("<I",entries,i+m.E_TEAM)[0]
        if t in counts and entries[i+m.E_CID] in state["national_cids"]:
            counts[t]+=1
    require(set(clubs)<=known and all(v==1 for v in counts.values()), "Check club IDs and national memberships")
    lines=[]
    for tier,cid,rid,legs,field,exchange in [
        (1,a,top,1,state["a1"],"promote=0 demote=2"),
        (2,b,lower,2,state["a2"],f"above={top} promote=2 demote=0")]:
        label=f"{name} A{tier}"
        m.add_league(comp,regs,entries,cid,rid,m.enc_region(16),label,f"BR_{code}_A{tier}",
                     field,proto_code="BRAZIL_D1_LEAGUE",tier=tier)
        pos=len(regs)-m.REG
        struct.pack_into("<H",regs,pos,lower if tier==1 else 0)
        struct.pack_into("<H",regs,pos+4,top if tier==2 else 0)
        rule=struct.unpack_from("<I",regs,pos+16)[0]
        struct.pack_into("<I",regs,pos+16,(rule&~(7<<12)) | (legs<<12))
        p=len(comp)-m.COMP+m.FLAG_OFF
        comp[p]=(comp[p]&~7)|4
        lines.append(f"league {rid} cid={cid} region=16 country=146 conf=4 slot={fl26world.DEFAULT_SLOT[rid]} tier={tier} startyear=1 {exchange} clubs={len(field)} legs={legs} kickoff={99 if tier==1 else 76} name={label}")
    m.write_tables(world,comp,regs,entries)
    semi_label=f"{name} A1 - Semifinais"
    if len(semi_label.encode("utf8"))>24:
        semi_label=f"{code} A1 - Semi"
    mkeuropo.prerounds_single(str(db),str(world),playoff,f"BR_{code}_FINAIS",semi_label,
                              [(semi,2)],one_match=True,region=16,confederation=4)
    scratch=next(i for i in range(254,0,-1) if i not in set(comp[m.CID_OFF::m.COMP])|{playoff})
    winners=f"{semi+1024}:0,{semi+2048}:0"
    run("mkccup.py","--base",db,"--out",world,"--cup",
        f"{name} A1 - Final|BR_{code}_FINAL|{scratch}|{final}|{final}|0|{winners}|4|16|31")
    comp,regs,entries=load_tables(db)
    require(scratch not in entries[m.E_CID::m.ENT] and comp[-m.COMP+m.CID_OFF]==scratch,"Unexpected final entries")
    del comp[-m.COMP:]
    for p in range(0,len(regs),m.REG):
        rid=struct.unpack_from("<H",regs,p+m.R_ID)[0]
        if rid==final:
            regs[p+m.R_CID]=playoff
        if rid==semi:
            m.put_names(regs,p,f"{name} A1 - Fase final")
    m.write_tables(world,comp,regs,entries)
    lines.extend([f"rcal {top} 0 {days[10]} 0 0 68 0",f"rcal {lower} 0 {days[13]} 0 0 68 0",
                  f"lpre {semi} cup={final} fill={days[10]+1} days={days[11]},{days[11]} entry={top}:1,{top}:4,{top}:2,{top}:3 single=1",
                  f"ccup {final} ko={final} groups=0 entry={winners} fill={days[11]+1} national=1 cal=1 days={days[12]},{days[13]} name={name} A1 - Final"])
    if revision == 7:
        # Retain the Brazil category and domestic bracket template created above.
        # Remove the old opening round and its two replicas before publishing.
        remaining = bytearray()
        removed = set()
        for pos in range(0, len(regs), m.REG):
            row = regs[pos:pos+m.REG]
            rid = struct.unpack_from("<H", row, m.R_ID)[0]
            if row[m.R_CID] == playoff and rid in (semi, semi+1024, semi+2048):
                removed.add(rid)
                continue
            if rid == final:
                require(row[m.R_CID] == playoff, "Wrong knockout competition")
                row[m.R_TEAMS] = (row[m.R_TEAMS] & ~63) | 4
                row[17] = (row[17] & ~14) | 4
                m.put_names(row, 0, f"{name} A1 - Fase final")
            remaining.extend(row)
        require(removed == {semi, semi+1024, semi+2048}, "Unexpected pre-round layout")
        m.write_tables(world, comp, remaining, entries)
        lines[-2:] = [f"ccup {final} ko={final} groups=0 entry={top}:1,{top}:4,{top}:2,{top}:3 "
                      f"fill={days[10]+1} national=1 cal=1 days={days[11]},{days[12]},{days[13]} name={name} A1 - Fase final"]
    with (world/"fl26world.txt").open("a",encoding="utf8") as stream:
        stream.write("\n"+"\n".join(lines)+"\n")


def categories(world, ids):
    path=world/"modules/fl26regions.lua"
    pattern=r'local rows = .*?new="([0-9a-f]+)"'
    def rows(lua):
        match=re.search(pattern,lua)
        require(match,"Unsupported fl26regions.lua format")
        return match,dict(struct.iter_unpack("<II",bytes.fromhex(match[1])))
    previous=rows(path.read_text())[1] if path.exists() else {}
    run("mkregioncats.py","--root",world,"--comps",",".join(map(str,sorted(set(previous)|ids))),"--out",path,"--write")
    lua=path.read_text()
    match,current=rows(lua)
    current.update(previous)
    for cid in ids:
        current[cid]=current[21]
    encoded=b"".join(struct.pack("<II",c,g) for c,g in current.items()).hex()
    path.write_text(lua[:match.start(1)]+encoded+lua[match.end(1):],encoding="utf8")


def module(states, calendar, zig, work, dest, revision=5):
    native=TOOLS/"native"
    source=(native/"fl26swiss.c").read_text(encoding="utf8")
    def insert(mark, addition):
        nonlocal source
        require(source.count(mark)==1,f"Unsupported source: {mark}")
        source=source.replace(mark,mark+addition)
    mark="char setcl_handler(uint64_t id, u32vec* list, uint64_t flag)"
    declaration="static int state_final_ok(uint16_t,const uint32_t*,size_t,int);\n"
    source=source.replace(mark,declaration+mark)
    insert(mark+"\n{","\n  if (list && list->b && list->e>list->b && !state_final_ok((uint16_t)id,list->b,list->e-list->b,1)) return 0;")
    def array(items):
        return "{"+",".join(map(str,items))+"}"
    config="static const struct state_ids {unsigned a1,a2,semi,final;} states[]={"+",".join(array(s["regulations"]) for s in states)+"};\n"
    config+="static const struct {int year; unsigned short days[14];} state_calendar[]={"+",".join(array([y,array(d)]) for y,d in calendar.items())+"};\n"
    mark="static void lpre_fill(int i)\n{"
    insert(mark,"\n  state_fill_days();")
    source=source.replace(mark,config+(native/("estadual_r7.inc" if revision == 7 else "estadual.inc")).read_text()+"\n"+mark)
    insert("static void ccup_fill_days(void)\n{","\n  state_fill_days();")
    insert("    int f = season_ord(c->fill), s = season_ord(d);","\n    if (!state_final_ok(c->ko,NULL,0,0)) continue;")
    insert("static int ccup_fill_one(int k, void* started)\n{","\n  if (!state_final_ok(g_ccup[k].ko,NULL,0,0)) return 0;")
    insert("if (vec) nt_sample(reg, vec);","\n  uint64_t result=0; if (vec && state_dates(id,reg,vec,&result)) return result;\n")
    if revision == 7:
        def before(mark, addition):
            nonlocal source
            require(source.count(mark)==1, f"Unsupported source: {mark}")
            source=source.replace(mark, addition+"\n"+mark)
        before("  int r = hook((unsigned char*)(uintptr_t)(exe_base + GEN_RVA)",
               (native/"estadual_r7_install.inc").read_text())
        mark="static int ko_sync(uint16_t reg, const char* why)\n{"
        before(mark,(native/"estadual_r7_seed.inc").read_text())
        insert(mark,'\n  if (!strcmp(why,"filled")) state_seed(reg);')
        before("    if (c->filled_year == year || !ccup_world(c)) continue;",
               "    if (!state_final_ok(c->ko,NULL,0,0)) continue;")
        mark="    ccup_fill_one(k, 0);"
        require(source.count(mark)==1, "Unsupported national cup fill")
        source=source.replace(mark,"    int filled=ccup_fill_one(k, 0);\n"
                              "    if (!filled && state_for(c->ko) && !ccup_matches(c->ko)) c->filled_year=0;")
    c=work/"fl26swiss.c"
    c.write_text(source,encoding="utf8")
    dll=work/"fl26swiss.dll"
    subprocess.run([str(zig),"cc","-shared","-target","x86_64-windows-gnu","-O2","-s","-I",str(native),"-o",str(dll),str(c),"-lkernel32"],check=True)
    shutil.copy2(dll,dest/dll.name)


def build(base, out, recipe, zig):
    base,out=base.resolve(),out.resolve()
    require(not out.exists() and not out.is_relative_to(base),"Output must be new and outside base")
    revision=recipe.get("revision",5)
    require(revision in (5,7),"Unsupported recipe revision")
    states=recipe["states"]
    calendar={int(y):d for y,d in sorted(recipe["calendar"].items())}
    require(states and calendar and all(1900<=y<=2200 and len(d)==14 and
            all(type(n) is int and 0<=n<365 for n in d) and sorted(set(d))==d for y,d in calendar.items()),"Invalid calendar")
    all_clubs=[t for s in states for t in s["a1"]+s["a2"]]
    require(len(all_clubs)==len(set(all_clubs)),"Club assigned to multiple states")
    require(len({s["code"] for s in states})==len(states),"Duplicate state code")
    if revision==7:
        years=list(calendar)
        require(years==list(range(years[0],years[-1]+1)), "State calendar has a missing year")
        regs=[rid for state in states for rid in state["regulations"]]
        require(len(regs)==len(set(regs)), "State regulation IDs overlap")
    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        work=Path(temp)
        world=work/"world"
        shutil.copytree(base,world)
        desc=world/"fl26world.txt"
        content,count=re.subn(r"^world .+$",lambda _:f"world {out.name}",desc.read_text(encoding="utf8"),flags=re.M)
        require(count==1,"Expected one world name")
        desc.write_text(content,encoding="utf8")
        for state in states:
            add_state(world,state,next(iter(calendar.values())),revision)
        for old,new in zip(load_tables(base/DB),load_tables(world/DB)):
            require(new.startswith(old),"An existing database record changed")
        mods=world/"modules"
        mods.mkdir(exist_ok=True)
        categories(world,{cid for s in states for cid in s["cids"]})
        run("mkregnames.py","--root",world,"--out",mods/"fl26regnames.lua")
        run("buildcheck.py",world/DB,"--base",base/DB)
        module(states,calendar,zig,work,mods,revision)
        join_dll=work/"fl26join.dll"
        subprocess.run([str(zig),"cc","-shared","-target","x86_64-windows-gnu","-O2","-s",
                        str(TOOLS/"native/fl26join.c"),"-o",str(join_dll),"-lkernel32"],check=True)
        shutil.copy2(join_dll,mods/join_dll.name)
        shutil.copy2(TOOLS.parent/"sider/fl26joindll.lua",mods/"fl26joindll.lua")
        shutil.copy2(desc,mods/desc.name)
        world.rename(out)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("base","out","recipe","zig"):
        p.add_argument("--"+flag,type=Path,required=True)
    a=p.parse_args()
    build(a.base,a.out,json.loads(a.recipe.read_text(encoding="utf-8-sig")),a.zig.resolve())
