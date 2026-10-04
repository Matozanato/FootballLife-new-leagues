"""Import CSV: a row naming a game player of another club makes him join (JamesNotLike 04.10.)

    python tools/test_import_csv.py
"""
import csv, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbplayers as P

ROWS = [{"player": "10", "name": "Bayindir", "shirt": "1"}, {"player": "11", "name": "Onana", "shirt": "24"}]
OTHER = {"20": {"player": "20", "name": "Tielemans", "shirt": "8"}}


def table(lines):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(lines)
    return path


def main():
    p = table([["player", "name", "shirt"], ["11", "Onana", "13"], ["20", "Tielemans", "8"]])
    try:
        out, err, joins = P.import_csv(p, ROWS, OTHER.get)
        assert not err, err
        assert joins == ["20"], joins
        assert out == {"11": {"shirt": "13"}}, out           # Bayindir's place is left alone
        out, err, joins = P.import_csv(table([["player", "name"], ["99", "Nobody"]]), ROWS, OTHER.get)
        assert err and not out and not joins, (out, err)     # an unknown id is no place
        out, err = P.import_csv(p, ROWS)                       # the old call still works
        assert "10" in out or "11" in out
    finally:
        os.remove(p)
    print("all passed")


if __name__ == "__main__":
    main()
