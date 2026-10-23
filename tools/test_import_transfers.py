"""python test_import_transfers.py -- Players > More > Import transfers... (jibibi 23.10., mato:
a CSV the player makes, Mod Studio reads it; nothing is fetched from a website):
lbplayers.import_transfers matches each line's player and club in the world."""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbplayers as P

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


PLAYERS = [
    {"player": "100", "name": "Kylian Mbappé", "home": ["108"]},
    {"player": "101", "name": "Bradley Barcola", "home": ["111"]},
    {"player": "102", "name": "Lucas Hernández", "home": ["111"]},
    {"player": "103", "name": "Lucas Hernandez", "home": ["5"]},          # two of one name
    {"player": "Ligue 2/3/7", "name": "Téji Savanier", "home": ["Ligue 2/3"]},
    {"player": "104", "name": "J. Doe", "home": []},
]
CLUBS = [("Paris Saint-Germain", "111"), ("Real Madrid CF", "108"), ("Olympique Lyonnais", "5"),
         ("AS Saint-Étienne", "Ligue 2/3"), ("Lyon FC", "Ligue 2/4"), ("Lyon", "Ligue 2/5")]


def write(root, name, text):
    p = os.path.join(root, name)
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    return p


def main():
    root = tempfile.mkdtemp(prefix="fl26_transfers_")
    try:
        p = write(root, "t.csv", "player,to,from\n"
                  "kylian mbappe,Paris Saint-Germain FC,\n"           # no accents, FC more
                  "101,Real Madrid CF,\n"                               # an id
                  "Lucas Hernandez,Real Madrid CF,PSG\n"                # from that is no club: still two
                  "Lucas Hernandez,AS Saint-Etienne,Olympique Lyonnais\n"
                  "Teji Savanier,111,\n"                               # a game team id
                  "John Doe,Real Madrid CF,\n"                          # J. Doe
                  "Nobody Here,Real Madrid CF,\n"
                  "Bradley Barcola,Nowhere United,\n"
                  "101,Paris Saint-Germain,\n"                          # again: the first line counts
                  ",,\n")
        moves, err = P.import_transfers(p, PLAYERS, CLUBS)
        ok("names without accents and case, a club without FC, an id, a team id",
           ("100", "111", 2) in moves and ("101", "108", 3) in moves and ("Ligue 2/3/7", "111", 6) in moves)
        ok("two players of one name: the from column picks the one of that club",
           ("103", "Ligue 2/3", 5) in moves and not any(m[0] == "102" for m in moves))
        ok("and without a from that tells them apart it is a problem, not a guess",
           any(e.startswith("line 4:") and "2 players" in e for e in err))
        ok("a first name against an initial (John Doe / J. Doe)", ("104", "108", 7) in moves)
        ok("no such player, no such club: problems", any(e.startswith("line 8:") for e in err)
           and any(e.startswith("line 9:") and "no club" in e for e in err))
        ok("a player twice: the first line counts", any(e.startswith("line 10:") for e in err)
           and sum(m[0] == "101" for m in moves) == 1)
        ok("an empty line is no problem", not any(e.startswith("line 11:") for e in err))
        ok("five moves, four problems", len(moves) == 5 and len(err) == 4)

        p = write(root, "semi.csv", "Name;New club\nKylian Mbappé;Paris Saint-Germain\n")
        ok("a table with ; and other column names (Name, New club)",
           P.import_transfers(p, PLAYERS, CLUBS)[0] == [("100", "111", 2)])
        p = write(root, "lyon.csv", "player,club\nKylian Mbappé,Lyon\n")
        moves, err = P.import_transfers(p, PLAYERS, CLUBS)
        ok("a club name two clubs answer to is a problem", not moves and "2 clubs" in err[0])
        p = write(root, "bad.csv", "who,where\nx,y\n")
        try:
            P.import_transfers(p, PLAYERS, CLUBS)
            ok("columns it does not know: an error naming them", False)
        except P.Error as e:
            ok("columns it does not know: an error naming them", "who, where" in str(e))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
