/* A season of two tournaments of the game (Colombia, the MLS) counted as a whole for its places:
   the world file's `seasonsum <total> parts=<half>,<half>` (fl26_swiss_seasonsum, ssum_of).

     zig cc -O2 -fno-sanitize=undefined test_season_sum.c -o test_season_sum.exe && test_season_sum.exe

   (tools/test_season_sum.py builds and runs it.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST, FL26_STATE_TEST as test_state_keep.c). When the
   table is kept (ssum_keep: the last half's matches all played, read from the game's tables) is
   seen only in the game; here, what holds around it:
     - the sum of the halves' tables (ssum_rows, ssum_order): a row read as the game writes it
       (tools/leaguetable.py), a half under way or not played refused, a club of one half only
       counted, the order by points, goal difference, goals;
     - the lines: a total and its halves taken, a line with no half or the total as its own half
       left out, a total given twice taken once;
     - nothing but ssum_keep keeps a table for the total (keep_final leaves it alone, so the July
       and New Year teardowns cannot put a half's table or the game's own in its place);
     - the total's places: the whole-season table once one is kept -- for a Libertadores place
       (access_club_kept, CONT_KEEP) and for a cup of ours (cwc_club, CONT_KEEP too: a
       February-December league's table of December stands to the next one); with none kept yet,
       the first half's places, as a place of that half had them (a first season);
     - the whole-season table is written to the save folder's file and read back after a restart,
       as every other kept table (B49);
     - a world without the line: the halves' places as they were. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

static int g_today_test = 0, g_year_now = 2026;
static uint32_t g_user_test = 0;
static char g_path_test[MAX_PATH + 64];
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }      /* B329: no day load, no league rounds */
int rcal_test_round(uint16_t id) { (void)id; return 0; }
int state_test_date(void) { return g_year_now * 365 + g_today_test; }
uint32_t state_test_user(void) { return g_user_test; }
const char* state_test_path(void) { return g_path_test; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

#define COL 119          /* Liga BetPlay DIMAYOR: the total */
#define COL_I 168        /* its Apertura */
#define COL_II 169       /* its Clausura */
#define MLS 51
#define CLUB(i) ((uint32_t)(i) << 14 | 0x1000)
static const uint32_t USER_A = CLUB(9001);

static void go(int year, int day) { g_year_now = year; g_today_test = day; abs_day(); }
static void keep_table(uint16_t reg, int first, int n)
{
  final_t* f = 0;
  for (int i = 0; i < g_nfinal; i++) if (g_final[i].reg == reg) f = &g_final[i];
  if (!f) f = &g_final[g_nfinal++];
  f->reg = reg; f->n = (uint16_t)n; f->day = abs_day();
  for (int k = 0; k < n; k++) f->club[k] = CLUB(first + k);
}
static void restart(void)
{
  memset(g_final, 0, sizeof g_final); g_nfinal = 0;
  memset(g_cupwin, 0, sizeof g_cupwin); g_ncupwin = 0;
  memset(g_seed, 0, sizeof g_seed); g_nseed = 0;
  g_year_off = 0; g_last_day = -1; g_timeline = 0;
  g_new_career = 0; g_day_ticked = 0; g_first_day = -1;
  g_built_gdate = -1; g_built_stored = 0;
  g_st_off = g_st_day = -0x7fffffff; g_st_user = 0; g_st_busy = 0; g_st_read_back = 0;
}
/* places 1..n of reg as the Libertadores reads them: all from a kept table, club first + rank - 1 */
static int lib_places(uint16_t reg, int first, int n)
{
  for (int r = 1; r <= n; r++) {
    int ft = 0;
    uint32_t c = access_club_kept(reg, r, &ft, CONT_KEEP);
    if (!ft || c != CLUB(first + r - 1)) return 0;
  }
  return 1;
}
/* places 1..n of reg as a cup of ours reads them */
static int cup_places(uint16_t reg, int first, int n, const char* want)
{
  for (int r = 1; r <= n; r++) {
    const char* how = "";
    uint32_t c = cwc_club(reg, r, &how);
    if (c != CLUB(first + r - 1) || strcmp(how, want)) return 0;
  }
  return 1;
}

/* a table row as the game has it: club, points, the six-bit counts, matches played */
static void row(unsigned char* t, int k, int club, int pts, int gf, int ga, int mp)
{
  unsigned char* r = t + k * 20;
  memset(r, 0, 20);
  *(uint32_t*)r = CLUB(club);
  *(uint32_t*)(r + 4) = (uint32_t)k + 1;
  uint64_t v = (uint64_t)(pts / 3) | (uint64_t)(gf & 63) << 24 | (uint64_t)(gf >> 6) << 30
             | (uint64_t)(ga & 63) << 36 | (uint64_t)(ga >> 6) << 42;
  r[8] = (unsigned char)pts;
  for (int b = 0; b < 6; b++) r[9 + b] = (unsigned char)(v >> (8 * b));
  r[0x0f] = (unsigned char)mp;
}

int main(void)
{
  char tmp[MAX_PATH];
  GetTempPathA(sizeof tmp, tmp);
  snprintf(g_path_test, sizeof g_path_test, "%sfl26swiss-ssum-test-%lu.bin", tmp, GetCurrentProcessId());
  DeleteFileA(g_path_test);

  printf("The halves' tables added together\n");
  {
    unsigned char a[20 * 40], b[20 * 40];
    /* the Apertura: 1 on 40 pts, 2 on 38, 3 and 4 on 30 (3 the better difference), 5 on 10 */
    row(a, 0, 1, 40, 35, 10, 19); row(a, 1, 2, 38, 30, 12, 19); row(a, 2, 3, 30, 70, 20, 19);
    row(a, 3, 4, 30, 25, 20, 19); row(a, 4, 5, 10, 8, 40, 19);
    /* the Clausura: 2 on 41, 4 on 35, 1 on 30, 3 on 30, 6 (up in the summer) on 20 */
    row(b, 0, 2, 41, 30, 9, 19); row(b, 1, 4, 35, 22, 15, 19); row(b, 2, 1, 30, 20, 20, 19);
    row(b, 3, 3, 30, 15, 25, 19); row(b, 4, 6, 20, 12, 30, 19);
    ssum_tab_t s; s.n = 0;
    expect(ssum_rows(a, 5, &s) == 19 && ssum_rows(b, 5, &s) == 19 && s.n == 6, "two tables of 19 matches a club, six clubs");
    ssum_order(&s);
    /* 2: 79, 1: 70, 4: 65, 3: 60 (difference 40), 6: 20, 5: 10 */
    expect(s.club[0] == CLUB(2) && s.pts[0] == 79 && s.club[1] == CLUB(1) && s.pts[1] == 70
           && s.club[2] == CLUB(4) && s.club[3] == CLUB(3) && s.gd[3] == 40 && s.gf[3] == 85
           && s.club[4] == CLUB(6) && s.club[5] == CLUB(5), "points, then difference: 2, 1, 4, 3, 6, 5");
    expect(s.gf[0] == 60 && s.gd[0] == 39 && s.gf[3] == 85, "goals (70 in one half: over six bits) and the difference from the counts");
    row(b, 0, 7, 50, 2, 1, 2); row(b, 1, 8, 50, 2, 1, 2); row(b, 2, 9, 50, 2, 1, 2);
    row(b, 3, 10, 50, 2, 1, 1); row(b, 4, 11, 50, 2, 1, 2);
    ssum_tab_t z; z.n = 0;
    expect(ssum_rows(b, 5, &z) == 0 && z.n == 0, "a half under way (one club a match short): refused, nothing added");
    for (int k = 0; k < 5; k++) b[k * 20 + 0x0f] = 0;
    expect(ssum_rows(b, 5, &z) == 0 && z.n == 0, "a half nobody has played: refused");
    expect(ssum_rows(0, 5, &z) == -1 && ssum_rows(b, 3, &z) == -1, "no table, or one of 3 rows: none");
    /* equal on everything: the first counted stays first */
    ssum_tab_t e; e.n = 0;
    row(a, 0, 20, 10, 5, 5, 3); row(a, 1, 21, 10, 5, 5, 3); row(a, 2, 22, 9, 5, 5, 3); row(a, 3, 23, 9, 5, 5, 3);
    ssum_rows(a, 4, &e); ssum_order(&e);
    expect(e.club[0] == CLUB(20) && e.club[1] == CLUB(21) && e.club[2] == CLUB(22), "a tie keeps the first table's order");
  }

  printf("\nThe world file's seasonsum lines\n");
  {
    const uint16_t v[] = { COL, COL_I, COL_II, 0,
                           MLS, 166, 167, 0,
                           300, 0, 0, 0,                  /* no half */
                           301, 301, 302, 0,              /* the total as its own half */
                           COL, COL_I, 0, 0 };            /* Colombia again */
    expect(fl26_swiss_seasonsum(v, 5) == 2, "Colombia and the MLS taken, three lines left out");
    const ssum_t* s = ssum_of(COL);
    expect(s && s->part[0] == COL_I && s->part[1] == COL_II && !s->part[2], "Colombia: 119 = 168 + 169");
    expect(ssum_of(MLS) && !ssum_of(300) && !ssum_of(301) && !ssum_of(COL_I), "no other id is a whole season");
    expect(fl26_swiss_seasonsum(0, 0) == 0 && !ssum_of(COL), "an empty list clears them");
    expect(fl26_swiss_seasonsum(0, 1) == -1, "a count without a list: refused");
    expect(fl26_swiss_seasonsum(v, 2) == 2, "taken again");
  }

  printf("\nNothing but the whole-season count keeps the total's table\n");
  restart();
  g_user_test = USER_A;
  go(2026, 10);
  expect(keep_final(COL, 360, abs_day()) == 0 && !final_of(COL), "keep_final leaves the total alone (New Year, July)");

  printf("\nA first season: no whole-season table yet\n");
  restart();
  go(2026, 176);
  keep_table(COL_I, 100, 20);                     /* the Apertura's table, kept at the July teardown */
  go(2026, 250);
  expect(cup_places(COL, 100, 4, "kept table"), "a cup of ours: the Apertura's kept table, as a place of 168 had it");
  go(2026, 300);
  expect(lib_places(COL, 100, 4), "the total's Libertadores places read the Apertura, as a place of 168 did");

  printf("\nThe season ends: the whole-season table kept in December\n");
  go(2026, 350);
  keep_table(COL, 500, 20);                       /* what ssum_keep keeps: club 500 first */
  state_store();
  go(2027, 0);
  expect(lib_places(COL, 500, 6), "1 January, the Libertadores filed: the whole season's 1st-6th");
  expect(lib_places(COL_I, 100, 2), "168's own places stay the Apertura's");
  go(2027, 41);
  expect(lib_places(COL, 500, 6), "day 41, its groups: the same");
  go(2027, 226);
  expect(cup_places(COL, 500, 4, "whole-season table"), "an August-May cup of ours in August: still the whole season's");
  expect(keep_final(COL, 360, abs_day()) == 0 && final_of(COL)->club[0] == CLUB(500),
         "the New Year teardown leaves the whole-season table as it is");

  printf("\nThe game quit, the save of 20 January 2027 loaded\n");
  restart();
  go(2027, 20);
  expect(lib_places(COL, 500, 6), "the whole-season table from the save folder's file");

  printf("\nA world without the line\n");
  fl26_swiss_seasonsum(0, 0);
  restart();
  go(2026, 176);
  keep_table(COL_I, 100, 20);
  go(2026, 300);
  expect(lib_places(COL_I, 100, 4), "168's places from its own table, as before");
  expect(!ssum_of(COL), "119 is an id like any other again");

  DeleteFileA(g_path_test);
  printf(fails ? "\n%d check(s) FAILED\n" : "\nall checks passed\n", fails);
  return fails ? 1 : 0;
}
