/* The league play-off's pure parts (0.2.5, the Liga FUTVE): the entries dealt into the groups in
   their order and the final ordered by the regular phase.

     zig cc -O2 -fno-sanitize=undefined test_ccup_league.c -o test_ccup_league.exe && test_ccup_league.exe

   (tools/test_futve_playoff.py builds and runs it.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST + the state stubs), as test_state_keep.c: the
   functions ccup_league_groups, ccup_entry_rank and ccup_league_final are called with synthetic
   fields and eranks. The cases:
     - 8 entries in the world file's order (1, 4, 5, 8, 2, 3, 6, 7) into two groups of four:
       A gets 1, 4, 5, 8 and B 2, 3, 6, 7;
     - 16 entries into four groups of four;
     - a field that does not divide into groups, or no groups at all: refused;
     - the final: the two winners, the better regular position first, whatever the group order;
     - a club that is not an entry sorts last, and a zero (an empty table row) is left out;
     - the same club in two groups is put in once (the final is then refused by the DLL);
     - four winners (a two-a-group play-off) sorted by position. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <string.h>

static int g_today_test = 0, g_year_now = 2026;
static uint32_t g_user_test = 0;
static char g_path_test[MAX_PATH + 64];
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return g_year_now * 365 + g_today_test; }
uint32_t state_test_user(void) { return g_user_test; }
const char* state_test_path(void) { return g_path_test; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

#define CLUB(i) ((uint32_t)(0x100u + (i)))

int main(void)
{
  setvbuf(stdout, NULL, _IONBF, 0);
  uint32_t field[16], out[CCUP_MAX_ENTRY], win[8];
  uint32_t grp[CCUP_MAX_GROUPS][8];
  unsigned per = 0;
  ccup_t cup;
  memset(&cup, 0, sizeof cup);

  /* 8 entries: the world file writes 1, 4, 5, 8 (group A), 2, 3, 6, 7 (group B) */
  {
    static const int pos[8] = { 1, 4, 5, 8, 2, 3, 6, 7 };
    for (int i = 0; i < 8; i++) { field[i] = CLUB(i); cup.erank[i] = (uint8_t)pos[i]; }
    int n = ccup_league_groups(field, 8, 2, grp, &per);
    expect(n == 2 && per == 4, "eight entries deal into two groups of four");
    expect(grp[0][0] == CLUB(0) && grp[0][1] == CLUB(1) && grp[0][2] == CLUB(2) && grp[0][3] == CLUB(3),
           "group A gets the first half of the entries (1, 4, 5, 8)");
    expect(grp[1][0] == CLUB(4) && grp[1][1] == CLUB(5) && grp[1][2] == CLUB(6) && grp[1][3] == CLUB(7),
           "group B gets the second half (2, 3, 6, 7)");
    expect(ccup_entry_rank(&cup, field, 8, CLUB(1)) == 4, "entry 1 is the 4th of the regular phase");
    expect(ccup_entry_rank(&cup, field, 8, CLUB(99)) == 256, "a club that is not an entry sorts last");
  }
  /* 16 entries into four groups */
  {
    for (int i = 0; i < 16; i++) { field[i] = CLUB(i); cup.erank[i] = (uint8_t)(i + 1); }
    int n = ccup_league_groups(field, 16, 4, grp, &per);
    expect(n == 4 && per == 4 && grp[3][0] == CLUB(12) && grp[3][3] == CLUB(15),
           "sixteen entries deal into four groups of four");
    expect(ccup_league_groups(field, 15, 4, grp, &per) == 0, "a field that does not divide is refused");
    expect(ccup_league_groups(field, 8, 0, grp, &per) == 0, "no group is refused");
    expect(ccup_league_groups(field, 4, 5, grp, &per) == 0, "more groups than clubs is refused");
  }
  /* the final: the better regular position first, whatever the group order */
  {
    static const int pos[8] = { 1, 4, 5, 8, 2, 3, 6, 7 };
    for (int i = 0; i < 8; i++) { field[i] = CLUB(i); cup.erank[i] = (uint8_t)pos[i]; }
    win[0] = CLUB(2);                 /* group A's winner came 5th */
    win[1] = CLUB(4);                 /* group B's winner came 2nd */
    int n = ccup_league_final(&cup, field, 8, win, 2, out);
    expect(n == 2 && out[0] == CLUB(4) && out[1] == CLUB(2),
           "the better placed club goes first (2nd before 5th)");
    win[0] = CLUB(4); win[1] = CLUB(2);
    n = ccup_league_final(&cup, field, 8, win, 2, out);
    expect(n == 2 && out[0] == CLUB(4), "the order of the groups does not matter");
    win[0] = CLUB(0); win[1] = CLUB(0);
    n = ccup_league_final(&cup, field, 8, win, 2, out);
    expect(n == 1 && out[0] == CLUB(0), "the same club in two groups is put in once");
    win[0] = 0; win[1] = CLUB(4);
    n = ccup_league_final(&cup, field, 8, win, 2, out);
    expect(n == 1 && out[0] == CLUB(4), "an empty table row (0) is left out");
    win[0] = CLUB(99); win[1] = CLUB(4);
    n = ccup_league_final(&cup, field, 8, win, 2, out);
    expect(n == 2 && out[0] == CLUB(4) && out[1] == CLUB(99), "a club that is not an entry sorts last");
    win[0] = CLUB(2); win[1] = CLUB(4); win[2] = CLUB(6); win[3] = CLUB(0);
    n = ccup_league_final(&cup, field, 8, win, 4, out);
    expect(n == 4 && out[0] == CLUB(0) && out[1] == CLUB(4) && out[2] == CLUB(2) && out[3] == CLUB(6),
           "four winners (a two-a-group play-off) sorted by regular position (1, 2, 5, 6)");
  }

  if (fails) { printf("%d check(s) failed\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
