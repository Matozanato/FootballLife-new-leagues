"""Big object graphs freed a piece at a time, in a thread of their own (B480, 17.11.2026).

Python frees a dict, a list or a tuple in one call of C code that keeps Python's lock until the
last object under it is gone. A world's plan or recipe read back is millions of objects (the
GigaPack's plan is 286 MB of JSON): the last name for it going away -- a function returning, a
cache entry popped, `project.recipe = new` -- kept the lock for 3 s and more, and the window's
thread could not get its turn (the exe test of beta4o, Make it editable: stops of 3.1 s and 2.8 s
with a worker in Py_Dealloc, and 7.2 s with the window's own thread in it, in adopt; hangstacks:
12.6 s user + 12.7 s kernel, most of it reading the paged-out objects back to free them).

drop(obj) hands obj to the thread here. It waits until it holds the only name for obj (the caller
lets go of its own right after the call), then takes it apart from the top: the members of a
dict, list or set one by one, a member that is itself a container of its own the same way. Python
gives its lock away between two of these steps (sys.setswitchinterval), so the window keeps its
turns. Only what nobody else holds is taken apart: a member that something else still refers to
is just let go of (it stays as it is, for whoever has it). The memory comes back as before, a few
seconds later at most.
"""
import queue
import sys
import threading
import time

_Q = queue.SimpleQueue()
_started = False
_start_lock = threading.Lock()
_count_lock = threading.Lock()
_busy = [0]                         # objects handed over and not taken apart yet (for the tests)
_CONTAINERS = (dict, list, set, tuple)
WAIT = 60.0                          # seconds to wait for the other holders of a root to let go
SMALL = 64                           # a container this short of plain values goes in one go
# and the thread rests, more than bigjson's readers do (nobody waits for this): a thread that never
# stops holds back every call Qt makes into Python on the window's thread by a switch interval
# (bigjson.GENTLE). 3 ms of 6 still left a stop of 0.66 s after Make it editable with 220,000 players
WORK, REST = 0.002, 0.008
# and it starts QUIET seconds after the last drop: a drop comes at the end of a job, when the window
# has the most to do (the pages, the header, the box); the memory can wait that long (B480,
# 17.11.2026: the exe test of beta4p, this thread at work through every stop after Make it editable)
QUIET = 2.0
_last = [0.0]


def drop(*objs):
    """free objs (a world's plan, a recipe, a cache entry) in a thread of its own, in small steps.
    The caller lets go of its own names for them right after (del)"""
    global _started
    _last[0] = time.monotonic()
    for o in objs:
        if isinstance(o, _CONTAINERS) and o:
            with _count_lock:
                _busy[0] += 1
            _Q.put(o)
    if not _started:
        with _start_lock:
            if not _started:
                threading.Thread(target=_run, name="letgo", daemon=True).start()
                _started = True


def pending():
    """objects handed to drop() that are not taken apart yet"""
    return _busy[0]


def wait(timeout=30.0):
    """until every object handed over so far is taken apart (the tests); True when it was"""
    end = time.monotonic() + timeout
    while _busy[0] and time.monotonic() < end:
        time.sleep(0.01)
    return not _busy[0]


def _run():
    waiting = []                     # [(root, since)] that someone else still holds
    while True:
        try:
            got = _Q.get(timeout=0.1 if waiting else None)
            waiting.append([got, time.monotonic()])
            del got
        except queue.Empty:
            pass
        now = time.monotonic()
        if now - _last[0] < QUIET:
            continue                 # (the queue is asked again in 0.1 s: waiting is not empty)
        keep = []
        while waiting:
            item = waiting.pop()
            if _alone_root(item) or now - item[1] > WAIT:
                try:
                    _take_apart(item)
                except Exception:
                    pass
                del item
                with _count_lock:
                    _busy[0] -= 1
            else:
                keep.append(item)
                del item
        waiting = keep
        del keep


def _alone_root(item):
    """True when the list `item` ([root, since]) holds the only name for root"""
    probe = [{}, 0.0]
    base = sys.getrefcount(probe[0])
    del probe
    return sys.getrefcount(item[0]) <= base


def _take_apart(item):
    """free item[0] (item: [root, since], the only name for root) member by member, depth first; a
    member someone else holds is let go of only"""
    stack = [item.pop(0)]
    probe = [{}]
    o = probe.pop()
    alone = sys.getrefcount(o)       # the count of a container only `o` holds, measured like below
    del o, probe
    clock = time.perf_counter() + WORK
    while stack:
        o = stack.pop()
        if sys.getrefcount(o) > alone:
            del o                    # someone else has it: theirs now
            continue
        t = type(o)
        if t is dict:
            while o:
                _k, v = o.popitem()
                if _worth(v):
                    stack.append(v)
                del _k, v            # (a small one is freed here, in one short call)
                if time.perf_counter() >= clock:
                    _pause()
                    clock = time.perf_counter() + WORK
        elif t is list or t is set:
            while o:
                v = o.pop()
                if _worth(v):
                    stack.append(v)
                del v
                if time.perf_counter() >= clock:
                    _pause()
                    clock = time.perf_counter() + WORK
        elif t is tuple:
            # a tuple cannot be emptied: its big members go on the stack, then the tuple goes
            stack.extend(v for v in o if _worth(v))
        del o


def _pause():
    """the rest between two steps, longer while drops keep coming (QUIET)"""
    time.sleep(REST)
    while time.monotonic() - _last[0] < QUIET:
        time.sleep(0.05)


def _worth(v):
    """True when v is to be taken apart member by member: a container longer than SMALL, or one
    that holds a container (a plan's few keys over its leagues, a (stamp, plan) tuple). Only a
    short one of plain values is freed in one go: a name list, a club's numbers"""
    if type(v) not in _CONTAINERS or not v:
        return False
    if len(v) > SMALL:
        return True
    for x in (v.values() if type(v) is dict else v):
        if type(x) in _CONTAINERS and x:
            return True
    return False
