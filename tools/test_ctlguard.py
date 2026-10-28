"""python tools/test_ctlguard.py

fl26ctlguard's trampoline (sider/experimental/fl26ctlguard.lua) gives every team on the user's
controller except the user's club back to the computer. It must never touch a national team:
a Become a Legend player's country is on the user's controller while it has him called up, and
handing it to the computer let the game play its matches without him (B261, BouhMiDov,
28.10.2026). The team record marks a national team with bit 2 of byte +0x423 (all 141 national
teams of a loaded career, none of its 1797 clubs; release/0.2.5/b261/natbit.py).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "sider", "experimental", "fl26ctlguard.lua")

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def tramp():
    s = open(SRC, encoding="utf-8").read()
    return "".join(re.findall(r'"([0-9a-f]+)"', s[s.index("local TRAMP"):s.index("local TEAMS_LE")]))


def main():
    t = tramp()
    ok("the trampoline fits the cave in front of .rdata (0x14252ef00..0x14252f000)", len(t) // 2 <= 0x100)
    # test byte ptr [rcx+0x423], 4 ; jne <next team>  -- in front of the write of 0xff
    at = t.find("f6812304000004" + "75")
    ok("a national team is skipped (test byte [rcx+0x423],4 / jne)", at >= 0)
    ok("... before the controller byte is set to 0xff", 0 <= at < t.find("c6811d040000ff"))
    ok("... and its jne lands on the next team (add rcx,0x690)",
       t[at + 16:at + 18] == "12" and t[at + 18 + 2 * 0x12:].startswith("4881c190060000"))
    try:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    except ImportError:
        print("capstone not installed: the whole-trampoline decode is skipped")
    else:
        ins = list(Cs(CS_ARCH_X86, CS_MODE_64).disasm(bytes.fromhex(t), 0x14252ef00))
        ok("capstone decodes every byte of the trampoline", sum(len(i.bytes) for i in ins) == len(t) // 2)
        ok("it ends in ret", ins[-1].mnemonic == "ret")
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
