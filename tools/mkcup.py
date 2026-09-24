r"""python mkcup.py --base <pesdb dir> --out <livecpk root> --teams a,b,c,...
                  [--cid N] [--reg N] [--region N] [--name S] [--code S]
                  [--like BELGIUM_CUP] [--bracket N] [--dry]

Add one knockout cup, the same way mkleague.py adds a league.

Every competition this project has made so far is a league, which is also why a Master League
season in our world contains no cup fixtures.  It turns out a cup needs no new machinery.  A
competition is three rows -- Competition.bin, CompetitionRegulation.bin, CompetitionEntry.bin
-- and what makes one a knockout rather than a league is byte 0x09 of the regulation (4
league, 3 knockout, 2 group stage, 1 playoff) together with the format template in bits 12-17
of +0x0c, which is 1 for a league and 2 for a domestic cup.  Since mkleague.add_league()
copies its prototype's rows wholesale and overwrites only the ids, the count and the names,
handing it a cup to copy produces a cup, templates and all.  This tool is that call with the
cup-shaped arguments and the checks a cup needs.

Reading the shipped tables makes the choice of prototype easy.  Football Life carries 56
knockout regulations; the useful ones for copying are:

    BELGIUM_CUP   cid 112  reg 122  bracket 16  16 entries   a plain national cup
    CHINA_CUP     cid 126  reg 127  bracket 16  16 entries   the same shape
    CUSTOM_CUP    cid  37  reg  48  bracket 16   0 entries   a cup with nobody in it

CUSTOM_CUP is the tempting one -- a 16-slot knockout that ships with no participants at all,
sitting in region 26, the "special" slot, paired with a 32-team group stage on regulation 47.
It is the closest thing to a blank the game carries.  The default here is still BELGIUM_CUP,
because a cup known to run every season in a real region is a safer thing to copy than one
nothing references, and because region 26 is not where a national cup belongs.  --like
CUSTOM_CUP is there for the day that turns out to be wrong.

Two ways a cup is not a league, both handled here:

  The bracket and the entry list are different numbers.  In a league the team count is the
  number of clubs and that is the end of it.  In a cup they diverge -- the FA Cup is bracket
  44 against 44 entries, but Coppa Italia is bracket 20 against 40, because the lower
  divisions enter in later rounds.  --bracket sets the regulation's count on its own and
  defaults to the number of clubs given, which is the plain every-club-enters case.

  Entry order is a seeding, not a table position.  The byte means "where this club starts in
  the bracket", not "where it finished last year", so the order clubs are passed in is the
  order they are drawn.

What this tool does NOT do is put the cup in the calendar, and that is the part nobody has
tested.  New leagues took a while to get fixtures at all, and the fix was to copy an existing
country's calendar dword rather than to invent one; copying a whole shipped cup should carry
that dword too, but "should" is doing real work in that sentence.  So build one, install it,
start a season, and look at the fixture list.

    python mkcup.py --base ...\pesdb --out ...\livecpk\_FL26E39x793 ^
                    --name "FL Cup 01" --code FL_CUP_01 --region 16 --teams 72318,72319,...

--dry prints what it would write and touches nothing.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

R_TYPE, KNOCKOUT = 0x09, 3


def prototype(comp, regs, code):
    """the competition id and regulation type byte of the competition with this code"""
    cid = None
    for i in range(len(comp) // M.COMP):
        r = comp[i * M.COMP:(i + 1) * M.COMP]
        if r[M.CODE_OFF:].split(b"\0")[0].decode("latin1") == code:
            cid = r[M.CID_OFF]
            break
    if cid is None:
        raise SystemExit("no competition coded %s" % code)
    for i in range(len(regs) // M.REG):
        if regs[i * M.REG + M.R_CID] == cid:
            return cid, regs[i * M.REG + R_TYPE]
    raise SystemExit("%s has no regulation row" % code)


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    teams = [int(x) for x in get("--teams", "").split(",") if x.strip()]
    if not base or not out or not teams:
        print(__doc__)
        return 1

    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin",
                         "CompetitionEntry.bin"))
    print("base: %d competitions, %d regulations, %d entries"
          % (len(comp) // M.COMP, len(regs) // M.REG, len(ents) // M.ENT))

    like = get("--like", "BELGIUM_CUP")
    _, ptype = prototype(comp, regs, like)
    if ptype != KNOCKOUT:
        # Copying a league and calling the result a cup is exactly the mistake this catches.
        # The type byte would be overwritten anyway, but the format template, the matchday
        # template and every other knockout-shaped bit would still be the league's, and the
        # failure would not show up until a season refused to draw a single tie.
        raise SystemExit("%s is competition type %d, not a knockout (3) -- pick a real cup"
                         % (like, ptype))

    bracket = int(get("--bracket", str(len(teams))))
    if not 2 <= bracket <= 0x3f:
        raise SystemExit("the regulation holds the count in six bits, so %d is out of range"
                         % bracket)
    if bracket > len(teams):
        print("note: bracket %d is bigger than the %d clubs entered, so there will be byes"
              % (bracket, len(teams)))

    # The old defaults were cid 150 and reg 200, and cid 150 is wrong in the only world this
    # is going to be used in: mkworld allocates competition ids from 130 upward, so a
    # 39-league world already owns 130-168 and the shipped rows carry on to 173.  Picking a
    # fixed number here means silently landing on top of one of our own leagues.  So do what
    # mkworld does and take the first id nothing claims -- measured on _FL26G39, that is cid
    # 174 and regulation 186.
    import mkworld as W
    used_cid = {comp[i * M.COMP + M.CID_OFF] for i in range(len(comp) // M.COMP)}
    used_reg = {int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
                for i in range(len(regs) // M.REG)}
    # Regulation ids above 175 work for Master League -- measured 17 September, and the
    # earlier belief that they did not came from the Select Team list, which is a different
    # question.  BAD_REG is still avoided: those are the ids the game reassigns as phases of
    # somebody else's competition.
    autocid = W.free_ids(used_cid, W.CID_MAX, 1, 130)[0]
    autoreg = W.free_ids(used_reg | W.BAD_REG, W.REG_MAX, 1, 186)[0]
    cid, reg = M.add_league(comp, regs, ents,
                            int(get("--cid", str(autocid))), int(get("--reg", str(autoreg))),
                            int(get("--region", "16")), get("--name", "FL Test Cup"),
                            get("--code", "FL_TEST_CUP"), teams, like)
    # add_league sized the count from the entry list, which is right for a league; a cup's
    # bracket is its own number, so set it back afterwards rather than teaching add_league
    # about cups.
    last = (len(regs) // M.REG - 1) * M.REG
    regs[last + M.R_TEAMS] = (regs[last + M.R_TEAMS] & 0xc0) | (bracket & 0x3f)
    print("copied %s: type %d (knockout), bracket %d, %d clubs entered"
          % (like, regs[last + R_TYPE], bracket, len(teams)))
    print("competition id %d, regulation %d" % (cid, reg))

    if "--dry" in a:
        print("dry run: nothing written")
        return 0
    M.write_tables(out, comp, regs, ents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
