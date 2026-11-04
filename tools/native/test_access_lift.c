/* B313 (pepponeee, 03.11.): a place the top-up gives goes to the next club of the league, and a
   club of that league already in a lower competition by its league position goes up to it.

     zig cc -O2 -fno-sanitize=undefined test_access_lift.c -o test_access_lift.exe && test_access_lift.exe

   (tools/test_access_lift.py builds and runs it.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST, FL26_STATE_TEST): last season's tables are kept
   in memory as the July teardown keeps them, the access list is the test's, access_build(0, 0)
   (no qualifying: 36 direct entrants each). The Premier League has places 1-5 in the Champions
   League, 6 in the Europa League and 7 in the Conference League, and the Europa League has one
   place no club of the list takes (pepponeee's recipe has no cup winner places):
     - the top-up gives it to England's 7th (Villa), who goes up from the Conference League, and
       the Conference League's place goes to the 8th (Brighton) in turn -- before, the 8th took
       the Europa League and the 7th stayed in the Conference League;
     - a club in the Conference League as its cup's winner, not by its league position, stays
       there: the Europa League's place goes to the next free position;
     - every club is on one list only. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

static int g_today_test = 200, g_year_now = 2027;
static char g_path_test[MAX_PATH + 64];
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return g_year_now * 365 + g_today_test; }
uint32_t state_test_user(void) { return 0; }
const char* state_test_path(void) { return g_path_test; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

#define CLUB(i) ((uint32_t)(i) << 14 | 0x1000)
#define CUP 300
/* the big five, then eleven other leagues; club 100 * (index + 1) + rank - 1 is a league's rank */
static const uint16_t REGS[16] = { R_ENG, R_ESP, R_ITA, R_GER, R_FRA, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70 };
static uint32_t club_at(int li, int rank) { return CLUB(100 * (li + 1) + rank - 1); }

/* FINAL_MAX rows: a rank past the table would go to the game's list (get_rec) */
static void keep_table(uint16_t reg, int first, int n)
{
  final_t* f = &g_final[g_nfinal++];
  f->reg = reg; f->n = (uint16_t)n; f->day = abs_day();
  for (int k = 0; k < n; k++) f->club[k] = CLUB(first + k);
}

static void place(uint16_t reg, int rank, int comp, uint16_t alt)
{
  access_t* a = &g_access_buf[g_naccess++];
  a->reg = reg; a->rank = (uint8_t)rank; a->comp = (uint8_t)comp; a->alt = alt;
}

static int where(uint32_t c)                         /* the competition c is in, -1 none, -2 twice */
{
  int at = -1;
  for (int k = 0; k < 3; k++)
    for (unsigned i = 0; i < g_nacc[k]; i++)
      if (g_acc[k][i] == c) at = at == -1 ? k : -2;
  return at;
}

static int each_once(void)
{
  for (int k = 0; k < 3; k++)
    for (unsigned i = 0; i < g_nacc[k]; i++)
      if (where(g_acc[k][i]) != k) return 0;
  return 1;
}

/* the list: the big five 1-5 and the others' champions in the Champions League (36); the others
   2-3 (four of them 7 too) and the big five 6-7 (England 6 only) in the Europa League (35, one
   place free); the others 4-6, the big five's 8th (England's 7th) and one more in the Conference League (36).
   cup: England's Conference League place is its cup's (winner Villa, next place the league's 8th) */
static void setup(int cup)
{
  memset(g_final, 0, sizeof g_final); g_nfinal = 0;
  memset(g_cupwin, 0, sizeof g_cupwin); g_ncupwin = 0;
  g_naccess = 0; g_access = g_access_buf;
  for (int li = 0; li < 16; li++) keep_table(REGS[li], 100 * (li + 1), FINAL_MAX);
  for (int li = 0; li < 5; li++) for (int r = 1; r <= 5; r++) place(REGS[li], r, UCL, 0);
  for (int li = 5; li < 16; li++) place(REGS[li], 1, UCL, 0);
  for (int li = 5; li < 16; li++) for (int r = 2; r <= 3; r++) place(REGS[li], r, UEL, 0);
  place(R_ENG, 6, UEL, 0);
  for (int li = 5; li < 9; li++) place(REGS[li], 7, UEL, 0);
  for (int li = 1; li < 5; li++) for (int r = 6; r <= 7; r++) place(REGS[li], r, UEL, 0);
  for (int li = 5; li < 15; li++) for (int r = 4; r <= 6; r++) place(REGS[li], r, UECL, 0);
  place(70, 4, UECL, 0);
  if (cup) {
    place(CUP, 0, UECL, R_ENG);
    cupwin_t* w = &g_cupwin[g_ncupwin++];
    w->reg = CUP; w->day = abs_day(); w->club = club_at(0, 7);
  } else place(R_ENG, 7, UECL, 0);
  for (int li = 1; li < 5; li++) place(REGS[li], 8, UECL, 0);
}

int main(void)
{
  snprintf(g_path_test, sizeof g_path_test, "%sfl26swiss-lift-test-%lu.bin", getenv("TEMP") ? getenv("TEMP") : ".",
           GetCurrentProcessId());
  setvbuf(stdout, NULL, _IONBF, 0);
  g_day_ticked = 1;                                  /* not a new career: no first-season list */
  abs_day();

  printf("\nThe Europa League's free place, England's 7th in the Conference League by its position\n");
  setup(0);
  access_build(0, 0);
  printf("  %u / %u / %u clubs\n", g_nacc[0], g_nacc[1], g_nacc[2]);
  expect(g_nacc[0] == FIELD && g_nacc[1] == FIELD && g_nacc[2] == FIELD, "36 clubs in each competition");
  expect(where(club_at(0, 7)) == UEL, "England's 7th goes up to the Europa League");
  expect(where(club_at(0, 8)) == UECL, "England's 8th takes the Conference League place it left");
  expect(where(club_at(0, 9)) == -1, "England's 9th is not in Europe");
  expect(each_once(), "every club on one list only");
  expect(strstr(g_log, "position 7 goes up from the UECL league phase to the UEL league phase") != 0, "the log says who went up");

  printf("\nThe same, England's Conference League place its cup's (won by its 7th)\n");
  g_log_len = 0; g_log[0] = 0;
  setup(1);
  access_build(0, 0);
  printf("  %u / %u / %u clubs\n", g_nacc[0], g_nacc[1], g_nacc[2]);
  expect(where(club_at(0, 7)) == UECL, "the cup winner stays in the Conference League");
  expect(where(club_at(0, 8)) == UEL, "the Europa League's place goes to England's 8th");
  expect(each_once(), "every club on one list only");
  expect(strstr(g_log, "goes up from") == 0, "nobody went up");

  if (fails) { printf("\n--- log ---\n%s\n%d check(s) FAILED\n", g_log, fails); return 1; }
  printf("\nall checks passed\n");
  return 0;
}
