/* B463 (Luka 13.11., mato 16.11.: "tjedan dana razmaka"): FL27's August qualifying rounds, the
   second leg a week after the first where it fits.

     zig cc -O2 -fno-sanitize=undefined -w test_b463_qdays.c -o test_b463_qdays.exe && test_b463_qdays.exe

   (tools/test_b463_qdays.py builds and runs it.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST, FL26_STATE_TEST), the world file's qround lines
   of all nine August rounds and FL27's two July first rounds. For every season 2026..2060 of FL27
   (g_native_uefa), the six August legs (qr_day) must:
     - lie between 218 (the season's build is day 216, 217 the first fill day) and 244, six days
       before FL27's own league phase (day 250, FL27_LP_DAY), in order;
     - be on a Tuesday, Wednesday or Thursday;
     - have each round's second leg 5..7 days after its first (two until B463), a week in the
       second qualifying round and the play-off of 2026..2028 but 2026's play-off (6 days: 2
       September is the last day), five in the third (the exceptions, printed every year);
     - leave a club two days at least between any two of its matches across the rounds, the July
       round included, and a fill day between a round's second leg and the next round's first
       (q_fill_from);
     - fill each round after the second leg the round before had until B463 (a save of then,
       its rounds dated the old way, is not filled before they are over);
     - leave the leagues at least as many weekend days in August as the old layout (busy_days:
       three days clear of every qualifying day);
   the July round keeps its two Wednesdays, the league phases' first matchday (swiss_day) and the
   national cups' first round (natcup_day) stay where they were. FL26 is the same as before
   (tools/test_uefa_q1_native.py compares its dump with the source before the July round; here
   its six weeks are checked again: one leg a week, a week apart). */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

static int g_today_test = 220, g_year_now = 2026;
static char g_path_test[MAX_PATH + 64];
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return g_year_now * 365 + g_today_test; }
uint32_t state_test_user(void) { return 0; }
const char* state_test_path(void) { return g_path_test; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  if (!ok) { printf("  FAIL  %s\n", what); fails++; }
}
static void expectf(int ok, const char* what, int y)
{
  if (!ok) { printf("  FAIL  %d: %s\n", y, what); fails++; }
}

static int qrounds(void)
{
  uint16_t v[3 * 11]; int n = 0;
  for (int c = 0; c < 3; c++) {
    uint16_t* e = v + 3 * n++; e[0] = (uint16_t)(10 + c); e[1] = 3; e[2] = (uint16_t)(500 + c);
    e = v + 3 * n++; e[0] = (uint16_t)(10 + c); e[1] = 2; e[2] = (uint16_t)(510 + c);
  }
  uint16_t* e = v + 3 * n++; e[0] = 10; e[1] = 1; e[2] = 520;
  e = v + 3 * n++; e[0] = 12; e[1] = 1; e[2] = 522;
  return fl26_swiss_qrounds(v, n);
}

/* weekend days 216..250 three days clear of every day in d[0..n) (busy_days, BZ_QUAL) */
static int free_weekend(int sy, const uint32_t* d, int n)
{
  int k = 0;
  for (uint32_t x = 216; x <= 250; x++) {
    if (wday_in(x, sy) < 5) continue;
    int ok = 1;
    for (int i = 0; i < n; i++) if ((x > d[i] ? x - d[i] : d[i] - x) < 3) ok = 0;
    k += ok;
  }
  return k;
}

static const char* const WD[7] = { "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun" };
static const char* const RN[3] = { "PO", "Q3", "Q2" };

static void fl27_part(void)
{
  printf("FL27: the August rounds, seasons 2026..2060\n");
  g_native_uefa = 1; g_test_year = 2026; g_qr_sy = -1;
  expect(qrounds() == 8, "all eight rounds taken (six August, two July)");
  expect(q1_world(0) && q1_world(2), "July first rounds: Champions League and Conference League");
  const int mask = 0x1ff | 1 << 9 | 1 << 11;
  int week[3] = { 0, 0, 0 }, five = 0;
  for (int y = 2026; y <= 2060; y++) {
    g_test_year = y; g_qr_sy = -1;
    uint32_t L[6];                                   /* Q2 first, second; Q3 ...; play-off ... */
    for (int st = 2, j = 0; st >= 0; st--, j += 2) { L[j] = qr_day(st, 0); L[j + 1] = qr_day(st, 1); }
    int g[3] = { (int)(L[1] - L[0]), (int)(L[3] - L[2]), (int)(L[5] - L[4]) };
    if (y <= 2028) {
      char b[6][24];
      printf("  %d:", y);
      for (int st = 2, j = 0; st >= 0; st--, j += 2)
        printf("  %s %s %u -> %s %u (%d days)", RN[st], WD[wday_in(L[j], y)], L[j], WD[wday_in(L[j + 1], y)], L[j + 1], g[j / 2]);
      printf("\n          ");
      for (int i = 0; i < 6; i++) printf(" %s", dstr(L[i], b[i], sizeof b[i]));
      printf("\n");
    }
    else printf("%s %d: %d/%d/%d%s", (y - 2029) % 6 ? "" : "   days apart (Q2/Q3/PO)", y, g[0], g[1], g[2],
                (y - 2029) % 6 == 5 || y == 2060 ? "\n" : "");
    expectf(L[0] >= 218 && L[5] + 6 <= FL27_LP_DAY, "between 218 and six days before their league phase", y);
    int ord = 1, mid = 1, gapok = 1;
    for (int i = 0; i < 6; i++) { if (i && L[i] <= L[i - 1]) ord = 0; if (wday_in(L[i], y) < 1 || wday_in(L[i], y) > 3) mid = 0; }
    for (int i = 1; i < 6; i++) if (L[i] - L[i - 1] < 2) gapok = 0;
    expectf(ord, "the legs in order", y);
    expectf(mid, "every leg on a Tuesday, Wednesday or Thursday", y);
    expectf(gapok, "two days at least between a club's two matches", y);
    expectf(g[0] >= 5 && g[1] >= 5 && g[2] >= 5 && g[0] <= 7 && g[1] <= 7 && g[2] <= 7, "each round's legs 5..7 days apart", y);
    expectf(g[0] == 7 || g[1] == 7 || g[2] == 7, "at least one round a week apart", y);
    for (int r = 0; r < 3; r++) { week[r] += g[r] == 7; five += g[r] == 5; }
    if (y >= 2027 && y <= 2028) expectf(g[0] == 7 && g[1] == 5 && g[2] == 7, "Q2 a week, Q3 five days, play-off a week", y);
    if (y == 2026) expectf(L[0] == 222 && L[1] == 229 && L[2] == 231 && L[3] == 236 && L[4] == 238 && L[5] == 244,
                           "2026: Q2 11/18 August, Q3 20/25, play-off 27 August / 2 September", y);
    /* the July round: two Wednesdays before the build, and two days at least before the August */
    uint32_t a = qr_day(3, 0), b = qr_day(3, 1);
    expectf(a >= 186 && a <= 192 && b == a + 7 && wday_in(a, y) == 2 && b < 216 && L[0] >= b + 2, "the July round as before", y);
    /* the fill days: the day after the round before's second leg, before the round's first leg,
       and after the second leg that round had until B463 */
    uint32_t O[3][2]; qr_fl27_old(y, O);    /* until B463: Wednesday and Friday, three weeks */
    for (int c = 0; c < 3; c++) {
      uint32_t f3 = q_fill_from(mask, 3 + c), fp = q_fill_from(mask, c), f2 = q_fill_from(mask, 6 + c);
      expectf(f2 >= 217 && f2 < L[0], "the second qualifying round filled after the build, before its first leg", y);
      expectf(f3 == L[1] + 1 && f3 < L[2], "the third qualifying round filled between", y);
      expectf(fp == L[3] + 1 && fp < L[4], "the play-off filled between", y);
      expectf(f3 > O[2][1] && fp > O[1][1], "filled after the old layout's second legs (a save of then)", y);
    }
    /* the leagues: weekend days clear of the qualifying, no fewer than before */
    uint32_t od[6] = { O[2][0], O[2][1], O[1][0], O[1][1], O[0][0], O[0][1] };
    int fn = free_weekend(y, L, 6), fo = free_weekend(y, od, 6);
    if (y <= 2028) printf("          weekend days in 216..250 clear for a league in Europe: %d (until B463: %d)\n", fn, fo);
    expectf(fn >= fo, "no fewer weekend days for the leagues than before", y);
    expectf(swiss_day(0) == eday(SWISS_DAYS[0]) && swiss_day(0) >= L[5] + 6, "the first league-phase matchday unmoved", y);
    expectf(natcup_day(0) >= 252 && natcup_clear(natcup_day(0)) && natcup_clear(natcup_day(1)), "the national cups' first round clear", y);
    uint32_t ud[96]; int nu = uefa_days(ud, 96, 1), has = 0;
    for (int i = 0; i < nu; i++) for (int k = 0; k < 6; k++) if (ud[i] == L[k]) { has++; break; }
    expectf(has == 6, "the six August days are the leagues' busy days (uefa_days)", y);
  }
  printf("  2026..2060: a week apart in %d / %d / %d seasons of 35 (Q2 / Q3 / play-off), five days %d times\n",
         week[2], week[1], week[0], five);
}

static void fl26_part(void)
{
  printf("FL26: six weeks, one leg a week, as before\n");
  g_native_uefa = 0;
  for (int y = 2025; y <= 2030; y++) {
    g_test_year = y; g_qr_sy = -1;
    uint32_t L[6];
    for (int st = 2, j = 0; st >= 0; st--, j += 2) { L[j] = qr_day(st, 0); L[j + 1] = qr_day(st, 1); }
    if (y <= 2027) printf("  %d: %u/%u %u/%u %u/%u\n", y, L[0], L[1], L[2], L[3], L[4], L[5]);
    int ok = 1;
    for (int i = 1; i < 6; i++) if (L[i] < L[i - 1] + 5) ok = 0;
    for (int r = 0; r < 3; r++) if (L[2 * r + 1] - L[2 * r] < 6 || L[2 * r + 1] - L[2 * r] > 8) ok = 0;
    expectf(ok, "one leg a week, each round's legs a week apart (6..8 days)", y);
  }
}

int main(void)
{
  snprintf(g_path_test, sizeof g_path_test, "%sfl26swiss-b463-test-%lu.bin", getenv("TEMP") ? getenv("TEMP") : ".",
           GetCurrentProcessId());
  DeleteFileA(g_path_test);
  setvbuf(stdout, NULL, _IONBF, 0);
  g_day_ticked = 1;
  abs_day();
  fl27_part();
  fl26_part();
  DeleteFileA(g_path_test);
  if (fails) { printf("\n%d check(s) FAILED\n", fails); return 1; }
  printf("\nall checks passed\n");
  return 0;
}
