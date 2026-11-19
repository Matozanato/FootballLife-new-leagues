"""Check a complete FL26 observer run against a recipe (REA calendar TSV, one career)."""
import argparse
from collections import Counter, defaultdict
import datetime as dt
import json
from pathlib import Path


def audit(log, recipe, code, year, start, end):
    state=next(s for s in recipe["states"] if s["code"]==code)
    top,lower,semi,final=state["regulations"]
    days=recipe["calendar"][str(year)]
    dates=[(dt.date(2001,1,1)+dt.timedelta(days=d)).replace(year=year).isoformat() for d in days]
    watched={top,lower,semi+1024,semi+2048,final}
    games=defaultdict(dict)
    future=set()
    unified=recipe.get("revision",5)==7
    knockout={}
    with log.open(encoding="utf-8-sig") as f:
        for line in f:
            v=line.rstrip().split("\t")
            if len(v)!=10 or not start<=v[1]<=end or v[3] not in ("jogo_inicial","jogo_observado","jogo_alterado"):
                continue
            reg=int(v[5])
            if reg not in watched or v[2][:4]!=str(year):
                continue
            match=(v[4],v[6],v[7],v[8])
            if v[6][:4]!=str(year):
                # Past fixtures may survive a reload. Future fixtures seen during
                # the state championship reveal rounds pushed into next January.
                if v[6][:4]>str(year) and v[2]<=dates[-1]: future.add((reg,*match))
                continue
            if unified and reg==final:
                knockout[v[4]]=(v[6],v[7],v[8],int(v[9]))
                continue
            games[reg][match]=games[reg].get(match,False) or bool(int(v[9])&0x4000)
    failures=[]
    summary={}
    for reg,expected,per_day in [(top,dates[:11],6),(lower,dates,4),(semi+1024,dates[11:12],1),
                                 (semi+2048,dates[11:12],1),(final,dates[12:14],1)]:
        if unified and reg not in (top,lower):
            continue
        records=games[reg]
        actual=Counter(m[1] for m in records)
        summary[reg]=[len(records),sum(records.values())]
        if actual!=Counter({d:per_day for d in expected}) or not all(records.values()):
            failures.append(reg)
    if unified:
        semis=[(h,a) for d,h,a,f in knockout.values() if d==dates[11] and (f&0x703f)==0x602e]
        legs=[[(h,a) for d,h,a,f in knockout.values() if d==day and (f&0x703f)==flag]
              for day,flag in zip(dates[12:],(0x4035,0x5035))]
        clubs={c for game in semis for c in game}
        summary[final]=[len(knockout),sum(bool(f&0x4000) for d,h,a,f in knockout.values())]
        if (len(knockout)!=4 or len(semis)!=2 or len(clubs)!=4 or "?" in clubs or
            len(legs[0])!=1 or legs[1]!=[legs[0][0][::-1]] or
            any(len(set(game)&set(legs[0][0]))!=1 for game in semis) or
            games[semi+1024] or games[semi+2048]):
            failures.append(final)
    return dict(ano=year,jogos_e_disputados=summary,regulamentos_incompletos=failures,
                jogos_empurrados_para_outro_ano=len(future),aprovado=not failures and not future)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("log",type=Path)
    p.add_argument("recipe",type=Path)
    p.add_argument("state")
    p.add_argument("year",type=int)
    p.add_argument("start",help="First wall-clock timestamp, ISO local")
    p.add_argument("end",help="Last wall-clock timestamp, ISO local")
    a=p.parse_args()
    result=audit(a.log,json.loads(a.recipe.read_text(encoding="utf-8-sig")),a.state,a.year,a.start,a.end)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["aprovado"] else 1)
