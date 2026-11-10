/* A league's first season with nobody abroad (fl26swiss.c, "firstabroad"): the slots of a
   pre-round that league would fill go to the next clubs of the round's other leagues.

     zig cc -O2 -fno-sanitize=undefined test_first_season.c -o test_first_season.exe && test_first_season.exe

   (tools/test_first_season.py builds and runs it, on Linux and macOS with tools/native/hosttest.)
   Exit code 1 on any failure. The world of the test: a pre-round with two places of league 11 (the
   one with no club abroad yet), two of league 29 and two of league 30, and a cup that takes league
   30's fifth. The cases:
     - abroad_last: a league's last place abroad, over every pre-round's and every cup's entries;
     - first_sub: the round's other leagues in turn, in the order of its entries, each its next club
       after that place; a club already in this round or in another one passed over; a round with no
       other league: nobody;
     - fl26_swiss_firstabroad: the league of the world file's `firstabroad <reg> 0` line, none without
       one; first_noabroad answers nothing for a league that is not the January-December title one. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int rcal_test_today(void) { return 100; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return 2026 * 365 + 100; }
uint32_t state_test_user(void) { return 0x45ed8006u; }
const char* state_test_path(void) { return "fl26swiss-test-first-season-none.bin"; }

#define CLUB(i) ((uint32_t)(i) << 14 | 0x1000)

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}
/* the league's table as the DLL keeps it: clubs first, first + 1, ... */
static void table(uint16_t reg, int first, int n)
{
  final_t* f = &g_final[g_nfinal++];
  f->reg = reg; f->n = (uint16_t)n; f->day = abs_day();
  for (int k = 0; k < n; k++) f->club[k] = CLUB(first + k);
}

int main(void)
{
  /* no game: an empty image, so the team lookup is "not where it was" and club values stand */
  g_base = (uintptr_t)calloc(1, TEAMLOOK_SITE + 64);
  state_sync();
  memset(g_final, 0, sizeof g_final); g_nfinal = 0;
  table(29, 2900, 20);
  table(30, 3000, 20);
  lpre_t* l = &g_lpre[0];
  memset(l, 0, sizeof *l);
  l->reg = 264; l->ties = 3;
  uint16_t er[] = { 11, 11, 29, 29, 30, 30 }; uint8_t rk[] = { 5, 6, 3, 4, 2, 3 };
  for (int e = 0; e < 6; e++) { l->ereg[e] = er[e]; l->erank[e] = rk[e]; }
  lpre_t* l2 = &g_lpre[1];
  memset(l2, 0, sizeof *l2);
  l2->reg = 267; l2->ties = 1; l2->ereg[0] = 29; l2->erank[0] = 1; l2->ereg[1] = 32917; l2->erank[1] = 4;
  g_nlpre = 2;
  ccup_t* c = &g_ccup[0];
  memset(c, 0, sizeof *c);
  c->reg = 257; c->ko = 258; c->n = 1; c->ereg[0] = 30; c->erank[0] = 5;
  g_nccup = 1;

  printf("abroad_last\n");
  expect(abroad_last(29) == 4, "league 29: its fourth, in the pre-round");
  expect(abroad_last(30) == 5, "league 30: its fifth, in the cup");
  expect(abroad_last(99) == 0, "a league with no place abroad: 0");

  printf("first_sub\n");
  const char* how = "";
  uint32_t a = first_sub(0, 11, 0, 0, &how);
  expect(a == CLUB(2904), "the first slot: league 29's next club after its fourth");
  expect(strcmp(how, "reg 29 position 5") == 0, "and the log says where it came from");
  l->club[0] = a;
  uint32_t b = first_sub(0, 11, 1, 1, &how);
  expect(b == CLUB(3005), "the second: league 30's, after its fifth in the cup");
  l->club[1] = b;
  expect(first_sub(0, 11, 2, 2, &how) == CLUB(2905), "a third: league 29 again, its club in the round passed over");
  l2->club[0] = CLUB(2905); l2->nclub = 1;
  expect(first_sub(0, 11, 2, 2, &how) == CLUB(2906), "a club already in another round passed over");
  expect(first_sub(1, 29, 0, 0, &how) == 0, "a round with no other league: nobody");

  printf("fl26_swiss_firstabroad\n");
  expect(g_noabroad_reg == 0 && !first_noabroad(11), "no line: no league");
  uint16_t v[] = { 11 };
  expect(fl26_swiss_firstabroad(v, 1) == 1 && g_noabroad_reg == 11, "the line's league taken");
  expect(!first_noabroad(11), "not the January-December title league: its first season goes as any league's");
  expect(fl26_swiss_firstabroad(v, 0) == 0 && g_noabroad_reg == 0, "no record: none");

  printf(fails ? "%d check(s) FAILED\n" : "all checks passed\n", fails);
  return fails ? 1 : 0;
}
