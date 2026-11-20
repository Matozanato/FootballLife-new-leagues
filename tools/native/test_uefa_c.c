/* FL27's UEFA qualifying, Prijedlog C (mato 07.11., notes/uefa-q1-srpanj.md).

     zig cc -O2 -fno-sanitize=undefined test_uefa_c.c -o test_uefa_c.exe && test_uefa_c.exe

   (tools/test_uefa_c_native.py builds and runs it, against this fl26swiss.c and against the one
   before Prijedlog C, and compares the DUMP lines.) Exit code 1 on any failure.

   fl26swiss.c without the game (FL26_RCAL_TEST, FL26_STATE_TEST), as test_uefa_q1.c. The DUMP
   part must print the same with the source before Prijedlog C: FL26 with Prijedlog C's world file
   (its play-off lines and July rounds left out), and FL27 with Prijedlog A's world file. The rest
   needs FL26_PRIJEDLOG_C:
     - the world file's `qround 11 0` / `qround 12 0` lines: the Europa and Conference League's
       August play-offs of 32, regulations of their own (188 / 189 stay February's), FL27 only,
       both or neither;
     - the rounds' sizes UCL 32 / 32 / 16 / 16, UEL 16 / 16 / 32 / 32, UECL 32 / 32 / 32, new clubs
       56 / 40 / 16 = 112, direct entrants 28 / 12 / 4; the Champions League Q1 losers to the
       Conference League Q2, the Europa League Q1 losers there too;
     - the access list into them, second season (every club on one list) and a first season (no
       July rounds: the places past the grown second rounds into the Conference League's);
     - the play-offs' winners and losers into the league phases: 36 / 36 / 36;
     - the Europa League Q1's result kept in the state file and read back after a restart. */
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
/* the uefa lines a Prijedlog C world gets (fl26world.c_places): direct 28 / 20 / 20, qualifying
   Champions League 56, Europa League 32 (with the Conference League's that moved up), Conference
   League 4 (past its room: none get in) */
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
  for (int li = 55; li < 59; li++) place(li, 1, UECLQ);
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
    /* FL27's fill days follow its August days, which B463 (16.11.) changed: compared in FL26 only */
    printf("DUMP %s round %d reg %u n %u room %u up %d down %d fill %u:", tag, i, (unsigned)q_reg(i), q_n(i),
           q_room(mask, i), q_up(mask, i), q_down(mask, i), g_native_uefa ? 0u : q_fill_from(mask, i));
    for (unsigned j = 0; j < g_nq[i]; j++) printf(" %08x", g_q[i][j]);
    printf("\n");
  }
  for (int c = 0; c < 3; c++) {
    printf("DUMP %s comp %d:", tag, c);
    for (unsigned j = 0; j < g_nacc[c]; j++) printf(" %08x", g_acc[c][j]);
    printf("\n");
  }
}

/* the DUMP part: the same with the source before Prijedlog C */
static void same_part(void)
{
  printf("\nFL26 with a Prijedlog C world file; FL27 with a Prijedlog A one (DUMP: as before)\n");
  g_native_uefa = 0; g_test_year = 2026; g_qr_sy = -1;
  int k = lines(C_LINES, 10);
  int mask = 0;
  for (int i = 0; i < NQR; i++) if (q_reg(i) && (i < NQ || g_qreg[i])) mask |= 1 << i;
  printf("DUMP FL26 qrounds taken %d mask %x legs %u/%u %u/%u %u/%u\n", k, mask, qr_day(0, 0), qr_day(0, 1),
         qr_day(1, 0), qr_day(1, 1), qr_day(2, 0), qr_day(2, 1));
  setup();
  int ok = access_build(1, mask);
  printf("DUMP FL26 access_build %d: %u / %u / %u\n", ok, g_nacc[0], g_nacc[1], g_nacc[2]);
  dump_lists("FL26", mask);

  g_native_uefa = 1; g_qr_sy = -1;
  k = lines(A_LINES, 7);
  int am = 1 << 0 | 1 << 1 | 1 << 2 | 1 << 3 | 1 << 4 | 1 << 5 | 1 << 6 | 1 << 8 | 1 << 9 | 1 << 11;
  /* the July legs only: the August ones are B463's (16.11.) */
  printf("DUMP A qrounds taken %d legs %u/%u\n", k, qr_day(3, 0), qr_day(3, 1));
  printf("  A: second qualifying round %u/%u\n", qr_day(2, 0), qr_day(2, 1));
  setup();
  ok = access_build(1, am);
  printf("DUMP A access_build %d: %u / %u / %u\n", ok, g_nacc[0], g_nacc[1], g_nacc[2]);
  dump_lists("A", am);
  setup();
  int a1 = am & ~(1 << 9 | 1 << 11);
  ok = access_build(1, a1);
  printf("DUMP A first season %d: %u / %u / %u\n", ok, g_nacc[0], g_nacc[1], g_nacc[2]);
  dump_lists("A1", a1);
#ifdef FL26_PRIJEDLOG_C
  expect(!qc_world() && !g_qreg[1] && !g_qreg[2] && q_reg(1) == UEL_PO && q_reg(2) == UECL_PO, "A: 188 / 189 play the play-offs");
  g_native_uefa = 0; lines(C_LINES, 10);
  expect(!qc_world() && !g_qreg[1] && !g_qreg[2] && q_reg(1) == UEL_PO && q_reg(2) == UECL_PO && !g_qreg[9] && !g_qreg[10],
         "FL26 leaves Prijedlog C's play-off lines and July rounds out: 188 / 189 as ever");
  for (int i = 0; i < NQR; i++) if (q_n(i) != 16) { expect(0, "FL26: every round sixteen"); break; }
  expect(q_added(531) < 0 && q_added(532 + 1024) < 0, "FL26: regs 531 / 532 are none of ours");
#endif
}

#ifdef FL26_PRIJEDLOG_C
static const int CMASK = 0x7ff & ~(1 << 11);        /* every round but a Conference League Q1 */

static void c_part(void)
{
  printf("\nFL27, Prijedlog C: the world file\n");
  g_native_uefa = 1; g_test_year = 2026; g_qr_sy = -1;
  g_log_len = 0; g_log[0] = 0;
  int k = lines(C_LINES, 10);
  expect(k == 10, "all ten lines taken (eight rounds, two play-offs)");
  expect(qc_world() && q_reg(0) == 2 && q_reg(1) == 531 && q_reg(2) == 532, "the play-offs: reg 2, then the world's 531 and 532");
  expect(strstr(g_log, "play-offs of 32 are regs 531 and 532") != 0, "the log names them");
  expect(q1_world(0) && q1_world(1) && !q1_world(2), "July first rounds: Champions League and Europa League");
  static const unsigned N[11] = { 16, 32, 32, 16, 32, 32, 32, 16, 32, 32, 16 };
  int sz = 1;
  for (int i = 0; i < 11; i++) sz &= q_n(i) == N[i];
  expect(sz, "sizes: UCL PO 16, Q3 16, Q2 32, Q1 32; UEL PO 32, Q3 32, Q2 16, Q1 16; UECL PO 32, Q3 32, Q2 32");
  expect(q_added(531) == 1 && q_added(531 + 16 * 1024) == 1 && q_added(531 + 17 * 1024) < 0 && q_added(532 + 1024) == 2
         && q_added(UEL_PO) < 0 && q_added(2) < 0, "q_added: the play-offs and their sixteen ties, not 188 nor reg 2");
  expect(q_tie_of(1, 15) == 531 + 16 * 1024 && q_tie_of(2, 0) == 532 + 1024, "their ties at reg + 1024 * k");
  int m = CMASK;
  printf("  rooms:");
  for (int i = 0; i < NQR; i++) if (m >> i & 1) printf(" %d=%u", i, q_room(m, i));
  printf("\n");
  expect(q_room(m, 0) == 8 && q_room(m, 3) == 0 && q_room(m, 6) == 16 && q_room(m, 9) == 32, "UCL new clubs PO 8, Q3 0, Q2 16, Q1 32");
  expect(q_room(m, 1) == 8 && q_room(m, 4) == 8 && q_room(m, 7) == 8 && q_room(m, 10) == 16, "UEL new clubs PO 8, Q3 8, Q2 8, Q1 16");
  expect(q_room(m, 2) == 0 && q_room(m, 5) == 8 && q_room(m, 8) == 8, "UECL new clubs PO 0, Q3 8, Q2 8");
  expect(sum_rooms(m) == 112, "112 new qualifying clubs");
  expect(q_up(m, 9) == 6 && q_down(m, 9) == 8, "UCL Q1: winners UCL Q2, losers UECL Q2");
  expect(q_up(m, 6) == 3 && q_down(m, 6) == 4, "UCL Q2: winners UCL Q3, losers UEL Q3");
  expect(q_up(m, 3) == 0 && q_down(m, 3) == 1, "UCL Q3: winners UCL PO, losers UEL PO");
  expect(q_up(m, 0) == -1 && q_down(m, 0) == -1, "UCL PO: league phase, losers UEL league phase");
  expect(q_up(m, 10) == 7 && q_down(m, 10) == 8, "UEL Q1: winners UEL Q2, losers UECL Q2");
  expect(q_up(m, 7) == 4 && q_down(m, 7) == 5, "UEL Q2: winners UEL Q3, losers UECL Q3");
  expect(q_up(m, 4) == 1 && q_down(m, 4) == 2, "UEL Q3: winners UEL PO, losers UECL PO");
  expect(q_up(m, 1) == -1 && q_down(m, 1) == -1, "UEL PO: league phase, losers UECL league phase");
  expect(q_up(m, 8) == 5 && q_down(m, 8) == -2 && q_up(m, 5) == 2 && q_down(m, 5) == -2 && q_down(m, 2) == -2,
         "UECL Q2 -> Q3 -> PO, losers out");
  int full = 1;
  for (int i = 0; i < NQR; i++) {
    if (!(m >> i & 1)) continue;
    unsigned fed = 0;
    for (int j = 0; j < NQR; j++) if (j != i && (m >> j & 1) && (q_up(m, j) == i || q_down(m, j) == i)) fed += q_n(j) / 2;
    full &= q_room(m, i) + fed == q_n(i);
  }
  expect(full, "every round: its new clubs and those sent to it make its size");
  for (int y = 2026; y <= 2030; y++) {
    g_test_year = y; g_qr_sy = -1;
    uint32_t a = qr_day(3, 0), b = qr_day(3, 1);
    char buf[2][40];
    printf("  %d: first rounds %s and %s, Q2 %u/%u, Q3 %u/%u, play-offs %u/%u\n", y, dstr(a, buf[0], 40), dstr(b, buf[1], 40),
           qr_day(2, 0), qr_day(2, 1), qr_day(1, 0), qr_day(1, 1), qr_day(0, 0), qr_day(0, 1));
    expect(a >= 186 && a <= 192 && b == a + 7 && b < 216, "UCL and UEL Q1: two Wednesdays in July, before the build");
    expect(q_fill_from(m, 7) >= 217 && q_fill_from(m, 8) >= 217 && q_fill_from(m, 6) >= 217, "the second rounds after the build");
    expect(q_fill_from(m, 1) > qr_day(1, 1) && q_fill_from(m, 2) > qr_day(1, 1) && q_fill_from(m, 1) < qr_day(0, 0),
           "the play-offs of 32 filled between the third rounds and their first leg");
  }
  g_test_year = 2026; g_qr_sy = -1;
  {
    uint32_t tab[PO_SLOTS]; uint32_t* keep = g_po_tab;
    g_po_tab = tab; po_fill(); g_po_tab = keep;
    int h1 = 0, h2 = 0;
    for (int i = 0; i < PO_SLOTS; i++) { h1 |= tab[i] == 531; h2 |= tab[i] == 532; }
    expect(h1 && h2 && tab[0] == UEL_PO && tab[1] == UECL_PO, "the match titles' play-off table has 531 and 532 (and 188, 189)");
  }

  printf("\nFL27, Prijedlog C: the access list, second season\n");
  setup();
  g_log_len = 0; g_log[0] = 0;
  int ok = access_build(1, m);
  unsigned tot = 0;
  printf("  %u / %u / %u direct; rounds:", g_nacc[0], g_nacc[1], g_nacc[2]);
  for (int i = 0; i < NQR; i++) if (m >> i & 1) { printf(" %d=%u", i, g_nq[i]); tot += g_nq[i]; }
  printf("\n");
  expect(ok && g_nacc[0] == 28 && g_nacc[1] == 12 && g_nacc[2] == 4, "28 / 12 / 4 direct entrants");
  int rooms = 1;
  for (int i = 0; i < NQR; i++) if (m >> i & 1) rooms &= g_nq[i] == q_room(m, i);
  expect(rooms && tot == 112, "every round has its new clubs: 112");
  int po8 = 1;
  for (int li = 0; li < 5; li++) for (int r = 5; r <= 6; r++) po8 &= has_club(g_q[1], g_nq[1], club_at(li, r)) || has_club(g_acc[1], g_nacc[1], club_at(li, r));
  int spill = 0;
  for (int li = 5; li < 15; li++) spill += has_club(g_q[1], g_nq[1], club_at(li, 3));
  expect(po8 && spill == 8, "the Europa League's direct places past its 12: its play-off");
  int cl = 0;
  for (int li = 0; li < 20; li++) {
    int r = li < 5 ? 7 : 4;
    cl += has_club(g_q[5], g_nq[5], club_at(li, r)) + has_club(g_q[8], g_nq[8], club_at(li, r));
  }
  int uq = 0;
  for (int li = 55; li < 59; li++) uq += has_club(g_q[5], g_nq[5], club_at(li, 1)) + has_club(g_q[8], g_nq[8], club_at(li, 1));
  expect(cl == 16 && uq == 0, "the Conference League's 16 new clubs: its direct places past its four");
  expect(has_club(g_q[9], g_nq[9], club_at(54, 1)) && has_club(g_q[10], g_nq[10], club_at(46, 3)),
         "the weakest in the July first rounds");
  expect(each_once(), "every club on one list only");
  expect(strstr(g_log, "into the Conference League's rounds") == 0, "no spill in a season with the July rounds");

  printf("\nFL27, Prijedlog C: the play-offs into the league phases\n");
  for (int p = 0; p < NQ; p++)
    for (unsigned j = 0; j < q_n(p) / 2; j++) {
      g_qwin[p][j] = CLUB(70000 + 100 * p + j); g_qlose[p][j] = CLUB(80000 + 100 * p + j);
    }
  q_place(7);
  expect(g_nacc[0] == 36 && g_nacc[1] == 36 && g_nacc[2] == 36, "36 / 36 / 36");
  int ucl = 0, uel_w = 0, uel_l = 0, uecl_w = 0, uecl_l = 0;
  for (unsigned j = 0; j < 36; j++) {
    uint32_t c = g_acc[0][j]; ucl += c >= CLUB(70000) && c < CLUB(70100);
    c = g_acc[1][j]; uel_w += c >= CLUB(70100) && c < CLUB(70200); uel_l += c >= CLUB(80000) && c < CLUB(80100);
    c = g_acc[2][j]; uecl_w += c >= CLUB(70200) && c < CLUB(70300); uecl_l += c >= CLUB(80100) && c < CLUB(80200);
  }
  expect(ucl == 8, "UCL: 28 direct + 8 play-off winners");
  expect(uel_w == 16 && uel_l == 8, "UEL: 12 direct + 8 UCL play-off losers + 16 UEL play-off winners");
  expect(uecl_w == 16 && uecl_l == 16, "UECL: 4 direct + 16 UEL play-off losers + 16 UECL play-off winners");

  printf("\nFL27, Prijedlog C: a first season (no July rounds)\n");
  int m1 = m & ~(1 << 9 | 1 << 10);
  setup();
  g_log_len = 0; g_log[0] = 0;
  ok = access_build(1, m1);
  tot = 0;
  printf("  %u / %u / %u direct; rooms / clubs:", g_nacc[0], g_nacc[1], g_nacc[2]);
  for (int i = 0; i < NQR; i++) if (m1 >> i & 1) { printf(" %d=%u/%u", i, q_room(m1, i), g_nq[i]); tot += g_nq[i]; }
  printf("\n");
  expect(q_room(m1, 6) == 32 && q_room(m1, 7) == 16 && q_room(m1, 8) == 32, "the second rounds take all their clubs new: 32 / 16 / 32");
  rooms = 1;
  for (int i = 0; i < NQR; i++) if (m1 >> i & 1) rooms &= g_nq[i] == q_room(m1, i);
  expect(rooms && tot == 112, "every round full, 112 again");
  int down = 0;                                     /* the access list's last 16 Champions League places */
  for (int li = 45; li < 55; li++) down += has_club(g_q[8], g_nq[8], club_at(li, 1));
  for (int li = 13; li < 19; li++) down += has_club(g_q[8], g_nq[8], club_at(li, 2));
  expect(down == 16 && !has_club(g_q[8], g_nq[8], club_at(44, 1)), "the access list's last 16 Champions League places into the UECL Q2");
  int down2 = 0;
  for (int li = 39; li < 47; li++) down2 += has_club(g_q[8], g_nq[8], club_at(li, 3));
  expect(down2 == 8, "the 8 weakest Europa League places into the UECL Q2");
  expect(strstr(g_log, "24 qualifying place(s) into the Conference League's rounds") != 0, "the log says so");
  expect(each_once(), "every club on one list only");
  g_log_len = 0; g_log[0] = 0;

  printf("\nFL27, Prijedlog C: the Europa League Q1's result kept, a restart\n");
  g_user_test = CLUB(9002);
  g_today_test = 196; g_year_now = 2027; abs_day();
  q1kept_t* K = &g_q1kept[1];
  K->gdate = game_date();
  for (int j = 0; j < 8; j++) { K->win[j] = club_at(20 + j, 3); K->lose[j] = club_at(30 + j, 3); }
  state_store();
  expect(q1_kept(1), "kept on day 196");
  memset(g_q1kept, 0, sizeof g_q1kept);
  g_year_off = 0; g_last_day = -1; g_timeline = 0;
  g_st_off = g_st_day = -0x7fffffff; g_st_user = 0; g_st_busy = 0; g_st_read_back = 0;
  g_today_test = 220; abs_day();
  expect(q1_kept(1) && g_q1kept[1].win[7] == club_at(27, 3) && g_q1kept[1].lose[0] == club_at(30, 3),
         "read back after a restart: eight winners, eight losers");
  g_qmask = m; g_q_day = abs_day();
  int r = q_result(10);
  expect(r == 1 && g_qwin[10][2] == club_at(22, 3) && g_qlose[10][5] == club_at(35, 3), "q_result answers the kept result");
  g_native_uefa = 0;
  expect(!qc_world() && !q1_kept(1), "FL26 has none of it");
  g_native_uefa = 1;

  printf("\nFL27: one play-off line only\n");
  static const uint16_t ONE[2][3] = { { 11, 0, 531 }, { 11, 3, 501 } };
  g_log_len = 0; g_log[0] = 0;
  lines(ONE, 2);
  expect(!qc_world() && !g_qreg[1] && q_reg(1) == UEL_PO && strstr(g_log, "for one competition only") != 0,
         "left out: 188 plays the play-off");
  static const uint16_t BAD[3][3] = { { 10, 0, 533 }, { 11, 0, UEL_PO }, { 12, 0, 534 } };
  lines(BAD, 3);
  expect(!g_qreg[0] && !qc_world(), "no play-off line for the Champions League (reg 2) nor naming 188");
}
#endif

int main(void)
{
  snprintf(g_path_test, sizeof g_path_test, "%sfl26swiss-qc-test-%lu.bin", getenv("TEMP") ? getenv("TEMP") : ".",
           GetCurrentProcessId());
  DeleteFileA(g_path_test);
  setvbuf(stdout, NULL, _IONBF, 0);
  g_day_ticked = 1;                                  /* not a new career: no first-season list */
  abs_day();
  same_part();
#ifdef FL26_PRIJEDLOG_C
  c_part();
#endif
  DeleteFileA(g_path_test);
  if (fails) { printf("\n--- log ---\n%s\n%d check(s) FAILED\n", g_log, fails); return 1; }
  printf("\nall checks passed\n");
  return 0;
}
