"""NewLife's players take the game's id only when the names match (newlife._game_squads): a name
the game writes in plain letters or without a middle name made a second player (B31, 14.10.2026:
Kenan Yıldız / Kenan Yildiz, Yann Aurel Bisseck / Yann Bisseck).

    python tools/test_same_name.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbplayers as P

SAME = [("Kenan Yıldız", "Kenan Yildiz"), ("Uğur Kaan Yıldız", "Ugur Kaan Yildiz"),
        ("Yann Aurel Bisseck", "Yann Bisseck"), ("Florian Niederlechner", "F. Niederlechner"),
        ("Niederlechner Florian", "Florian Niederlechner"), ("Łukasz Skorupski", "Lukasz Skorupski"),
        ("Martin Ødegaard", "Martin Odegaard"), ("Duje Ćaleta-Car", "Duje Caleta Car"),
        ("Hannes Þór Halldórsson", "Hannes Thor Halldorsson"), ("Dario Đurić", "Dario Duric")]
OTHER = [("Yann Bisseck", "Yann Sommer"), ("Kenan Yıldız", "Uğur Kaan Yıldız"),
         ("João Moreira", "Diego Moreira"), ("Yann Aurel Bisseck", "Yann Aurel"),
         ("Gabriel", "Gabriel Jesus"), ("Ana Maria Silva", "Ana Paula Silva")]


def main():
    bad = [(a, b) for a, b in SAME if not (P.same_name(a, b) and P.same_name(b, a))]
    bad += [(a, b) for a, b in OTHER if P.same_name(a, b) or P.same_name(b, a)]
    assert not bad, bad
    print("same name: %d cases passed" % (len(SAME) + len(OTHER)))


if __name__ == "__main__":
    main()
