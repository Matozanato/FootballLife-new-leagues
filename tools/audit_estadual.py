"""Compare state-league participants in two decoded FL26 slots from one career."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


def season(path, ids, year):
    data=path.read_bytes()
    layout=struct.unpack_from("<II",data)
    if layout==(10,80):
        start,count=0xa357f0,65000
    elif layout==(9,80):
        start,count=0x2a24c0,(0xf7f948-0x2a24c0)//596
    else:
        raise ValueError("Unknown FL26 save layout")
    groups={rid:dict(fixtures=0,played=0,points=Counter(),appearances=Counter()) for rid in ids}
    for i in range(count):
        at=start+i*596
        ref,rid,flags,y=struct.unpack_from("<IHHH",data,at)
        if i!=ref or rid not in groups or y!=year:
            continue
        g=groups[rid]
        sides=struct.unpack_from("<II",data,at+20)
        if 0xffffffff in sides or sides[0]==sides[1]:
            raise ValueError(f"Invalid fixture {ref}")
        clubs=[key>>14 for key in sides]
        g["fixtures"]+=1
        g["appearances"].update(clubs)
        if flags&0x4000:
            g["played"]+=1
            diff=data[at+28]-data[at+31]
            for club,margin in zip(clubs,(diff,-diff)):
                g["points"][club]+=3 if margin>0 else int(margin==0)
    return layout,groups,hashlib.sha256(data).hexdigest()


def compare(before,after,ids,year):
    mode,old,h1=season(before,ids,year)
    mode2,new,h2=season(after,ids,year+1)
    if mode!=mode2:
        raise ValueError("Slots must belong to the same mode and career")
    fields=lambda groups:[set(groups[r]["appearances"]) for r in ids]
    a,b=fields(old)
    c,d=fields(new)
    up,down=b&c,a&d
    field_ok=(len(a),len(b),len(c),len(d))==(12,8,12,8) and not (a&b or c&d) and a|b==c|d
    complete=all(old[r]["played"]==old[r]["fixtures"]==n and
                 set(old[r]["appearances"].values())=={per_club}
                 for r,n,per_club in zip(ids,(66,56),(11,14)))
    result="insufficient_evidence"
    if field_ok and complete:
        result="unexpected_exchange"
        if len(up)==len(down)==2:
            top,lower=(old[r]["points"] for r in ids)
            cut_up=min(lower[t] for t in up)-max(lower[t] for t in b-up)
            cut_down=min(top[t] for t in a-down)-max(top[t] for t in down)
            if min(cut_up,cut_down)>=0:
                result="verify_tiebreak" if min(cut_up,cut_down)==0 else "confirmed"
    return dict(status=result,year=year,mode=mode[0],sha256=[h1,h2],promoted=sorted(up),
                relegated=sorted(down),before=old,after=new)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("before",type=Path)
    p.add_argument("after",type=Path)
    p.add_argument("year",type=int)
    p.add_argument("divisions",type=int,nargs=2)
    a=p.parse_args()
    print(json.dumps(compare(a.before,a.after,a.divisions,a.year),indent=2))
