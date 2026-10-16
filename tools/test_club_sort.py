r"""python tools/test_club_sort.py

A-Z of a league's clubs (13.10., our test 0.2.2): HNK Đakovo Croatia came after Vukovar in the
Prva NL. club_sort_key compared code points, so Đ (U+0110), Č, Š and Ž went after Z. It now folds
the letters as ascii_letters does (FOLD, then the marks taken off): Đakovo files under D.
club_order only swaps the order numbers of a league's entries: every entry keeps its club, and
no team id changes.

No game: the tables are made here.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import leaguebuilder as B

M, W = B.M, B.W
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    key = B.club_sort_key
    ok("Đakovo before Dinamo, after Čakovec, never after Vukovar",
       sorted(["HNK Vukovar 1991", "HNK Đakovo Croatia", "GNK Dinamo", "NK Čakovec"], key=key)
       == ["NK Čakovec", "HNK Đakovo Croatia", "GNK Dinamo", "HNK Vukovar 1991"])
    ok("Šibenik with the S, Žrinjski with the Z, Ørsted with the O",
       sorted(["NK Zagreb", "HNK Šibenik", "NK Osijek", "Žrinjski", "FC Ørsted", "NK Rudeš"], key=key)
       == ["FC Ørsted", "NK Osijek", "NK Rudeš", "HNK Šibenik", "NK Zagreb", "Žrinjski"])
    ok("the prefixes are still left out (FC Augsburg under A)", key("FC Augsburg") == "augsburg")
    ok("a plain name is as before", key("Arsenal FC") == "arsenal fc")

    # club_order on one league of ours: the entries keep their clubs, the order numbers move
    names = {9001: "HNK Vukovar 1991", 9002: "HNK Đakovo Croatia", 9003: "NK Dubrava", 9004: "NK Šibenik"}
    raw = bytearray(W.T_REC * len(names))
    for i, (tid, n) in enumerate(names.items()):
        o = i * W.T_REC
        raw[o + W.T_ID:o + W.T_ID + 4] = tid.to_bytes(4, "little")
        raw[o + W.T_NAME:o + W.T_NAME + len(n.encode())] = n.encode()
    regs = bytearray(M.REG)
    regs[M.R_CID], regs[M.R_TYPE] = 120, 4
    ents = bytearray(M.ENT * len(names))
    for i, tid in enumerate(names):
        o = i * M.ENT
        ents[o + M.E_TEAM:o + M.E_TEAM + 4] = tid.to_bytes(4, "little")
        ents[o + M.E_CID], ents[o + M.E_ORDER] = 120, i + 1
    before = [(int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little"), ents[o + M.E_CID])
              for o in range(0, len(ents), M.ENT)]
    B.club_order({"leagues": [{"cid": 120}]}, ents, regs, raw, 9004, log=lambda t: None)
    after = sorted((ents[o + M.E_ORDER], int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little"))
                   for o in range(0, len(ents), M.ENT))
    ok("the league lists Đakovo, Dubrava, Šibenik, Vukovar: %s" % [names[t] for _o, t in after],
       [t for _o, t in after] == [9002, 9003, 9004, 9001])
    ok("every entry keeps its club and competition (no id changes)",
       [(int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little"), ents[o + M.E_CID])
        for o in range(0, len(ents), M.ENT)] == before)
    ok("the order numbers are the same set, 1..4", sorted(o for o, _t in after) == [1, 2, 3, 4])
    print("test_club_sort: ok (%d)" % N)


if __name__ == "__main__":
    main()
