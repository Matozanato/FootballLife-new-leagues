/* B315 (huliaanos, 03.11.): promotion and relegation between calendar-year leagues of ours, done
   by fl26join at the New Year teardown (cal_swap, the part that touches no game memory).

     zig cc -O2 -fno-sanitize=undefined test_cal_exchange.c -o test_cal_exchange.exe && test_cal_exchange.exe

   (tools/test_cal_exchange.py builds and runs it.) Exit code 1 on any failure.

   Finland as huliaanos built it, the clubs numbered by league and final rank: 11 (12 clubs,
   2 down), 49 (10, 2 up and 2 down), 60 (12, 2 up and 3 down), 61 (18, 3 up), every season
   played in full. The pairs go top-down, each on the lists the pair above left:
     - the last two of 11 and the first two of 49 change places, then 49's last two and 60's
       first two, then 60's last three and 61's first three; every league keeps its size and
       every club is in one league;
     - a club of the lower league that may not go up (a reserve side) is passed over for the
       next one, and with too few that may, nobody moves (the mover's rule);
     - a club a match or two short (a postponed match never played) does not hold the league
       back; a table that is not a whole season (a club at half of it, or with none) moves nobody;
     - a club not in the league its table says (the lists already changed) moves nobody. */
#define FL26_JOIN_TEST
#include "fl26join.c"
#include <stdio.h>

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

#define CLUB(league, rank) ((uint32_t)((league) * 100 + (rank)) << 14)
static const uint16_t LG[4] = { 11, 49, 60, 61 };
static const int NCLUBS[4] = { 12, 10, 12, 18 }, XCH[3] = { 2, 2, 3 };
static uint32_t g_tab[4][CAL_MAXCLUBS], g_lst[4][CAL_MAXCLUBS];
static uint8_t g_pld[4][CAL_MAXCLUBS];
static int g_n[4];
static uint32_t g_blocked = 0, g_blocked2 = 0;
static int test_eligible(uint32_t h) { return h != g_blocked && h != g_blocked2; }

static void setup(void)
{
  for (int l = 0; l < 4; l++) {
    g_n[l] = NCLUBS[l];
    for (int r = 0; r < NCLUBS[l]; r++) {
      g_tab[l][r] = CLUB(LG[l], r + 1);
      g_lst[l][r] = CLUB(LG[l], r + 1);
      g_pld[l][r] = (uint8_t)(l == 0 || l == 1 ? 33 : 34);
    }
    for (int r = 0; r < NCLUBS[l] / 2; r++) {         /* list order is not table order */
      uint32_t t = g_lst[l][r]; g_lst[l][r] = g_lst[l][NCLUBS[l] - 1 - r]; g_lst[l][NCLUBS[l] - 1 - r] = t;
    }
  }
}

static int pair(int l)
{
  uint32_t down[CAL_MAXCLUBS], up[CAL_MAXCLUBS];
  return cal_swap(g_tab[l], g_pld[l], NCLUBS[l], g_lst[l], &g_n[l],
                  g_tab[l + 1], g_pld[l + 1], NCLUBS[l + 1], g_lst[l + 1], &g_n[l + 1],
                  XCH[l], test_eligible, down, up);
}

static int in(int l, uint32_t c) { for (int i = 0; i < g_n[l]; i++) if (g_lst[l][i] == c) return 1; return 0; }
static int once_each(void)
{
  int total = 0;
  for (int l = 0; l < 4; l++) {
    total += g_n[l];
    for (int i = 0; i < g_n[l]; i++)
      for (int m = 0; m < 4; m++)
        for (int j = 0; j < g_n[m]; j++)
          if ((m != l || j != i) && g_lst[m][j] == g_lst[l][i]) return 0;
  }
  return total == 12 + 10 + 12 + 18;
}

int main(void)
{
  setvbuf(stdout, NULL, _IONBF, 0);

  printf("\nFour tiers, every season played\n");
  setup();
  expect(pair(0) == 2, "11<->49: two each way");
  expect(pair(1) == 2, "49<->60: two each way");
  expect(pair(2) == 3, "60<->61: three each way");
  expect(in(0, CLUB(49, 1)) && in(0, CLUB(49, 2)) && !in(0, CLUB(11, 11)) && !in(0, CLUB(11, 12)), "49's top two in 11, 11's last two gone");
  expect(in(1, CLUB(11, 11)) && in(1, CLUB(11, 12)), "11's last two in 49");
  expect(!in(1, CLUB(49, 9)) && !in(1, CLUB(49, 10)) && in(2, CLUB(49, 9)) && in(2, CLUB(49, 10)), "49's last two in 60");
  expect(in(1, CLUB(60, 1)) && in(1, CLUB(60, 2)) && !in(2, CLUB(60, 1)), "60's top two in 49");
  expect(in(2, CLUB(61, 1)) && in(2, CLUB(61, 2)) && in(2, CLUB(61, 3)) && !in(2, CLUB(61, 4)), "61's top three in 60");
  expect(in(3, CLUB(60, 10)) && in(3, CLUB(60, 11)) && in(3, CLUB(60, 12)) && !in(3, CLUB(60, 9)), "60's last three in 61");
  expect(in(1, CLUB(49, 3)) && in(1, CLUB(49, 8)), "49's middle stays");
  expect(g_n[0] == 12 && g_n[1] == 10 && g_n[2] == 12 && g_n[3] == 18, "every league keeps its size");
  expect(once_each(), "every club in one league");

  printf("\n49's second may not go up\n");
  setup(); g_blocked = CLUB(49, 2);
  expect(pair(0) == 2, "11<->49: two each way");
  expect(in(0, CLUB(49, 1)) && in(0, CLUB(49, 3)) && !in(0, CLUB(49, 2)), "the first and the third go up, the second stays");
  expect(once_each(), "every club in one league");
  g_blocked = 0;

  printf("\nToo few that may go up\n");
  setup();
  { uint32_t down[4], up[4]; int na = 2, nb = 2; uint32_t ta[2] = { 1u << 14, 2u << 14 }, la[2] = { 1u << 14, 2u << 14 };
    uint32_t tb[2] = { 3u << 14, 4u << 14 }, lb[2] = { 3u << 14, 4u << 14 }; uint8_t p[2] = { 2, 2 };
    g_blocked = 3u << 14;
    expect(cal_swap(ta, p, 2, la, &na, tb, p, 2, lb, &nb, 1, test_eligible, down, up) == 1, "one of two eligible: one moves");
    g_blocked = 0; }
  { uint32_t down[4], up[4]; int na = 3, nb = 3; uint32_t ta[3] = { 1u << 14, 2u << 14, 5u << 14 }, la[3] = { 1u << 14, 2u << 14, 5u << 14 };
    uint32_t tb[3] = { 3u << 14, 4u << 14, 6u << 14 }, lb[3] = { 3u << 14, 4u << 14, 6u << 14 }; uint8_t p[3] = { 4, 4, 4 };
    g_blocked = 3u << 14; g_blocked2 = 6u << 14;
    expect(cal_swap(ta, p, 3, la, &na, tb, p, 3, lb, &nb, 2, test_eligible, down, up) == 0, "two to go up, one eligible: nobody moves");
    expect(la[0] == (1u << 14) && la[1] == (2u << 14) && la[2] == (5u << 14) && lb[0] == (3u << 14), "both lists as they were");
    g_blocked = g_blocked2 = 0; }
  setup(); g_blocked = CLUB(49, 1);
  { uint32_t down[4], up[4];
    int r = cal_swap(g_tab[0], g_pld[0], 12, g_lst[0], &g_n[0], g_tab[1], g_pld[1], 1, g_lst[1], &g_n[1], 1, test_eligible, down, up);
    expect(r == -1 || r == 0, "a lower league of one row moves nobody"); }
  g_blocked = 0;

  printf("\nA season not played in full\n");
  setup(); g_pld[3][2] = 32; g_pld[3][15] = 32; g_pld[3][5] = 33;
  pair(0); pair(1);
  expect(pair(2) == 3, "60<->61: three clubs of 61 a match or two short (postponed), still three each way");
  setup(); g_pld[1][4] = 16;
  expect(pair(0) == -1, "11<->49: a club of 49 at half the season, nobody moves");
  expect(in(0, CLUB(11, 12)) && in(1, CLUB(49, 1)), "both lists as they were");
  setup(); g_pld[0][0] = 0;
  expect(pair(0) == -1, "a club with no match: nobody moves");

  printf("\nA list that no longer matches its table\n");
  setup(); g_lst[1][0] = CLUB(99, 1); g_lst[1][1] = CLUB(99, 2);
  for (int i = 0; i < g_n[1]; i++) if (g_lst[1][i] == CLUB(49, 1)) g_lst[1][i] = CLUB(99, 3);
  expect(pair(0) == -2, "49's champion not in 49's list: nobody moves");
  expect(in(0, CLUB(11, 12)), "11's list as it was");

  if (fails) { printf("\n%d check(s) FAILED\n", fails); return 1; }
  printf("\nall checks passed\n");
  return 0;
}
