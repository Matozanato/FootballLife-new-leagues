/* B243: the modern Sudamericana's group draw keeps clubs of one association apart.

     zig cc -O2 -fno-sanitize=undefined test_potdraw.c -o test_potdraw.exe && test_potdraw.exe

   (tools/test_potdraw.py builds and runs it.) Exit code 1 on any failure.

   pot_draw from fl26swiss.c without the game (FL26_RCAL_TEST). The cases, each drawn many times:
     - a Sudamericana field of 32 (four pots of eight) with six Argentine and six Brazilian clubs
       spread over the pots, the rest from eight other associations: every draw has one club of
       every pot in each group, every club once, and no two clubs of one association in a group
       (antonimus, 26.10.: Velez and Argentinos Juniors in group 7);
     - Argentina with two clubs in each pot (eight in all): still no group with two;
     - nine clubs of one association in 32 places: no draw can keep them apart, and the one that
       stands has a single pair, not more;
     - a field of one association only (nothing to keep apart): the draw is still whole. */
#define FL26_RCAL_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <stdlib.h>

static int g_today_test = 0;
int rcal_test_today(void) { return g_today_test; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

#define CLUB(i) ((uint32_t)(i) << 14 | 0x1000)

/* every club once, one of every pot in each group; returns the same-association pairs */
static int check(const uint32_t* field, const int* key, uint32_t grp[CCUP_MAX_GROUPS][8], int* whole)
{
  int seen[32] = { 0 }, pairs = 0;
  *whole = 1;
  for (int g = 0; g < 8; g++)
    for (int pot = 0; pot < 4; pot++) {
      int e = -1;
      for (int i = 0; i < 32; i++) if (field[i] == grp[g][pot]) e = i;
      if (e < 0 || e / 8 != pot || seen[e]++) *whole = 0;
      for (int q = 0; q < pot && e >= 0; q++)
        for (int i = 0; i < 32; i++)
          if (field[i] == grp[g][q] && key[i] == key[e]) pairs++;
    }
  return pairs;
}

static void run(const char* name, const int* key, int want_pairs, int runs)
{
  uint32_t field[32], grp[CCUP_MAX_GROUPS][8];
  for (int i = 0; i < 32; i++) field[i] = CLUB(100 + i);
  int whole_all = 1, worst = 0, said = 0, tries_max = 0;
  for (int r = 0; r < runs; r++) {
    int tries = 0, whole;
    int best = pot_draw(field, key, 32, 8, grp, &tries);
    int pairs = check(field, key, grp, &whole);
    if (!whole) whole_all = 0;
    if (pairs != best && !said) { said = 1; printf("    pot_draw said %d pair(s), the groups hold %d\n", best, pairs); }
    if (pairs > worst) worst = pairs;
    if (tries > tries_max) tries_max = tries;
  }
  char buf[200];
  snprintf(buf, sizeof buf, "%s: %d draws whole (one club of every pot per group, every club once)", name, runs);
  expect(whole_all, buf);
  snprintf(buf, sizeof buf, "%s: at most %d same-association pair(s) (worst %d; up to %d draws tried)",
           name, want_pairs, worst, tries_max);
  expect(worst <= want_pairs && !said, buf);
}

int main(void)
{
  int key[32];
  /* pots of eight: ARG 3+1+1+1, BRA 2+2+1+1, the rest one per association and pot */
  static const int sud[32] = {
    1, 1, 1, 2, 2, 3, 4, 5,      /* pot 1 */
    1, 2, 2, 3, 4, 5, 6, 7,      /* pot 2 */
    1, 2, 3, 4, 5, 6, 7, 8,      /* pot 3 */
    1, 2, 3, 4, 6, 7, 9, 10 };   /* pot 4: the Libertadores F3 losers and the first stage's */
  run("Sudamericana field (6 ARG, 6 BRA)", sud, 0, 2000);

  for (int i = 0; i < 32; i++) key[i] = 20 + i;
  for (int pot = 0; pot < 4; pot++) key[pot * 8] = key[pot * 8 + 1] = 1;
  run("two Argentine clubs in every pot", key, 0, 2000);

  for (int i = 0; i < 32; i++) key[i] = 20 + i;
  static const int nine[9] = { 0, 1, 8, 9, 16, 17, 24, 25, 26 };
  for (int i = 0; i < 9; i++) key[nine[i]] = 1;
  run("nine clubs of one association", key, 1, 500);

  for (int i = 0; i < 32; i++) key[i] = 1;
  run("one association only", key, 48, 200);

  if (fails) { printf("%d check(s) FAILED\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
