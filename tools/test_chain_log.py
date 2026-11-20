"""python tools/test_chain_log.py

08.11. (Megapack, 313 leagues): one season pass writes far more of fl26chain.dll's log than its
16 KB held before the loader could drain it, so the season end's fix lines -- the ones that say
who went up and down -- never reached sider.log, and a drain cut lines in two ("fl26chain:
clubs", "fl26chain: 2/48"). The log now holds 256 KB, a drain hands over whole lines only, and
lines that still do not fit are counted and said. The log is filled through fl26_chain_cups,
which writes a line a cup and needs no game.
"""
import ctypes, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DLL = os.path.join(HERE, "native", "fl26chain.dll")
N = 0


def ok(name, cond):
    global N
    print(("ok    " if cond else "FAIL  ") + name)
    N += 0 if cond else 1


def drain(d, cap):
    buf = ctypes.create_string_buffer(cap)
    parts = []
    while True:
        n = d.fl26_chain_log(buf, cap)
        if n <= 0:
            return parts
        parts.append(buf.raw[:n].decode())


def main():
    d = ctypes.CDLL(DLL)
    d.fl26_chain_log.argtypes = [ctypes.c_char_p, ctypes.c_int]
    cup = (ctypes.c_uint16 * 3)(300, 17, 18)
    for _i in range(1000):                 # 2000 lines, ~110 KB: more than the 16 KB of before
        d.fl26_chain_cups(cup, 1)
    parts = drain(d, 100)
    text = "".join(parts)
    ok("every line of a big pass kept (2000)", text.count("\n") == 2000)
    ok("a drain hands over whole lines only", all(p.endswith("\n") for p in parts))
    ok("no line cut in two", all(l.startswith("fl26chain: ") for l in text.splitlines()))
    for _i in range(3000):                 # 6000 lines, ~330 KB: more than the log holds
        d.fl26_chain_cups(cup, 1)
    kept = "".join(drain(d, 4096))
    d.fl26_chain_cups(cup, 1)              # the first line after the drain: the count goes first
    text = "".join(drain(d, 4096))
    ok("a full log keeps what fit", kept.count("\n") > 4000)
    ok("then says how many lines it lost", text.startswith("(") and "log line(s) lost: the log was full" in text)
    print("%d failed" % N)
    sys.exit(1 if N else 0)


if __name__ == "__main__":
    main()
