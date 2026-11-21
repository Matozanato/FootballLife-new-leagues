/* FL27's first qualifying round in July (mato 06.11., notes/uefa-q1-srpanj.md, "Prijedlog A").

     zig cc -O2 -fno-sanitize=undefined test_uefa_q1.c -o test_uefa_q1.exe && test_uefa_q1.exe

   (tools/test_uefa_q1_native.py builds and runs it, against this fl26swiss.c and against the one
   before the first qualifying round, and compares the FL26 part.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST, FL26_STATE_TEST): the world file's qround lines
   go through fl26_swiss_qrounds, the access list and last season's tables are the test's. The
   first part, "FL26", is printed as a dump that must be the same with the old source: the rounds'
   rooms and days, and the clubs access_build puts in each round, for a world of all nine August
   rounds -- the first qualifying round's lines in that world file are left out there. The rest
   needs the new source (NQS):
     - FL27 (g_native_uefa): the Champions League and the Conference League get a first round of 32
       in July, their second rounds 32 too; the rooms are UCL 8 / 0 / 16 / 32, UEL 0 / 0, UECL
       0 / 0 / 0 / 32: 88 new qualifying clubs;
     - the first round's losers go to the Conference League's second round, its winners to the
       Champions League's; the legs are two Wednesdays 6..20 July, before the build on day 216;
     - the access list's Europa League qualifying places go to the Conference League's first
       round (no Europa League round takes new clubs); every club on one list only;
     - a first season (no first round) has second rounds of 32 new clubs each;
     - the result kept the day after the second leg is written to the state file and read back
       after a restart, and not by a save of an earlier day nor by FL26. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

static int g_today_test = 150, g_year_now = 2027;
static uint32_t g_user_test = 0;
static char g_path_test[MAX_PATH + 64];
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int rcal_test_dayload(int d) { (void)d; return 0; }
int rcal_test_round(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return g_year_now * 365 + g_today_test; }
uint32_t state_test_user(void) { return g_user_test; }
const char* state_test_path(void) { return g_path_test; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

#define CLUB(i) ((uint32_t)(i) << 14 | 0x1000)
#define NL 55                                         /* leagues: the big five, then 50 more */
static uint16_t lreg(int li)
{
  static const uint16_t BIG[5] = { R_ENG, R_ESP, R_ITA, R_GER, R_FRA };
  return li < 5 ? BIG[li] : (uint16_t)(400 + li);
}
static uint32_t club_at(int li, int rank) { return CLUB(1000 * (li + 1) + rank); }
static void keep_table(int li)
{
  final_t* f = &g_final[g_nfinal++];
  f->reg = lreg(li); f->n = FINAL_MAX; f->day = abs_day();
  for (int k = 0; k < FINAL_MAX; k++) f->club[k] = club_at(li, k + 1);
}
static void place(int li, int rank, int comp)
{
  access_t* a = &g_access_buf[g_naccess++];
  a->reg = lreg(li); a->rank = (uint8_t)rank; a->comp = (uint8_t)comp; a->alt = 0;
}
/* direct places 28 / 20 / 20; Champions League qualifying 56, Europa League 16, Conference League 25 */
static void setup(void)
{
  memset(g_final, 0, sizeof g_final); g_nfinal = 0;
  memset(g_cupwin, 0, sizeof g_cupwin); g_ncupwin = 0;
  g_naccess = 0; g_access = g_access_buf; g_access_on = 1;
  memset(g_nq, 0, sizeof g_nq);                       /* a round off in this mask keeps no clubs of the last */
  for (int li = 0; li < NL; li++) keep_table(li);
  for (int li = 0; li < 5; li++) for (int r = 1; r <= 4; r++) place(li, r, UCL);
  for (int li = 5; li < 13; li++) place(li, 1, UCL);
  for (int li = 5; li < 13; li++) place(li, 2, UCLQ);
  for (int li = 13; li < NL; li++) place(li, 1, UCLQ);
  for (int li = 13; li < 19; li++) place(li, 2, UCLQ);
  for (int li = 0; li < 5; li++) for (int r = 5; r <= 6; r++) place(li, r, UEL);
  for (int li = 5; li < 15; li++) place(li, 3, UEL);
  for (int li = 15; li < 31; li++) place(li, 3, UELQ);
  for (int li = 0; li < 5; li++) place(li, 7, UECL);
  for (int li = 5; li < 20; li++) place(li, 4, UECL);
  for (int li = 31; li < NL; li++) place(li, 2, UECLQ);
  place(19, 5, UECLQ);
}

/* the world file's qround lines: all nine August rounds, and (q1) the two first rounds */
static int qrounds(int q1)
{
  uint16_t v[3 * 11]; int n = 0;
  for (int c = 0; c < 3; c++) {
    uint16_t* e = v + 3 * n++; e[0] = (uint16_t)(10 + c); e[1] = 3; e[2] = (uint16_t)(500 + c);
    e = v + 3 * n++; e[0] = (uint16_t)(10 + c); e[1] = 2; e[2] = (uint16_t)(510 + c);
  }
  if (q1) {
    uint16_t* e = v + 3 * n++; e[0] = 10; e[1] = 1; e[2] = 520;
    e = v + 3 * n++; e[0] = 12; e[1] = 1; e[2] = 522;
  }
  return fl26_swiss_qrounds(v, n);
}

static unsigned sum_rooms(int mask)
{
  unsigned n = 0;
  for (int i = 0; i < 9; i++) if (mask >> i & 1) n += q_room(mask, i);
#ifdef NQS
  for (int i = 9; i < NQR; i++) if (mask >> i & 1) n += q_room(mask, i);
#endif
  return n;
}

/* every club access_build placed, on one list or round only */
static int each_once(void)
{
  uint32_t all[3 * FIELD + 12 * 32]; unsigned n = 0;
  for (int k = 0; k < 3; k++) for (unsigned i = 0; i < g_nacc[k]; i++) all[n++] = g_acc[k][i];
  for (int i = 0; i < NQR; i++) for (unsigned j = 0; j < g_nq[i]; j++) all[n++] = g_q[i][j];
  for (unsigned i = 0; i < n; i++) for (unsigned j = i + 1; j < n; j++) if (all[i] == all[j]) return 0;
  return 1;
}

/* the FL26 dump: the same text from this source and from the one before the first round */
static void fl26_part(void)
{
  printf("\nFL26: a world file with all nine August rounds and two first rounds (FL27's)\n");
  g_native_uefa = 0;
  g_test_year = 2026;
  int k = qrounds(1);
  printf("DUMP qrounds taken %d\n", k);
  int mask = 0x1ff;
  for (int i = 0; i < 9; i++)
    printf("DUMP round %d reg %u room %u up %d down %d fill from %u\n", i, (unsigned)q_reg(i), q_room(mask, i),
           q_up(mask, i), q_down(mask, i), q_fill_from(mask, i));
  for (int y = 2026; y <= 2028; y++) {
    g_test_year = y; g_qr_sy = -1;
    printf("DUMP %d legs:", y);
    for (int s = 0; s < 3; s++) printf(" %u/%u", qr_day(s, 0), qr_day(s, 1));
    uint32_t ud[96]; int nu = uefa_days(ud, 96, 1);
    printf(" quals days %d, swiss %u\n", nu, swiss_day(0));
  }
  g_test_year = 2026; g_qr_sy = -1;
  printf("DUMP new qualifying clubs %u\n", sum_rooms(mask));
  setup();
  int ok = access_build(1, mask);
  printf("DUMP access_build %d: %u / %u / %u\n", ok, g_nacc[0], g_nacc[1], g_nacc[2]);
  for (int i = 0; i < 9; i++) {
    printf("DUMP round %d:", i);
    for (unsigned j = 0; j < g_nq[i]; j++) printf(" %08x", g_q[i][j]);
    printf("\n");
  }
  for (int c = 0; c < 3; c++) {
    printf("DUMP comp %d:", c);
    for (unsigned j = 0; j < g_nacc[c]; j++) printf(" %08x", g_acc[c][j]);
    printf("\n");
  }
#ifdef NQS
  expect(k == 6, "FL26 takes the six August rounds, not the first rounds");
  expect(!g_qreg[9] && !g_qreg[11] && !q1_world(0) && !q1_world(2), "no first qualifying round in FL26");
  expect(q_n(6) == 16 && q_n(8) == 16, "the second rounds stay sixteen clubs");
  expect(!qr_day(3, 0) && !qr_day(3, 1), "no July days");
  expect(sum_rooms(mask) == 64, "64 new qualifying clubs, as before");
  expect(each_once(), "every club on one list only");
#endif
}

#ifdef NQS
static const int Q1MASK = 1 << 0 | 1 << 1 | 1 << 2 | 1 << 3 | 1 << 4 | 1 << 5 | 1 << 6 | 1 << 8 | 1 << 9 | 1 << 11;
static int bits(const int* r, int n) { int m = 0; for (int i = 0; i < n; i++) m |= 1 << r[i]; return m; }

static void fl27_part(void)
{
  printf("\nFL27: the world builder's rounds with the first qualifying round\n");
  g_native_uefa = 1;
  g_test_year = 2026; g_qr_sy = -1;
  /* Prijedlog A: UCL Q1 Q2 Q3 PO, UEL Q3 PO, UECL Q1 Q2 Q3 PO -- no UEL second round */
  uint16_t v[3 * 10]; int n = 0;
  static const uint16_t L[10][3] = { { 10, 3, 500 }, { 11, 3, 501 }, { 12, 3, 502 }, { 10, 2, 510 }, { 12, 2, 512 },
                                     { 10, 1, 520 }, { 12, 1, 522 } };
  for (int i = 0; i < 7; i++) { memcpy(v + 3 * n, L[i], sizeof L[i]); n++; }
  expect(fl26_swiss_qrounds(v, n) == 7, "all seven rounds taken");
  expect(q1_world(0) && !q1_world(1) && q1_world(2), "first rounds: Champions League and Conference League");
  expect(q_n(9) == 32 && q_n(11) == 32 && q_n(6) == 32 && q_n(8) == 32 && q_n(3) == 16 && q_n(0) == 16,
         "first and second rounds 32 clubs, the third rounds and play-offs 16");
  int m = Q1MASK;
  printf("  rooms:");
  for (int i = 0; i < NQR; i++) if (m >> i & 1) printf(" %d=%u", i, q_room(m, i));
  printf("\n");
  expect(q_room(m, 0) == 8 && q_room(m, 3) == 0 && q_room(m, 6) == 16 && q_room(m, 9) == 32, "UCL new clubs 8 / 0 / 16 / 32");
  expect(q_room(m, 1) == 0 && q_room(m, 4) == 0, "UEL 0 / 0 (the Champions League's losers)");
  expect(q_room(m, 2) == 0 && q_room(m, 5) == 0 && q_room(m, 8) == 0 && q_room(m, 11) == 32, "UECL 0 / 0 / 0 / 32");
  expect(sum_rooms(m) == 88, "88 new qualifying clubs (64 before)");
  expect(q_up(m, 9) == 6 && q_down(m, 9) == 8, "UCL Q1: winners to UCL Q2, losers to UECL Q2");
  expect(q_down(m, 6) == 4 && q_down(m, 3) == 1 && q_up(m, 11) == 8 && q_down(m, 11) == -2, "the rest as UEFA's");
  for (int y = 2026; y <= 2030; y++) {
    g_test_year = y; g_qr_sy = -1;
    uint32_t a = qr_day(3, 0), b = qr_day(3, 1);
    char buf[2][40];
    printf("  %d: first round %s and %s, second round %u/%u, play-off %u/%u\n", y, dstr(a, buf[0], 40), dstr(b, buf[1], 40),
           qr_day(2, 0), qr_day(2, 1), qr_day(0, 0), qr_day(0, 1));
    expect(a >= 186 && a <= 192 && b == a + 7 && wday_in(a, y) == 2 && wday_in(b, y) == 2 && b < 216,
           "two Wednesdays 6..19 July, before the build on day 216");
    expect(q_fill_from(m, 6) >= 217 && q_fill_from(m, 8) >= 217, "the second rounds are filled after the build");
    uint32_t ud[96]; int nu = uefa_days(ud, 96, 1), has = 0;
    for (int i = 0; i < nu; i++) if (ud[i] == a || ud[i] == b) has++;
    expect(has == 2, "the July days are European days (busy for the leagues that feed Europe)");
  }
  g_test_year = 2026; g_qr_sy = -1;

  printf("\nFL27: the access list into the rounds, second season (with the first round)\n");
  setup();
  g_log_len = 0; g_log[0] = 0;
  int ok = access_build(1, m);
  printf("  %u / %u / %u direct; rounds:", g_nacc[0], g_nacc[1], g_nacc[2]);
  unsigned tot = 0;
  for (int i = 0; i < NQR; i++) if (m >> i & 1) { printf(" %d=%u", i, g_nq[i]); tot += g_nq[i]; }
  printf("\n");
  expect(ok && g_nacc[0] == 28 && g_nacc[1] == 20 && g_nacc[2] == 20, "28 / 20 / 20 direct entrants");
  expect(g_nq[0] == 8 && g_nq[6] == 16 && g_nq[9] == 32 && g_nq[11] == 32 && tot == 88, "PO 8, Q2 16, UCL Q1 32, UECL Q1 32: 88");
  int el = 0, cl = 0;
  for (int li = 15; li < 31; li++) el += has_club(g_q[11], g_nq[11], club_at(li, 3));
  for (int li = 31; li < 47; li++) cl += has_club(g_q[11], g_nq[11], club_at(li, 2));
  expect(el == 16 && cl == 16, "UECL Q1: the 16 Europa League qualifying places, then 16 of the Conference League's");
  expect(has_club(g_q[9], g_nq[9], club_at(54, 1)) && has_club(g_q[9], g_nq[9], club_at(29, 1)) && !has_club(g_q[9], g_nq[9], club_at(28, 1)),
         "UCL Q1: the weakest champions (the strongest in the rounds nearer the league phase)");
  expect(each_once(), "every club on one list only");

  printf("\nFL27: a first season (4 August: no first round)\n");
  int m1 = m & ~(1 << 9 | 1 << 11);
  setup();
  ok = access_build(1, m1);
  printf("  rounds:");
  tot = 0;
  for (int i = 0; i < NQR; i++) if (m1 >> i & 1) { printf(" %d=%u", i, g_nq[i]); tot += g_nq[i]; }
  printf("\n");
  expect(ok && q_room(m1, 6) == 32 && q_room(m1, 8) == 32 && g_nq[6] == 32 && g_nq[8] == 32 && g_nq[0] == 8,
         "the second rounds take 32 new clubs each, the play-off 8");
  expect(each_once(), "every club on one list only");
  expect(sum_rooms(bits((const int[]){ 0, 1, 2, 3, 4, 5, 6, 8 }, 8)) == 72, "72 new qualifying clubs in a first summer");

  printf("\nFL27: the first round's result kept, a restart, a save of an earlier day\n");
  g_user_test = CLUB(9001);
  g_today_test = 196; g_year_now = 2027; abs_day();
  for (int k = 0; k < 16; k++) { g_qwin[9][k] = club_at(40 + k % 15, 1); g_qlose[9][k] = club_at(13 + k, 1); }
  q1kept_t* K = &g_q1kept[0];
  K->gdate = game_date();
  for (int k = 0; k < 16; k++) { K->win[k] = g_qwin[9][k]; K->lose[k] = g_qlose[9][k]; }
  state_store();
  expect(q1_kept(0), "kept on day 196");
  /* the game quit and started again: the DLL's memory gone */
  memset(g_q1kept, 0, sizeof g_q1kept);
  g_year_off = 0; g_last_day = -1; g_timeline = 0;
  g_st_off = g_st_day = -0x7fffffff; g_st_user = 0; g_st_busy = 0; g_st_read_back = 0;
  g_today_test = 220; abs_day();
  expect(q1_kept(0) && g_q1kept[0].win[3] == club_at(43, 1) && g_q1kept[0].lose[15] == club_at(28, 1),
         "read back from the state file after a restart (day 220)");
  expect(strstr(g_log, "first qualifying round result(s)") != 0, "the log says it was read back");
  g_qmask = Q1MASK; g_q_day = abs_day();           /* q_dest: the summer's rounds (no game to ask) */
  int r = q_result(9);
  expect(r == 1 && g_qwin[9][5] == club_at(45, 1) && g_qlose[9][0] == club_at(13, 1), "q_result answers the kept result");
  memset(g_q1kept, 0, sizeof g_q1kept);
  g_year_off = 0; g_last_day = -1; g_timeline = 0;
  g_st_off = g_st_day = -0x7fffffff; g_st_user = 0;
  g_today_test = 190; abs_day();
  expect(!q1_kept(0), "a save of 10 July (before the second leg) does not take it");
  g_today_test = 200; g_year_now = 2028; abs_day();
  expect(!q1_kept(0), "nor the next summer");
  g_native_uefa = 0;
  g_year_now = 2027; g_today_test = 220;
  g_st_off = g_st_day = -0x7fffffff; g_st_user = 0;
  expect(!q1_kept(0), "nor FL26");
  g_native_uefa = 1;
}
#endif

int main(void)
{
  snprintf(g_path_test, sizeof g_path_test, "%sfl26swiss-q1-test-%lu.bin", getenv("TEMP") ? getenv("TEMP") : ".",
           GetCurrentProcessId());
  DeleteFileA(g_path_test);
  setvbuf(stdout, NULL, _IONBF, 0);
  g_day_ticked = 1;                                  /* not a new career: no first-season list */
  abs_day();
  fl26_part();
#ifdef NQS
  fl27_part();
#endif
  DeleteFileA(g_path_test);
  if (fails) { printf("\n--- log ---\n%s\n%d check(s) FAILED\n", g_log, fails); return 1; }
  printf("\nall checks passed\n");
  return 0;
}
