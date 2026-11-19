"""Verify the generated R7 tables, memberships and cup descriptors before installing."""
import argparse
import json
import struct
from pathlib import Path

import mkleague as m
from mkestaduais import DB, load_tables, require


def verify(base, world, recipe):
    require(recipe.get("revision")==7, "Expected a revision 7 recipe")
    old=load_tables(base/DB)
    tables=load_tables(world/DB)
    require(all(after.startswith(before) for before,after in zip(old,tables)), "Base records changed")
    comp,regs,entries=tables
    text=(world/"fl26world.txt").read_bytes()
    require(text==(world/"modules/fl26world.txt").read_bytes(), "Descriptor copies differ")
    lines=text.decode("utf8").splitlines()
    for state in recipe["states"]:
        a1,a2,semi,final=state["regulations"]
        first,second,knockout=state["cids"]
        rows=[regs[i:i+m.REG] for i in range(0,len(regs),m.REG) if regs[i+m.R_CID]==knockout]
        require(len(rows)==1, "Expected one knockout regulation")
        row=rows[0]
        require(struct.unpack_from("<H",row,m.R_ID)[0]==final and row[m.R_TEAMS]&63==4
                and (row[17]>>1)&7==2, "Wrong knockout rule")
        expected=f"entry={a1}:1,{a1}:4,{a1}:2,{a1}:3"
        cup=[line.split() for line in lines if line.startswith(f"ccup {final} ")]
        require(len(cup)==1 and {expected,"cal=1","national=1",f"ko={final}"}<=set(cup[0]), "Wrong draw")
        require(not any(line.startswith(f"lpre {semi} ") for line in lines), "Legacy pre-round retained")
        for cid,clubs in [(first,state["a1"]),(second,state["a2"]),(knockout,[])]:
            registered=[struct.unpack_from("<I",entries,i+m.E_TEAM)[0] for i in range(0,len(entries),m.ENT)
                        if entries[i+m.E_CID]==cid]
            require(registered==clubs,f"Unexpected membership for competition {cid}")
        print(f"{state['code']}: A1 {a1}, A2 {a2}, four-club knockout {final} verified")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("base","world","recipe"):
        parser.add_argument(arg,type=Path)
    args=parser.parse_args()
    verify(args.base,args.world,json.loads(args.recipe.read_text(encoding="utf-8-sig")))
