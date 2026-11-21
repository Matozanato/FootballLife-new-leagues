/* FL27's wide Conference League (Prijedlog C with a Conference League Q1 of 62, mato 07.11.:
   "kvalifikacije za europu prosiriti ako je to moguce").

     zig cc -O2 -fno-sanitize=undefined test_uecl_wide.c -o test_uecl_wide.exe && test_uecl_wide.exe

   (tools/test_uecl_wide_native.py builds and runs it.) Exit code 1 on any failure.

   fl26swiss.c without the game, as test_uefa_c.c: a Prijedlog C world file and its `qround 12 1`
   line (qcw_world), the rounds' sizes UCL 32 / 32 / 16 / 16, UEL 16 / 16 / 32 / 32, UECL 62 / 62 /
   40 / 40 (a regulation's team count is 6 bits: 62 the most), new clubs 56 / 40 / 74 = 170, direct
   entrants 28 / 12 / 0, the access list (second season and a first one without the July rounds),
   the play-offs into the league phases 36 / 36 / 36, the UECL Q1's 31 winners and 31 losers kept
   in the state file as two records and read back after a restart, and FL26 / a Prijedlog C world
   without the line as before. */
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
#define NL 60                                         /* leagues: the big five, then 55 more */
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
/* the uefa lines a wide Conference League world gets (fl26world.c_places with CW_SIZE): direct
   28 / 20 / 20, qualifying Champions League 56, Europa League 32, Conference League 54 -- the
   UECL's 20 direct places past its none first, then 54 more for its 62 Q1 -- and two past that */
static void setup(void)
{
  memset(g_final, 0, sizeof g_final); g_nfinal = 0;
  memset(g_cupwin, 0, sizeof g_cupwin); g_ncupwin = 0;
  g_naccess = 0; g_access = g_access_buf; g_access_on = 1;
  memset(g_nq, 0, sizeof g_nq);
  for (int li = 0; li < NL; li++) keep_table(li);
  for (int li = 0; li < 5; li++) for (int r = 1; r <= 4; r++) place(li, r, UCL);
  for (int li = 5; li < 13; li++) place(li, 1, UCL);
  for (int li = 5; li < 13; li++) place(li, 2, UCLQ);
  for (int li = 13; li < 55; li++) place(li, 1, UCLQ);
  for (int li = 13; li < 19; li++) place(li, 2, UCLQ);
  for (int li = 0; li < 5; li++) for (int r = 5; r <= 6; r++) place(li, r, UEL);
  for (int li = 5; li < 15; li++) place(li, 3, UEL);
  for (int li = 15; li < 47; li++) place(li, 3, UELQ);
  for (int li = 0; li < 5; li++) place(li, 7, UECL);
  for (int li = 5; li < 20; li++) place(li, 4, UECL);
  for (int li = 20; li < 60; li++) place(li, 4, UECLQ);
  for (int li = 5; li < 21; li++) place(li, 5, UECLQ);     /* 14 more, then li 19 and 20: past the rooms */
}

static const uint16_t A_LINES[7][3] = { { 10, 3, 500 }, { 11, 3, 501 }, { 12, 3, 502 }, { 10, 2, 510 }, { 12, 2, 512 },
                                        { 10, 1, 520 }, { 12, 1, 522 } };
static const uint16_t C_LINES[10][3] = { { 10, 3, 500 }, { 10, 2, 510 }, { 10, 1, 520 },
                                         { 11, 0, 531 }, { 11, 3, 501 }, { 11, 2, 511 }, { 11, 1, 521 },
                                         { 12, 0, 532 }, { 12, 3, 502 }, { 12, 2, 512 } };
static int lines(const uint16_t (*L)[3], int n)
{
  uint16_t v[3 * 16];
  for (int i = 0; i < n; i++) memcpy(v + 3 * i, L[i], sizeof L[i]);
  return fl26_swiss_qrounds(v, n);
}
static unsigned sum_rooms(int mask)
{
  unsigned n = 0;
  for (int i = 0; i < NQR; i++) if (mask >> i & 1) n += q_room(mask, i);
  return n;
}
static int each_once(void)
{
  uint32_t all[3 * FIELD + NQR * Q_MAX]; unsigned n = 0;
  for (int k = 0; k < 3; k++) for (unsigned i = 0; i < g_nacc[k]; i++) all[n++] = g_acc[k][i];
  for (int i = 0; i < NQR; i++) for (unsigned j = 0; j < g_nq[i]; j++) all[n++] = g_q[i][j];
  for (unsigned i = 0; i < n; i++) for (unsigned j = i + 1; j < n; j++) if (all[i] == all[j]) return 0;
  return 1;
}
static void dump_lists(const char* tag, int mask)
{
  for (int i = 0; i < NQR; i++) {
    if (!(mask >> i & 1)) continue;
    printf("DUMP %s round %d reg %u n %u room %u up %d down %d fill %u:", tag, i, (unsigned)q_reg(i), q_n(i),
           q_room(mask, i), q_up(mask, i), q_down(mask, i), q_fill_from(mask, i));
    for (unsigned j = 0; j < g_nq[i]; j++) printf(" %08x", g_q[i][j]);
    printf("\n");
  }
  for (int c = 0; c < 3; c++) {
    printf("DUMP %s comp %d:", tag, c);
    for (unsigned j = 0; j < g_nacc[c]; j++) printf(" %08x", g_acc[c][j]);
    printf("\n");
  }
}

static const uint16_t W_LINES[11][3] = { { 10, 3, 500 }, { 10, 2, 510 }, { 10, 1, 520 },
                                         { 11, 0, 531 }, { 11, 3, 501 }, { 11, 2, 511 }, { 11, 1, 521 },
                                         { 12, 0, 532 }, { 12, 3, 502 }, { 12, 2, 512 }, { 12, 1, 522 } };
static const int WMASK = 0xfff;                      /* every round */

static void old_worlds(void)
{
  printf("\nA Prijedlog C world without the line, and FL26: as before\n");
  g_native_uefa = 1; g_test_year = 2026; g_qr_sy = -1;
  lines(C_LINES, 10);
  int m = 0x7ff & ~(1 << 11);
  expect(qc_world() && !qcw_world(), "Prijedlog C, not wide");
  expect(q_n(8) == 32 && q_n(5) == 32 && q_n(2) == 32 && sum_rooms(m) == 112, "UECL 32 / 32 / 32, 112 new clubs");
  setup();
  int ok = access_build(1, m);
  expect(ok && g_nacc[2] == 4, "4 Conference League direct entrants");
  g_native_uefa = 0; g_qr_sy = -1;
  lines(W_LINES, 11);
  expect(!qc_world() && !qcw_world() && !g_qreg[11], "FL26 leaves the line out");
  int six = 1;
  for (int i = 0; i < NQR; i++) six &= q_n(i) == 16;
  expect(six, "FL26: every round sixteen");
  g_native_uefa = 1;
}

static void wide_part(void)
{
  printf("\nFL27, wide Conference League: the world file\n");
  g_native_uefa = 1; g_test_year = 2026; g_qr_sy = -1;
  g_log_len = 0; g_log[0] = 0;
  int k = lines(W_LINES, 11);
  expect(k == 11, "all eleven lines taken");
  expect(qc_world() && qcw_world() && q_reg(11) == 522, "qcw_world: the Conference League Q1 is reg 522");
  expect(q1_world(0) && q1_world(1) && q1_world(2), "July first rounds: all three competitions");
  static const unsigned N[12] = { 16, 32, 40, 16, 32, 40, 32, 16, 62, 32, 16, 62 };
  int sz = 1;
  for (int i = 0; i < 12; i++) sz &= q_n(i) == N[i];
  expect(sz, "sizes: UCL 32 / 32 / 16 / 16, UEL 16 / 16 / 32 / 32, UECL 62 / 62 / 40 / 40");
  expect(q_n(11) <= Q_MAX && q_n(11) / 2 <= FINAL_MAX, "62: within Q_MAX, half within a state record");
  expect(q_tie_of(11, 30) == 522 + 31 * 1024 && q_added(522 + 31 * 1024) == 11 && q_added(512 + 31 * 1024) == 8
         && q_added(502 + 20 * 1024) == 5 && q_added(502 + 21 * 1024) < 0 && q_added(532 + 20 * 1024) == 2,
         "q_added: 31 ties of the 62s, 20 of the 40s");
  int m = WMASK;
  printf("  rooms:");
  for (int i = 0; i < NQR; i++) if (m >> i & 1) printf(" %d=%u", i, q_room(m, i));
  printf("\n");
  expect(q_room(m, 0) == 8 && q_room(m, 3) == 0 && q_room(m, 6) == 16 && q_room(m, 9) == 32, "UCL new clubs PO 8, Q3 0, Q2 16, Q1 32");
  expect(q_room(m, 1) == 8 && q_room(m, 4) == 8 && q_room(m, 7) == 8 && q_room(m, 10) == 16, "UEL new clubs PO 8, Q3 8, Q2 8, Q1 16");
  expect(q_room(m, 2) == 4 && q_room(m, 5) == 1 && q_room(m, 8) == 7 && q_room(m, 11) == 62, "UECL new clubs PO 4, Q3 1, Q2 7, Q1 62");
  expect(sum_rooms(m) == 170, "170 new qualifying clubs");
  expect(q_up(m, 11) == 8 && q_down(m, 11) == -2, "UECL Q1: winners UECL Q2, losers out");
  expect(q_down(m, 9) == 8 && q_down(m, 10) == 8 && q_down(m, 7) == 5 && q_down(m, 4) == 2,
         "the UCL / UEL losers into the UECL as in Prijedlog C");
  int full = 1;
  for (int i = 0; i < NQR; i++) {
    if (!(m >> i & 1)) continue;
    unsigned fed = 0;
    for (int j = 0; j < NQR; j++) if (j != i && (m >> j & 1) && (q_up(m, j) == i || q_down(m, j) == i)) fed += q_n(j) / 2;
    full &= q_room(m, i) + fed == q_n(i);
  }
  expect(full, "every round: its new clubs and those sent to it make its size");
  int days = 1;
  for (int y = 2026; y <= 2030; y++) {
    g_test_year = y; g_qr_sy = -1;
    uint32_t a = qr_day(3, 0), b = qr_day(3, 1);
    days &= a >= 186 && a <= 192 && b == a + 7 && b < 216 && q_fill_from(m, 8) >= 217 && q_fill_from(m, 11) <= 182;
  }
  expect(days, "2026-2030: the UECL Q1 on the two July Wednesdays, filled after the teardown; its Q2 after the build");
  g_test_year = 2026; g_qr_sy = -1;

  printf("\nFL27, wide Conference League: the access list, second season\n");
  setup();
  g_log_len = 0; g_log[0] = 0;
  int ok = access_build(1, m);
  unsigned tot = 0;
  printf("  %u / %u / %u direct; rounds:", g_nacc[0], g_nacc[1], g_nacc[2]);
  for (int i = 0; i < NQR; i++) if (m >> i & 1) { printf(" %d=%u", i, g_nq[i]); tot += g_nq[i]; }
  printf("\n");
  expect(ok && g_nacc[0] == 28 && g_nacc[1] == 12 && g_nacc[2] == 0, "28 / 12 / 0 direct entrants");
  int rooms = 1;
  for (int i = 0; i < NQR; i++) if (m >> i & 1) rooms &= g_nq[i] == q_room(m, i);
  expect(rooms && tot == 170, "every round has its new clubs: 170");
  int top = 0;
  for (int li = 0; li < 5; li++) top += has_club(g_q[2], g_nq[2], club_at(li, 7));
  expect(top == 4 && has_club(g_q[5], g_nq[5], club_at(4, 7)), "the UECL's strongest places nearest the league phase");
  expect(has_club(g_q[11], g_nq[11], club_at(18, 5)) && !has_club(g_q[11], g_nq[11], club_at(19, 5))
         && !has_club(g_q[11], g_nq[11], club_at(20, 5)), "the UECL Q1 takes 62, the two past it none");
  expect(each_once(), "every club on one list only");

  printf("\nFL27, wide Conference League: the play-offs into the league phases\n");
  for (int p = 0; p < NQ; p++)
    for (unsigned j = 0; j < q_n(p) / 2; j++) {
      g_qwin[p][j] = CLUB(70000 + 100 * p + j); g_qlose[p][j] = CLUB(80000 + 100 * p + j);
    }
  q_place(7);
  expect(g_nacc[0] == 36 && g_nacc[1] == 36 && g_nacc[2] == 36, "36 / 36 / 36");
  int uecl_w = 0, uecl_l = 0;
  for (unsigned j = 0; j < 36; j++) {
    uint32_t c = g_acc[2][j]; uecl_w += c >= CLUB(70200) && c < CLUB(70300); uecl_l += c >= CLUB(80100) && c < CLUB(80200);
  }
  expect(uecl_w == 20 && uecl_l == 16, "UECL: 20 play-off winners + 16 UEL play-off losers");

  printf("\nFL27, wide Conference League: a first season (no July rounds)\n");
  int m1 = m & ~(1 << 9 | 1 << 10 | 1 << 11);
  setup();
  g_log_len = 0; g_log[0] = 0;
  ok = access_build(1, m1);
  tot = 0;
  printf("  %u / %u / %u direct; rooms / clubs:", g_nacc[0], g_nacc[1], g_nacc[2]);
  for (int i = 0; i < NQR; i++) if (m1 >> i & 1) { printf(" %d=%u/%u", i, q_room(m1, i), g_nq[i]); tot += g_nq[i]; }
  printf("\n");
  expect(q_room(m1, 8) == 62 && q_room(m1, 5) == 1 && q_room(m1, 2) == 4, "the UECL Q2 takes all its 62 new");
  rooms = 1;
  for (int i = 0; i < NQR; i++) if (m1 >> i & 1) rooms &= g_nq[i] == q_room(m1, i);
  expect(rooms && tot == 139, "every round full: 139 (40 + 32 + 67; the weakest UECL places wait for July)");
  top = 0;
  for (int li = 0; li < 4; li++) top += has_club(g_q[2], g_nq[2], club_at(li, 7));
  expect(top == 4, "the UECL play-off: its own strongest places, not the spilled ones");
  expect(strstr(g_log, "24 qualifying place(s) into the Conference League's rounds") != 0, "the UCL's last 16 and the UEL's last 8 into the UECL Q2, logged");
  expect(each_once(), "every club on one list only");

  printf("\nFL27, wide Conference League: the UECL Q1's result kept, a restart\n");
  g_user_test = CLUB(9003);
  g_today_test = 196; g_year_now = 2027; abs_day();
  q1kept_t* K = &g_q1kept[2];
  K->gdate = game_date();
  for (int j = 0; j < 31; j++) { K->win[j] = club_at(20 + j, 4); K->lose[j] = club_at(20 + j, 5); }
  state_store();
  expect(q1_kept(2), "kept on day 196");
  memset(g_q1kept, 0, sizeof g_q1kept);
  g_year_off = 0; g_last_day = -1; g_timeline = 0;
  g_st_off = g_st_day = -0x7fffffff; g_st_user = 0; g_st_busy = 0; g_st_read_back = 0;
  g_today_test = 220; abs_day();
  expect(q1_kept(2) && g_q1kept[2].win[0] == club_at(20, 4) && g_q1kept[2].win[30] == club_at(50, 4)
         && g_q1kept[2].lose[0] == club_at(20, 5) && g_q1kept[2].lose[30] == club_at(50, 5),
         "read back after a restart: 31 winners, 31 losers (two records)");
  g_qmask = m; g_q_day = abs_day();
  int r = q_result(11);
  expect(r == 1 && g_qwin[11][30] == club_at(50, 4) && g_qlose[11][17] == club_at(37, 5), "q_result answers the kept result");
  g_native_uefa = 0;
  expect(!qcw_world() && !q1_kept(2), "FL26 has none of it");
  g_native_uefa = 1;
}

int main(void)
{
  snprintf(g_path_test, sizeof g_path_test, "%sfl26swiss-qcw-test-%lu.bin", getenv("TEMP") ? getenv("TEMP") : ".",
           GetCurrentProcessId());
  DeleteFileA(g_path_test);
  setvbuf(stdout, NULL, _IONBF, 0);
  g_day_ticked = 1;                                  /* not a new career: no first-season list */
  abs_day();
  old_worlds();
  wide_part();
  DeleteFileA(g_path_test);
  if (fails) { printf("\n--- log ---\n%s\n%d check(s) FAILED\n", g_log, fails); return 1; }
  printf("\nall checks passed\n");
  return 0;
}
