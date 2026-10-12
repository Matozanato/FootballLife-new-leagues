"""python tools/test_best_eleven.py

Best eleven (lbplayers.best_eleven): a player who can also play a place (position rated 1)
competes for it at his overall less SECOND_POS, so a strong midfielder starts at DMF over a
weak registered DMF, while a registered DMF close to him keeps the place; goalkeepers stay
in goal; a player who cannot play a place comes after everyone who can.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1


POS = ["GK", "CB", "LB", "RB", "DMF", "CMF", "RMF", "LMF", "AMF", "LWF", "RWF", "SS", "CF"]
ABIL = ["Low Pass", "Lofted Pass", "Ball Control", "Stamina", "Ball Winning", "Offensive Awareness",
        "Defensive Awareness", "Speed", "Physical Contact", "Heading", "Jump", "Dribbling", "Finishing",
        "Acceleration", "GK Awareness", "GK Catching", "GK Clearing", "GK Reflexes", "GK Reach"]


def player(name, reg, level, order, **also):
    r = {"player": name, "name": name, "Registered Position": reg, "order": str(order)}
    for p in POS:
        r[p] = "2" if p == reg else str(also.get(p, 0))
    for a in ABIL:
        r[a] = str(level)
    return r


def lineup(rows):
    o = L.best_eleven(rows)
    return [n for n, _ in sorted(o.items(), key=lambda kv: int(kv[1]))]


# Arsenal: Rice (CMF, DMF 1, 83) over Julienne (DMF, 62)
squad = [player("Raya", "GK", 91, 0), player("Gabriel", "CB", 91, 1), player("Saliba", "CB", 86, 2),
         player("Timber", "RB", 80, 3), player("Calafiori", "LB", 78, 4), player("Zubimendi", "DMF", 81, 5),
         player("Julienne", "DMF", 62, 6), player("Rice", "CMF", 83, 7, DMF=1), player("Merino", "CMF", 82, 8, DMF=1),
         player("Saka", "RWF", 85, 9, RMF=1), player("Martinelli", "LWF", 80, 10, LMF=1), player("Eze", "AMF", 82, 11),
         player("Gyokeres", "CF", 83, 12), player("Kepa", "GK", 78, 13), player("Havertz", "CF", 80, 14)]
xi = lineup(squad)[:11]
ok("Rice starts at DMF", xi[5:7] == ["Zubimendi", "Rice"])
ok("Julienne on the bench", "Julienne" not in xi)
ok("the wingers take the wide places", xi[7] == "Saka" and xi[8] == "Martinelli")
ok("one keeper, in goal", xi[0] == "Raya" and "Kepa" not in xi)

# the other places filled, two DMF places to fight for
base = [player("%s%d" % (p, i), p, 60, 20 + i) for i, p in enumerate(["GK", "CB", "CB", "RB", "LB", "RMF", "LMF", "AMF", "CF"])]
near = base + [player("A", "DMF", 80, 0), player("B", "CMF", 84, 1, DMF=1), player("C", "DMF", 70, 2)]
o = L.best_eleven(near)
ok("the real DMF within SECOND_POS keeps the place", o["A"] == "5" and o["B"] == "6" and o["C"] == "11")
far = base + [player("A", "DMF", 80, 0), player("B", "CMF", 90, 1, DMF=1), player("C", "DMF", 70, 2)]
o = L.best_eleven(far)
ok("a midfielder far better than the DMFs takes the first place", o["B"] == "5" and o["A"] == "6" and o["C"] == "11")

# a player who cannot play a place comes after everyone who can
cant = [player("%s%d" % (p, i), p, 60, 20 + i) for i, p in enumerate(["GK", "RB", "LB", "DMF", "DMF", "RMF", "LMF", "AMF", "CF"])]
cant += [player("D", "CB", 50, 1), player("M", "DMF", 65, 2, CB=1), player("S", "CF", 90, 3)]
o = L.best_eleven(cant)
ok("the CB and the DMF who can play there beat a striker who cannot", sorted((o["D"], o["M"])) == ["1", "2"] and o["S"] == "10")

# the rest keep their order
rest = lineup(squad)[11:]
ok("the bench keeps its order", rest == ["Julienne", "Kepa", "Havertz"] or rest == sorted(rest, key=lambda n: next(int(r["order"]) for r in squad if r["player"] == n)))

print("ok: %d checks" % N)
