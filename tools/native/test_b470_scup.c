/* B470 (FL Testovi, GigaPack beta 3, season 2 to 15.10.2027, 17.11.): two things of the summer roll.

   1. The UEFA Super Cup (reg 7) was never played after the first summer: the July teardown
      emptied it (2 -> 0 on day 181) and the game's own setup never filled it again. fl26swiss
      now fills it from the kept Champions League (reg 4) and Europa League (reg 6) winners on
      days UEFA_SCUP_FROM..UEFA_SCUP_TO when the game has not (uefa_scup_fill_days). Here: the
      rule it applies (uefa_scup_decide) -- the window, a pair already set with its match to
      play, played this summer, a winner missing, the same club twice -- with season 1's real
      winners, Real Madrid (001b403e) and AS Roma (001f402f).
   2. The Europa League knockout (reg 6) kept last season's 24 clubs: the game's July list closes
      4 and 5 but not 6. teardown_pre adds it (uel_ko_close_ids): 6 for 4, a row or tie of 4 the
      same with 6, nothing when the list already names it, has no record of it or does not close 4.
   3. B470b (beta4q (B) on beta4r, 18.11.): 2. never ran -- 6 is on the July list; the season close
      empties 4, 5 and 7 but passes 6 over. After the game's day, days 181..330, a reg 6 that still
      holds clubs while 4 is empty is emptied (uel_ko_stale decides), its winner kept first.

     zig cc -O2 -fno-sanitize=undefined -w test_b470_scup.c -o test_b470_scup.exe && test_b470_scup.exe

   (tools/test_b470_scup.py builds and runs it.) Exit code 1 on any failure. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

int rcal_test_today(void) { return 181; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return 2027 * 365 + 181; }
uint32_t state_test_user(void) { return 0; }
const char* state_test_path(void) { return ""; }

static int fails = 0;
static void expect(int ok, const char* what, int v)
{
  if (!ok) { printf("  FAIL  %s (%d)\n", what, v); fails++; }
}

#define REAL_MADRID 0x001b403eu
#define AS_ROMA     0x001f402fu

/* the regulations with a record: GigaPack's 2..7 and their rows, not 1030 */
static int live_all(uint16_t id) { return id >= 2 && id <= 7 || id == 1027 || id == 1028 || id == 1029; }
static int live_wide(uint16_t id) { return live_all(id) || id == 1030 || id == (6 | 2 << 10); }
static int live_none(uint16_t id) { (void)id; return 0; }

static int has(const uint16_t* v, int n, uint16_t id)
{
  for (int i = 0; i < n; i++) if (v[i] == id) return 1;
  return 0;
}

int main(void)
{
  /* ---- the Super Cup rule ---- */
  expect(uefa_scup_decide(181, 0, 0, REAL_MADRID, AS_ROMA) == USC_OUT, "day 181 (the roll): not yet", 181);
  expect(uefa_scup_decide(UEFA_SCUP_FROM - 1, 0, 0, REAL_MADRID, AS_ROMA) == USC_OUT, "the day before the window", UEFA_SCUP_FROM - 1);
  expect(uefa_scup_decide(UEFA_SCUP_FROM, 0, 0, REAL_MADRID, AS_ROMA) == USC_FILL, "first day: Real Madrid v Roma", UEFA_SCUP_FROM);
  expect(uefa_scup_decide(UEFA_SCUP_TO, 0, 0, REAL_MADRID, AS_ROMA) == USC_FILL, "last day: still filled", UEFA_SCUP_TO);
  expect(uefa_scup_decide(222, 0, 0, REAL_MADRID, AS_ROMA) == USC_OUT, "its own day 222: too late to fill", 222);
  expect(UEFA_SCUP_TO < 222 && UEFA_SCUP_FROM > 182, "the window sits between the roll and day 222", UEFA_SCUP_FROM);
  expect(uefa_scup_decide(210, 1, 0, REAL_MADRID, AS_ROMA) == USC_HAVE, "a pair with its match to play: left alone", 210);
  expect(uefa_scup_decide(210, 0, 1, REAL_MADRID, AS_ROMA) == USC_PLAYED, "played this summer: not again", 210);
  expect(uefa_scup_decide(210, 1, 1, REAL_MADRID, AS_ROMA) == USC_HAVE, "both: left alone", 210);
  expect(uefa_scup_decide(210, 0, 0, 0, AS_ROMA) == USC_NO_UCL, "no Champions League winner", 210);
  expect(uefa_scup_decide(210, 0, 0, REAL_MADRID, 0) == USC_NO_UEL, "no Europa League winner", 210);
  expect(uefa_scup_decide(210, 0, 0, 0x3fffu, AS_ROMA) == USC_NO_UCL, "a handle of team 0 is no winner", 210);
  expect(uefa_scup_decide(210, 0, 0, REAL_MADRID, (REAL_MADRID & ~0x3fffu) | 0x11u) == USC_SAME,
         "the same club (team id) won both", 210);
  for (int r = USC_SAME; r <= USC_HAVE; r++)
    expect(uefa_scup_why(r)[0] != 0, "every reason has its words", r);

  /* ---- reg 6 at the July teardown ---- */
  {
    /* the game's list on day 181 of GigaPack's season 2, the European part: 2 3 4 5 and the rows
       of the league phases, no 6 */
    const uint16_t game[] = { 2, 3, 4, 5, 1027, 1029, 300, 301 };
    int n = (int)(sizeof game / sizeof *game);
    uint16_t out[UEL_KO_CLOSE_MAX];
    int k = uel_ko_close_ids(game, n, live_all, out, UEL_KO_CLOSE_MAX);
    expect(k == 1 && out[0] == R_UELKO, "reg 6 is closed with reg 4", k);

    const uint16_t with6[] = { 2, 3, 4, 5, 6, 1027, 1029 };
    k = uel_ko_close_ids(with6, 7, live_all, out, UEL_KO_CLOSE_MAX);
    expect(k == 0, "the list already closes 6: nothing added", k);

    const uint16_t no4[] = { 2, 3, 5, 1027, 1029 };
    k = uel_ko_close_ids(no4, 5, live_all, out, UEL_KO_CLOSE_MAX);
    expect(k == 0, "the list does not close 4: nothing added", k);

    k = uel_ko_close_ids(game, n, live_none, out, UEL_KO_CLOSE_MAX);
    expect(k == 0, "no record of 6: nothing added", k);

    const uint16_t rows[] = { 2, 4, 1028, 4 | 2 << 10, 4, 5 };
    k = uel_ko_close_ids(rows, 6, live_wide, out, UEL_KO_CLOSE_MAX);
    expect(k == 3 && has(out, k, 6) && has(out, k, 1030) && has(out, k, 6 | 2 << 10),
           "a row and a tie of 4 bring the same of 6, 4 twice brings 6 once", k);
    k = uel_ko_close_ids(rows, 6, live_all, out, UEL_KO_CLOSE_MAX);
    expect(k == 1 && out[0] == 6, "rows of 6 with no record are left out", k);

    k = uel_ko_close_ids(rows, 6, live_wide, out, 1);
    expect(k == 1, "never more than the room it is given", k);
  }

  /* ---- B470b: reg 6 after the season close (uel_ko_stale) ----
     beta4q (B) on beta4r, 18.11.: reg 6 IS on the July list (the event table gives 2..7 one
     region), the season close emptied 4 (24 -> 0), 5 and 7 but not 6 (34 clubs), and the UEL
     page showed 59 clubs on 12.08. */
  {
    expect(uel_ko_stale(1, 181, 1, 0, 1, 34), "day 181, 4 emptied, 6 still 34: emptied", 181);
    expect(uel_ko_stale(1, 223, 1, 0, 1, 34), "12.08. (day 223), a save of the summer: emptied", 223);
    expect(uel_ko_stale(1, UEL_KO_STALE_TO, 1, 0, 1, 1), "the last day of the window", UEL_KO_STALE_TO);
    expect(!uel_ko_stale(1, 180, 1, 0, 1, 34), "30 June, before the roll: left alone", 180);
    expect(!uel_ko_stale(1, UEL_KO_STALE_TO + 1, 1, 0, 1, 34), "after the window: left alone", UEL_KO_STALE_TO + 1);
    expect(!uel_ko_stale(1, 40, 1, 16, 1, 16), "February, the knockouts of this season: left alone", 40);
    expect(!uel_ko_stale(1, 181, 1, 24, 1, 34), "4 not emptied yet (the close has not run): left alone", 181);
    expect(!uel_ko_stale(1, 200, 1, 0, 1, 0), "6 already empty: nothing to do", 200);
    expect(!uel_ko_stale(1, 200, 0, 0, 1, 34), "no reg 4 record: left alone", 200);
    expect(!uel_ko_stale(1, 200, 1, 0, 0, 0), "no reg 6 record: left alone", 200);
    expect(!uel_ko_stale(0, 200, 1, 0, 1, 34), "FL26 (not the game's own UEFA): left alone", 200);
    expect(UEL_KO_STALE_FROM == 181 && UEL_KO_STALE_TO < 365 && UEL_KO_STALE_TO >= UEFA_SCUP_TO,
           "the window starts at the roll and covers the Super Cup's", UEL_KO_STALE_TO);
  }

  if (fails) { printf("%d check(s) FAILED\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
