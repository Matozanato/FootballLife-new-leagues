/* Offline check of the league-phase draw's association rule (fl26swiss_draw.h), no game needed.
 *
 *   zig cc -O2 -o swissdraw_test.exe swissdraw_test.c && swissdraw_test.exe [runs] [seed]
 *
 * Runs `runs` random fields (default 1000) through the same search the DLL runs, for the 36-club
 * table (8 opponents, pots of nine) and the Conference League's (6 opponents, pots of six), and
 * checks the result independently of the search's own cost: no club meets its own association,
 * no club meets more than two of one other association. The fields are shaped like real ones:
 * a few strong associations with up to six clubs, mostly in the top pots, and a long tail of
 * associations with one or two. Some fields cannot be drawn at all under the two rules (see the
 * counting bound in main); those are counted apart, and a conflict left in one of them is not a
 * failure. Exit code 1 if any other draw is left with a conflict. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fl26swiss_table.h"
#include "fl26swiss_draw.h"

static uint64_t rs;
static uint32_t rnd(void) { rs = rs * 6364136223846793005ull + 1442695040888963407ull; return (uint32_t)(rs >> 33); }
static double frnd(void) { return rnd() / 2147483648.0; }

/* n clubs in pot order: association a (0..29) is picked with weight max(0.3, 7 - 0.6a), capped
   at 6/5/4/3/2 clubs (England had six in 2025/26); the strength that orders the field favours
   the low (strong) associations, with enough spread that a big association reaches every pot */
static void field(int n, uint32_t* clubs, int* key)
{
  double st[DRAW_MAXCLUBS]; int cnt[30] = { 0 }, have = 0;
  double wsum = 0, w[30];
  for (int a = 0; a < 30; a++) { w[a] = 7.0 - 0.6 * a; if (w[a] < 0.3) w[a] = 0.3; wsum += w[a]; }
  while (have < n) {
    double x = frnd() * wsum; int a = 0;
    while (a < 29 && x >= w[a]) { x -= w[a]; a++; }
    int cap = a < 1 ? 6 : a < 4 ? 5 : a < 6 ? 4 : a < 10 ? 3 : 2;
    if (cnt[a] >= cap) continue;
    cnt[a]++;
    st[have] = frnd() * 4 + (30 - a) / 6.0; key[have] = a + 1; have++;
  }
  for (int i = 0; i < n; i++)                         /* strongest first */
    for (int j = i + 1; j < n; j++)
      if (st[j] > st[i]) { double t = st[i]; st[i] = st[j]; st[j] = t; int k = key[i]; key[i] = key[j]; key[j] = k; }
  for (int i = 0; i < n; i++) clubs[i] = (1 + rnd() % 80000) << 14;
}

static void check(const int* key, const uint8_t* perm, int n, const fl26_pair_t* table, int npairs,
                  int* same, int* third)
{
  int opp[DRAW_MAXCLUBS][8], no[DRAW_MAXCLUBS]; memset(no, 0, sizeof no);
  for (int k = 0; k < npairs; k++) {
    int h = table[k].home, a = table[k].away;
    if (h >= n || a >= n) continue;
    int ch = perm[h], ca = perm[a];
    if (no[ch] < 8) opp[ch][no[ch]++] = key[ca];
    if (no[ca] < 8) opp[ca][no[ca]++] = key[ch];
  }
  *same = *third = 0;
  for (int i = 0; i < n; i++)
    for (int j = 0; j < no[i]; j++) {
      if (opp[i][j] == key[i]) (*same)++;
      int c = 0, first = 1;
      for (int q = 0; q < no[i]; q++) { if (opp[i][q] == opp[i][j]) { c++; if (q < j) first = 0; } }
      if (first && c > 2) (*third)++;
    }
  *same /= 2;
}

int main(int argc, char** argv)
{
  int runs = argc > 1 ? atoi(argv[1]) : 1000;
  rs = argc > 2 ? strtoull(argv[2], 0, 10) : 2026;
  int bad_all = 0;
  for (int six = 0; six < 2; six++) {
    const fl26_pair_t* table = six ? FL26_SWISS6 : FL26_SWISS36;
    int npairs = six ? FL26_SWISS6_PAIRS : FL26_SWISS36_PAIRS, pot = six ? 6 : 9;
    int ok = 0, reshuffled = 0, maxtries = 0, impossible = 0, n = 36;
    long long tries_sum = 0;
    for (int r = 0; r < runs; r++) {
      uint32_t clubs[DRAW_MAXCLUBS]; int key[DRAW_MAXCLUBS]; uint8_t perm[DRAW_MAXCLUBS];
      field(n, clubs, key);
      int before, tries, same, third;
      int left = draw_spread(key, clubs, n, table, npairs, pot, perm, &before, &tries);
      check(key, perm, n, table, npairs, &same, &third);
      /* perm must still be a permutation that keeps every club in its pot */
      int seen[DRAW_MAXCLUBS] = { 0 };
      for (int i = 0; i < n; i++) {
        if (perm[i] / pot != i / pot || seen[perm[i]]++) { printf("perm broken, run %d\n", r); return 2; }
      }
      if (before) reshuffled++;
      if (tries > maxtries) maxtries = tries;
      tries_sum += tries;
      /* A field no draw can satisfy, by counting: every club of association A meets `per` clubs
         of each pot, so the clubs of pot P outside A absorb per * |A| meetings with A, and none
         of them may take more than two -- per * |A| <= 2 * (pot - |A in P|). And no more than
         half a pot of one association (the pot's own matches are cycles). */
      int crowded = 0, per = six ? 1 : 2;
      for (int p = 0; p * pot < n && !crowded; p++)
        for (int i = p * pot; i < p * pot + pot && !crowded; i++) {
          int c = 0, all = 0;
          for (int j = p * pot; j < p * pot + pot; j++) c += key[j] == key[i];
          for (int j = 0; j < n; j++) all += key[j] == key[i];
          if (c > pot / 2 || per * all > 2 * (pot - c)) crowded = 1;
        }
      if (crowded) { impossible++; if (same || third) continue; }
      if (!same && !third) ok++;
      else {
        bad_all++;
        if (bad_all <= 10) {
          printf("  conflict left: run %d, %d same-association pair(s), %d third opponent(s) (cost %d); pots:",
                 r, same, third, left);
          for (int i = 0; i < n; i++) printf("%s%d", i % pot ? "," : " | ", key[i]);
          printf("\n");
        }
      }
      if ((left == 0) != (!same && !third)) { printf("cost and check disagree, run %d\n", r); return 2; }
    }
    printf("%s: %d/%d draws with no conflict (%d fields no draw can satisfy); %d needed a reshuffle; "
           "repair steps: avg %lld, max %d\n", six ? "Conference League (6 pots of 6)" : "36 clubs (4 pots of 9)",
           ok, runs, impossible, reshuffled, tries_sum / (runs ? runs : 1), maxtries);
  }
  return bad_all ? 1 : 0;
}
