/* Title leagues (fl26swiss.c, "title leagues"): a split league whose title is a final of two cups'
   (an Apertura/Clausura grand final), any number of them in one world.

     zig cc -O2 -fno-sanitize=undefined test_grand_final.c -o test_grand_final.exe && test_grand_final.exe

   (tools/test_grand_final.py builds and runs it, on Linux and macOS with tools/native/hosttest.)
   Exit code 1 on any failure. The world of the test: two Apertura/Clausura leagues, each with its
   two play-offs (adv=1) and its grand final (src=), and a Scottish split with no final. The cases:
     - fl26_swiss_title_league takes both finals' competitions and the two leagues fed by a final;
       the split with none keeps its own title (not a title league); the first one is g_tl_total;
     - grand_final_of: each league its own final, not the other's (the last final of the world was
       every league's before);
     - league_champion_kept: the grand final's winner; the club that won both feeding finals when
       there was none; nobody when the two were different clubs and the final is not played, or
       the wins are too old; each league its own champion. */
#define FL26_RCAL_TEST
#define FL26_STATE_TEST
#include "fl26swiss.c"
#include <stdio.h>
#include <string.h>

int rcal_test_today(void) { return 100; }
int rcal_test_invites(int k, uint16_t id) { (void)k; (void)id; return 0; }
int rcal_test_recday(uint16_t id) { (void)id; return -1; }
int state_test_date(void) { return 2026 * 365 + 100; }
uint32_t state_test_user(void) { return 0x45ed8006u; }
const char* state_test_path(void) { return "fl26swiss-test-grand-final-none.bin"; }

static int fails = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

static int cup(uint16_t reg, uint16_t ko, uint16_t first, uint8_t adv, uint16_t s0, uint16_t s1)
{
  ccup_t* c = &g_ccup[g_nccup];
  memset(c, 0, sizeof *c);
  c->reg = reg; c->ko = ko; c->n = 2; c->ereg[0] = first; c->erank[0] = 1; c->adv = adv;
  c->groups = adv ? 2 : 0; c->src[0] = s0; c->src[1] = s1;
  return g_nccup++;
}
static void win(uint16_t ko, int day, uint32_t club)
{
  cupwin_t* w = cupwin_of(ko);
  if (!w) { w = &g_cupwin[g_ncupwin++]; w->reg = ko; }
  w->day = day; w->club = club;
}

#define A 0x45ed8006u
#define B 0x45ec400du
#define C 0x45ee4002u

int main(void)
{
  /* splits: total, regular, groups */
  split_t s1 = { 11, 191, { 192, 0, 0 } }, s2 = { 12, 193, { 194, 0, 0 } }, s3 = { 13, 195, { 196, 197, 0 } };
  SPLITS[0] = s1; SPLITS[1] = s2; SPLITS[2] = s3; g_nsplits = 3;
  cup(257, 258, 191, 1, 0, 0); cup(259, 260, 192, 1, 0, 0);
  int f1 = cup(261, 261, 191, 0, 258, 260);
  cup(262, 263, 193, 1, 0, 0); cup(264, 265, 194, 1, 0, 0);
  int f2 = cup(266, 266, 193, 0, 263, 265);
  uint16_t v[] = { 261, 135, 266, 136, 11, 130, 12, 131, 13, 132 };

  printf("fl26_swiss_title_league\n");
  int got = fl26_swiss_title_league(v, 5);
  expect(got == 4, "both finals and both leagues taken, the Scottish split left out");
  expect(g_ccup_fcid[f1] == 135 && g_ccup_fcid[f2] == 136, "each final its own competition");
  expect(is_title_league(11) && is_title_league(12) && !is_title_league(13), "11 and 12 are title leagues, 13 is not");
  expect(g_tl_total == 11 && g_tl_cid == 130, "the first one is g_tl_total");
  expect(fl26_swiss_title_league(v + 4, 1) == 0 && g_ntl == 2, "named again: left out");

  printf("grand_final_of\n");
  expect(grand_final_of(11) == f1 && grand_final_of(12) == f2, "each league its own final");
  expect(grand_final_of(13) == -1 && grand_final_of(99) == -1, "a split with none, an unknown league: -1");

  printf("league_champion_kept\n");
  int ad = 2026 * 365 + 170;
  expect(league_champion_kept(11, ad) == 0, "nothing played: none");
  win(258, ad - 60, A); win(260, ad - 5, B);
  expect(league_champion_kept(11, ad) == 0, "two different finals' winners, no grand final yet: none");
  win(261, ad - 1, B);
  expect(league_champion_kept(11, ad) == B, "the grand final's winner");
  win(263, ad - 60, C); win(265, ad - 5, C);
  expect(league_champion_kept(12, ad) == C, "the other league: the club that won both finals");
  expect(league_champion_kept(12, ad + 400) == 0, "wins of more than 300 days ago: none");
  expect(league_champion_kept(13, ad) == 0, "a league with no final: none");

  printf(fails ? "%d check(s) FAILED\n" : "all checks passed\n", fails);
  return fails ? 1 : 0;
}
